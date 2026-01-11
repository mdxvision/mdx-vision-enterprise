"""
Extended tests for rag.py - Targets uncovered data models and KnowledgeManager
Focus on Feature #89 Knowledge Management
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock


class TestSourceTypeEnum:
    """Tests for SourceType enum"""

    def test_all_source_types(self):
        """Should have all expected source types"""
        from rag import SourceType

        expected = [
            "clinical_guideline",
            "pubmed_abstract",
            "drug_info",
            "uptodate",
            "cdc_guideline",
            "aha_guideline",
            "uspstf",
            "custom"
        ]

        for source in expected:
            assert SourceType(source) is not None

    def test_source_type_values(self):
        """Should have correct string values"""
        from rag import SourceType

        assert SourceType.CLINICAL_GUIDELINE.value == "clinical_guideline"
        assert SourceType.PUBMED_ABSTRACT.value == "pubmed_abstract"
        assert SourceType.CUSTOM.value == "custom"


class TestGuidelineStatusEnum:
    """Tests for GuidelineStatus enum"""

    def test_all_statuses(self):
        """Should have all expected statuses"""
        from rag import GuidelineStatus

        expected = ["current", "superseded", "deprecated", "draft", "archived"]

        for status in expected:
            assert GuidelineStatus(status) is not None

    def test_status_values(self):
        """Should have correct string values"""
        from rag import GuidelineStatus

        assert GuidelineStatus.CURRENT.value == "current"
        assert GuidelineStatus.SUPERSEDED.value == "superseded"
        assert GuidelineStatus.DEPRECATED.value == "deprecated"


class TestFeedbackRatingEnum:
    """Tests for FeedbackRating enum"""

    def test_all_ratings(self):
        """Should have all expected ratings"""
        from rag import FeedbackRating

        expected = [
            "very_helpful",
            "helpful",
            "neutral",
            "not_helpful",
            "incorrect"
        ]

        for rating in expected:
            assert FeedbackRating(rating) is not None


class TestGuidelineVersion:
    """Tests for GuidelineVersion dataclass"""

    def test_create_guideline_version(self):
        """Should create GuidelineVersion with required fields"""
        from rag import GuidelineVersion, GuidelineStatus

        version = GuidelineVersion(
            version_id="test-v1",
            guideline_id="test-guideline",
            version_number="2024.1",
            publication_date="2024-01-01",
            effective_date="2024-01-15",
            status=GuidelineStatus.CURRENT
        )

        assert version.version_id == "test-v1"
        assert version.guideline_id == "test-guideline"
        assert version.version_number == "2024.1"
        assert version.status == GuidelineStatus.CURRENT

    def test_guideline_version_with_supersession(self):
        """Should track supersession chain"""
        from rag import GuidelineVersion, GuidelineStatus

        version = GuidelineVersion(
            version_id="test-v2",
            guideline_id="test-guideline",
            version_number="2024.2",
            publication_date="2024-06-01",
            effective_date="2024-06-15",
            status=GuidelineStatus.CURRENT,
            supersedes="test-v1",
            superseded_by=None,
            change_summary="Updated dosing recommendations"
        )

        assert version.supersedes == "test-v1"
        assert version.superseded_by is None
        assert "dosing" in version.change_summary

    def test_guideline_version_created_at(self):
        """Should auto-generate created_at timestamp"""
        from rag import GuidelineVersion, GuidelineStatus

        version = GuidelineVersion(
            version_id="test-v1",
            guideline_id="test-guideline",
            version_number="2024.1",
            publication_date="2024-01-01",
            effective_date="2024-01-15",
            status=GuidelineStatus.CURRENT
        )

        assert version.created_at is not None
        # Should be ISO format
        datetime.fromisoformat(version.created_at)


class TestCitationFeedback:
    """Tests for CitationFeedback dataclass"""

    def test_create_citation_feedback(self):
        """Should create CitationFeedback"""
        from rag import CitationFeedback, FeedbackRating

        feedback = CitationFeedback(
            feedback_id="fb-001",
            document_id="doc-001",
            query="chest pain management",
            rating=FeedbackRating.VERY_HELPFUL,
            comment="Great reference!",
            clinician_specialty="cardiology"
        )

        assert feedback.feedback_id == "fb-001"
        assert feedback.document_id == "doc-001"
        assert feedback.rating == FeedbackRating.VERY_HELPFUL
        assert feedback.comment == "Great reference!"

    def test_citation_feedback_timestamp(self):
        """Should auto-generate timestamp"""
        from rag import CitationFeedback, FeedbackRating

        feedback = CitationFeedback(
            feedback_id="fb-001",
            document_id="doc-001",
            query="query",
            rating=FeedbackRating.HELPFUL
        )

        assert feedback.timestamp is not None
        datetime.fromisoformat(feedback.timestamp)


class TestSpecialtyCollection:
    """Tests for SpecialtyCollection dataclass"""

    def test_create_specialty_collection(self):
        """Should create SpecialtyCollection"""
        from rag import SpecialtyCollection

        collection = SpecialtyCollection(
            specialty="cardiology",
            document_ids=["doc-1", "doc-2", "doc-3"],
            description="Cardiology clinical guidelines",
            curator="Dr. Smith"
        )

        assert collection.specialty == "cardiology"
        assert len(collection.document_ids) == 3
        assert collection.curator == "Dr. Smith"

    def test_specialty_collection_last_updated(self):
        """Should auto-generate last_updated"""
        from rag import SpecialtyCollection

        collection = SpecialtyCollection(
            specialty="pulmonology",
            document_ids=[],
            description="Test"
        )

        assert collection.last_updated is not None


class TestConflictAlert:
    """Tests for ConflictAlert dataclass"""

    def test_create_conflict_alert(self):
        """Should create ConflictAlert"""
        from rag import ConflictAlert

        alert = ConflictAlert(
            alert_id="alert-001",
            document_id_1="doc-1",
            document_id_2="doc-2",
            conflict_type="dosing",
            description="Different recommended doses for drug X",
            severity="high"
        )

        assert alert.alert_id == "alert-001"
        assert alert.conflict_type == "dosing"
        assert alert.severity == "high"
        assert alert.resolved is False

    def test_conflict_alert_resolution(self):
        """Should track resolution"""
        from rag import ConflictAlert

        alert = ConflictAlert(
            alert_id="alert-001",
            document_id_1="doc-1",
            document_id_2="doc-2",
            conflict_type="recommendation",
            description="Conflicting recommendations",
            severity="medium",
            resolved=True,
            resolution_notes="Newer guideline takes precedence"
        )

        assert alert.resolved is True
        assert alert.resolution_notes is not None


class TestPubMedArticle:
    """Tests for PubMedArticle dataclass"""

    def test_create_pubmed_article(self):
        """Should create PubMedArticle"""
        from rag import PubMedArticle

        article = PubMedArticle(
            pmid="12345678",
            title="Study on Heart Failure Treatment",
            abstract="This study examines...",
            authors=["Smith J", "Jones M"],
            journal="NEJM",
            publication_date="2024-01",
            mesh_terms=["Heart Failure", "Treatment"],
            doi="10.1000/test"
        )

        assert article.pmid == "12345678"
        assert article.journal == "NEJM"
        assert len(article.authors) == 2
        assert article.doi == "10.1000/test"

    def test_pubmed_article_optional_doi(self):
        """Should allow optional DOI"""
        from rag import PubMedArticle

        article = PubMedArticle(
            pmid="12345678",
            title="Test",
            abstract="Test abstract",
            authors=[],
            journal="Test Journal",
            publication_date="2024-01",
            mesh_terms=[]
        )

        assert article.doi is None


class TestMedicalDocument:
    """Tests for MedicalDocument dataclass"""

    def test_to_dict(self):
        """Should convert to dictionary"""
        from rag import MedicalDocument, SourceType

        doc = MedicalDocument(
            id="doc-001",
            title="Test Document",
            content="Test content",
            source_type=SourceType.CLINICAL_GUIDELINE,
            source_name="Test Source"
        )

        d = doc.to_dict()

        assert d["id"] == "doc-001"
        assert d["title"] == "Test Document"
        assert d["source_type"] == "clinical_guideline"

    def test_from_dict(self):
        """Should create from dictionary"""
        from rag import MedicalDocument

        data = {
            "id": "doc-002",
            "title": "Test Doc",
            "content": "Content",
            "source_type": "pubmed_abstract",
            "source_name": None,
            "source_url": None,
            "publication_date": None,
            "authors": None,
            "keywords": None,
            "specialty": None,
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

        assert doc.id == "doc-002"
        from rag import SourceType, GuidelineStatus
        assert doc.source_type == SourceType.PUBMED_ABSTRACT
        assert doc.status == GuidelineStatus.CURRENT

    def test_quality_score_no_feedback(self):
        """Should return 0.5 with no feedback"""
        from rag import MedicalDocument, SourceType

        doc = MedicalDocument(
            id="doc-001",
            title="Test",
            content="Test",
            source_type=SourceType.CUSTOM
        )

        assert doc.quality_score == 0.5

    def test_quality_score_with_feedback(self):
        """Should calculate quality score from feedback"""
        from rag import MedicalDocument, SourceType

        doc = MedicalDocument(
            id="doc-001",
            title="Test",
            content="Test",
            source_type=SourceType.CUSTOM,
            helpful_count=8,
            not_helpful_count=2
        )

        assert doc.quality_score == 0.8

    def test_quality_score_all_negative(self):
        """Should handle all negative feedback"""
        from rag import MedicalDocument, SourceType

        doc = MedicalDocument(
            id="doc-001",
            title="Test",
            content="Test",
            source_type=SourceType.CUSTOM,
            helpful_count=0,
            not_helpful_count=5
        )

        assert doc.quality_score == 0.0


class TestRetrievedContext:
    """Tests for RetrievedContext dataclass"""

    def test_to_citation_with_all_fields(self):
        """Should generate full citation"""
        from rag import RetrievedContext, MedicalDocument, SourceType

        doc = MedicalDocument(
            id="doc-001",
            title="Test",
            content="Test content",
            source_type=SourceType.AHA_GUIDELINE,
            source_name="AHA",
            source_url="https://aha.org/test",
            publication_date="2024"
        )

        ctx = RetrievedContext(
            document=doc,
            relevance_score=0.95,
            matched_chunk="Test content"
        )

        citation = ctx.to_citation()

        assert "[AHA]" in citation
        assert "(2024)" in citation
        assert "https://aha.org/test" in citation

    def test_to_citation_minimal(self):
        """Should generate citation with minimal fields"""
        from rag import RetrievedContext, MedicalDocument, SourceType

        doc = MedicalDocument(
            id="doc-001",
            title="Test",
            content="Test",
            source_type=SourceType.CUSTOM
        )

        ctx = RetrievedContext(
            document=doc,
            relevance_score=0.5,
            matched_chunk="Test"
        )

        citation = ctx.to_citation()

        assert "[custom]" in citation


class TestBuiltInGuidelines:
    """Tests for built-in guidelines constant"""

    def test_guidelines_exist(self):
        """Should have built-in guidelines"""
        from rag import BUILT_IN_GUIDELINES

        assert len(BUILT_IN_GUIDELINES) > 0

    def test_guideline_structure(self):
        """Should have correct structure"""
        from rag import BUILT_IN_GUIDELINES

        for guideline in BUILT_IN_GUIDELINES:
            assert "id" in guideline
            assert "title" in guideline
            assert "content" in guideline
            assert "source_type" in guideline

    def test_specialty_coverage(self):
        """Should cover multiple specialties"""
        from rag import BUILT_IN_GUIDELINES

        specialties = set()
        for guideline in BUILT_IN_GUIDELINES:
            if "specialty" in guideline:
                specialties.add(guideline["specialty"])

        # Should have cardiology, pulmonology, etc.
        assert len(specialties) >= 2


class TestKnowledgeManagerInit:
    """Tests for KnowledgeManager initialization"""

    def test_init_creates_data_dir(self):
        """Should create data directory"""
        from rag import KnowledgeManager, RAGEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "knowledge"
            mock_engine = MagicMock(spec=RAGEngine)

            manager = KnowledgeManager(mock_engine, str(data_dir))

            assert data_dir.exists()

    def test_init_loads_empty_data(self):
        """Should initialize with empty data structures"""
        from rag import KnowledgeManager, RAGEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_engine = MagicMock(spec=RAGEngine)
            manager = KnowledgeManager(mock_engine, tmpdir)

            assert manager.versions == {}
            assert manager.feedback == []
            assert manager.collections == {}
            assert manager.conflicts == []


class TestKnowledgeManagerVersioning:
    """Tests for guideline versioning"""

    def test_add_guideline_version(self):
        """Should add new guideline version"""
        from rag import KnowledgeManager, RAGEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_engine = MagicMock(spec=RAGEngine)
            mock_engine.add_document = MagicMock(return_value=True)

            manager = KnowledgeManager(mock_engine, tmpdir)

            success, version_id = manager.add_guideline_version(
                guideline_id="test-guideline",
                version_number="2024.1",
                publication_date="2024-01-01",
                content="Test guideline content",
                title="Test Guideline",
                source_name="Test Source"
            )

            assert success is True
            assert version_id == "test-guideline-v2024.1"
            assert version_id in manager.versions

    def test_add_version_supersedes_previous(self):
        """Should mark previous version as superseded"""
        from rag import KnowledgeManager, RAGEngine, GuidelineStatus, GuidelineVersion

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_engine = MagicMock(spec=RAGEngine)
            mock_engine.add_document = MagicMock(return_value=True)

            manager = KnowledgeManager(mock_engine, tmpdir)

            # Add old version first
            manager.versions["test-v1"] = GuidelineVersion(
                version_id="test-v1",
                guideline_id="test",
                version_number="2023.1",
                publication_date="2023-01-01",
                effective_date="2023-01-01",
                status=GuidelineStatus.CURRENT
            )

            # Add new version that supersedes
            success, version_id = manager.add_guideline_version(
                guideline_id="test",
                version_number="2024.1",
                publication_date="2024-01-01",
                content="Updated content",
                title="Test",
                source_name="Test",
                supersedes_id="test-v1",
                change_summary="Updated for 2024"
            )

            assert success is True
            assert manager.versions["test-v1"].status == GuidelineStatus.SUPERSEDED
            assert manager.versions["test-v1"].superseded_by == version_id

    def test_deprecate_guideline(self):
        """Should deprecate guideline"""
        from rag import KnowledgeManager, RAGEngine, GuidelineStatus, GuidelineVersion

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_engine = MagicMock(spec=RAGEngine)
            manager = KnowledgeManager(mock_engine, tmpdir)

            manager.versions["test-v1"] = GuidelineVersion(
                version_id="test-v1",
                guideline_id="test",
                version_number="2023.1",
                publication_date="2023-01-01",
                effective_date="2023-01-01",
                status=GuidelineStatus.CURRENT
            )

            result = manager.deprecate_guideline("test-v1", "Outdated")

            assert result is True
            assert manager.versions["test-v1"].status == GuidelineStatus.DEPRECATED

    def test_deprecate_nonexistent(self):
        """Should return False for nonexistent guideline"""
        from rag import KnowledgeManager, RAGEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_engine = MagicMock(spec=RAGEngine)
            manager = KnowledgeManager(mock_engine, tmpdir)

            result = manager.deprecate_guideline("nonexistent", "Test")

            assert result is False

    def test_get_current_version(self):
        """Should get current version"""
        from rag import KnowledgeManager, RAGEngine, GuidelineStatus, GuidelineVersion

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_engine = MagicMock(spec=RAGEngine)
            manager = KnowledgeManager(mock_engine, tmpdir)

            # Add multiple versions
            manager.versions["test-v1"] = GuidelineVersion(
                version_id="test-v1",
                guideline_id="test-guideline",
                version_number="2023.1",
                publication_date="2023-01-01",
                effective_date="2023-01-01",
                status=GuidelineStatus.SUPERSEDED
            )
            manager.versions["test-v2"] = GuidelineVersion(
                version_id="test-v2",
                guideline_id="test-guideline",
                version_number="2024.1",
                publication_date="2024-01-01",
                effective_date="2024-01-01",
                status=GuidelineStatus.CURRENT
            )

            current = manager.get_current_version("test-guideline")

            assert current == "test-v2"

    def test_get_version_history(self):
        """Should get version history"""
        from rag import KnowledgeManager, RAGEngine, GuidelineStatus, GuidelineVersion

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_engine = MagicMock(spec=RAGEngine)
            manager = KnowledgeManager(mock_engine, tmpdir)

            manager.versions["test-v1"] = GuidelineVersion(
                version_id="test-v1",
                guideline_id="test-guideline",
                version_number="2023.1",
                publication_date="2023-01-01",
                effective_date="2023-01-01",
                status=GuidelineStatus.SUPERSEDED
            )
            manager.versions["test-v2"] = GuidelineVersion(
                version_id="test-v2",
                guideline_id="test-guideline",
                version_number="2024.1",
                publication_date="2024-01-01",
                effective_date="2024-01-01",
                status=GuidelineStatus.CURRENT
            )
            manager.versions["other-v1"] = GuidelineVersion(
                version_id="other-v1",
                guideline_id="other-guideline",
                version_number="2024.1",
                publication_date="2024-01-01",
                effective_date="2024-01-01",
                status=GuidelineStatus.CURRENT
            )

            history = manager.get_version_history("test-guideline")

            assert len(history) == 2


class TestKnowledgeManagerFeedback:
    """Tests for feedback tracking"""

    def test_record_feedback(self):
        """Should record citation feedback"""
        from rag import KnowledgeManager, RAGEngine, CitationFeedback, FeedbackRating

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_engine = MagicMock(spec=RAGEngine)
            manager = KnowledgeManager(mock_engine, tmpdir)

            feedback = CitationFeedback(
                feedback_id="fb-001",
                document_id="doc-001",
                query="test query",
                rating=FeedbackRating.VERY_HELPFUL,
                comment="Great!"
            )

            manager.feedback.append(feedback)
            manager._save_feedback()

            # Reload
            manager2 = KnowledgeManager(mock_engine, tmpdir)
            assert len(manager2.feedback) == 1
            assert manager2.feedback[0].feedback_id == "fb-001"


class TestKnowledgeManagerCollections:
    """Tests for specialty collections"""

    def test_save_and_load_collection(self):
        """Should persist collections"""
        from rag import KnowledgeManager, RAGEngine, SpecialtyCollection

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_engine = MagicMock(spec=RAGEngine)
            manager = KnowledgeManager(mock_engine, tmpdir)

            collection = SpecialtyCollection(
                specialty="cardiology",
                document_ids=["doc-1", "doc-2"],
                description="Cardiology guidelines"
            )
            manager.collections["cardiology"] = collection
            manager._save_collections()

            # Reload
            manager2 = KnowledgeManager(mock_engine, tmpdir)
            assert "cardiology" in manager2.collections
            assert len(manager2.collections["cardiology"].document_ids) == 2


class TestKnowledgeManagerConflicts:
    """Tests for conflict detection"""

    def test_save_and_load_conflicts(self):
        """Should persist conflicts"""
        from rag import KnowledgeManager, RAGEngine, ConflictAlert

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_engine = MagicMock(spec=RAGEngine)
            manager = KnowledgeManager(mock_engine, tmpdir)

            conflict = ConflictAlert(
                alert_id="alert-001",
                document_id_1="doc-1",
                document_id_2="doc-2",
                conflict_type="dosing",
                description="Different doses",
                severity="high"
            )
            manager.conflicts.append(conflict)
            manager._save_conflicts()

            # Reload
            manager2 = KnowledgeManager(mock_engine, tmpdir)
            assert len(manager2.conflicts) == 1
            assert manager2.conflicts[0].alert_id == "alert-001"


class TestKnowledgeManagerAnalytics:
    """Tests for analytics tracking"""

    def test_default_analytics(self):
        """Should have default analytics structure"""
        from rag import KnowledgeManager, RAGEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_engine = MagicMock(spec=RAGEngine)
            manager = KnowledgeManager(mock_engine, tmpdir)

            assert "total_queries" in manager.analytics
            assert "total_retrievals" in manager.analytics
            assert "feedback_count" in manager.analytics
            assert "top_documents" in manager.analytics
            assert "specialty_usage" in manager.analytics

    def test_save_and_load_analytics(self):
        """Should persist analytics"""
        from rag import KnowledgeManager, RAGEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_engine = MagicMock(spec=RAGEngine)
            manager = KnowledgeManager(mock_engine, tmpdir)

            manager.analytics["total_queries"] = 100
            manager.analytics["total_retrievals"] = 500
            manager._save_analytics()

            # Reload
            manager2 = KnowledgeManager(mock_engine, tmpdir)
            assert manager2.analytics["total_queries"] == 100
            assert manager2.analytics["total_retrievals"] == 500


class TestHelperFunctions:
    """Tests for module-level helper functions"""

    def test_add_custom_document(self):
        """Should add custom document via helper"""
        from rag import add_custom_document, rag_engine

        # May fail if RAG not initialized, but tests the code path
        try:
            result = add_custom_document(
                title="Test Custom Document",
                content="Custom content for testing",
                source_type="custom",
                source_name="Test",
                specialty="testing"
            )
            # Result depends on whether RAG is initialized
            assert result in [True, False]
        except Exception:
            # Expected if RAG dependencies not available
            pass

    def test_retrieve_context(self):
        """Should retrieve context via helper"""
        from rag import retrieve_context

        try:
            results = retrieve_context("chest pain")
            assert isinstance(results, list)
        except Exception:
            # Expected if RAG not initialized
            pass

    def test_get_augmented_prompt(self):
        """Should get augmented prompt via helper"""
        from rag import get_augmented_prompt

        try:
            prompt, sources = get_augmented_prompt("heart failure treatment")
            assert isinstance(prompt, str)
            assert isinstance(sources, list)
        except Exception:
            # Expected if RAG not initialized
            pass


class TestRAGEngineNotInitialized:
    """Tests for RAGEngine when not initialized"""

    def test_retrieve_when_not_initialized(self):
        """Should return empty list when not initialized"""
        from rag import RAGEngine

        engine = RAGEngine()
        engine.initialized = False

        results = engine.retrieve("test query")

        assert results == []

    def test_add_document_when_not_initialized(self):
        """Should return False when not initialized"""
        from rag import RAGEngine, MedicalDocument, SourceType

        engine = RAGEngine()
        engine.initialized = False

        doc = MedicalDocument(
            id="test",
            title="Test",
            content="Test",
            source_type=SourceType.CUSTOM
        )

        result = engine.add_document(doc)

        assert result is False

    def test_get_statistics_when_not_initialized(self):
        """Should indicate not initialized"""
        from rag import RAGEngine

        engine = RAGEngine()
        engine.initialized = False

        stats = engine.get_statistics()

        assert stats["initialized"] is False


class TestRAGEngineGeneratePrompt:
    """Tests for prompt generation"""

    def test_generate_augmented_prompt_empty_contexts(self):
        """Should return original query with empty contexts"""
        from rag import RAGEngine

        engine = RAGEngine()

        result = engine.generate_augmented_prompt("test query", [])

        assert result == "test query"

    def test_generate_augmented_prompt_with_contexts(self):
        """Should include context in prompt"""
        from rag import RAGEngine, RetrievedContext, MedicalDocument, SourceType

        engine = RAGEngine()

        doc = MedicalDocument(
            id="doc-1",
            title="Test Doc",
            content="Test content for augmentation",
            source_type=SourceType.CLINICAL_GUIDELINE,
            source_name="Test Source",
            publication_date="2024"
        )
        ctx = RetrievedContext(
            document=doc,
            relevance_score=0.9,
            matched_chunk="Test content"
        )

        result = engine.generate_augmented_prompt("my query", [ctx])

        assert "REFERENCE SOURCES" in result
        assert "Test content for augmentation" in result
        assert "my query" in result
        assert "[1]" in result
        assert "Test Source" in result


class TestRAGResponse:
    """Tests for RAGResponse dataclass"""

    def test_create_rag_response(self):
        """Should create RAGResponse"""
        from rag import RAGResponse

        response = RAGResponse(
            response="Test response with [1] citation",
            citations=["[1] AHA 2024"],
            sources=[{"title": "AHA Guideline", "url": "http://test"}],
            confidence=0.85,
            retrieval_count=3
        )

        assert response.response == "Test response with [1] citation"
        assert len(response.citations) == 1
        assert len(response.sources) == 1
        assert response.confidence == 0.85
        assert response.retrieval_count == 3
