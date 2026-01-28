"""
MDx Vision - FHIR API Retry Logic with Exponential Backoff

Provides resilient HTTP calls to external EHR systems (Cerner, Epic, Veradigm)
with automatic retry on transient failures.

Features:
- Exponential backoff with jitter (2s, 4s, 8s)
- Retry on transient errors: 429, 502, 503, 504, connection errors, timeouts
- NO retry on client errors: 400, 401, 403, 404
- Respects Retry-After header for 429 responses
- Configurable via environment variables
- Request tracking with X-Retry-Count header
- Comprehensive logging for debugging

Usage:
    from fhir_retry import fhir_client, FHIRRetryConfig

    # Use the pre-configured client
    response = await fhir_client.get(url, headers=headers)

    # Or use decorator for custom functions
    @with_fhir_retry()
    async def fetch_patient(patient_id: str):
        ...

Configuration (environment variables):
    FHIR_RETRY_MAX_ATTEMPTS=3
    FHIR_RETRY_MIN_WAIT=2
    FHIR_RETRY_MAX_WAIT=10
    FHIR_RETRY_MULTIPLIER=2
    FHIR_REQUEST_TIMEOUT=30
"""

import os
import asyncio
import random
import logging
import time
from typing import Optional, Callable, Any, Set
from functools import wraps
from dataclasses import dataclass, field

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
    RetryError
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FHIRRetryConfig:
    """Configuration for FHIR API retry behavior"""

    # Retry limits
    max_attempts: int = int(os.getenv("FHIR_RETRY_MAX_ATTEMPTS", "3"))

    # Backoff timing (seconds)
    min_wait: float = float(os.getenv("FHIR_RETRY_MIN_WAIT", "2"))
    max_wait: float = float(os.getenv("FHIR_RETRY_MAX_WAIT", "10"))
    multiplier: float = float(os.getenv("FHIR_RETRY_MULTIPLIER", "2"))

    # Request timeout
    timeout: float = float(os.getenv("FHIR_REQUEST_TIMEOUT", "30"))

    # Status codes that should trigger retry
    retryable_status_codes: Set[int] = field(default_factory=lambda: {429, 502, 503, 504})

    # Status codes that should NOT retry (client errors)
    non_retryable_status_codes: Set[int] = field(default_factory=lambda: {400, 401, 403, 404, 422})

    # Add jitter to prevent thundering herd
    jitter: bool = True
    jitter_range: tuple = (0.5, 1.5)


# Global config instance
_config = FHIRRetryConfig()


def get_config() -> FHIRRetryConfig:
    """Get the current retry configuration"""
    return _config


def set_config(config: FHIRRetryConfig) -> None:
    """Set a new retry configuration"""
    global _config
    _config = config


# ═══════════════════════════════════════════════════════════════════════════════
# Retry Statistics
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RetryStats:
    """Track retry statistics for monitoring"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_retries: int = 0
    retries_by_status: dict = field(default_factory=dict)
    last_retry_at: Optional[float] = None

    def record_success(self, retry_count: int = 0) -> None:
        """Record a successful request"""
        self.total_requests += 1
        self.successful_requests += 1
        self.total_retries += retry_count

    def record_failure(self, retry_count: int = 0, status_code: Optional[int] = None) -> None:
        """Record a failed request"""
        self.total_requests += 1
        self.failed_requests += 1
        self.total_retries += retry_count
        if status_code:
            self.retries_by_status[status_code] = self.retries_by_status.get(status_code, 0) + 1

    def record_retry(self, status_code: Optional[int] = None) -> None:
        """Record a retry attempt"""
        self.total_retries += 1
        self.last_retry_at = time.time()
        if status_code:
            self.retries_by_status[status_code] = self.retries_by_status.get(status_code, 0) + 1

    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    def to_dict(self) -> dict:
        """Export stats as dictionary"""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "total_retries": self.total_retries,
            "success_rate": round(self.success_rate, 4),
            "retries_by_status": self.retries_by_status,
            "last_retry_at": self.last_retry_at,
        }


# Global stats instance
_stats = RetryStats()


def get_stats() -> RetryStats:
    """Get retry statistics"""
    return _stats


def reset_stats() -> None:
    """Reset retry statistics"""
    global _stats
    _stats = RetryStats()


# ═══════════════════════════════════════════════════════════════════════════════
# Custom Exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class FHIRRetryableError(Exception):
    """Exception raised for transient FHIR errors that should be retried"""

    def __init__(self, message: str, status_code: Optional[int] = None,
                 retry_after: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class FHIRNonRetryableError(Exception):
    """Exception raised for FHIR errors that should NOT be retried"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


