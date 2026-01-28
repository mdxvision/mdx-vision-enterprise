"""
Tests for Tier 1 Knowledge Source Ingestion Functions
OpenFDA, ClinicalTrials.gov, RxNorm/UMLS
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from dataclasses import asdict

import sys
sys.path.insert(0, '/Users/rafaelrodriguez/projects/mdx-vision-enterprise/ehr-proxy')


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE TYPE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSourceTypes:
    """New SourceType values exist"""

    def test_openfda_source_type(self):
        from rag import SourceType
        assert SourceType.OPENFDA.value == "openfda"

    def test_clinical_trial_source_type(self):
        from rag import SourceType
        assert SourceType.CLINICAL_TRIAL.value == "clinical_trial"

    def test_umls_terminology_source_type(self):
        from rag import SourceType
        assert SourceType.UMLS_TERMINOLOGY.value == "umls_terminology"


# ═══════════════════════════════════════════════════════════════════════════════
# OPENFDA TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestOpenFDA:
    """Tests for OpenFDA drug label ingestion"""

    @pytest.fixture
    def km(self):
        from rag import KnowledgeManager, RAGEngine
        mock_rag = MagicMock(spec=RAGEngine)
        mock_rag.initialized = True
        mock_rag.add_document = MagicMock(return_value=True)
        manager = KnowledgeManager.__new__(KnowledgeManager)
        manager.rag_engine = mock_rag
        manager.versions = {}
        manager.feedback = []
        manager.collections = {}
        manager.conflicts = []
        manager.analytics = {}
        return manager

    @pytest.mark.asyncio
    async def test_search_openfda_returns_results(self, km):
        """Should fetch drug labels from OpenFDA API"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "test-label-1",
                    "openfda": {
                        "generic_name": ["metformin"],
                        "brand_name": ["Glucophage"]
                    },
                    "indications_and_usage": ["Type 2 diabetes management"],
                    "contraindications": ["Renal impairment"],
                    "warnings_and_cautions": ["Lactic acidosis risk"],
                    "dosage_and_administration": ["500mg twice daily"],
                    "adverse_reactions": ["GI disturbances"],
                    "drug_interactions": ["Contrast dye interaction"],
                    "boxed_warning": ["Lactic acidosis - rare but serious"]
                }
            ]
        }

        with patch('httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            results = await km.search_openfda("metformin")
            assert len(results) == 1
            assert results[0]["openfda"]["generic_name"][0] == "metformin"

    @pytest.mark.asyncio
    async def test_ingest_openfda_drug(self, km):
        """Should ingest drug labels into knowledge base"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "label-123",
                    "openfda": {
                        "generic_name": ["warfarin"],
                        "brand_name": ["Coumadin"]
                    },
                    "indications_and_usage": ["Anticoagulation therapy"],
                    "contraindications": ["Active bleeding"],
                    "boxed_warning": ["Bleeding risk"],
                    "drug_interactions": ["Many drug and food interactions"],
                    "effective_time": "20240101"
                }
            ]
        }

        with patch('httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            count, ids = await km.ingest_openfda_drug("warfarin")
            assert count == 1
            assert "label-123" in ids

            # Verify add_document was called with correct source type
            call_args = km.rag_engine.add_document.call_args[0][0]
            assert call_args.source_type.value == "openfda"
            assert "warfarin" in call_args.title.lower() or "Coumadin" in call_args.title
            assert call_args.source_name == "U.S. FDA / OpenFDA"

    @pytest.mark.asyncio
    async def test_ingest_openfda_handles_empty(self, km):
        """Should handle no results gracefully"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}

        with patch('httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            count, ids = await km.ingest_openfda_drug("nonexistentdrug12345")
            assert count == 0
            assert ids == []

    @pytest.mark.asyncio
    async def test_ingest_openfda_batch(self, km):
        """Should ingest multiple drugs"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{
                "id": "label-1",
                "openfda": {"generic_name": ["test"], "brand_name": []},
                "indications_and_usage": ["Test indication"]
            }]
        }

        with patch('httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            results = await km.ingest_openfda_batch(["aspirin", "ibuprofen"])
            assert "aspirin" in results
            assert "ibuprofen" in results


# ═══════════════════════════════════════════════════════════════════════════════
# CLINICALTRIALS.GOV TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestClinicalTrials:
    """Tests for ClinicalTrials.gov ingestion"""

    @pytest.fixture
    def km(self):
        from rag import KnowledgeManager, RAGEngine
        mock_rag = MagicMock(spec=RAGEngine)
        mock_rag.initialized = True
        mock_rag.add_document = MagicMock(return_value=True)
        manager = KnowledgeManager.__new__(KnowledgeManager)
        manager.rag_engine = mock_rag
        manager.versions = {}
        manager.feedback = []
        manager.collections = {}
        manager.conflicts = []
        manager.analytics = {}
        return manager

    @pytest.mark.asyncio
    async def test_search_clinical_trials(self, km):
        """Should fetch trials from ClinicalTrials.gov API v2"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "studies": [
                {
                    "protocolSection": {
                        "identificationModule": {
                            "nctId": "NCT12345678",
                            "briefTitle": "Test Trial for Heart Failure",
                            "officialTitle": "A Phase 3 Study of Drug X in Heart Failure"
                        },
                        "descriptionModule": {
                            "briefSummary": "This trial evaluates Drug X..."
                        },
                        "statusModule": {
                            "overallStatus": "RECRUITING",
                            "studyFirstPostDateStruct": {"date": "2024-01-15"}
                        },
                        "designModule": {
                            "phases": ["PHASE3"]
                        },
                        "armsInterventionsModule": {
                            "interventions": [
                                {"name": "Drug X", "type": "DRUG"}
                            ]
                        },
                        "conditionsModule": {
                            "conditions": ["Heart Failure"]
                        },
                        "sponsorCollaboratorsModule": {
                            "leadSponsor": {"name": "Pharma Corp"}
                        },
                        "contactsLocationsModule": {
                            "locations": [
                                {"facility": "Mayo Clinic", "city": "Rochester", "state": "MN"}
                            ]
                        },
                        "eligibilityModule": {
                            "eligibilityCriteria": "Adults 18+ with NYHA Class II-IV"
                        }
                    }
                }
            ]
        }

        with patch('httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            results = await km.search_clinical_trials("heart failure", max_results=5)
            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_ingest_clinical_trials(self, km):
        """Should ingest trials into knowledge base"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "studies": [
                {
                    "protocolSection": {
                        "identificationModule": {
                            "nctId": "NCT99999999",
                            "briefTitle": "Novel CAR-T for Leukemia",
                            "officialTitle": "Phase 2 CAR-T Cell Therapy"
                        },
                        "descriptionModule": {
                            "briefSummary": "Evaluating CAR-T therapy..."
                        },
                        "statusModule": {
                            "overallStatus": "RECRUITING",
                            "studyFirstPostDateStruct": {"date": "2024-06-01"}
                        },
                        "designModule": {"phases": ["PHASE2"]},
                        "armsInterventionsModule": {
                            "interventions": [{"name": "CAR-T Cells", "type": "BIOLOGICAL"}]
                        },
                        "conditionsModule": {"conditions": ["Leukemia"]},
                        "sponsorCollaboratorsModule": {"leadSponsor": {"name": "NCI"}},
                        "contactsLocationsModule": {"locations": []},
                        "eligibilityModule": {"eligibilityCriteria": "Ages 18-75"}
                    }
                }
            ]
        }

        with patch('httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            count, nct_ids = await km.ingest_clinical_trials("leukemia", max_trials=5)
            assert count == 1
            assert "NCT99999999" in nct_ids

            call_args = km.rag_engine.add_document.call_args[0][0]
            assert call_args.source_type.value == "clinical_trial"
            assert call_args.source_name == "ClinicalTrials.gov"
            assert "NCT99999999" in call_args.source_url

    @pytest.mark.asyncio
    async def test_ingest_trials_skips_no_nctid(self, km):
        """Should skip trials without NCT ID"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "studies": [
                {"protocolSection": {"identificationModule": {}}}
            ]
        }

        with patch('httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            count, nct_ids = await km.ingest_clinical_trials("test")
            assert count == 0


# ═══════════════════════════════════════════════════════════════════════════════
# RXNORM / UMLS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRxNorm:
    """Tests for RxNorm drug terminology ingestion"""

    @pytest.fixture
    def km(self):
        from rag import KnowledgeManager, RAGEngine
        mock_rag = MagicMock(spec=RAGEngine)
        mock_rag.initialized = True
        mock_rag.add_document = MagicMock(return_value=True)
        manager = KnowledgeManager.__new__(KnowledgeManager)
        manager.rag_engine = mock_rag
        manager.versions = {}
        manager.feedback = []
        manager.collections = {}
        manager.conflicts = []
        manager.analytics = {}
        return manager

    @pytest.mark.asyncio
    async def test_search_rxnorm(self, km):
        """Should search RxNorm for drug concepts"""
        approx_response = MagicMock()
        approx_response.status_code = 200
        approx_response.json.return_value = {
            "approximateGroup": {
                "candidate": [
                    {"rxcui": "6809", "name": "metformin", "score": "100"}
                ]
            }
        }

        props_response = MagicMock()
        props_response.status_code = 200
        props_response.json.return_value = {
            "propConceptGroup": {
                "propConcept": [
                    {"propName": "TTY", "propValue": "IN"},
                    {"propName": "SNOMEDCT", "propValue": "109081006"},
                    {"propName": "ATC", "propValue": "A10BA02"}
                ]
            }
        }

        interactions_response = MagicMock()
        interactions_response.status_code = 200
        interactions_response.json.return_value = {
            "interactionTypeGroup": [
                {
                    "interactionType": [
                        {
                            "interactionPair": [
                                {"description": "Metformin + Contrast dye may increase lactic acidosis risk"}
                            ]
                        }
                    ]
                }
            ]
        }

        with patch('httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=[
                approx_response, props_response, interactions_response
            ])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            results = await km.search_rxnorm("metformin")
            assert len(results) == 1
            assert results[0]["rxcui"] == "6809"
            assert results[0]["name"] == "metformin"
            assert "TTY" in results[0]["properties"]
            assert len(results[0]["interactions"]) == 1

    @pytest.mark.asyncio
    async def test_ingest_rxnorm_drug(self, km):
        """Should ingest drug terminology into knowledge base"""
        approx_response = MagicMock()
        approx_response.status_code = 200
        approx_response.json.return_value = {
            "approximateGroup": {
                "candidate": [
                    {"rxcui": "11289", "name": "warfarin", "score": "100"}
                ]
            }
        }

        props_response = MagicMock()
        props_response.status_code = 200
        props_response.json.return_value = {
            "propConceptGroup": {
                "propConcept": [
                    {"propName": "TTY", "propValue": "IN"},
                    {"propName": "DRUGBANK", "propValue": "DB00682"}
                ]
            }
        }

        interactions_response = MagicMock()
        interactions_response.status_code = 404
        interactions_response.json.return_value = {}

        with patch('httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=[
                approx_response, props_response, interactions_response
            ])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            count, rxcuis = await km.ingest_rxnorm_drug("warfarin")
            assert count == 1
            assert "11289" in rxcuis

            call_args = km.rag_engine.add_document.call_args[0][0]
            assert call_args.source_type.value == "umls_terminology"
            assert call_args.source_name == "NLM RxNorm / DrugBank"
            assert "warfarin" in call_args.title.lower()

    @pytest.mark.asyncio
    async def test_search_rxnorm_no_results(self, km):
        """Should handle no results gracefully"""
        approx_response = MagicMock()
        approx_response.status_code = 200
        approx_response.json.return_value = {
            "approximateGroup": {"candidate": []}
        }

        with patch('httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=approx_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            results = await km.search_rxnorm("nonexistent12345")
            assert results == []

    @pytest.mark.asyncio
    async def test_ingest_rxnorm_batch(self, km):
        """Should ingest multiple drugs"""
        approx_response = MagicMock()
        approx_response.status_code = 200
        approx_response.json.return_value = {
            "approximateGroup": {
                "candidate": [{"rxcui": "12345", "name": "testdrug", "score": "100"}]
            }
        }

        props_response = MagicMock()
        props_response.status_code = 200
        props_response.json.return_value = {
            "propConceptGroup": {"propConcept": [{"propName": "TTY", "propValue": "IN"}]}
        }

        interactions_response = MagicMock()
        interactions_response.status_code = 404

        with patch('httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=[
                approx_response, props_response, interactions_response,
                approx_response, props_response, interactions_response,
            ])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            results = await km.ingest_rxnorm_batch(["aspirin", "lisinopril"])
            assert "aspirin" in results
            assert "lisinopril" in results


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL HELPER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestModuleHelpers:
    """Tests for module-level convenience functions"""

    def test_ingest_from_openfda_exists(self):
        from rag import ingest_from_openfda
        assert callable(ingest_from_openfda)

    def test_ingest_openfda_batch_exists(self):
        from rag import ingest_openfda_batch
        assert callable(ingest_openfda_batch)

    def test_ingest_from_clinical_trials_exists(self):
        from rag import ingest_from_clinical_trials
        assert callable(ingest_from_clinical_trials)

    def test_ingest_from_rxnorm_exists(self):
        from rag import ingest_from_rxnorm
        assert callable(ingest_from_rxnorm)

    def test_ingest_rxnorm_batch_exists(self):
        from rag import ingest_rxnorm_batch
        assert callable(ingest_rxnorm_batch)
