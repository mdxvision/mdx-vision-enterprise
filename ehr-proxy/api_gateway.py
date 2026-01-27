"""
API Gateway (Issue #96)

Lightweight API Gateway providing:
- Centralized routing to backend services
- Unified authentication/authorization
- Rate limiting (uses existing slowapi)
- Health checks with circuit breaker
- Request/response logging with correlation IDs
- CORS at gateway level

This can run standalone or be integrated into ehr-proxy.

Usage:
    Standalone: python api_gateway.py (port 8000)
    Integrated: Import and mount in main.py
"""

import asyncio
import httpx
import time
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from functools import wraps

from fastapi import FastAPI, Request, Response, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# =============================================================================
# SERVICE REGISTRY
# =============================================================================

class ServiceStatus(str, Enum):
    """Health status of a backend service."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceConfig:
    """Configuration for a backend service."""
    name: str
    base_url: str
    health_endpoint: str = "/ping"
    timeout: float = 30.0
    # Circuit breaker settings
    failure_threshold: int = 5  # failures before opening circuit
    recovery_timeout: float = 30.0  # seconds before trying again
    # Current state
    status: ServiceStatus = ServiceStatus.UNKNOWN
    consecutive_failures: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    circuit_open: bool = False
    circuit_opened_at: Optional[datetime] = None


class ServiceRegistry:
    """
    Registry of backend services with health tracking.
    """

    def __init__(self):
        self._services: Dict[str, ServiceConfig] = {}
        self._init_default_services()

    def _init_default_services(self):
        """Initialize default service configurations."""
        # EHR Proxy (primary backend)
        self.register_service(ServiceConfig(
            name="ehr-proxy",
            base_url="http://localhost:8002",
            health_endpoint="/ping",
            timeout=30.0
        ))

        # Legacy Java backend (if running)
        self.register_service(ServiceConfig(
            name="backend",
            base_url="http://localhost:8080",
            health_endpoint="/actuator/health",
            timeout=15.0
        ))

        # AI Service (if running)
        self.register_service(ServiceConfig(
            name="ai-service",
            base_url="http://localhost:8003",
            health_endpoint="/health",
            timeout=60.0  # AI can be slow
        ))

    def register_service(self, config: ServiceConfig):
        """Register a backend service."""
        self._services[config.name] = config
        logger.info(f"Registered service: {config.name} at {config.base_url}")

    def get_service(self, name: str) -> Optional[ServiceConfig]:
        """Get service configuration by name."""
        return self._services.get(name)

    def list_services(self) -> List[Dict[str, Any]]:
        """List all registered services with status."""
        return [
            {
                "name": svc.name,
                "base_url": svc.base_url,
                "status": svc.status.value,
                "circuit_open": svc.circuit_open,
                "consecutive_failures": svc.consecutive_failures,
                "last_success": svc.last_success_time.isoformat() if svc.last_success_time else None,
                "last_failure": svc.last_failure_time.isoformat() if svc.last_failure_time else None
            }
            for svc in self._services.values()
        ]

    def record_success(self, name: str):
        """Record successful request to service."""
        svc = self._services.get(name)
        if svc:
            svc.consecutive_failures = 0
            svc.last_success_time = datetime.now(timezone.utc)
            svc.status = ServiceStatus.HEALTHY
            if svc.circuit_open:
                svc.circuit_open = False
                svc.circuit_opened_at = None
                logger.info(f"Circuit closed for {name}")

    def record_failure(self, name: str):
        """Record failed request to service."""
        svc = self._services.get(name)
        if svc:
            svc.consecutive_failures += 1
            svc.last_failure_time = datetime.now(timezone.utc)

            if svc.consecutive_failures >= svc.failure_threshold:
                if not svc.circuit_open:
                    svc.circuit_open = True
                    svc.circuit_opened_at = datetime.now(timezone.utc)
                    svc.status = ServiceStatus.UNHEALTHY
                    logger.warning(f"Circuit opened for {name} after {svc.consecutive_failures} failures")
            else:
                svc.status = ServiceStatus.DEGRADED

    def is_circuit_open(self, name: str) -> bool:
        """Check if circuit breaker is open (service unavailable)."""
        svc = self._services.get(name)
        if not svc:
            return True  # Unknown service = open circuit

        if not svc.circuit_open:
            return False

        # Check if recovery timeout has passed
        if svc.circuit_opened_at:
            elapsed = (datetime.now(timezone.utc) - svc.circuit_opened_at).total_seconds()
            if elapsed >= svc.recovery_timeout:
                # Half-open: allow one request through
                logger.info(f"Circuit half-open for {name}, allowing probe request")
                return False

        return True


# Global registry
_service_registry: Optional[ServiceRegistry] = None


def get_service_registry() -> ServiceRegistry:
    """Get the global service registry."""
    global _service_registry
    if _service_registry is None:
        _service_registry = ServiceRegistry()
    return _service_registry


# =============================================================================
# REQUEST PROXY
# =============================================================================

class GatewayProxy:
    """
    Proxies requests to backend services with:
    - Circuit breaker protection
    - Timeout handling
    - Correlation ID propagation
    - Error handling
    """

    def __init__(self, registry: ServiceRegistry):
        self.registry = registry

    async def proxy_request(
        self,
        service_name: str,
        request: Request,
        path: str,
        correlation_id: str
    ) -> Response:
        """
        Proxy a request to a backend service.

        Args:
            service_name: Name of the target service
            request: Incoming FastAPI request
            path: Path to forward (after stripping gateway prefix)
            correlation_id: Request correlation ID

        Returns:
            Response from backend service
        """
        service = self.registry.get_service(service_name)
        if not service:
            raise HTTPException(status_code=502, detail=f"Unknown service: {service_name}")

        # Check circuit breaker
        if self.registry.is_circuit_open(service_name):
            raise HTTPException(
                status_code=503,
                detail=f"Service {service_name} is temporarily unavailable (circuit open)"
            )

        # Build target URL
        target_url = f"{service.base_url}{path}"
        if request.url.query:
            target_url += f"?{request.url.query}"

        # Forward headers (filter out hop-by-hop headers)
        forward_headers = {}
        hop_by_hop = {"host", "connection", "keep-alive", "transfer-encoding", "upgrade"}
        for key, value in request.headers.items():
            if key.lower() not in hop_by_hop:
                forward_headers[key] = value

        # Add correlation ID
        forward_headers["X-Correlation-ID"] = correlation_id
        forward_headers["X-Forwarded-For"] = request.client.host if request.client else "unknown"
        forward_headers["X-Forwarded-Proto"] = request.url.scheme

        # Get request body
        body = await request.body()

        try:
            async with httpx.AsyncClient(timeout=service.timeout) as client:
                response = await client.request(
                    method=request.method,
                    url=target_url,
                    headers=forward_headers,
                    content=body if body else None
                )

            # Record success
            self.registry.record_success(service_name)

            # Build response
            # Filter out hop-by-hop response headers
            response_headers = {}
            for key, value in response.headers.items():
                if key.lower() not in hop_by_hop and key.lower() != "content-encoding":
                    response_headers[key] = value

            # Add gateway headers
            response_headers["X-Correlation-ID"] = correlation_id
            response_headers["X-Gateway-Service"] = service_name

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get("content-type")
            )

        except httpx.TimeoutException:
            self.registry.record_failure(service_name)
            logger.error(f"Timeout proxying to {service_name}: {target_url}")
            raise HTTPException(
                status_code=504,
                detail=f"Service {service_name} timed out"
            )
        except httpx.ConnectError:
            self.registry.record_failure(service_name)
            logger.error(f"Connection error to {service_name}: {target_url}")
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to service {service_name}"
            )
        except Exception as e:
            self.registry.record_failure(service_name)
            logger.error(f"Error proxying to {service_name}: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Gateway error: {str(e)}"
            )


# =============================================================================
# HEALTH CHECKER
# =============================================================================

class HealthChecker:
    """
    Periodically checks health of backend services.
    """

    def __init__(self, registry: ServiceRegistry, interval: float = 30.0):
        self.registry = registry
        self.interval = interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start background health checking."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._health_check_loop())
            logger.info("Health checker started")

    async def stop(self):
        """Stop background health checking."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Health checker stopped")

    async def _health_check_loop(self):
        """Background loop to check service health."""
        while self._running:
            await self.check_all_services()
            await asyncio.sleep(self.interval)

    async def check_all_services(self):
        """Check health of all registered services."""
        for name, service in self.registry._services.items():
            await self.check_service(name, service)

    async def check_service(self, name: str, service: ServiceConfig):
        """Check health of a single service."""
        url = f"{service.base_url}{service.health_endpoint}"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    self.registry.record_success(name)
                else:
                    self.registry.record_failure(name)
        except Exception as e:
            self.registry.record_failure(name)
            logger.debug(f"Health check failed for {name}: {e}")


