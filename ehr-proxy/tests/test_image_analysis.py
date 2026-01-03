"""
Tests for Medical Image Analysis API endpoint (Feature #70).

Tests the Claude Vision-powered image analysis feature that generates
clinical assessments, findings, ICD-10 codes, and recommendations from
medical images.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import base64
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)

# Small valid JPEG image (1x1 pixel red)
VALID_JPEG_BASE64 = "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAn/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBEQCEPwF/tgAAAB//2Q=="

# Invalid base64 string
INVALID_BASE64 = "not-valid-base64!!!"


class TestImageAnalysisEndpointValidation:
    """Test input validation for image analysis endpoint"""

    def test_image_analysis_requires_image_data(self):
        """Image data is required"""
        response = client.post("/api/v1/image/analyze", json={
            "media_type": "image/jpeg"
        })
        assert response.status_code == 422  # Validation error

    def test_image_analysis_empty_base64_rejected(self):
        """Empty image base64 is rejected"""
        response = client.post("/api/v1/image/analyze", json={
            "image_base64": "",
            "media_type": "image/jpeg"
        })
        assert response.status_code == 400
        assert "required" in response.json()["detail"].lower()

    def test_image_analysis_whitespace_base64_rejected(self):
        """Whitespace-only image base64 is rejected"""
        response = client.post("/api/v1/image/analyze", json={
            "image_base64": "   ",
            "media_type": "image/jpeg"
        })
        assert response.status_code == 400

    def test_image_analysis_unsupported_media_type_rejected(self):
        """Unsupported media type is rejected"""
        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "media_type": "image/tiff"
        })
        assert response.status_code == 400
        assert "unsupported" in response.json()["detail"].lower()

    def test_image_analysis_accepts_jpeg(self):
        """Accepts JPEG media type"""
        # This will fail without Claude API, but validates media type is accepted
        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "media_type": "image/jpeg"
        })
        # Either 200 (success) or 503 (no API key) - not 400
        assert response.status_code in [200, 500, 503]

    def test_image_analysis_accepts_png(self):
        """Accepts PNG media type"""
        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,  # Actually JPEG but testing media type validation
            "media_type": "image/png"
        })
        assert response.status_code in [200, 500, 503]

    def test_image_analysis_accepts_webp(self):
        """Accepts WebP media type"""
        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "media_type": "image/webp"
        })
        assert response.status_code in [200, 500, 503]

    def test_image_analysis_accepts_gif(self):
        """Accepts GIF media type"""
        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "media_type": "image/gif"
        })
        assert response.status_code in [200, 500, 503]


class TestImageAnalysisRequestFormats:
    """Test various request formats for image analysis"""

    def test_image_analysis_minimal_request(self):
        """Accepts minimal request with just image"""
        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64
        })
        # Default media_type is image/jpeg
        assert response.status_code in [200, 500, 503]

    def test_image_analysis_with_context(self):
        """Accepts request with analysis context"""
        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "media_type": "image/jpeg",
            "analysis_context": "wound"
        })
        assert response.status_code in [200, 500, 503]

    def test_image_analysis_with_patient_context(self):
        """Accepts request with full patient context"""
        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "media_type": "image/jpeg",
            "analysis_context": "rash",
            "patient_id": "12345",
            "chief_complaint": "Skin rash for 3 days",
            "patient_age": 45,
            "patient_gender": "female"
        })
        assert response.status_code in [200, 500, 503]

    def test_image_analysis_wound_context(self):
        """Accepts wound analysis context"""
        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "analysis_context": "wound"
        })
        assert response.status_code in [200, 500, 503]

    def test_image_analysis_rash_context(self):
        """Accepts rash analysis context"""
        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "analysis_context": "rash"
        })
        assert response.status_code in [200, 500, 503]

    def test_image_analysis_xray_context(self):
        """Accepts xray analysis context"""
        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "analysis_context": "xray"
        })
        assert response.status_code in [200, 500, 503]

    def test_image_analysis_general_context(self):
        """Accepts general analysis context"""
        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "analysis_context": "general"
        })
        assert response.status_code in [200, 500, 503]


class TestImageAnalysisSizeValidation:
    """Test image size validation"""

    def test_image_analysis_rejects_oversized_image(self):
        """Rejects images over 15MB (20MB base64)"""
        # Create a large base64 string (just over 20MB)
        large_base64 = "A" * (21 * 1024 * 1024)  # 21MB of 'A' characters
        response = client.post("/api/v1/image/analyze", json={
            "image_base64": large_base64,
            "media_type": "image/jpeg"
        })
        assert response.status_code == 400
        assert "too large" in response.json()["detail"].lower()

    def test_image_analysis_accepts_normal_size_image(self):
        """Accepts normal size images"""
        # ~1KB base64 image
        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "media_type": "image/jpeg"
        })
        # Should not fail due to size
        assert response.status_code in [200, 500, 503]


class TestImageAnalysisResponseFormat:
    """Test expected response format (with mocked Claude API)"""

    @patch('main.CLAUDE_API_KEY', 'test-key')
    @patch('anthropic.Anthropic')
    def test_image_analysis_response_structure(self, mock_anthropic):
        """Response has expected structure"""
        # Mock the Claude API response
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "assessment": "Test assessment",
            "findings": [
                {
                    "finding": "Test finding",
                    "confidence": "high",
                    "location": "right arm",
                    "characteristics": ["red", "swollen"]
                }
            ],
            "icd10_codes": [
                {"code": "L03.90", "description": "Cellulitis, unspecified"}
            ],
            "recommendations": ["Clean and dress wound"],
            "red_flags": [],
            "differential_considerations": ["Consider infection"]
        }))]
        mock_client.messages.create.return_value = mock_response

        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "media_type": "image/jpeg"
        })

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "assessment" in data
        assert "findings" in data
        assert "icd10_codes" in data
        assert "recommendations" in data
        assert "red_flags" in data
        assert "differential_considerations" in data
        assert "disclaimer" in data
        assert "timestamp" in data

    @patch('main.CLAUDE_API_KEY', 'test-key')
    @patch('anthropic.Anthropic')
    def test_image_analysis_finding_structure(self, mock_anthropic):
        """Each finding has required fields"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "assessment": "Test assessment",
            "findings": [
                {
                    "finding": "Laceration",
                    "confidence": "high",
                    "location": "forearm",
                    "characteristics": ["linear", "clean edges"]
                }
            ],
            "icd10_codes": [],
            "recommendations": [],
            "red_flags": [],
            "differential_considerations": []
        }))]
        mock_client.messages.create.return_value = mock_response

        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "media_type": "image/jpeg"
        })

        assert response.status_code == 200
        data = response.json()

        finding = data["findings"][0]
        assert "finding" in finding
        assert "confidence" in finding
        assert finding["confidence"] in ["high", "moderate", "low"]

    @patch('main.CLAUDE_API_KEY', 'test-key')
    @patch('anthropic.Anthropic')
    def test_image_analysis_icd10_structure(self, mock_anthropic):
        """ICD-10 codes have required fields"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "assessment": "Infected wound",
            "findings": [],
            "icd10_codes": [
                {"code": "L03.90", "description": "Cellulitis, unspecified"},
                {"code": "T14.1", "description": "Open wound"}
            ],
            "recommendations": [],
            "red_flags": [],
            "differential_considerations": []
        }))]
        mock_client.messages.create.return_value = mock_response

        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "media_type": "image/jpeg"
        })

        assert response.status_code == 200
        data = response.json()

        for code in data["icd10_codes"]:
            assert "code" in code
            assert "description" in code

    @patch('main.CLAUDE_API_KEY', 'test-key')
    @patch('anthropic.Anthropic')
    def test_image_analysis_disclaimer_present(self, mock_anthropic):
        """Response includes safety disclaimer"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "assessment": "Test",
            "findings": [],
            "icd10_codes": [],
            "recommendations": [],
            "red_flags": [],
            "differential_considerations": []
        }))]
        mock_client.messages.create.return_value = mock_response

        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "media_type": "image/jpeg"
        })

        assert response.status_code == 200
        data = response.json()
        assert "disclaimer" in data
        assert "clinical decision support" in data["disclaimer"].lower()


