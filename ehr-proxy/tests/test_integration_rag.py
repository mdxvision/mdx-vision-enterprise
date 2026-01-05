"""
Real Integration Tests for RAG Knowledge System

Run with: pytest tests/test_integration_rag.py --live

These tests use real ChromaDB and sentence-transformers
to verify the knowledge retrieval system works correctly.

Requirements:
    - chromadb installed
    - sentence-transformers installed
"""

import pytest
import os
import tempfile
import shutil

# Mark all tests as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.rag]


@pytest.fixture(scope="module")
def chroma_test_dir():
    """Create a temporary directory for ChromaDB."""
    temp_dir = tempfile.mkdtemp(prefix="chroma_test_")
    yield temp_dir
    # Cleanup after tests
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="module")
def real_chromadb_client(chroma_test_dir):
    """Create a real ChromaDB client for testing."""
    try:
        import chromadb
        from chromadb.config import Settings

        client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=chroma_test_dir,
            anonymized_telemetry=False
        ))
        return client
    except ImportError:
        pytest.skip("chromadb not installed")
    except Exception as e:
        pytest.skip(f"ChromaDB initialization failed: {e}")


@pytest.fixture(scope="module")
def real_embedder():
    """Create real sentence transformer embedder."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        return model
    except ImportError:
        pytest.skip("sentence-transformers not installed")


class TestChromaDBConnection:
    """Test ChromaDB connection and basic operations"""

    def test_chromadb_client_creation(self, real_chromadb_client):
        """Should create ChromaDB client successfully"""
        assert real_chromadb_client is not None

    def test_create_collection(self, real_chromadb_client):
        """Should create a collection"""
        collection = real_chromadb_client.create_collection(
            name="test_collection",
            metadata={"description": "Test collection"}
        )
        assert collection is not None
        assert collection.name == "test_collection"

        # Cleanup
        real_chromadb_client.delete_collection("test_collection")

    def test_add_documents(self, real_chromadb_client):
        """Should add documents to collection"""
        collection = real_chromadb_client.create_collection(name="test_docs")

        collection.add(
            documents=[
                "Chest pain evaluation should include ECG and troponin",
                "Type 2 diabetes management starts with metformin",
                "Hypertension treatment begins with lifestyle modifications"
            ],
            metadatas=[
                {"source": "AHA", "specialty": "cardiology"},
                {"source": "ADA", "specialty": "endocrinology"},
                {"source": "JNC8", "specialty": "cardiology"}
            ],
            ids=["doc1", "doc2", "doc3"]
        )

        assert collection.count() == 3

        # Cleanup
        real_chromadb_client.delete_collection("test_docs")


class TestSentenceTransformerEmbeddings:
    """Test sentence transformer embeddings"""

    def test_embedding_generation(self, real_embedder):
        """Should generate embeddings for text"""
        text = "Patient presents with chest pain and shortness of breath"
        embedding = real_embedder.encode(text)

        assert embedding is not None
        assert len(embedding) == 384  # all-MiniLM-L6-v2 dimension

    def test_embedding_similarity(self, real_embedder):
        """Should produce similar embeddings for similar texts"""
        import numpy as np

        text1 = "Patient has chest pain"
        text2 = "Patient presents with chest discomfort"
        text3 = "The weather is sunny today"

        emb1 = real_embedder.encode(text1)
        emb2 = real_embedder.encode(text2)
        emb3 = real_embedder.encode(text3)

        # Cosine similarity
        def cosine_sim(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        sim_12 = cosine_sim(emb1, emb2)
        sim_13 = cosine_sim(emb1, emb3)

        # Similar texts should have higher similarity
        assert sim_12 > sim_13
        assert sim_12 > 0.7  # Similar medical texts
        assert sim_13 < 0.5  # Unrelated texts

    def test_batch_embedding(self, real_embedder):
        """Should efficiently embed multiple texts"""
        texts = [
            "Diabetes mellitus type 2",
            "Hypertension management",
            "Coronary artery disease",
            "Chronic kidney disease",
            "Heart failure with reduced ejection fraction"
        ]

        embeddings = real_embedder.encode(texts)

        assert len(embeddings) == 5
        assert all(len(e) == 384 for e in embeddings)


class TestRAGKnowledgeRetrieval:
    """Test RAG retrieval functionality"""

    @pytest.fixture
    def populated_collection(self, real_chromadb_client, real_embedder):
        """Create and populate a test collection with medical knowledge"""
        # Create collection with embedding function
        try:
            real_chromadb_client.delete_collection("medical_knowledge")
        except:
            pass

        collection = real_chromadb_client.create_collection(
            name="medical_knowledge"
        )

        # Medical guidelines
        documents = [
            "Chest pain evaluation: Order ECG within 10 minutes. Check troponin at presentation and 3-6 hours later. Consider HEART score for risk stratification.",
            "Type 2 diabetes: Start metformin as first-line therapy. Target A1c less than 7% for most adults. Add GLP-1 agonist for patients with cardiovascular disease.",
            "Heart failure: Optimize GDMT including ACE inhibitor or ARNI, beta-blocker, MRA, and SGLT2 inhibitor. Target heart rate below 70 bpm.",
            "Hypertension: Start with lifestyle modifications. First-line medications include ACE inhibitors, ARBs, calcium channel blockers, or thiazide diuretics.",
            "Acute stroke: Activate stroke protocol. CT head immediately. Consider tPA if within 4.5 hours of symptom onset.",
            "Sepsis: Early recognition is critical. Start antibiotics within 1 hour. Fluid resuscitation with 30 mL/kg crystalloid.",
            "COPD exacerbation: Bronchodilators, systemic corticosteroids, and antibiotics if purulent sputum. Consider non-invasive ventilation.",
            "Pneumonia: Stratify with PSI or CURB-65. Empiric antibiotics based on severity and risk factors."
        ]

        metadatas = [
            {"source": "AHA 2024", "specialty": "cardiology", "topic": "chest_pain"},
            {"source": "ADA 2024", "specialty": "endocrinology", "topic": "diabetes"},
            {"source": "AHA 2024", "specialty": "cardiology", "topic": "heart_failure"},
            {"source": "JNC8", "specialty": "cardiology", "topic": "hypertension"},
            {"source": "AHA/ASA 2024", "specialty": "neurology", "topic": "stroke"},
            {"source": "Surviving Sepsis 2024", "specialty": "critical_care", "topic": "sepsis"},
            {"source": "GOLD 2024", "specialty": "pulmonology", "topic": "copd"},
            {"source": "IDSA/ATS 2024", "specialty": "infectious_disease", "topic": "pneumonia"}
        ]

        # Embed documents
        embeddings = real_embedder.encode(documents).tolist()

        collection.add(
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
            ids=[f"doc_{i}" for i in range(len(documents))]
        )

        yield collection

        # Cleanup
        real_chromadb_client.delete_collection("medical_knowledge")

    def test_semantic_search_chest_pain(self, populated_collection, real_embedder):
        """Should retrieve relevant chest pain guidance"""
        query = "Patient with chest pain, what should I order?"
        query_embedding = real_embedder.encode(query).tolist()

        results = populated_collection.query(
            query_embeddings=[query_embedding],
            n_results=3
        )

        # Should find chest pain document
        assert len(results["documents"][0]) > 0
        top_result = results["documents"][0][0]
        assert "chest pain" in top_result.lower() or "ecg" in top_result.lower()

    def test_semantic_search_diabetes(self, populated_collection, real_embedder):
        """Should retrieve relevant diabetes guidance"""
        query = "How should I manage type 2 diabetes?"
        query_embedding = real_embedder.encode(query).tolist()

        results = populated_collection.query(
            query_embeddings=[query_embedding],
            n_results=3
        )

        top_result = results["documents"][0][0]
        assert "diabetes" in top_result.lower() or "metformin" in top_result.lower()

    def test_semantic_search_emergency(self, populated_collection, real_embedder):
        """Should retrieve stroke protocol for emergency query"""
        query = "Acute stroke patient just arrived, what do I do?"
        query_embedding = real_embedder.encode(query).tolist()

        results = populated_collection.query(
            query_embeddings=[query_embedding],
            n_results=3
        )

        top_result = results["documents"][0][0]
        assert "stroke" in top_result.lower() or "ct" in top_result.lower() or "tpa" in top_result.lower()

    def test_metadata_filtering(self, populated_collection, real_embedder):
        """Should filter by specialty metadata"""
        query = "cardiac patient management"
        query_embedding = real_embedder.encode(query).tolist()

        results = populated_collection.query(
            query_embeddings=[query_embedding],
            n_results=5,
            where={"specialty": "cardiology"}
        )

        # All results should be cardiology
        for metadata in results["metadatas"][0]:
            assert metadata["specialty"] == "cardiology"


class TestRAGPerformance:
    """Performance tests for RAG system"""

    @pytest.mark.slow
    def test_embedding_latency(self, real_embedder):
        """Should embed text within acceptable time"""
        import time

        text = "Patient presents with acute chest pain radiating to left arm, diaphoresis, and shortness of breath for the past 30 minutes."

        start = time.time()
        embedding = real_embedder.encode(text)
        elapsed = time.time() - start

        assert elapsed < 0.5, f"Embedding took {elapsed:.3f}s (>0.5s)"
        print(f"\n⏱️ Single embedding: {elapsed:.3f}s")

    @pytest.mark.slow
    def test_batch_embedding_latency(self, real_embedder):
        """Should batch embed efficiently"""
        import time

        texts = [
            "Chest pain evaluation",
            "Diabetes management",
            "Heart failure treatment",
            "Stroke protocol",
            "Sepsis management"
        ] * 10  # 50 texts

        start = time.time()
        embeddings = real_embedder.encode(texts)
        elapsed = time.time() - start

        assert elapsed < 5.0, f"Batch embedding (50 texts) took {elapsed:.3f}s (>5s)"
        print(f"\n⏱️ Batch embedding (50 texts): {elapsed:.3f}s ({elapsed/50*1000:.1f}ms/text)")


class TestRAGDocumentManagement:
    """Test document CRUD operations"""

    def test_add_and_update_document(self, real_chromadb_client, real_embedder):
        """Should add and update documents"""
        collection = real_chromadb_client.create_collection(name="test_crud")

        # Add initial document
        doc = "Initial diabetes guidelines"
        embedding = real_embedder.encode(doc).tolist()

        collection.add(
            documents=[doc],
            metadatas=[{"version": "1.0"}],
            embeddings=[embedding],
            ids=["diabetes_guide"]
        )

        assert collection.count() == 1

        # Update document
        new_doc = "Updated diabetes guidelines 2024"
        new_embedding = real_embedder.encode(new_doc).tolist()

        collection.update(
            ids=["diabetes_guide"],
            documents=[new_doc],
            metadatas=[{"version": "2.0"}],
            embeddings=[new_embedding]
        )

        # Verify update
        result = collection.get(ids=["diabetes_guide"])
        assert result["documents"][0] == new_doc
        assert result["metadatas"][0]["version"] == "2.0"

        # Cleanup
        real_chromadb_client.delete_collection("test_crud")

    def test_delete_document(self, real_chromadb_client, real_embedder):
        """Should delete documents"""
        collection = real_chromadb_client.create_collection(name="test_delete")

        embedding = real_embedder.encode("Test document").tolist()
        collection.add(
            documents=["Test document"],
            embeddings=[embedding],
            ids=["test_doc"]
        )

        assert collection.count() == 1

        collection.delete(ids=["test_doc"])

        assert collection.count() == 0

        # Cleanup
        real_chromadb_client.delete_collection("test_delete")
