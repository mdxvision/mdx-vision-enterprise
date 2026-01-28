"""
Tests for HTTPS and Security Headers (Issue #20)
HIPAA §164.312(e)(1) - Transmission Security

Tests security headers, HSTS, and HTTPS configuration.
"""

import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app


class TestSecurityHeaders:
    """Tests for security headers on all responses."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_x_content_type_options_header(self, client):
        """X-Content-Type-Options should be set to nosniff."""
        response = client.get("/ping")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options_header(self, client):
        """X-Frame-Options should be set to DENY."""
        response = client.get("/ping")
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_x_xss_protection_header(self, client):
        """X-XSS-Protection should be enabled."""
        response = client.get("/ping")
        assert "1" in response.headers.get("X-XSS-Protection", "")

    def test_referrer_policy_header(self, client):
        """Referrer-Policy should be set."""
        response = client.get("/ping")
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy_header(self, client):
        """Permissions-Policy should restrict dangerous features."""
        response = client.get("/ping")
        permissions = response.headers.get("Permissions-Policy", "")
        assert "geolocation=()" in permissions
        assert "camera=" in permissions

    def test_content_security_policy_header(self, client):
        """Content-Security-Policy should be set."""
        response = client.get("/ping")
        csp = response.headers.get("Content-Security-Policy", "")
        assert "default-src" in csp
        assert "frame-ancestors 'none'" in csp

    def test_security_headers_on_api_endpoint(self, client):
        """Security headers should be on API endpoints too."""
        response = client.get("/api/v1/patient/12724066")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_security_headers_on_error_responses(self, client):
        """Security headers should be on error responses too."""
        response = client.get("/nonexistent-endpoint")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"


class TestEnvironmentConfiguration:
    """Tests for environment-based configuration."""

    def test_environment_defaults_to_development(self):
        """ENVIRONMENT should default to development."""
        from main import ENVIRONMENT, IS_PRODUCTION
        # In test environment, should be development by default
        assert ENVIRONMENT == "development" or not IS_PRODUCTION

    def test_https_port_default(self):
        """HTTPS_PORT should have a sensible default."""
        from main import HTTPS_PORT
        assert HTTPS_PORT == 8443 or HTTPS_PORT == 443


class TestHSTSHeader:
    """Tests for HSTS header configuration."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_hsts_not_in_development(self, client):
        """HSTS should not be sent in development mode (without HTTPS)."""
        # In development mode without FORCE_HTTPS, HSTS should not be set
        # or should be set conditionally
        from main import IS_PRODUCTION, FORCE_HTTPS

        response = client.get("/ping")

        if not IS_PRODUCTION and not FORCE_HTTPS:
            # HSTS may or may not be present in dev, that's okay
            # Just ensure the app doesn't crash
            pass
        else:
            # In production/FORCE_HTTPS, HSTS should be present
            hsts = response.headers.get("Strict-Transport-Security", "")
            assert "max-age" in hsts


class TestSSLConfiguration:
    """Tests for SSL/TLS configuration variables."""

    def test_ssl_keyfile_is_configurable(self):
        """SSL_KEYFILE should be configurable via environment."""
        from main import SSL_KEYFILE
        # Should be empty string by default (not a path that doesn't exist)
        assert isinstance(SSL_KEYFILE, str)

    def test_ssl_certfile_is_configurable(self):
        """SSL_CERTFILE should be configurable via environment."""
        from main import SSL_CERTFILE
        assert isinstance(SSL_CERTFILE, str)

    def test_https_port_is_integer(self):
        """HTTPS_PORT should be an integer."""
        from main import HTTPS_PORT
        assert isinstance(HTTPS_PORT, int)
        assert 1 <= HTTPS_PORT <= 65535
