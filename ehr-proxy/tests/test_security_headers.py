"""
Tests for Security Headers (Issue #91 - OWASP Security Headers)
Verifies HSTS, CSP, X-Frame-Options, and other security headers.

Tests cover:
- HSTS (HTTP Strict Transport Security)
- CSP (Content Security Policy)
- X-Frame-Options (Clickjacking prevention)
- X-Content-Type-Options (MIME sniffing prevention)
- Referrer-Policy
- Permissions-Policy
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app


class TestSecurityHeadersPresent:
    """Tests that all required security headers are present."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_x_content_type_options_present(self, client):
        """X-Content-Type-Options header should be present."""
        response = client.get("/ping")
        assert "x-content-type-options" in response.headers
        assert response.headers["x-content-type-options"] == "nosniff"

    def test_x_frame_options_present(self, client):
        """X-Frame-Options header should be present."""
        response = client.get("/ping")
        assert "x-frame-options" in response.headers
        assert response.headers["x-frame-options"] == "DENY"

    def test_x_xss_protection_present(self, client):
        """X-XSS-Protection header should be present."""
        response = client.get("/ping")
        assert "x-xss-protection" in response.headers
        assert "1" in response.headers["x-xss-protection"]
        assert "mode=block" in response.headers["x-xss-protection"]

    def test_referrer_policy_present(self, client):
        """Referrer-Policy header should be present."""
        response = client.get("/ping")
        assert "referrer-policy" in response.headers
        assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy_present(self, client):
        """Permissions-Policy header should be present."""
        response = client.get("/ping")
        assert "permissions-policy" in response.headers
        policy = response.headers["permissions-policy"]
        assert "geolocation=()" in policy
        assert "camera=()" in policy

    def test_csp_present(self, client):
        """Content-Security-Policy header should be present."""
        response = client.get("/ping")
        assert "content-security-policy" in response.headers


class TestContentSecurityPolicy:
    """Tests for CSP header configuration."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_csp_default_src_self(self, client):
        """CSP should have default-src 'self'."""
        response = client.get("/ping")
        csp = response.headers.get("content-security-policy", "")
        assert "default-src 'self'" in csp

    def test_csp_script_src(self, client):
        """CSP should define script-src."""
        response = client.get("/ping")
        csp = response.headers.get("content-security-policy", "")
        assert "script-src" in csp
        assert "'self'" in csp

    def test_csp_style_src(self, client):
        """CSP should define style-src."""
        response = client.get("/ping")
        csp = response.headers.get("content-security-policy", "")
        assert "style-src" in csp

    def test_csp_img_src(self, client):
        """CSP should allow images from self, data, and https."""
        response = client.get("/ping")
        csp = response.headers.get("content-security-policy", "")
        assert "img-src" in csp
        assert "data:" in csp

    def test_csp_connect_src_includes_apis(self, client):
        """CSP should allow connections to required APIs."""
        response = client.get("/ping")
        csp = response.headers.get("content-security-policy", "")
        assert "connect-src" in csp
        assert "wss:" in csp  # WebSocket for transcription
        # Should allow AssemblyAI and Anthropic APIs
        assert "assemblyai" in csp.lower() or "https:" in csp

    def test_csp_frame_ancestors_none(self, client):
        """CSP should prevent framing (clickjacking)."""
        response = client.get("/ping")
        csp = response.headers.get("content-security-policy", "")
        assert "frame-ancestors 'none'" in csp

    def test_csp_font_src(self, client):
        """CSP should define font-src."""
        response = client.get("/ping")
        csp = response.headers.get("content-security-policy", "")
        assert "font-src" in csp

    def test_csp_base_uri(self, client):
        """CSP should restrict base-uri."""
        response = client.get("/ping")
        csp = response.headers.get("content-security-policy", "")
        assert "base-uri 'self'" in csp

    def test_csp_form_action(self, client):
        """CSP should restrict form-action."""
        response = client.get("/ping")
        csp = response.headers.get("content-security-policy", "")
        assert "form-action 'self'" in csp


class TestXFrameOptions:
    """Tests for clickjacking prevention."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_x_frame_options_deny(self, client):
        """X-Frame-Options should be DENY to prevent all framing."""
        response = client.get("/ping")
        assert response.headers.get("x-frame-options") == "DENY"

    def test_x_frame_options_on_api_endpoints(self, client):
        """API endpoints should also have X-Frame-Options."""
        response = client.get("/api/v1/worklist")
        assert response.headers.get("x-frame-options") == "DENY"

    def test_x_frame_options_on_patient_endpoint(self, client):
        """Patient endpoint should have X-Frame-Options."""
        response = client.get("/api/v1/patient/12724066")
        assert response.headers.get("x-frame-options") == "DENY"