# ═══════════════════════════════════════════════════════════════════════════════
# Retry Logic Implementation
# ═══════════════════════════════════════════════════════════════════════════════

def _calculate_wait_time(attempt: int, config: FHIRRetryConfig,
                         retry_after: Optional[int] = None) -> float:
    """Calculate wait time with exponential backoff and optional jitter"""
    if retry_after is not None:
        # Respect Retry-After header
        return min(retry_after, config.max_wait)

    # Exponential backoff
    wait = min(config.min_wait * (config.multiplier ** attempt), config.max_wait)

    # Add jitter
    if config.jitter:
        jitter_factor = random.uniform(*config.jitter_range)
        wait *= jitter_factor

    return wait


def _should_retry(status_code: int, config: FHIRRetryConfig) -> bool:
    """Determine if a status code should trigger a retry"""
    if status_code in config.non_retryable_status_codes:
        return False
    return status_code in config.retryable_status_codes


def _get_retry_after(response: httpx.Response) -> Optional[int]:
    """Extract Retry-After header value (in seconds)"""
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return int(retry_after)
        except ValueError:
            # Retry-After might be a date, ignore for now
            pass
    return None


async def _handle_response(response: httpx.Response, attempt: int) -> httpx.Response:
    """
    Check response and raise appropriate exception for retry logic.

    Args:
        response: The HTTP response
        attempt: Current attempt number (0-indexed)

    Returns:
        The response if successful

    Raises:
        FHIRRetryableError: For transient errors that should be retried
        FHIRNonRetryableError: For client errors that should not be retried
    """
    config = get_config()
    status = response.status_code

    if 200 <= status < 300:
        return response

    # Check if retryable
    if _should_retry(status, config):
        retry_after = _get_retry_after(response)
        _stats.record_retry(status)

        logger.warning(
            f"FHIR API returned {status}, will retry (attempt {attempt + 1}/{config.max_attempts})",
            extra={
                "status_code": status,
                "attempt": attempt + 1,
                "retry_after": retry_after,
                "url": str(response.url),
            }
        )

        raise FHIRRetryableError(
            f"FHIR API returned retryable status {status}",
            status_code=status,
            retry_after=retry_after
        )

    # Non-retryable error
    logger.error(
        f"FHIR API returned non-retryable error {status}",
        extra={"status_code": status, "url": str(response.url)}
    )
    raise FHIRNonRetryableError(
        f"FHIR API returned {status}",
        status_code=status
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Retry Decorator
# ═══════════════════════════════════════════════════════════════════════════════

def with_fhir_retry(config: Optional[FHIRRetryConfig] = None):
    """
    Decorator to add FHIR retry logic to async functions.

    Usage:
        @with_fhir_retry()
        async def fetch_patient(patient_id: str):
            response = await httpx.get(f"/Patient/{patient_id}")
            return response.json()

        # Or with custom config
        @with_fhir_retry(FHIRRetryConfig(max_attempts=5))
        async def critical_fetch():
            ...
    """
    cfg = config or get_config()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            attempt = 0
            last_exception = None

            while attempt < cfg.max_attempts:
                try:
                    result = await func(*args, **kwargs)
                    _stats.record_success(retry_count=attempt)
                    return result

                except FHIRRetryableError as e:
                    last_exception = e
                    attempt += 1

                    if attempt >= cfg.max_attempts:
                        _stats.record_failure(retry_count=attempt, status_code=e.status_code)
                        raise

                    wait_time = _calculate_wait_time(attempt - 1, cfg, e.retry_after)
                    logger.info(f"Waiting {wait_time:.2f}s before retry attempt {attempt + 1}")
                    await asyncio.sleep(wait_time)

                except FHIRNonRetryableError:
                    _stats.record_failure(retry_count=attempt)
                    raise

                except (httpx.ConnectError, httpx.TimeoutException) as e:
                    last_exception = e
                    attempt += 1
                    _stats.record_retry()

                    logger.warning(
                        f"Connection error, will retry (attempt {attempt}/{cfg.max_attempts}): {e}",
                        extra={"attempt": attempt, "error": str(e)}
                    )

                    if attempt >= cfg.max_attempts:
                        _stats.record_failure(retry_count=attempt)
                        raise

                    wait_time = _calculate_wait_time(attempt - 1, cfg)
                    await asyncio.sleep(wait_time)

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# Pre-configured HTTP Client with Retry
# ═══════════════════════════════════════════════════════════════════════════════

class FHIRClient:
    """
    HTTP client wrapper with automatic retry for FHIR API calls.

    Usage:
        client = FHIRClient()

        # GET request
        response = await client.get(url, headers={"Authorization": "Bearer ..."})

        # POST request
        response = await client.post(url, json=data, headers=headers)
    """

    def __init__(self, config: Optional[FHIRRetryConfig] = None):
        self.config = config or get_config()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.close()

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[dict] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: Request URL
            headers: Request headers
            **kwargs: Additional arguments passed to httpx

        Returns:
            httpx.Response on success

        Raises:
            FHIRNonRetryableError: For client errors (400, 401, 403, 404)
            FHIRRetryableError: After all retries exhausted
            httpx.ConnectError: Connection failures after retries
            httpx.TimeoutException: Timeouts after retries
        """
        client = await self._get_client()
        attempt = 0
        last_exception = None

        # Add retry tracking header
        headers = headers or {}

        while attempt < self.config.max_attempts:
            try:
                # Add retry count header
                request_headers = {**headers, "X-Retry-Count": str(attempt)}

                response = await client.request(method, url, headers=request_headers, **kwargs)

                # Check for retryable errors
                await _handle_response(response, attempt)

                # Success
                _stats.record_success(retry_count=attempt)
                return response

            except FHIRRetryableError as e:
                last_exception = e
                attempt += 1

                if attempt >= self.config.max_attempts:
                    _stats.record_failure(retry_count=attempt, status_code=e.status_code)
                    raise

                wait_time = _calculate_wait_time(attempt - 1, self.config, e.retry_after)
                logger.info(f"Waiting {wait_time:.2f}s before retry attempt {attempt + 1}")
                await asyncio.sleep(wait_time)

            except FHIRNonRetryableError:
                _stats.record_failure(retry_count=attempt)
                raise

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                attempt += 1
                _stats.record_retry()

                logger.warning(
                    f"Connection error on {method} {url}, attempt {attempt}/{self.config.max_attempts}: {e}"
                )

                if attempt >= self.config.max_attempts:
                    _stats.record_failure(retry_count=attempt)
                    raise

                wait_time = _calculate_wait_time(attempt - 1, self.config)
                await asyncio.sleep(wait_time)

        # Should not reach here
        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected retry loop exit")

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """HTTP GET with retry"""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """HTTP POST with retry"""
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> httpx.Response:
        """HTTP PUT with retry"""
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """HTTP DELETE with retry"""
        return await self.request("DELETE", url, **kwargs)

    async def patch(self, url: str, **kwargs) -> httpx.Response:
        """HTTP PATCH with retry"""
        return await self.request("PATCH", url, **kwargs)


# Global client instance
_fhir_client: Optional[FHIRClient] = None


async def get_fhir_client() -> FHIRClient:
    """Get or create the global FHIR client"""
    global _fhir_client
    if _fhir_client is None:
        _fhir_client = FHIRClient()
    return _fhir_client


async def close_fhir_client() -> None:
    """Close the global FHIR client"""
    global _fhir_client
    if _fhir_client:
        await _fhir_client.close()
        _fhir_client = None


# ═══════════════════════════════════════════════════════════════════════════════
# Convenience Functions
# ═══════════════════════════════════════════════════════════════════════════════

async def fhir_get(url: str, headers: Optional[dict] = None, **kwargs) -> httpx.Response:
    """Convenience function for FHIR GET requests with retry"""
    client = await get_fhir_client()
    return await client.get(url, headers=headers, **kwargs)


async def fhir_post(url: str, headers: Optional[dict] = None, **kwargs) -> httpx.Response:
    """Convenience function for FHIR POST requests with retry"""
    client = await get_fhir_client()
    return await client.post(url, headers=headers, **kwargs)
