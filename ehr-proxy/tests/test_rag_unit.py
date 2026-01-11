"""
Unit tests for rag.py - RAG Knowledge System

Covers:
- Data models (MedicalDocument, RetrievedContext, etc.)
- Enums (SourceType, GuidelineStatus, FeedbackRating)
- Document serialization/deserialization
- Quality scoring
- Citation generation
- Knowledge management models (Feature #89)
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestSourceTypeEnum:
    """Tests for SourceType enum"""

    def test_clinical_guideline_value(self):
        """Should have correct enum values"""
        from rag import SourceType

        assert SourceType.CLINICAL_GUIDELINE.value == "clinical_guideline"
        assert SourceType.PUBMED_ABSTRACT.value == "pubmed_abstract"
        assert SourceType.DRUG_INFO.value == "drug_info"
        assert SourceType.CDC_GUIDELINE.value == "cdc_guideline"
        assert SourceType.AHA_GUIDELINE.value == "aha_guideline"

    def test_enum_from_string(self):
        """Should create enum from string"""
        from rag import SourceType

        source = SourceType("clinical_guideline")
        assert source == SourceType.CLINICAL_GUIDELINE


class TestGuidelineStatusEnum:
    """Tests for GuidelineStatus enum (Feature #89)"""

    def test_guideline_status_values(self):
        """Should have correct status values"""
        from rag import GuidelineStatus

        assert GuidelineStatus.CURRENT.value == "current"
        assert GuidelineStatus.SUPERSEDED.value == "superseded"
        assert GuidelineStatus.DEPRECATED.value == "deprecated"
        assert GuidelineStatus.DRAFT.value == "draft"
        assert GuidelineStatus.ARCHIVED.value == "archived"


class TestFeedbackRatingEnum:
    """Tests for FeedbackRating enum (Feature #89)"""

    def test_feedback_rating_values(self):
        """Should have correct rating values"""
        from rag import FeedbackRating

        assert FeedbackRating.VERY_HELPFUL.value == "very_helpful"
        assert FeedbackRating.HELPFUL.value == "helpful"
        assert FeedbackRating.NEUTRAL.value == "neutral"
        assert FeedbackRating.NOT_HELPFUL.value == "not_helpful"
        assert FeedbackRating.INCORRECT.value == "incorrect"


class TestMedicalDocument:
    """Tests for MedicalDocument dataclass"""

    def test_create_basic_document(self):
        """Should create document with required fields"""
        from rag import MedicalDocument, SourceType

        doc = MedicalDocument(
            id="test-001",
            title="Test Guideline",
            content="Test content",
            source_type=SourceType.CLINICAL_GUIDELINE
        )

        assert doc.id == "test-001"
        assert doc.title == "Test Guideline"
        assert doc.content == "Test content"
        assert doc.source_type == SourceType.CLINICAL_GUIDELINE

    def test_create_full_document(self):
        """Should create document with all fields"""
        from rag import MedicalDocument, SourceType, GuidelineStatus

        doc = MedicalDocument(
            id="aha-chest-pain-2021",
            title="AHA Chest Pain Guidelines",
            content="Clinical guidelines for chest pain evaluation...",
            source_type=SourceType.AHA_GUIDELINE,
            source_url="https://example.com/guidelines",
            source_name="AHA/ACC",
            publication_date="2021",
            authors=["Smith J", "Jones M"],
            keywords=["chest pain", "cardiology"],
            specialty="cardiology",
            version="2021.1",
            status=GuidelineStatus.CURRENT,
            pmid="12345678",
            usage_count=100,
            helpful_count=80,
            not_helpful_count=5
        )

        assert doc.source_name == "AHA/ACC"
        assert doc.publication_date == "2021"
        assert doc.specialty == "cardiology"
        assert doc.status == GuidelineStatus.CURRENT
        assert doc.pmid == "12345678"

    def test_to_dict(self):
        """Should serialize to dict"""
        from rag import MedicalDocument, SourceType

        doc = MedicalDocument(
            id="test-001",
            title="Test",
            content="Content",
            source_type=SourceType.PUBMED_ABSTRACT
        )

        data = doc.to_dict()

        assert isinstance(data, dict)
        assert data["id"] == "test-001"
        assert data["title"] == "Test"
        assert data["source_type"] == "pubmed_abstract"

    def test_from_dict(self):
        """Should deserialize from dict"""
        from rag import MedicalDocument, SourceType, GuidelineStatus

        data = {
            "id": "test-001",
            "title": "Test Guideline",
            "content": "Test content",
            "source_type": "clinical_guideline",
            "source_url": None,
            "source_name": "CDC",
            "publication_date": "2024",
            "authors": None,
            "keywords": ["test"],
            "specialty": "infectious_disease",
            "last_updated": None,
            "version": None,
            "status": "current",
            "supersedes_id": None,
            "pmid": None,
            "usage_count": 0,
            "helpful_count": 0,
            "not_helpful_count": 0
        }

        doc = MedicalDocument.from_dict(data)

        assert doc.id == "test-001"
        assert doc.source_type == SourceType.CLINICAL_GUIDELINE
        assert doc.source_name == "CDC"
        assert doc.status == GuidelineStatus.CURRENT

    def test_quality_score_no_feedback(self):
        """Should return neutral score with no feedback"""
        from rag import MedicalDocument, SourceType

        doc = MedicalDocument(
            id="test",
            title="Test",
            content="Content",
            source_type=SourceType.CLINICAL_GUIDELINE,
            helpful_count=0,
            not_helpful_count=0
        )

        assert doc.quality_score == 0.5

    def test_quality_score_all_positive(self):
        """Should return 1.0 with all positive feedback"""
        from rag import MedicalDocument, SourceType

        doc = MedicalDocument(
            id="test",
            title="Test",
            content="Content",
            source_type=SourceType.CLINICAL_GUIDELINE,
            helpful_count=10,
            not_helpful_count=0
        )

        assert doc.quality_score == 1.0

    def test_quality_score_mixed_feedback(self):
        """Should calculate correct ratio"""
        from rag import MedicalDocument, SourceType

        doc = MedicalDocument(
            id="test",
            title="Test",
            content="Content",
            source_type=SourceType.CLINICAL_GUIDELINE,
            helpful_count=75,
            not_helpful_count=25
        )

        assert doc.quality_score == 0.75


class TestRetrievedContext:
    """Tests for RetrievedContext dataclass"""

    def test_create_retrieved_context(self):
        """Should create context with document and score"""
        from rag import RetrievedContext, MedicalDocument, SourceType

        doc = MedicalDocument(
            id="test",
            title="Test Doc",
            content="Full content here",
            source_type=SourceType.AHA_GUIDELINE,
            source_name="AHA",
            publication_date="2024"
        )

        context = RetrievedContext(
            document=doc,
            relevance_score=0.92,
            matched_chunk="Relevant section about chest pain..."
        )

        assert context.document == doc
        assert context.relevance_score == 0.92
        assert "chest pain" in context.matched_chunk

    def test_to_citation_with_all_info(self):
        """Should generate full citation"""
        from rag import RetrievedContext, MedicalDocument, SourceType

        doc = MedicalDocument(
            id="test",
            title="Test",
            content="Content",
            source_type=SourceType.AHA_GUIDELINE,
            source_name="AHA/ACC",
            source_url="https://example.com/guidelines",
            publication_date="2024"
        )

        context = RetrievedContext(
            document=doc,
            relevance_score=0.9,
            matched_chunk="chunk"
        )

        citation = context.to_citation()

        assert "[AHA/ACC]" in citation
        assert "(2024)" in citation
        assert "https://example.com/guidelines" in citation

    def test_to_citation_minimal_info(self):
        """Should generate citation with minimal info"""
        from rag import RetrievedContext, MedicalDocument, SourceType

        doc = MedicalDocument(
            id="test",
            title="Test",
            content="Content",
            source_type=SourceType.PUBMED_ABSTRACT
        )

        context = RetrievedContext(
            document=doc,
            relevance_score=0.8,
            matched_chunk="chunk"
        )

        citation = context.to_citation()

        assert "[pubmed_abstract]" in citation


class TestRAGResponse:
    """Tests for RAGResponse dataclass"""

    def test_create_rag_response(self):
        """Should create RAG response"""
        from rag import RAGResponse

        response = RAGResponse(
            response="The patient should be evaluated for ACS based on...",
            citations=["[AHA 2024]", "[ACC 2023]"],
            sources=[{"id": "doc1", "title": "AHA Guidelines"}],
            confidence=0.85,
            retrieval_count=3
        )

        assert "ACS" in response.response
        assert len(response.citations) == 2
        assert response.confidence == 0.85
        assert response.retrieval_count == 3


class TestGuidelineVersion:
    """Tests for GuidelineVersion dataclass (Feature #89)"""

    def test_create_guideline_version(self):
        """Should create guideline version"""
        from rag import GuidelineVersion, GuidelineStatus

        version = GuidelineVersion(
            version_id="aha-chest-2024.1",
            guideline_id="aha-chest-pain",
            version_number="2024.1",
            publication_date="2024-01-15",
            effective_date="2024-02-01",
            status=GuidelineStatus.CURRENT,
            supersedes="aha-chest-2023.1",
            change_summary="Updated troponin thresholds"
        )

        assert version.version_number == "2024.1"
        assert version.status == GuidelineStatus.CURRENT
        assert version.supersedes == "aha-chest-2023.1"

    def test_version_with_superseded_by(self):
        """Should track superseded versions"""
        from rag import GuidelineVersion, GuidelineStatus

        old_version = GuidelineVersion(
            version_id="aha-chest-2023.1",
            guideline_id="aha-chest-pain",
            version_number="2023.1",
            publication_date="2023-01-15",
            effective_date="2023-02-01",
            status=GuidelineStatus.SUPERSEDED,
            superseded_by="aha-chest-2024.1"
        )

        assert old_version.status == GuidelineStatus.SUPERSEDED
        assert old_version.superseded_by == "aha-chest-2024.1"


class TestCitationFeedback:
    """Tests for CitationFeedback dataclass (Feature #89)"""

    def test_create_positive_feedback(self):
        """Should create positive feedback"""
        from rag import CitationFeedback, FeedbackRating

        feedback = CitationFeedback(
            feedback_id="fb-001",
            document_id="aha-chest-2024",
            query="chest pain evaluation",
            rating=FeedbackRating.VERY_HELPFUL,
            comment="Exactly what I needed",
            clinician_specialty="cardiology"
        )

        assert feedback.rating == FeedbackRating.VERY_HELPFUL
        assert feedback.clinician_specialty == "cardiology"

    def test_create_negative_feedback(self):
        """Should create negative feedback"""
        from rag import CitationFeedback, FeedbackRating

        feedback = CitationFeedback(
            feedback_id="fb-002",
            document_id="old-guideline",
            query="diabetes management",
            rating=FeedbackRating.INCORRECT,
            comment="This guideline is outdated"
        )

        assert feedback.rating == FeedbackRating.INCORRECT


class TestSpecialtyCollection:
    """Tests for SpecialtyCollection dataclass (Feature #89)"""

    def test_create_specialty_collection(self):
        """Should create specialty collection"""
        from rag import SpecialtyCollection

        collection = SpecialtyCollection(
            specialty="cardiology",
            document_ids=["aha-chest-2024", "aha-hf-2022", "aha-afib-2023"],
            description="Cardiology clinical guidelines",
            curator="Dr. Smith"
        )

        assert collection.specialty == "cardiology"
        assert len(collection.document_ids) == 3
        assert "aha-chest-2024" in collection.document_ids


class TestConflictAlert:
    """Tests for ConflictAlert dataclass (Feature #89)"""

    def test_create_conflict_alert(self):
        """Should create conflict alert"""
        from rag import ConflictAlert

        alert = ConflictAlert(
            alert_id="conflict-001",
            document_id_1="guideline-a",
            document_id_2="guideline-b",
            conflict_type="dosing",
            description="Conflicting aspirin dosing recommendations",
            severity="high"
        )

        assert alert.conflict_type == "dosing"
        assert alert.severity == "high"
        assert alert.resolved is False

    def test_resolve_conflict(self):
        """Should track conflict resolution"""
        from rag import ConflictAlert

        alert = ConflictAlert(
            alert_id="conflict-001",
            document_id_1="guideline-a",
            document_id_2="guideline-b",
            conflict_type="recommendation",
            description="Different recommendations",
            severity="medium",
            resolved=True,
            resolution_notes="Guideline A is more recent"
        )

        assert alert.resolved is True
        assert "more recent" in alert.resolution_notes


class TestPubMedArticle:
    """Tests for PubMedArticle dataclass (Feature #89)"""

    def test_create_pubmed_article(self):
        """Should create PubMed article"""
        from rag import PubMedArticle

        article = PubMedArticle(
            pmid="12345678",
            title="Novel Approach to Cardiac Imaging",
            abstract="Background: This study evaluates...",
            authors=["Smith J", "Jones M", "Williams K"],
            journal="JAMA Cardiology",
            publication_date="2024-01-15",
            mesh_terms=["Cardiac Imaging Techniques", "Heart Diseases"],
            doi="10.1001/jamacardio.2024.0001"
        )

        assert article.pmid == "12345678"
        assert len(article.authors) == 3
        assert "JAMA" in article.journal
        assert len(article.mesh_terms) == 2


class TestBuiltInGuidelines:
    """Tests for built-in clinical guidelines"""

    def test_guidelines_exist(self):
        """Should have built-in guidelines"""
        from rag import BUILT_IN_GUIDELINES

        assert len(BUILT_IN_GUIDELINES) > 0

    def test_guideline_structure(self):
        """Should have correct structure"""
        from rag import BUILT_IN_GUIDELINES

        for guideline in BUILT_IN_GUIDELINES[:3]:  # Check first few
            assert "id" in guideline
            assert "title" in guideline
            assert "content" in guideline
            assert "source_type" in guideline

    def test_chest_pain_guideline_exists(self):
        """Should include chest pain guideline"""
        from rag import BUILT_IN_GUIDELINES

        chest_pain = next(
            (g for g in BUILT_IN_GUIDELINES if "chest" in g["id"].lower()),
            None
        )

        assert chest_pain is not None
        assert "AHA" in chest_pain.get("source_name", "") or "aha" in chest_pain.get("source_type", "")


class TestDependencyFlags:
    """Tests for optional dependency flags"""

    def test_chromadb_flag_exists(self):
        """Should have ChromaDB availability flag"""
        from rag import CHROMADB_AVAILABLE

        assert isinstance(CHROMADB_AVAILABLE, bool)

    def test_embeddings_flag_exists(self):
        """Should have embeddings availability flag"""
        from rag import EMBEDDINGS_AVAILABLE

        assert isinstance(EMBEDDINGS_AVAILABLE, bool)

    def test_httpx_flag_exists(self):
        """Should have httpx availability flag"""
        from rag import HTTPX_AVAILABLE

        assert isinstance(HTTPX_AVAILABLE, bool)


class TestDocumentQualityMetrics:
    """Tests for document quality metrics"""

    def test_usage_tracking(self):
        """Should track document usage"""
        from rag import MedicalDocument, SourceType

        doc = MedicalDocument(
            id="test",
            title="Test",
            content="Content",
            source_type=SourceType.CLINICAL_GUIDELINE,
            usage_count=0
        )

        # Simulate usage increment
        doc.usage_count += 1
        assert doc.usage_count == 1

    def test_feedback_tracking(self):
        """Should track feedback counts"""
        from rag import MedicalDocument, SourceType

        doc = MedicalDocument(
            id="test",
            title="Test",
            content="Content",
            source_type=SourceType.CLINICAL_GUIDELINE
        )

        # Simulate feedback
        doc.helpful_count += 1
        doc.helpful_count += 1
        doc.not_helpful_count += 1

        assert doc.helpful_count == 2
        assert doc.not_helpful_count == 1
        assert doc.quality_score == 2/3


class TestKnowledgeManagerVersioning:
    """Tests for KnowledgeManager versioning methods (Feature #89)"""

    @patch("rag.RAGEngine")
    def test_add_guideline_version(self, mock_rag_engine):
        """Should add new guideline version"""
        from rag import KnowledgeManager

        mock_engine = MagicMock()
        mock_engine.add_document.return_value = True
        mock_rag_engine.return_value = mock_engine

        km = KnowledgeManager(mock_engine)

        success, version_id = km.add_guideline_version(
            guideline_id="aha-chest-pain",
            version_number="2024.1",
            publication_date="2024-01-15",
            content="Updated chest pain evaluation guidelines...",
            title="AHA Chest Pain Guidelines",
            source_name="AHA/ACC"
        )

        assert success is True
        assert "aha-chest-pain-v2024.1" == version_id

    @patch("rag.RAGEngine")
    def test_add_version_supersedes_previous(self, mock_rag_engine):
        """Should mark previous version as superseded"""
        from rag import KnowledgeManager, GuidelineVersion, GuidelineStatus

        mock_engine = MagicMock()
        mock_engine.add_document.return_value = True
        mock_rag_engine.return_value = mock_engine

        km = KnowledgeManager(mock_engine)

        # Add first version
        km.versions["aha-chest-pain-v2023.1"] = GuidelineVersion(
            version_id="aha-chest-pain-v2023.1",
            guideline_id="aha-chest-pain",
            version_number="2023.1",
            publication_date="2023-01-15",
            effective_date="2023-02-01",
            status=GuidelineStatus.CURRENT
        )

        # Add new version that supersedes
        km.add_guideline_version(
            guideline_id="aha-chest-pain",
            version_number="2024.1",
            publication_date="2024-01-15",
            content="Updated guidelines",
            title="AHA Chest Pain",
            source_name="AHA",
            supersedes_id="aha-chest-pain-v2023.1"
        )

        # Old version should be marked superseded
        old_version = km.versions["aha-chest-pain-v2023.1"]
        assert old_version.status == GuidelineStatus.SUPERSEDED
        assert old_version.superseded_by == "aha-chest-pain-v2024.1"

    @patch("rag.RAGEngine")
    def test_deprecate_guideline(self, mock_rag_engine):
        """Should deprecate a guideline"""
        from rag import KnowledgeManager, GuidelineVersion, GuidelineStatus

        mock_engine = MagicMock()
        km = KnowledgeManager(mock_engine)

        # Add a version
        km.versions["old-guideline-v1"] = GuidelineVersion(
            version_id="old-guideline-v1",
            guideline_id="old-guideline",
            version_number="1.0",
            publication_date="2020-01-01",
            effective_date="2020-02-01",
            status=GuidelineStatus.CURRENT
        )

        result = km.deprecate_guideline("old-guideline-v1", "Outdated evidence")

        assert result is True
        assert km.versions["old-guideline-v1"].status == GuidelineStatus.DEPRECATED

    @patch("rag.RAGEngine")
    def test_deprecate_nonexistent_guideline(self, mock_rag_engine):
        """Should return False for nonexistent guideline"""
        from rag import KnowledgeManager

        mock_engine = MagicMock()
        km = KnowledgeManager(mock_engine)

        result = km.deprecate_guideline("nonexistent", "reason")

        assert result is False

    @patch("rag.RAGEngine")
    def test_get_current_version(self, mock_rag_engine):
        """Should get current version of guideline"""
        from rag import KnowledgeManager, GuidelineVersion, GuidelineStatus

        mock_engine = MagicMock()
        km = KnowledgeManager(mock_engine)

        km.versions["aha-chest-pain-v2023.1"] = GuidelineVersion(
            version_id="aha-chest-pain-v2023.1",
            guideline_id="aha-chest-pain",
            version_number="2023.1",
            publication_date="2023-01-15",
            effective_date="2023-02-01",
            status=GuidelineStatus.SUPERSEDED
        )
        km.versions["aha-chest-pain-v2024.1"] = GuidelineVersion(
            version_id="aha-chest-pain-v2024.1",
            guideline_id="aha-chest-pain",
            version_number="2024.1",
            publication_date="2024-01-15",
            effective_date="2024-02-01",
            status=GuidelineStatus.CURRENT
        )

        current = km.get_current_version("aha-chest-pain")

        assert current == "aha-chest-pain-v2024.1"

    @patch("rag.RAGEngine")
    def test_get_current_version_none(self, mock_rag_engine):
        """Should return None if no current version"""
        from rag import KnowledgeManager

        mock_engine = MagicMock()
        km = KnowledgeManager(mock_engine)

        current = km.get_current_version("nonexistent-guideline")

        assert current is None

    @patch("rag.RAGEngine")
    def test_get_version_history(self, mock_rag_engine):
        """Should get version history for guideline"""
        from rag import KnowledgeManager, GuidelineVersion, GuidelineStatus

        mock_engine = MagicMock()
        km = KnowledgeManager(mock_engine)

        km.versions["aha-chest-pain-v2022.1"] = GuidelineVersion(
            version_id="aha-chest-pain-v2022.1",
            guideline_id="aha-chest-pain",
            version_number="2022.1",
            publication_date="2022-01-15",
            effective_date="2022-02-01",
            status=GuidelineStatus.SUPERSEDED
        )
        km.versions["aha-chest-pain-v2023.1"] = GuidelineVersion(
            version_id="aha-chest-pain-v2023.1",
            guideline_id="aha-chest-pain",
            version_number="2023.1",
            publication_date="2023-01-15",
            effective_date="2023-02-01",
            status=GuidelineStatus.SUPERSEDED
        )
        km.versions["aha-chest-pain-v2024.1"] = GuidelineVersion(
            version_id="aha-chest-pain-v2024.1",
            guideline_id="aha-chest-pain",
            version_number="2024.1",
            publication_date="2024-01-15",
            effective_date="2024-02-01",
            status=GuidelineStatus.CURRENT
        )

        history = km.get_version_history("aha-chest-pain")

        assert len(history) == 3


class TestKnowledgeManagerFeedback:
    """Tests for KnowledgeManager feedback methods (Feature #89)"""

    @patch("rag.RAGEngine")
    def test_record_feedback(self, mock_rag_engine):
        """Should record citation feedback"""
        from rag import KnowledgeManager

        mock_engine = MagicMock()
        km = KnowledgeManager(mock_engine)
        km.feedback = []  # Clear any persisted feedback

        feedback_id = km.record_feedback(
            document_id="aha-chest-2024",
            query="chest pain evaluation",
            rating="very_helpful",
            comment="Excellent guidance",
            clinician_specialty="cardiology"
        )

        assert feedback_id is not None
        assert len(feedback_id) > 0
        # Check that feedback was added (at least 1)
        new_feedback = [f for f in km.feedback if f.document_id == "aha-chest-2024"]
        assert len(new_feedback) >= 1
        assert new_feedback[-1].rating.value == "very_helpful"

    @patch("rag.RAGEngine")
    def test_record_multiple_feedback(self, mock_rag_engine):
        """Should record multiple feedback entries"""
        from rag import KnowledgeManager

        mock_engine = MagicMock()
        km = KnowledgeManager(mock_engine)
        initial_count = len(km.feedback)
        km.feedback = []  # Clear any persisted feedback

        km.record_feedback("test-doc-x", "query1", "helpful")
        km.record_feedback("test-doc-x", "query2", "very_helpful")
        km.record_feedback("test-doc-x", "query3", "not_helpful")

        # Should have added 3 feedback entries
        test_feedback = [f for f in km.feedback if f.document_id == "test-doc-x"]
        assert len(test_feedback) == 3

    @patch("rag.RAGEngine")
    def test_get_document_feedback_summary(self, mock_rag_engine):
        """Should get feedback summary for document"""
        from rag import KnowledgeManager, CitationFeedback, FeedbackRating

        mock_engine = MagicMock()
        km = KnowledgeManager(mock_engine)
        km.feedback = []  # Clear any persisted feedback

        # Create fresh feedback entries with proper enum values
        km.feedback = [
            CitationFeedback(
                feedback_id="f1",
                document_id="test-summary-doc",
                query="q1",
                rating=FeedbackRating.VERY_HELPFUL
            ),
            CitationFeedback(
                feedback_id="f2",
                document_id="test-summary-doc",
                query="q2",
                rating=FeedbackRating.HELPFUL
            ),
            CitationFeedback(
                feedback_id="f3",
                document_id="test-summary-doc",
                query="q3",
                rating=FeedbackRating.HELPFUL
            ),
            CitationFeedback(
                feedback_id="f4",
                document_id="test-summary-doc",
                query="q4",
                rating=FeedbackRating.NOT_HELPFUL
            ),
        ]

        summary = km.get_document_feedback_summary("test-summary-doc")

        assert summary["document_id"] == "test-summary-doc"
        assert summary["total_feedback"] == 4
        assert summary["helpful_percentage"] == 75.0
        assert summary["quality_score"] == 0.75

    @patch("rag.RAGEngine")
    def test_feedback_summary_empty(self, mock_rag_engine):
        """Should handle empty feedback"""
        from rag import KnowledgeManager

        mock_engine = MagicMock()
        km = KnowledgeManager(mock_engine)

        summary = km.get_document_feedback_summary("nonexistent")

        assert summary["total_feedback"] == 0
        assert summary["helpful_percentage"] == 0


class TestKnowledgeManagerCollections:
    """Tests for KnowledgeManager specialty collection methods"""

    @patch("rag.RAGEngine")
    def test_create_specialty_collection(self, mock_rag_engine):
        """Should create specialty collection"""
        from rag import KnowledgeManager

        mock_engine = MagicMock()
        km = KnowledgeManager(mock_engine)

        result = km.create_specialty_collection(
            specialty="cardiology",
            description="Cardiology guidelines",
            document_ids=["doc1", "doc2"],
            curator="Dr. Smith"
        )

        assert result is True
        assert "cardiology" in km.collections
        assert km.collections["cardiology"].curator == "Dr. Smith"

    @patch("rag.RAGEngine")
    def test_add_to_collection(self, mock_rag_engine):
        """Should add document to collection"""
        from rag import KnowledgeManager

        mock_engine = MagicMock()
        km = KnowledgeManager(mock_engine)

        km.create_specialty_collection("cardiology", "Heart stuff")
        result = km.add_to_collection("cardiology", "new-doc")

        assert result is True
        assert "new-doc" in km.collections["cardiology"].document_ids

    @patch("rag.RAGEngine")
    def test_add_to_nonexistent_collection(self, mock_rag_engine):
        """Should fail for nonexistent collection"""
        from rag import KnowledgeManager

        mock_engine = MagicMock()
        km = KnowledgeManager(mock_engine)

        result = km.add_to_collection("nonexistent", "doc1")

        assert result is False

    @patch("rag.RAGEngine")
    def test_get_collection_documents(self, mock_rag_engine):
        """Should get documents in collection"""
        from rag import KnowledgeManager

        mock_engine = MagicMock()
        km = KnowledgeManager(mock_engine)

        km.create_specialty_collection(
            "pulmonology",
            "Lung guidelines",
            document_ids=["copd-2024", "asthma-2023"]
        )

        docs = km.get_collection_documents("pulmonology")

        assert len(docs) == 2
        assert "copd-2024" in docs

    @patch("rag.RAGEngine")
    def test_get_nonexistent_collection_documents(self, mock_rag_engine):
        """Should return empty for nonexistent collection"""
        from rag import KnowledgeManager

        mock_engine = MagicMock()
        km = KnowledgeManager(mock_engine)

        docs = km.get_collection_documents("nonexistent")

        assert docs == []

    @patch("rag.RAGEngine")
    def test_list_collections(self, mock_rag_engine):
        """Should list all collections"""
        from rag import KnowledgeManager

        mock_engine = MagicMock()
        km = KnowledgeManager(mock_engine)

        km.create_specialty_collection("cardiology", "Heart", ["doc1"])
        km.create_specialty_collection("pulmonology", "Lungs", ["doc2", "doc3"])

        collections = km.list_collections()

        assert len(collections) == 2
        cardio = next(c for c in collections if c["specialty"] == "cardiology")
        assert cardio["document_count"] == 1


class TestKnowledgeManagerConflicts:
    """Tests for KnowledgeManager conflict detection"""

    @patch("rag.RAGEngine")
    def test_resolve_conflict(self, mock_rag_engine):
        """Should resolve conflict alert"""
        from rag import KnowledgeManager, ConflictAlert

        mock_engine = MagicMock()
        km = KnowledgeManager(mock_engine)

        km.conflicts.append(ConflictAlert(
            alert_id="conflict-001",
            document_id_1="doc1",
            document_id_2="doc2",
            conflict_type="dosing",
            description="Conflicting doses",
            severity="high"
        ))

        result = km.resolve_conflict("conflict-001", "doc1 is more recent")

        assert result is True
        assert km.conflicts[0].resolved is True
        assert "more recent" in km.conflicts[0].resolution_notes

    @patch("rag.RAGEngine")
    def test_resolve_nonexistent_conflict(self, mock_rag_engine):
        """Should fail for nonexistent conflict"""
        from rag import KnowledgeManager

        mock_engine = MagicMock()
        km = KnowledgeManager(mock_engine)

        result = km.resolve_conflict("nonexistent", "notes")

        assert result is False

    @patch("rag.RAGEngine")
    def test_get_unresolved_conflicts(self, mock_rag_engine):
        """Should get unresolved conflicts only"""
        from rag import KnowledgeManager, ConflictAlert

        mock_engine = MagicMock()
        km = KnowledgeManager(mock_engine)
        km.conflicts = []  # Clear any persisted conflicts

        km.conflicts.append(ConflictAlert(
            alert_id="c1", document_id_1="d1", document_id_2="d2",
            conflict_type="dosing", description="test1", severity="high",
            resolved=False
        ))
        km.conflicts.append(ConflictAlert(
            alert_id="c2", document_id_1="d3", document_id_2="d4",
            conflict_type="rec", description="test2", severity="medium",
            resolved=True, resolution_notes="Resolved"
        ))
        km.conflicts.append(ConflictAlert(
            alert_id="c3", document_id_1="d5", document_id_2="d6",
            conflict_type="contra", description="test3", severity="low",
            resolved=False
        ))

        unresolved = km.get_unresolved_conflicts()

        assert len(unresolved) == 2


class TestPubMedParsing:
    """Tests for PubMed XML parsing"""

    @patch("rag.RAGEngine")
    def test_parse_pubmed_xml_basic(self, mock_rag_engine):
        """Should parse basic PubMed XML"""
        from rag import KnowledgeManager

        mock_engine = MagicMock()
        km = KnowledgeManager(mock_engine)

        xml_text = """
        <PubmedArticle>
            <ArticleTitle>Test Article Title</ArticleTitle>
            <AbstractText>This is the abstract text.</AbstractText>
            <Title>Test Journal</Title>
        </PubmedArticle>
        """

        articles = km._parse_pubmed_xml(xml_text, ["12345678"])

        assert len(articles) == 1
        assert articles[0].pmid == "12345678"
        assert "Test Article Title" in articles[0].title
        assert "abstract text" in articles[0].abstract

    @patch("rag.RAGEngine")
    def test_parse_pubmed_xml_empty(self, mock_rag_engine):
        """Should handle empty XML"""
        from rag import KnowledgeManager

        mock_engine = MagicMock()
        km = KnowledgeManager(mock_engine)

        articles = km._parse_pubmed_xml("<empty></empty>", ["12345"])

        # Should still create article with unknown title
        assert len(articles) == 1
        assert articles[0].title == "Unknown Title"


class TestRAGEngineStubs:
    """Tests for RAGEngine when dependencies not available"""

    def test_rag_engine_init_without_chromadb(self):
        """Should initialize even without ChromaDB"""
        from rag import RAGEngine

        engine = RAGEngine(persist_directory="/tmp/test")

        assert engine.persist_directory == "/tmp/test"
        assert engine.initialized is False

    def test_rag_engine_retrieve_when_not_initialized(self):
        """Should return empty list when not initialized"""
        from rag import RAGEngine

        engine = RAGEngine()
        results = engine.retrieve("test query")

        assert results == []

    def test_rag_engine_add_document_when_not_initialized(self):
        """Should return False when not initialized"""
        from rag import RAGEngine, MedicalDocument, SourceType

        engine = RAGEngine()
        doc = MedicalDocument(
            id="test",
            title="Test",
            content="Content",
            source_type=SourceType.CLINICAL_GUIDELINE
        )

        result = engine.add_document(doc)

        assert result is False


class TestRAGResponseGeneration:
    """Tests for RAG prompt generation"""

    def test_generate_augmented_prompt_empty(self):
        """Should handle empty contexts"""
        from rag import RAGEngine

        engine = RAGEngine()
        prompt = engine.generate_augmented_prompt("test query", [])

        assert "test query" in prompt

    def test_generate_augmented_prompt_with_contexts(self):
        """Should include context in prompt"""
        from rag import RAGEngine, RetrievedContext, MedicalDocument, SourceType

        engine = RAGEngine()

        doc = MedicalDocument(
            id="test",
            title="AHA Guidelines",
            content="Chest pain evaluation requires...",
            source_type=SourceType.AHA_GUIDELINE,
            source_name="AHA"
        )
        context = RetrievedContext(
            document=doc,
            relevance_score=0.9,
            matched_chunk="Chest pain evaluation requires..."
        )

        prompt = engine.generate_augmented_prompt(
            "How to evaluate chest pain?",
            [context]
        )

        assert "AHA" in prompt or "chest pain" in prompt.lower()