class TestXContentTypeOptions:
    """Tests for MIME sniffing prevention."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_nosniff_on_json_responses(self, client):
        """JSON responses should have nosniff."""
        response = client.get("/api/v1/worklist")
        assert response.headers.get("x-content-type-options") == "nosniff"

    def test_nosniff_prevents_mime_sniffing(self, client):
        """nosniff should be present on all responses."""
        endpoints = ["/ping", "/api/v1/worklist", "/api/v1/patient/12724066"]
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.headers.get("x-content-type-options") == "nosniff", \
                f"Missing nosniff on {endpoint}"


class TestReferrerPolicy:
    """Tests for Referrer-Policy header."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_referrer_policy_strict(self, client):
        """Referrer-Policy should be strict-origin-when-cross-origin."""
        response = client.get("/ping")
        policy = response.headers.get("referrer-policy")
        assert policy == "strict-origin-when-cross-origin"

    def test_referrer_policy_protects_phi(self, client):
        """Referrer-Policy should protect PHI in URLs."""
        # Patient endpoints should have referrer policy
        response = client.get("/api/v1/patient/12724066")
        assert "referrer-policy" in response.headers


class TestPermissionsPolicy:
    """Tests for Permissions-Policy header."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_geolocation_disabled(self, client):
        """Geolocation should be disabled."""
        response = client.get("/ping")
        policy = response.headers.get("permissions-policy", "")
        assert "geolocation=()" in policy

    def test_camera_restricted(self, client):
        """Camera should be restricted."""
        response = client.get("/ping")
        policy = response.headers.get("permissions-policy", "")
        assert "camera=()" in policy

    def test_microphone_allowed_self(self, client):
        """Microphone should be allowed for self (voice commands)."""
        response = client.get("/ping")
        policy = response.headers.get("permissions-policy", "")
        # Microphone needed for voice commands
        assert "microphone=" in policy


class TestSecurityHeadersOnAllEndpoints:
    """Verify security headers are present on all endpoint types."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    REQUIRED_HEADERS = [
        "x-content-type-options",
        "x-frame-options",
        "referrer-policy",
        "content-security-policy",
    ]

    def test_headers_on_get_endpoints(self, client):
        """GET endpoints should have security headers."""
        endpoints = ["/ping", "/api/v1/worklist"]
        for endpoint in endpoints:
            response = client.get(endpoint)
            for header in self.REQUIRED_HEADERS:
                assert header in response.headers, \
                    f"Missing {header} on GET {endpoint}"

    def test_headers_on_post_endpoints(self, client):
        """POST endpoints should have security headers."""
        response = client.post(
            "/api/v1/minerva/chat",
            json={"message": "test", "patient_id": "12724066"}
        )
        for header in self.REQUIRED_HEADERS:
            assert header in response.headers, \
                f"Missing {header} on POST /api/v1/minerva/chat"

    def test_headers_on_error_responses(self, client):
        """Error responses should also have security headers."""
        response = client.get("/api/v1/patient/nonexistent")
        assert response.status_code >= 400
        for header in self.REQUIRED_HEADERS:
            assert header in response.headers, \
                f"Missing {header} on error response"


class TestHSTSConfiguration:
    """Tests for HSTS header (when enabled)."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_hsts_max_age_if_present(self, client):
        """HSTS max-age should be at least 1 year if present."""
        response = client.get("/ping")
        hsts = response.headers.get("strict-transport-security", "")
        if hsts:
            assert "max-age=" in hsts
            # Extract max-age value
            import re
            match = re.search(r'max-age=(\d+)', hsts)
            if match:
                max_age = int(match.group(1))
                assert max_age >= 31536000, "HSTS max-age should be at least 1 year"

    def test_hsts_include_subdomains_if_present(self, client):
        """HSTS should include subdomains if present."""
        response = client.get("/ping")
        hsts = response.headers.get("strict-transport-security", "")
        if hsts:
            assert "includeSubDomains" in hsts


class TestNoInsecureHeaders:
    """Tests that insecure headers are not present."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_no_server_header_leak(self, client):
        """Server header should not leak version info."""
        response = client.get("/ping")
        server = response.headers.get("server", "")
        # Should not contain detailed version info
        assert "python" not in server.lower() or "uvicorn" in server.lower()

    def test_no_x_powered_by(self, client):
        """X-Powered-By header should not be present."""
        response = client.get("/ping")
        # FastAPI/Starlette don't add this by default, verify it stays that way
        powered_by = response.headers.get("x-powered-by", "")
        assert not powered_by or "fastapi" not in powered_by.lower()
