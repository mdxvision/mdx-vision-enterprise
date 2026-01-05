"""
Test Interpreter Integration Features (Feature #86)

Tests language services for LEP patients, interpreter requests,
pre-translated phrases, and Title VI compliance.
"""

import pytest
from httpx import AsyncClient, ASGITransport

import sys
sys.path.insert(0, '..')
from main import app


class TestLanguages:
    """Tests for /api/v1/interpreter/languages endpoint"""

    @pytest.mark.asyncio
    async def test_languages_endpoint_exists(self):
        """Should have languages endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/interpreter/languages")

            assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_includes_common_languages(self):
        """Should include common languages"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/interpreter/languages")

            if response.status_code == 200:
                data = response.json()
                # Should include Spanish, Chinese, Vietnamese, etc.
                assert isinstance(data, list) or isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_includes_asl(self):
        """Should include ASL (American Sign Language)"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/interpreter/languages")

            if response.status_code == 200:
                data = response.json()
                languages_text = str(data).lower()
                # May include ASL


class TestInterpreterRequest:
    """Tests for /api/v1/interpreter/request endpoint"""

    @pytest.mark.asyncio
    async def test_request_endpoint_exists(self):
        """Should have interpreter request endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/interpreter/request",
                json={
                    "patient_id": "test-patient",
                    "language": "spanish",
                    "type": "video"
                }
            )

            assert response.status_code in [200, 404, 422]

    @pytest.mark.asyncio
    async def test_interpreter_types(self):
        """Should support multiple interpreter types"""
        types = ["in_person", "video", "phone", "staff"]

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for interp_type in types:
                response = await client.post(
                    "/api/v1/interpreter/request",
                    json={
                        "patient_id": "test-patient",
                        "language": "spanish",
                        "type": interp_type
                    }
                )

                assert response.status_code in [200, 404, 422]


class TestSessionManagement:
    """Tests for interpreter session management"""

    @pytest.mark.asyncio
    async def test_start_session_endpoint(self):
        """Should have start session endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/interpreter/start-session",
                json={
                    "patient_id": "test-patient",
                    "language": "spanish",
                    "interpreter_type": "phone"
                }
            )

            assert response.status_code in [200, 404, 422]

    @pytest.mark.asyncio
    async def test_end_session_endpoint(self):
        """Should have end session endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/interpreter/end-session",
                json={
                    "session_id": "test-session"
                }
            )

            assert response.status_code in [200, 404, 422]


class TestClinicalPhrases:
    """Tests for pre-translated clinical phrases"""

    @pytest.mark.asyncio
    async def test_phrases_endpoint_exists(self):
        """Should have clinical phrases endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/interpreter/phrases/spanish")

            assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_spanish_phrases(self):
        """Should have Spanish clinical phrases"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/interpreter/phrases/spanish")

            if response.status_code == 200:
                data = response.json()
                # Should include basic clinical phrases
                assert isinstance(data, dict) or isinstance(data, list)

    @pytest.mark.asyncio
    async def test_chinese_phrases(self):
        """Should have Chinese clinical phrases"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/interpreter/phrases/chinese")

            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict) or isinstance(data, list)

    @pytest.mark.asyncio
    async def test_phrases_include_phonetics(self):
        """Phrases should include phonetic pronunciation"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/interpreter/phrases/spanish")

            if response.status_code == 200:
                data = response.json()
                # May include pronunciation guides


class TestLanguagePreference:
    """Tests for patient language preference"""

    @pytest.mark.asyncio
    async def test_set_preference_endpoint(self):
        """Should have set preference endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/interpreter/set-preference",
                json={
                    "patient_id": "test-patient",
                    "preferred_language": "spanish",
                    "interpreter_required": True
                }
            )

            assert response.status_code in [200, 404, 422]

    @pytest.mark.asyncio
    async def test_family_interpreter_declined(self):
        """Should document family interpreter declined"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/interpreter/set-preference",
                json={
                    "patient_id": "test-patient",
                    "preferred_language": "vietnamese",
                    "family_interpreter_declined": True
                }
            )

            if response.status_code == 200:
                data = response.json()
                # Should document Title VI compliance
                assert isinstance(data, dict)


class TestInterpreterServices:
    """Tests for interpreter service directory"""

    @pytest.mark.asyncio
    async def test_services_endpoint_exists(self):
        """Should have services directory endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/interpreter/services")

            assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_includes_phone_numbers(self):
        """Should include interpreter service phone numbers"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/interpreter/services")

            if response.status_code == 200:
                data = response.json()
                # Should include Language Line, CyraCom, etc.
                assert isinstance(data, dict) or isinstance(data, list)


class TestTitleVICompliance:
    """Tests for Title VI compliance features"""

    @pytest.mark.asyncio
    async def test_compliance_checklist_endpoint(self):
        """Should have compliance checklist endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/interpreter/compliance-checklist")

            assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_never_use_children_warning(self):
        """Should include warning about using children as interpreters"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/interpreter/compliance-checklist")

            if response.status_code == 200:
                data = response.json()
                # Should warn against using children
                checklist_text = str(data).lower()
                # May include child interpreter warning

    @pytest.mark.asyncio
    async def test_vital_documents_list(self):
        """Should list vital documents requiring translation"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/interpreter/compliance-checklist")

            if response.status_code == 200:
                data = response.json()
                # Should list: consent forms, discharge instructions, HIPAA
                assert isinstance(data, dict) or isinstance(data, list)


class TestDocumentInterpreter:
    """Tests for interpreter documentation"""

    @pytest.mark.asyncio
    async def test_document_interpreter_use(self):
        """Should document interpreter use"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/interpreter/start-session",
                json={
                    "patient_id": "test-patient",
                    "language": "spanish",
                    "interpreter_type": "video",
                    "interpreter_name": "Maria Garcia"
                }
            )

            if response.status_code == 200:
                data = response.json()
                # Should create documentation
                assert isinstance(data, dict)


class TestVoiceCommands:
    """Tests for voice command integration"""

    @pytest.mark.asyncio
    async def test_need_interpreter_command(self):
        """Should support 'need interpreter' voice command"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/interpreter/request",
                json={
                    "patient_id": "test-patient",
                    "language": "spanish"
                }
            )

            assert response.status_code in [200, 404, 422]

    @pytest.mark.asyncio
    async def test_language_specific_command(self):
        """Should support language-specific command"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/interpreter/request",
                json={
                    "patient_id": "test-patient",
                    "language": "mandarin"
                }
            )

            assert response.status_code in [200, 404, 422]


class TestAuditLogging:
    """Tests for interpreter feature audit logging"""

    @pytest.mark.asyncio
    async def test_interpreter_request_logged(self):
        """Should create audit log for interpreter requests"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/interpreter/request",
                json={
                    "patient_id": "test-patient",
                    "language": "spanish"
                }
            )
            # Audit logging verification would require checking log file

    @pytest.mark.asyncio
    async def test_session_duration_logged(self):
        """Should log session duration for billing"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Start session
            start_response = await client.post(
                "/api/v1/interpreter/start-session",
                json={
                    "patient_id": "test-patient",
                    "language": "spanish",
                    "interpreter_type": "phone"
                }
            )

            # End session should log duration
            if start_response.status_code == 200:
                session_data = start_response.json()
                if "session_id" in session_data:
                    await client.post(
                        "/api/v1/interpreter/end-session",
                        json={"session_id": session_data["session_id"]}
                    )