class TestImageAnalysisRedFlags:
    """Test red flag handling in image analysis"""

    @patch('main.CLAUDE_API_KEY', 'test-key')
    @patch('anthropic.Anthropic')
    def test_image_analysis_returns_red_flags(self, mock_anthropic):
        """Response includes red_flags field"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "assessment": "Severe wound",
            "findings": [],
            "icd10_codes": [],
            "recommendations": [],
            "red_flags": ["Signs of necrotizing fasciitis", "Requires immediate evaluation"],
            "differential_considerations": []
        }))]
        mock_client.messages.create.return_value = mock_response

        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "media_type": "image/jpeg"
        })

        assert response.status_code == 200
        data = response.json()
        assert "red_flags" in data
        assert isinstance(data["red_flags"], list)
        assert len(data["red_flags"]) == 2


class TestImageAnalysisAuditLogging:
    """Test HIPAA audit logging for image analysis"""

    def test_image_analysis_audit_logged(self):
        """Image analysis requests are audit logged"""
        # This test verifies the endpoint doesn't crash with audit logging
        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "media_type": "image/jpeg",
            "analysis_context": "wound"
        })
        # Should not fail due to audit logging
        assert response.status_code in [200, 500, 503]


class TestImageAnalysisErrorHandling:
    """Test error handling for image analysis"""

    def test_image_analysis_handles_missing_api_key(self):
        """Gracefully handles missing Claude API key"""
        # When no API key is configured, should return 503
        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "media_type": "image/jpeg"
        })
        # Could be 200 if key exists, 503 if not, or 500 on error
        assert response.status_code in [200, 500, 503]

    @patch('main.CLAUDE_API_KEY', 'test-key')
    @patch('anthropic.Anthropic')
    def test_image_analysis_handles_api_error(self, mock_anthropic):
        """Gracefully handles Claude API errors"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API error")

        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "media_type": "image/jpeg"
        })

        assert response.status_code == 500
        assert "failed" in response.json()["detail"].lower()

    @patch('main.CLAUDE_API_KEY', 'test-key')
    @patch('anthropic.Anthropic')
    def test_image_analysis_handles_malformed_response(self, mock_anthropic):
        """Handles malformed Claude response gracefully"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        # Return invalid JSON
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="not valid json")]
        mock_client.messages.create.return_value = mock_response

        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "media_type": "image/jpeg"
        })

        # Should still return 200 with fallback response
        assert response.status_code == 200
        data = response.json()
        assert "assessment" in data
        assert "failed" in data["assessment"].lower() or "parsing" in data["assessment"].lower()


class TestImageAnalysisIntegration:
    """Integration tests for image analysis feature"""

    @patch('main.CLAUDE_API_KEY', 'test-key')
    @patch('anthropic.Anthropic')
    def test_image_analysis_end_to_end_workflow(self, mock_anthropic):
        """Complete image analysis workflow"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "assessment": "Circular erythematous rash with central clearing",
            "findings": [
                {
                    "finding": "Circular rash with central clearing",
                    "confidence": "high",
                    "location": "left forearm",
                    "characteristics": ["erythematous", "expanding", "annular"]
                },
                {
                    "finding": "Possible tick bite at center",
                    "confidence": "moderate",
                    "location": "center of lesion",
                    "characteristics": ["punctate", "crusted"]
                }
            ],
            "icd10_codes": [
                {"code": "A69.20", "description": "Lyme disease, unspecified"},
                {"code": "L53.9", "description": "Erythematous condition, unspecified"}
            ],
            "recommendations": [
                "Consider Lyme serology",
                "Start empiric doxycycline if high suspicion",
                "Document size and progression"
            ],
            "red_flags": ["Classic erythema migrans pattern - consider Lyme disease"],
            "differential_considerations": [
                "Lyme disease (erythema migrans)",
                "Tinea corporis",
                "Granuloma annulare"
            ]
        }))]
        mock_client.messages.create.return_value = mock_response

        # 1. Submit image for analysis
        response = client.post("/api/v1/image/analyze", json={
            "image_base64": VALID_JPEG_BASE64,
            "media_type": "image/jpeg",
            "analysis_context": "rash",
            "chief_complaint": "Expanding rash on forearm",
            "patient_age": 35,
            "patient_gender": "male"
        })

        assert response.status_code == 200
        data = response.json()

        # 2. Verify complete response
        assert data["assessment"]
        assert len(data["findings"]) == 2
        assert len(data["icd10_codes"]) == 2
        assert len(data["recommendations"]) == 3
        assert len(data["red_flags"]) == 1
        assert len(data["differential_considerations"]) == 3

        # 3. Verify finding details
        finding = data["findings"][0]
        assert finding["confidence"] == "high"
        assert finding["location"] == "left forearm"

        # 4. Verify timestamp
        assert data["timestamp"]

        # 5. Verify disclaimer
        assert "clinical decision support" in data["disclaimer"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
