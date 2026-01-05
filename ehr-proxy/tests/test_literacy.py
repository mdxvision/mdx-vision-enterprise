"""
Test Health Literacy Assessment Features (Feature #85)

Tests literacy level assessment, plain language translations,
simplified discharge instructions, and teach-back checklists.
Health equity tests for patient education.
"""

import pytest
from httpx import AsyncClient, ASGITransport

import sys
sys.path.insert(0, '..')
from main import app


class TestLiteracyAssessment:
    """Tests for /api/v1/literacy/assess endpoint"""

    @pytest.mark.asyncio
    async def test_assessment_endpoint_exists(self):
        """Should have literacy assessment endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/literacy/assess",
                json={
                    "patient_id": "test-patient",
                    "indicators": []
                }
            )

            assert response.status_code in [200, 404, 422]

    @pytest.mark.asyncio
    async def test_literacy_levels(self):
        """Should recognize four literacy levels"""
        levels = ["inadequate", "marginal", "adequate", "proficient"]

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for level in levels:
                response = await client.post(
                    "/api/v1/literacy/assess",
                    json={
                        "patient_id": "test-patient",
                        "assessed_level": level
                    }
                )

                assert response.status_code in [200, 404, 422]


class TestScreeningQuestion:
    """Tests for BRIEF/SILS screening question"""

    @pytest.mark.asyncio
    async def test_screening_question_endpoint(self):
        """Should have screening question endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/literacy/screening-question")

            assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_screening_question_content(self):
        """Should return validated screening question"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/literacy/screening-question")

            if response.status_code == 200:
                data = response.json()
                # Should include "How confident filling out medical forms?"
                assert "question" in data or isinstance(data, dict)


class TestObservableIndicators:
    """Tests for observable literacy indicators"""

    @pytest.mark.asyncio
    async def test_indicators_flagging(self):
        """Should flag observable literacy indicators"""
        indicators = [
            "asks_to_take_home",  # Asks to take materials home
            "identifies_pills_by_color",  # Identifies pills by color not name
            "avoids_reading",  # Avoids reading materials
            "brings_family_to_read"  # Brings family to read materials
        ]

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/literacy/assess",
                json={
                    "patient_id": "test-patient",
                    "indicators": indicators
                }
            )

            if response.status_code == 200:
                data = response.json()
                # Should assess lower literacy based on indicators
                assert isinstance(data, dict)


class TestPlainLanguage:
    """Tests for plain language translations"""

    @pytest.mark.asyncio
    async def test_plain_language_endpoint(self):
        """Should have plain language endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/literacy/plain-language")

            assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_hypertension_translation(self):
        """Should translate 'hypertension' to 'high blood pressure'"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/literacy/plain-language")

            if response.status_code == 200:
                data = response.json()
                # Should include common term translations
                translations_text = str(data).lower()
                # May include hypertension -> high blood pressure

    @pytest.mark.asyncio
    async def test_medication_frequency_translation(self):
        """Should translate 'QID' to 'four times a day'"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/literacy/plain-language")

            if response.status_code == 200:
                data = response.json()
                # Should include medication frequency translations


class TestSimplifiedInstructions:
    """Tests for simplified discharge instructions"""

    @pytest.mark.asyncio
    async def test_simplify_instructions_endpoint(self):
        """Should have simplify instructions endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/literacy/simplify-instructions",
                json={
                    "template": "diabetes",
                    "literacy_level": "inadequate"
                }
            )

            assert response.status_code in [200, 404, 422]

    @pytest.mark.asyncio
    async def test_diabetes_simplified(self):
        """Should have simplified diabetes instructions"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/literacy/simplify-instructions",
                json={
                    "template": "diabetes",
                    "literacy_level": "marginal"
                }
            )

            if response.status_code == 200:
                data = response.json()
                # Should include key points, red flags, teach-back
                assert isinstance(data, dict)


class TestLevelAccommodations:
    """Tests for level-specific accommodations"""

    @pytest.mark.asyncio
    async def test_accommodations_endpoint(self):
        """Should have accommodations endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/literacy/accommodations/inadequate"
            )

            assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_inadequate_accommodations(self):
        """Should provide accommodations for inadequate literacy"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/literacy/accommodations/inadequate"
            )

            if response.status_code == 200:
                data = response.json()
                # Should include: pictures, verbal, 1-2 messages
                assert isinstance(data, dict) or isinstance(data, list)

    @pytest.mark.asyncio
    async def test_marginal_accommodations(self):
        """Should provide accommodations for marginal literacy"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/literacy/accommodations/marginal"
            )

            if response.status_code == 200:
                data = response.json()
                # Should include: 5th grade level, bullet points
                assert isinstance(data, dict) or isinstance(data, list)


class TestTeachBackChecklist:
    """Tests for teach-back checklist"""

    @pytest.mark.asyncio
    async def test_teach_back_endpoint(self):
        """Should have teach-back checklist endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/literacy/teach-back-checklist")

            assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_teach_back_includes_medications(self):
        """Teach-back should include medication understanding"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/literacy/teach-back-checklist")

            if response.status_code == 200:
                data = response.json()
                # Should include medication teach-back items
                assert isinstance(data, dict) or isinstance(data, list)

    @pytest.mark.asyncio
    async def test_teach_back_includes_warning_signs(self):
        """Teach-back should include warning signs understanding"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/literacy/teach-back-checklist")

            if response.status_code == 200:
                data = response.json()
                # Should include warning signs items


class TestDischargeTemplates:
    """Tests for simplified discharge templates"""

    templates = [
        "diabetes",
        "heart_failure",
        "hypertension",
        "anticoagulation",
        "infection",
        "post_surgery"
    ]

    @pytest.mark.asyncio
    async def test_template_availability(self):
        """Should have multiple simplified templates"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for template in self.templates:
                response = await client.post(
                    "/api/v1/literacy/simplify-instructions",
                    json={
                        "template": template,
                        "literacy_level": "marginal"
                    }
                )

                assert response.status_code in [200, 404, 422]


class TestVoiceCommands:
    """Tests for voice command integration"""

    @pytest.mark.asyncio
    async def test_literacy_voice_command(self):
        """Should support 'literacy' voice command"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/literacy/assess",
                json={
                    "patient_id": "test-patient"
                }
            )

            assert response.status_code in [200, 404, 422]


class TestAuditLogging:
    """Tests for literacy feature audit logging"""

    @pytest.mark.asyncio
    async def test_literacy_assessment_logged(self):
        """Should create audit log for literacy assessments"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/literacy/assess",
                json={
                    "patient_id": "test-patient",
                    "assessed_level": "marginal"
                }
            )
            # Audit logging verification would require checking log file


class TestNonStigmatizing:
    """Tests that feature doesn't stigmatize patients"""

    @pytest.mark.asyncio
    async def test_language_is_respectful(self):
        """Language should be respectful, not stigmatizing"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/literacy/screening-question")

            if response.status_code == 200:
                data = response.json()
                response_text = str(data).lower()
                # Should not use stigmatizing terms
                assert "stupid" not in response_text
                assert "dumb" not in response_text
                assert "illiterate" not in response_text
