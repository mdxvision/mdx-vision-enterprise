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