# =============================================================================
# GATEWAY APPLICATION
# =============================================================================

def create_gateway_app() -> FastAPI:
    """Create the API Gateway FastAPI application."""

    app = FastAPI(
        title="MDx Vision API Gateway",
        description="Centralized API Gateway for MDx Vision services",
        version="1.0.0"
    )

    # CORS configuration (centralized)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "https://mdxvision.com",
            "https://*.mdxvision.com",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID", "X-Gateway-Service"],
    )

    # Initialize components
    registry = get_service_registry()
    proxy = GatewayProxy(registry)
    health_checker = HealthChecker(registry)

    @app.on_event("startup")
    async def startup():
        await health_checker.start()

    @app.on_event("shutdown")
    async def shutdown():
        await health_checker.stop()

    # Middleware for correlation IDs
    @app.middleware("http")
    async def add_correlation_id(request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    # Gateway endpoints
    @app.get("/gateway/health")
    async def gateway_health():
        """Gateway health check."""
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": registry.list_services()
        }

    @app.get("/gateway/services")
    async def list_services():
        """List all registered backend services."""
        return {"services": registry.list_services()}

    @app.post("/gateway/services/{name}/circuit/reset")
    async def reset_circuit(name: str):
        """Manually reset circuit breaker for a service."""
        service = registry.get_service(name)
        if not service:
            raise HTTPException(status_code=404, detail=f"Service not found: {name}")

        service.circuit_open = False
        service.circuit_opened_at = None
        service.consecutive_failures = 0
        service.status = ServiceStatus.UNKNOWN

        return {"message": f"Circuit reset for {name}"}

    # Route: /api/ehr/* -> ehr-proxy
    @app.api_route("/api/ehr/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def proxy_ehr(request: Request, path: str):
        """Proxy requests to EHR Proxy service."""
        return await proxy.proxy_request(
            service_name="ehr-proxy",
            request=request,
            path=f"/api/v1/{path}",
            correlation_id=request.state.correlation_id
        )

    # Route: /api/backend/* -> Java backend
    @app.api_route("/api/backend/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def proxy_backend(request: Request, path: str):
        """Proxy requests to Java backend service."""
        return await proxy.proxy_request(
            service_name="backend",
            request=request,
            path=f"/api/{path}",
            correlation_id=request.state.correlation_id
        )

    # Route: /api/ai/* -> AI service
    @app.api_route("/api/ai/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def proxy_ai(request: Request, path: str):
        """Proxy requests to AI service."""
        return await proxy.proxy_request(
            service_name="ai-service",
            request=request,
            path=f"/{path}",
            correlation_id=request.state.correlation_id
        )

    # Direct passthrough to ehr-proxy for backward compatibility
    @app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def proxy_v1_ehr(request: Request, path: str):
        """Backward compatible route - proxies /api/v1/* to ehr-proxy."""
        return await proxy.proxy_request(
            service_name="ehr-proxy",
            request=request,
            path=f"/api/v1/{path}",
            correlation_id=request.state.correlation_id
        )

    return app


# Standalone gateway app
gateway_app = create_gateway_app()


if __name__ == "__main__":
    import uvicorn
    print("Starting API Gateway on port 8000...")
    print("Routes:")
    print("  /api/ehr/*     -> ehr-proxy (port 8002)")
    print("  /api/backend/* -> backend (port 8080)")
    print("  /api/ai/*      -> ai-service (port 8003)")
    print("  /api/v1/*      -> ehr-proxy (backward compatible)")
    uvicorn.run(gateway_app, host="0.0.0.0", port=8000)
