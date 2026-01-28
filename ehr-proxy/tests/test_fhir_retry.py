"""
Tests for FHIR Retry Logic with Exponential Backoff (Issue #24)
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
import httpx


class TestFHIRRetryConfig:
    """Tests for FHIRRetryConfig"""

    def test_default_config(self):
        """Should have sensible defaults"""
        from fhir_retry import FHIRRetryConfig

        config = FHIRRetryConfig()

        assert config.max_attempts == 3
        assert config.min_wait == 2
        assert config.max_wait == 10
        assert config.multiplier == 2
        assert config.timeout == 30
        assert 429 in config.retryable_status_codes
        assert 503 in config.retryable_status_codes
        assert 400 in config.non_retryable_status_codes
        assert 401 in config.non_retryable_status_codes

    def test_custom_config(self):
        """Should accept custom values"""
        from fhir_retry import FHIRRetryConfig

        config = FHIRRetryConfig(
            max_attempts=5,
            min_wait=1,
            max_wait=30,
            timeout=60
        )

        assert config.max_attempts == 5
        assert config.min_wait == 1
        assert config.max_wait == 30
        assert config.timeout == 60

    def test_config_from_env(self):
        """Should read from environment variables when module reloads"""
        import os
        import importlib

        # Save originals
        orig_max = os.environ.get("FHIR_RETRY_MAX_ATTEMPTS")

        try:
            os.environ["FHIR_RETRY_MAX_ATTEMPTS"] = "5"
            # Reload module to pick up new env var
            import fhir_retry
            importlib.reload(fhir_retry)
            config = fhir_retry.FHIRRetryConfig()
            assert config.max_attempts == 5
        finally:
            if orig_max:
                os.environ["FHIR_RETRY_MAX_ATTEMPTS"] = orig_max
            else:
                os.environ.pop("FHIR_RETRY_MAX_ATTEMPTS", None)
            # Reload again to restore default
            import fhir_retry
            importlib.reload(fhir_retry)


class TestRetryStats:
    """Tests for RetryStats tracking"""

    def test_initial_stats(self):
        """Should start with zero stats"""
        from fhir_retry import RetryStats

        stats = RetryStats()

        assert stats.total_requests == 0
        assert stats.successful_requests == 0
        assert stats.failed_requests == 0
        assert stats.total_retries == 0
        assert stats.success_rate == 1.0

    def test_record_success(self):
        """Should track successful requests"""
        from fhir_retry import RetryStats

        stats = RetryStats()
        stats.record_success(retry_count=0)
        stats.record_success(retry_count=2)

        assert stats.total_requests == 2
        assert stats.successful_requests == 2
        assert stats.total_retries == 2
        assert stats.success_rate == 1.0

    def test_record_failure(self):
        """Should track failed requests"""
        from fhir_retry import RetryStats

        stats = RetryStats()
        stats.record_failure(retry_count=3, status_code=503)
        stats.record_failure(retry_count=3, status_code=429)

        assert stats.total_requests == 2
        assert stats.failed_requests == 2
        assert stats.total_retries == 6
        assert stats.retries_by_status[503] == 1
        assert stats.retries_by_status[429] == 1
        assert stats.success_rate == 0.0

    def test_success_rate_calculation(self):
        """Should calculate correct success rate"""
        from fhir_retry import RetryStats

        stats = RetryStats()
        stats.record_success()
        stats.record_success()
        stats.record_success()
        stats.record_failure()

        assert stats.success_rate == 0.75

    def test_to_dict(self):
        """Should export stats as dictionary"""
        from fhir_retry import RetryStats

        stats = RetryStats()
        stats.record_success()
        stats.record_failure(status_code=503)

        result = stats.to_dict()

        assert "total_requests" in result
        assert "success_rate" in result
        assert "retries_by_status" in result


class TestRetryExceptions:
    """Tests for custom retry exceptions"""

    def test_retryable_error(self):
        """Should store status code and retry_after"""
        from fhir_retry import FHIRRetryableError

        error = FHIRRetryableError("Service unavailable", status_code=503, retry_after=30)

        assert str(error) == "Service unavailable"
        assert error.status_code == 503
        assert error.retry_after == 30

    def test_non_retryable_error(self):
        """Should store status code"""
        from fhir_retry import FHIRNonRetryableError

        error = FHIRNonRetryableError("Not found", status_code=404)

        assert str(error) == "Not found"
        assert error.status_code == 404


class TestWaitTimeCalculation:
    """Tests for exponential backoff calculation"""

    def test_basic_exponential_backoff(self):
        """Should calculate exponential wait times"""
        from fhir_retry import _calculate_wait_time, FHIRRetryConfig

        config = FHIRRetryConfig(min_wait=2, multiplier=2, max_wait=10, jitter=False)

        # Attempt 0: 2 * 2^0 = 2
        wait0 = _calculate_wait_time(0, config)
        assert wait0 == 2

        # Attempt 1: 2 * 2^1 = 4
        wait1 = _calculate_wait_time(1, config)
        assert wait1 == 4

        # Attempt 2: 2 * 2^2 = 8
        wait2 = _calculate_wait_time(2, config)
        assert wait2 == 8

    def test_max_wait_cap(self):
        """Should cap at max_wait"""
        from fhir_retry import _calculate_wait_time, FHIRRetryConfig

        config = FHIRRetryConfig(min_wait=2, multiplier=2, max_wait=5, jitter=False)

        # Attempt 2: 2 * 2^2 = 8, but capped at 5
        wait = _calculate_wait_time(2, config)
        assert wait == 5

    def test_retry_after_header(self):
        """Should respect Retry-After header"""
        from fhir_retry import _calculate_wait_time, FHIRRetryConfig

        config = FHIRRetryConfig(min_wait=2, max_wait=10, jitter=False)

        # Retry-After should override calculation
        wait = _calculate_wait_time(0, config, retry_after=5)
        assert wait == 5

    def test_retry_after_capped(self):
        """Should cap Retry-After at max_wait"""
        from fhir_retry import _calculate_wait_time, FHIRRetryConfig

        config = FHIRRetryConfig(max_wait=10, jitter=False)

        # Retry-After of 30 should be capped at 10
        wait = _calculate_wait_time(0, config, retry_after=30)
        assert wait == 10

    def test_jitter_applied(self):
        """Should apply jitter when enabled"""
        from fhir_retry import _calculate_wait_time, FHIRRetryConfig

        config = FHIRRetryConfig(min_wait=2, multiplier=2, max_wait=10, jitter=True)

        # Run multiple times - should get different values
        waits = [_calculate_wait_time(0, config) for _ in range(10)]

        # Not all should be exactly the same (jitter applied)
        assert len(set(waits)) > 1


class TestShouldRetry:
    """Tests for retry decision logic"""

    def test_retryable_status_codes(self):
        """Should return True for retryable status codes"""
        from fhir_retry import _should_retry, FHIRRetryConfig

        config = FHIRRetryConfig()

        assert _should_retry(429, config) is True
        assert _should_retry(502, config) is True
        assert _should_retry(503, config) is True
        assert _should_retry(504, config) is True

    def test_non_retryable_status_codes(self):
        """Should return False for non-retryable status codes"""
        from fhir_retry import _should_retry, FHIRRetryConfig

        config = FHIRRetryConfig()

        assert _should_retry(400, config) is False
        assert _should_retry(401, config) is False
        assert _should_retry(403, config) is False
        assert _should_retry(404, config) is False
        assert _should_retry(422, config) is False

    def test_success_codes_not_retried(self):
        """Should return False for success status codes"""
        from fhir_retry import _should_retry, FHIRRetryConfig

        config = FHIRRetryConfig()

        assert _should_retry(200, config) is False
        assert _should_retry(201, config) is False
        assert _should_retry(204, config) is False


class TestRetryAfterHeader:
    """Tests for Retry-After header extraction"""

    def test_integer_retry_after(self):
        """Should parse integer Retry-After"""
        from fhir_retry import _get_retry_after

        response = MagicMock()
        response.headers = {"Retry-After": "30"}

        result = _get_retry_after(response)
        assert result == 30

    def test_missing_retry_after(self):
        """Should return None when header missing"""
        from fhir_retry import _get_retry_after

        response = MagicMock()
        response.headers = {}

        result = _get_retry_after(response)
        assert result is None

    def test_invalid_retry_after(self):
        """Should return None for invalid values"""
        from fhir_retry import _get_retry_after

        response = MagicMock()
        response.headers = {"Retry-After": "not-a-number"}

        result = _get_retry_after(response)
        assert result is None


class TestWithFHIRRetryDecorator:
    """Tests for the retry decorator"""

    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        """Should succeed without retry on first attempt"""
        from fhir_retry import with_fhir_retry, reset_stats, get_stats

        reset_stats()

        @with_fhir_retry()
        async def successful_call():
            return "success"

        result = await successful_call()

        assert result == "success"
        stats = get_stats()
        assert stats.successful_requests == 1
        assert stats.total_retries == 0

    @pytest.mark.asyncio
    async def test_retries_on_retryable_error(self):
        """Should retry on FHIRRetryableError"""
        from fhir_retry import with_fhir_retry, FHIRRetryableError, FHIRRetryConfig, reset_stats, get_stats

        reset_stats()
        call_count = 0

        config = FHIRRetryConfig(max_attempts=3, min_wait=0.01, jitter=False)

        @with_fhir_retry(config)
        async def flaky_call():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise FHIRRetryableError("Service unavailable", status_code=503)
            return "success"

        result = await flaky_call()

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_does_not_retry_non_retryable(self):
        """Should NOT retry on FHIRNonRetryableError"""
        from fhir_retry import with_fhir_retry, FHIRNonRetryableError, FHIRRetryConfig, reset_stats

        reset_stats()
        call_count = 0

        config = FHIRRetryConfig(max_attempts=3, min_wait=0.01)

        @with_fhir_retry(config)
        async def not_found_call():
            nonlocal call_count
            call_count += 1
            raise FHIRNonRetryableError("Not found", status_code=404)

        with pytest.raises(FHIRNonRetryableError):
            await not_found_call()

        # Should only be called once (no retry)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_exhausts_retries(self):
        """Should exhaust all retries then raise"""
        from fhir_retry import with_fhir_retry, FHIRRetryableError, FHIRRetryConfig, reset_stats, get_stats

        reset_stats()
        call_count = 0

        config = FHIRRetryConfig(max_attempts=3, min_wait=0.01, jitter=False)

        @with_fhir_retry(config)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise FHIRRetryableError("Always fails", status_code=503)

        with pytest.raises(FHIRRetryableError):
            await always_fails()

        assert call_count == 3
        stats = get_stats()
        assert stats.failed_requests == 1

    @pytest.mark.asyncio
    async def test_retries_on_connection_error(self):
        """Should retry on connection errors"""
        from fhir_retry import with_fhir_retry, FHIRRetryConfig, reset_stats

        reset_stats()
        call_count = 0

        config = FHIRRetryConfig(max_attempts=3, min_wait=0.01, jitter=False)

        @with_fhir_retry(config)
        async def connection_flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("Connection refused")
            return "connected"

        result = await connection_flaky()

        assert result == "connected"
        assert call_count == 2


class TestFHIRClient:
    """Tests for FHIRClient class"""

    @pytest.mark.asyncio
    async def test_get_success(self):
        """Should make successful GET request"""
        from fhir_retry import FHIRClient, FHIRRetryConfig, reset_stats

        reset_stats()
        config = FHIRRetryConfig(timeout=5)
        client = FHIRClient(config)

        # Mock the httpx client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}

        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.request = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client

            response = await client.get("https://fhir.example.com/Patient/123")

            assert response.status_code == 200
            mock_http_client.request.assert_called_once()

        await client.close()

    @pytest.mark.asyncio
    async def test_adds_retry_count_header(self):
        """Should add X-Retry-Count header"""
        from fhir_retry import FHIRClient, FHIRRetryConfig

        config = FHIRRetryConfig(timeout=5)
        client = FHIRClient(config)

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.request = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client

            await client.get("https://fhir.example.com/Patient/123", headers={"Authorization": "Bearer token"})

            call_args = mock_http_client.request.call_args
            headers = call_args.kwargs.get('headers', {})
            assert "X-Retry-Count" in headers
            assert headers["X-Retry-Count"] == "0"

        await client.close()


class TestGlobalFunctions:
    """Tests for module-level convenience functions"""

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Should return global stats instance"""
        from fhir_retry import get_stats, reset_stats

        reset_stats()
        stats = get_stats()

        assert stats.total_requests == 0

    @pytest.mark.asyncio
    async def test_reset_stats(self):
        """Should reset global stats"""
        from fhir_retry import get_stats, reset_stats

        stats = get_stats()
        stats.record_success()
        stats.record_failure()

        assert stats.total_requests == 2

        reset_stats()
        new_stats = get_stats()

        assert new_stats.total_requests == 0

    @pytest.mark.asyncio
    async def test_get_config(self):
        """Should return global config"""
        from fhir_retry import get_config

        config = get_config()

        assert config.max_attempts >= 1
        assert config.timeout > 0

    @pytest.mark.asyncio
    async def test_set_config(self):
        """Should update global config"""
        from fhir_retry import get_config, set_config, FHIRRetryConfig

        original_config = get_config()
        original_max = original_config.max_attempts

        try:
            new_config = FHIRRetryConfig(max_attempts=10)
            set_config(new_config)

            updated = get_config()
            assert updated.max_attempts == 10
        finally:
            # Restore original
            set_config(FHIRRetryConfig(max_attempts=original_max))
