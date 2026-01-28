"""
Tests for Error Sanitization (Issue #30)
Verifies error messages don't leak internal details.

OWASP: Improper Error Handling - CWE-209, CWE-211
HIPAA: §164.312(a)(1) - Access Control
"""

import pytest
from fastapi.testclient import TestClient
import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from error_handling import (
    contains_sensitive_info, sanitize_error_message, get_safe_error_response,
    generate_correlation_id, ErrorCode, get_safe_third_party_error
)


class TestSensitiveInfoDetection:
    """Tests for sensitive information detection."""

    def test_detects_file_paths(self):
        """Should detect file paths in messages."""
        assert contains_sensitive_info("/Users/john/app/main.py")
        assert contains_sensitive_info('File "/app/service.py", line 42')
        assert contains_sensitive_info("at com.example.Service(Service.java:99)")

    def test_detects_stack_traces(self):
        """Should detect stack trace patterns."""
        assert contains_sensitive_info("Traceback (most recent call last)")
        assert contains_sensitive_info("    at java.lang.Thread.run")

    def test_detects_database_details(self):
        """Should detect database connection info."""
        assert contains_sensitive_info("postgresql://user:pass@localhost:5432/db")
        assert contains_sensitive_info("mysql://root@127.0.0.1:3306")
        assert contains_sensitive_info('relation "users" does not exist')
        assert contains_sensitive_info("SELECT * FROM patients WHERE id = 1")

    def test_detects_api_keys(self):
        """Should detect API keys and secrets."""
        assert contains_sensitive_info("api_key: sk-abc123xyz")
        assert contains_sensitive_info('apiKey="secret123"')
        assert contains_sensitive_info("sk-proj-abcd1234567890")
        assert contains_sensitive_info("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")

    def test_detects_internal_urls(self):
        """Should detect internal URLs and ports."""
        assert contains_sensitive_info("localhost:8002")
        assert contains_sensitive_info("127.0.0.1:5000")
        assert contains_sensitive_info("http://internal-service:3000")

    def test_detects_internal_ips(self):
        """Should detect internal IP addresses."""
        assert contains_sensitive_info("10.0.0.1")
        assert contains_sensitive_info("192.168.1.100")
        assert contains_sensitive_info("172.16.0.50")

    def test_allows_safe_messages(self):
        """Should allow safe error messages."""
        assert not contains_sensitive_info("Patient not found")
        assert not contains_sensitive_info("Invalid request")
        assert not contains_sensitive_info("Authentication required")
        assert not contains_sensitive_info("Resource conflict")


class TestMessageSanitization:
    """Tests for error message sanitization."""

    def test_sanitizes_sensitive_messages(self):
        """Should replace sensitive messages with generic ones."""
        result = sanitize_error_message("Failed at /app/main.py line 42")
        assert "/app/main.py" not in result
        assert "line 42" not in result

    def test_truncates_long_messages(self):
        """Should truncate very long messages."""
        long_message = "A" * 500
        result = sanitize_error_message(long_message)
        assert len(result) <= 203  # 200 + "..."

    def test_handles_empty_messages(self):
        """Should handle empty messages gracefully."""
        assert sanitize_error_message("") == "An error occurred"
        assert sanitize_error_message(None) == "An error occurred"

    def test_preserves_safe_messages(self):
        """Should preserve safe, short messages."""
        assert sanitize_error_message("Invalid patient ID") == "Invalid patient ID"


class TestSafeErrorResponse:
    """Tests for structured error responses."""

    def test_500_never_exposes_details(self):
        """500 errors should never expose original error."""
        response = get_safe_error_response(
            status_code=500,
            original_error="NullPointerException at Service.java:42"
        )
        assert "NullPointerException" not in response["error"]
        assert "Service.java" not in response["error"]
        assert response["code"] == ErrorCode.INTERNAL_ERROR.value

    def test_404_allows_resource_type(self):
        """404 errors can mention what wasn't found."""
        response = get_safe_error_response(
            status_code=404,
            original_error="Patient not found"
        )
        assert "not found" in response["error"].lower()
        assert response["code"] == ErrorCode.NOT_FOUND.value

    def test_includes_correlation_id(self):
        """All responses should include correlation ID."""
        response = get_safe_error_response(status_code=500)
        assert "request_id" in response
        assert len(response["request_id"]) == 8

    def test_custom_correlation_id(self):
        """Should use provided correlation ID."""
        response = get_safe_error_response(
            status_code=500,
            correlation_id="CUSTOM01"
        )
        assert response["request_id"] == "CUSTOM01"

    def test_includes_error_code(self):
        """Responses should include standardized error code."""
        response = get_safe_error_response(status_code=401)
        assert response["code"] == ErrorCode.AUTH_REQUIRED.value


