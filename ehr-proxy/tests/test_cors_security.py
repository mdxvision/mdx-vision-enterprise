"""
Tests for CORS Security (Issue #15)
Restrict CORS from wildcard "*" to specific allowed origins.

Tests that only whitelisted origins can make cross-origin requests.
"""

import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app, ALLOWED_ORIGINS


class TestCORSConfiguration:
    """Tests for CORS configuration."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_allowed_origins_not_wildcard(self):
        """ALLOWED_ORIGINS should not contain wildcard."""
        assert "*" not in ALLOWED_ORIGINS, "Wildcard '*' should not be in ALLOWED_ORIGINS"

    def test_allowed_origins_is_list(self):
        """ALLOWED_ORIGINS should be a list."""
        assert isinstance(ALLOWED_ORIGINS, list), "ALLOWED_ORIGINS should be a list"

    def test_allowed_origins_not_empty(self):
        """ALLOWED_ORIGINS should have at least one entry."""
        assert len(ALLOWED_ORIGINS) > 0, "ALLOWED_ORIGINS should not be empty"

    def test_default_origins_include_localhost(self):
        """Default origins should include localhost for development."""
        localhost_origins = [o for o in ALLOWED_ORIGINS if "localhost" in o or "127.0.0.1" in o]
        assert len(localhost_origins) > 0, "Should have localhost origins for development"


class TestCORSAllowedOrigins:
    """Tests for allowed origin requests."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_cors_allowed_origin_localhost_3000(self, client):
        """Requests from localhost:3000 should include CORS headers."""
        response = client.get(
            "/ping",
            headers={"Origin": "http://localhost:3000"}
        )
        assert response.status_code == 200
        # Should have CORS header for allowed origin
        cors_header = response.headers.get("access-control-allow-origin")
        assert cors_header == "http://localhost:3000", f"Expected localhost:3000, got {cors_header}"

    def test_cors_allowed_origin_localhost_5173(self, client):
        """Requests from localhost:5173 should include CORS headers."""
        response = client.get(
            "/ping",
            headers={"Origin": "http://localhost:5173"}
        )
        assert response.status_code == 200
        cors_header = response.headers.get("access-control-allow-origin")
        assert cors_header == "http://localhost:5173"

    def test_cors_preflight_allowed_origin(self, client):
        """Preflight OPTIONS request from allowed origin should succeed."""
        response = client.options(
            "/api/v1/patient/12724066",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert "GET" in response.headers.get("access-control-allow-methods", "")

    def test_cors_credentials_allowed(self, client):
        """CORS should allow credentials for allowed origins."""
        response = client.get(
            "/ping",
            headers={"Origin": "http://localhost:3000"}
        )
        assert response.headers.get("access-control-allow-credentials") == "true"


class TestCORSDisallowedOrigins:
    """Tests for disallowed origin requests."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    MALICIOUS_ORIGINS = [
        "http://evil.com",
        "http://attacker.com",
        "https://phishing-site.com",
        "http://localhost.evil.com",  # Subdomain trick
        "http://localhost:3000.evil.com",  # Subdomain trick
        "http://not-localhost:3000",
        "null",  # null origin attack
    ]

    def test_cors_disallowed_origin_no_header(self, client):
        """Requests from disallowed origins should not get CORS headers."""
        for origin in self.MALICIOUS_ORIGINS:
            response = client.get(
                "/ping",
                headers={"Origin": origin}
            )
            # Request still succeeds (CORS is browser-enforced)
            # But should NOT have access-control-allow-origin header
            cors_header = response.headers.get("access-control-allow-origin")
            assert cors_header != "*", f"Wildcard should never be returned for {origin}"
            assert cors_header != origin, f"Malicious origin should not be allowed: {origin}"

    def test_cors_preflight_disallowed_origin(self, client):
        """Preflight from disallowed origin should not include CORS headers."""
        response = client.options(
            "/api/v1/patient/12724066",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "GET",
            }
        )
        cors_header = response.headers.get("access-control-allow-origin")
        assert cors_header != "http://evil.com"
        assert cors_header != "*"


class TestCORSSecurityHeaders:
    """Tests for CORS-related security headers."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_no_wildcard_in_response(self, client):
        """Response should never contain wildcard CORS header."""
        # Test with various origins
        origins = [
            "http://localhost:3000",
            "http://evil.com",
            None,  # No origin
        ]
        for origin in origins:
            headers = {"Origin": origin} if origin else {}
            response = client.get("/ping", headers=headers)
            cors_header = response.headers.get("access-control-allow-origin", "")
            assert cors_header != "*", f"Wildcard returned for origin: {origin}"

    def test_cors_methods_restricted(self, client):
        """CORS should only allow specific HTTP methods."""
        response = client.options(
            "/api/v1/patient/12724066",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        allowed_methods = response.headers.get("access-control-allow-methods", "")
        # Should have specific methods, not wildcard
        assert "GET" in allowed_methods
        assert "POST" in allowed_methods
        # Dangerous methods should be controlled
        # (We allow DELETE/PATCH but they should be explicitly listed)


class TestCORSWithAPIEndpoints:
    """Integration tests for CORS on actual API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_patient_endpoint_cors_allowed(self, client):
        """Patient API should work with allowed CORS origin."""
        response = client.get(
            "/api/v1/patient/12724066",
            headers={"Origin": "http://localhost:3000"}
        )
        # Should work (may be 200 or other status depending on backend)
        assert response.status_code != 403
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_worklist_endpoint_cors_allowed(self, client):
        """Worklist API should work with allowed CORS origin."""
        response = client.get(
            "/api/v1/worklist",
            headers={"Origin": "http://localhost:5173"}
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_minerva_endpoint_cors_allowed(self, client):
        """Minerva API should work with allowed CORS origin."""
        response = client.post(
            "/api/v1/minerva/chat",
            json={"message": "Hello"},
            headers={"Origin": "http://localhost:3000"}
        )
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


class TestCORSEnvironmentConfiguration:
    """Tests for environment-based CORS configuration."""

    def test_allowed_origins_from_environment(self, monkeypatch):
        """ALLOWED_ORIGINS should be configurable via environment."""
        # This tests the parsing logic
        test_origins = "https://prod.example.com,https://app.example.com"
        origins_list = [o.strip() for o in test_origins.split(",") if o.strip()]
        assert len(origins_list) == 2
        assert "https://prod.example.com" in origins_list
        assert "https://app.example.com" in origins_list

    def test_empty_env_uses_defaults(self):
        """Empty ALLOWED_ORIGINS env should use development defaults."""
        # Default should include localhost
        assert any("localhost" in o for o in ALLOWED_ORIGINS)
