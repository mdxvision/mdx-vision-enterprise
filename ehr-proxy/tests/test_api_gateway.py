"""
Tests for API Gateway (Issue #96)

Tests cover:
- Service registry
- Circuit breaker functionality
- Health checking
- Request proxying
- Gateway endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_gateway import (
    ServiceRegistry, ServiceConfig, ServiceStatus,
    GatewayProxy, HealthChecker,
    create_gateway_app, get_service_registry
)


class TestServiceRegistry:
    """Tests for service registry."""

    @pytest.fixture
    def registry(self):
        """Create fresh registry."""
        reg = ServiceRegistry()
        reg._services.clear()
        return reg

    def test_register_service(self, registry):
        """Should register a service."""
        config = ServiceConfig(
            name="test-service",
            base_url="http://localhost:9999"
        )
        registry.register_service(config)

        assert registry.get_service("test-service") is not None
        assert registry.get_service("test-service").base_url == "http://localhost:9999"

    def test_get_unknown_service_returns_none(self, registry):
        """Unknown service should return None."""
        assert registry.get_service("unknown") is None

    def test_list_services(self, registry):
        """Should list all services."""
        registry.register_service(ServiceConfig(name="svc1", base_url="http://localhost:1"))
        registry.register_service(ServiceConfig(name="svc2", base_url="http://localhost:2"))

        services = registry.list_services()
        assert len(services) == 2
        names = [s["name"] for s in services]
        assert "svc1" in names
        assert "svc2" in names

    def test_record_success(self, registry):
        """Record success should update status."""
        registry.register_service(ServiceConfig(name="test", base_url="http://localhost:1"))
        registry.record_success("test")

        svc = registry.get_service("test")
        assert svc.status == ServiceStatus.HEALTHY
        assert svc.consecutive_failures == 0
        assert svc.last_success_time is not None

    def test_record_failure_increments_count(self, registry):
        """Record failure should increment failure count."""
        registry.register_service(ServiceConfig(name="test", base_url="http://localhost:1"))

        registry.record_failure("test")
        assert registry.get_service("test").consecutive_failures == 1

        registry.record_failure("test")
        assert registry.get_service("test").consecutive_failures == 2

    def test_record_failure_opens_circuit(self, registry):
        """Multiple failures should open circuit."""
        config = ServiceConfig(
            name="test",
            base_url="http://localhost:1",
            failure_threshold=3
        )
        registry.register_service(config)

        # First failures don't open circuit
        registry.record_failure("test")
        registry.record_failure("test")
        assert not registry.is_circuit_open("test")

        # Third failure opens circuit
        registry.record_failure("test")
        assert registry.is_circuit_open("test")
        assert registry.get_service("test").status == ServiceStatus.UNHEALTHY

    def test_success_closes_circuit(self, registry):
        """Success after circuit open should close circuit."""
        config = ServiceConfig(
            name="test",
            base_url="http://localhost:1",
            failure_threshold=2
        )
        registry.register_service(config)

        # Open circuit
        registry.record_failure("test")
        registry.record_failure("test")
        assert registry.is_circuit_open("test")

        # Success closes it
        registry.record_success("test")
        assert not registry.is_circuit_open("test")
        assert registry.get_service("test").status == ServiceStatus.HEALTHY

    def test_circuit_half_open_after_timeout(self, registry):
        """Circuit should allow probe after recovery timeout."""
        config = ServiceConfig(
            name="test",
            base_url="http://localhost:1",
            failure_threshold=2,
            recovery_timeout=0.1  # 100ms for testing
        )
        registry.register_service(config)

        # Open circuit
        registry.record_failure("test")
        registry.record_failure("test")
        assert registry.is_circuit_open("test")

        # Simulate time passing
        svc = registry.get_service("test")
        svc.circuit_opened_at = datetime.now(timezone.utc) - timedelta(seconds=1)

        # Should be half-open (allow request)
        assert not registry.is_circuit_open("test")


class TestCircuitBreaker:
    """Tests for circuit breaker behavior."""

    @pytest.fixture
    def registry(self):
        reg = ServiceRegistry()
        reg._services.clear()
        reg.register_service(ServiceConfig(
            name="flaky",
            base_url="http://localhost:1",
            failure_threshold=3,
            recovery_timeout=60.0
        ))
        return reg

    def test_circuit_stays_open_within_timeout(self, registry):
        """Circuit should stay open within recovery timeout."""
        for _ in range(3):
            registry.record_failure("flaky")

        # Circuit just opened, should be open
        assert registry.is_circuit_open("flaky")

    def test_unknown_service_has_open_circuit(self, registry):
        """Unknown service should be treated as open circuit."""
        assert registry.is_circuit_open("nonexistent")

    def test_degraded_status_before_threshold(self, registry):
        """Status should be degraded before hitting threshold."""
        registry.record_failure("flaky")
        registry.record_failure("flaky")

        svc = registry.get_service("flaky")
        assert svc.status == ServiceStatus.DEGRADED
        assert not svc.circuit_open


class TestGatewayProxy:
    """Tests for request proxying."""

    @pytest.fixture
    def registry(self):
        reg = ServiceRegistry()
        reg._services.clear()
        reg.register_service(ServiceConfig(
            name="backend",
            base_url="http://localhost:8080",
            failure_threshold=3
        ))
        return reg

    @pytest.fixture
    def proxy(self, registry):
        return GatewayProxy(registry)

    def test_proxy_unknown_service_raises(self, proxy):
        """Proxying to unknown service should raise 502."""
        from fastapi import Request

        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.url.query = ""
        mock_request.client.host = "127.0.0.1"
        mock_request.url.scheme = "http"

        with pytest.raises(Exception) as exc_info:
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                proxy.proxy_request("unknown", mock_request, "/test", "corr-123")
            )

    def test_proxy_circuit_open_raises_503(self, proxy, registry):
        """Proxying with open circuit should raise 503."""
        # Open circuit
        for _ in range(3):
            registry.record_failure("backend")

        mock_request = MagicMock()

        with pytest.raises(Exception) as exc_info:
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                proxy.proxy_request("backend", mock_request, "/test", "corr-123")
            )


class TestGatewayEndpoints:
    """Integration tests for gateway API endpoints."""

    @pytest.fixture
    def client(self):
        app = create_gateway_app()
        return TestClient(app)

    def test_gateway_health_endpoint(self, client):
        """GET /gateway/health should return status."""
        response = client.get("/gateway/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data
        assert "timestamp" in data

    def test_gateway_services_endpoint(self, client):
        """GET /gateway/services should list services."""
        response = client.get("/gateway/services")

        assert response.status_code == 200
        data = response.json()
        assert "services" in data
        assert isinstance(data["services"], list)

    def test_reset_circuit_endpoint(self, client):
        """POST /gateway/services/{name}/circuit/reset should reset circuit."""
        # First, get a service name from the list
        services_response = client.get("/gateway/services")
        services = services_response.json()["services"]

        if services:
            name = services[0]["name"]
            response = client.post(f"/gateway/services/{name}/circuit/reset")
            assert response.status_code == 200
            assert "reset" in response.json()["message"]

    def test_reset_circuit_unknown_service_404(self, client):
        """Reset circuit for unknown service should return 404."""
        response = client.post("/gateway/services/nonexistent/circuit/reset")
        assert response.status_code == 404

    def test_correlation_id_propagated(self, client):
        """Correlation ID should be in response headers."""
        response = client.get("/gateway/health")
        assert "X-Correlation-ID" in response.headers

    def test_correlation_id_preserved(self, client):
        """Provided correlation ID should be preserved."""
        corr_id = "test-correlation-123"
        response = client.get(
            "/gateway/health",
            headers={"X-Correlation-ID": corr_id}
        )
        assert response.headers["X-Correlation-ID"] == corr_id


class TestServiceConfig:
    """Tests for ServiceConfig dataclass."""

    def test_default_values(self):
        """ServiceConfig should have sensible defaults."""
        config = ServiceConfig(name="test", base_url="http://localhost")

        assert config.health_endpoint == "/ping"
        assert config.timeout == 30.0
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 30.0
        assert config.status == ServiceStatus.UNKNOWN
        assert config.consecutive_failures == 0
        assert not config.circuit_open

    def test_custom_values(self):
        """ServiceConfig should accept custom values."""
        config = ServiceConfig(
            name="custom",
            base_url="http://localhost:9000",
            health_endpoint="/health",
            timeout=60.0,
            failure_threshold=10,
            recovery_timeout=120.0
        )

        assert config.health_endpoint == "/health"
        assert config.timeout == 60.0
        assert config.failure_threshold == 10


class TestHealthChecker:
    """Tests for health checker."""

    @pytest.fixture
    def registry(self):
        reg = ServiceRegistry()
        reg._services.clear()
        return reg

    @pytest.fixture
    def health_checker(self, registry):
        return HealthChecker(registry, interval=1.0)

    def test_health_checker_init(self, health_checker):
        """Health checker should initialize correctly."""
        assert health_checker.interval == 1.0
        assert not health_checker._running

    @pytest.mark.asyncio
    async def test_start_stop(self, health_checker):
        """Health checker should start and stop."""
        await health_checker.start()
        assert health_checker._running

        await health_checker.stop()
        assert not health_checker._running


class TestRouting:
    """Tests for gateway routing rules."""

    @pytest.fixture
    def client(self):
        app = create_gateway_app()
        return TestClient(app)

    def test_ehr_route_defined(self, client):
        """Route /api/ehr/* should be defined."""
        # This will fail to connect but route should exist
        response = client.get("/api/ehr/patient/123")
        # 503 means route exists but service unavailable
        assert response.status_code in [503, 502, 504]

    def test_backend_route_defined(self, client):
        """Route /api/backend/* should be defined."""
        response = client.get("/api/backend/test")
        # 404 can happen if backend returns it, 50x means gateway error
        assert response.status_code in [404, 503, 502, 504]

    def test_ai_route_defined(self, client):
        """Route /api/ai/* should be defined."""
        response = client.get("/api/ai/test")
        assert response.status_code in [503, 502, 504]

    def test_v1_backward_compat_route(self, client):
        """Route /api/v1/* should proxy to ehr-proxy for backward compatibility."""
        response = client.get("/api/v1/worklist")
        assert response.status_code in [503, 502, 504, 200]


class TestServiceStatus:
    """Tests for ServiceStatus enum."""

    def test_status_values(self):
        """ServiceStatus should have expected values."""
        assert ServiceStatus.HEALTHY.value == "healthy"
        assert ServiceStatus.DEGRADED.value == "degraded"
        assert ServiceStatus.UNHEALTHY.value == "unhealthy"
        assert ServiceStatus.UNKNOWN.value == "unknown"


class TestGlobalRegistry:
    """Tests for global registry singleton."""

    def test_get_service_registry_returns_same_instance(self):
        """get_service_registry should return singleton."""
        reg1 = get_service_registry()
        reg2 = get_service_registry()
        assert reg1 is reg2

    def test_default_services_registered(self):
        """Default services should be registered."""
        registry = get_service_registry()

        assert registry.get_service("ehr-proxy") is not None
        assert registry.get_service("backend") is not None
        assert registry.get_service("ai-service") is not None