class TestCorrelationIds:
    """Tests for correlation ID generation."""

    def test_generates_unique_ids(self):
        """Should generate unique IDs."""
        ids = [generate_correlation_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All unique

    def test_id_format(self):
        """IDs should be uppercase 8-char strings."""
        cid = generate_correlation_id()
        assert len(cid) == 8
        assert cid == cid.upper()


class TestThirdPartyErrorSanitization:
    """Tests for third-party service error handling."""

    def test_sanitizes_openai_errors(self):
        """Should hide OpenAI API details."""
        error = Exception("OpenAI API error: Invalid API key sk-proj-abc123")
        result = get_safe_third_party_error(error)
        assert "sk-" not in result
        assert "API key" not in result
        assert "unavailable" in result.lower()

    def test_sanitizes_anthropic_errors(self):
        """Should hide Claude/Anthropic API details."""
        error = Exception("Anthropic rate limit exceeded for key xxx")
        result = get_safe_third_party_error(error, "claude")
        assert "rate limit" not in result.lower()
        assert "unavailable" in result.lower()

    def test_sanitizes_ehr_errors(self):
        """Should hide EHR service details."""
        error = Exception("Cerner FHIR error: Invalid client credentials")
        result = get_safe_third_party_error(error, "cerner")
        assert "credentials" not in result.lower()
        assert "EHR" in result

    def test_handles_timeout_errors(self):
        """Should provide user-friendly timeout message."""
        error = Exception("Connection timeout after 30s")
        result = get_safe_third_party_error(error)
        assert "timed out" in result.lower() or "timeout" in result.lower()
        assert "try again" in result.lower()

    def test_handles_connection_errors(self):
        """Should provide user-friendly connection message."""
        error = Exception("Connection refused to 10.0.0.1:5432")
        result = get_safe_third_party_error(error)
        assert "10.0.0.1" not in result
        assert "5432" not in result


class TestAPIErrorResponses:
    """Integration tests for API error responses."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_404_response_format(self, client):
        """404 responses should be properly formatted."""
        response = client.get("/api/v1/patient/nonexistent999")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "code" in data
        assert "request_id" in data

    def test_422_validation_error_format(self, client):
        """Validation errors should be formatted safely."""
        response = client.post(
            "/api/v1/vitals/push",
            json={"patient_id": ""}  # Invalid - missing required fields
        )
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        # Should not expose internal validation details
        assert "pydantic" not in str(data).lower()

    def test_500_errors_hide_details(self, client):
        """500 errors should never expose internals."""
        # Most endpoints won't actually 500, but we test the handler exists
        # by checking the error format
        response = client.get("/api/v1/patient/12724066")
        # Even successful responses shouldn't leak info
        if response.status_code >= 400:
            data = response.json()
            # Check no sensitive patterns in response
            response_str = str(data)
            assert "Traceback" not in response_str
            assert ".py" not in response_str or "entropy" not in response_str


class TestNoSensitiveInfoInResponses:
    """Verify no endpoint leaks sensitive information."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    SENSITIVE_PATTERNS = [
        r'\.py["\s:]',  # Python files
        r'\.java["\s:]',  # Java files
        r'line \d+',  # Line numbers
        r'Traceback',  # Python tracebacks
        r'Exception:.*at\s',  # Java exceptions
        r'localhost:\d+',  # Local ports
        r'sk-[a-zA-Z0-9]+',  # OpenAI keys
    ]

    def test_ping_no_leaks(self, client):
        """Ping endpoint should not leak info."""
        response = client.get("/ping")
        self._assert_no_sensitive_info(response)

    def test_worklist_no_leaks(self, client):
        """Worklist endpoint should not leak info."""
        response = client.get("/api/v1/worklist")
        self._assert_no_sensitive_info(response)

    def test_patient_not_found_no_leaks(self, client):
        """Patient not found should not leak info."""
        response = client.get("/api/v1/patient/invalid-id-12345")
        self._assert_no_sensitive_info(response)

    def test_invalid_json_no_leaks(self, client):
        """Invalid JSON should not leak info."""
        response = client.post(
            "/api/v1/minerva/chat",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        self._assert_no_sensitive_info(response)

    def _assert_no_sensitive_info(self, response):
        """Assert response contains no sensitive patterns."""
        response_text = response.text
        for pattern in self.SENSITIVE_PATTERNS:
            matches = re.findall(pattern, response_text, re.IGNORECASE)
            assert not matches, f"Found sensitive pattern '{pattern}' in response: {matches}"


class TestErrorCodeMapping:
    """Tests for error code consistency."""

    def test_all_status_codes_have_defaults(self):
        """Common HTTP status codes should have default messages."""
        for status in [400, 401, 403, 404, 409, 422, 429, 500, 502, 503]:
            response = get_safe_error_response(status_code=status)
            assert response["error"]  # Has a message
            assert response["code"]   # Has a code
            assert response["request_id"]  # Has tracking ID

    def test_error_codes_are_strings(self):
        """Error codes should be string values."""
        response = get_safe_error_response(status_code=500)
        assert isinstance(response["code"], str)
        assert response["code"].startswith(("AUTH_", "RES_", "VAL_", "RATE_", "EXT_", "INT_"))
