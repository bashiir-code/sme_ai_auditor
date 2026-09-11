"""
tests/unit/test_vectordb.py
---------------------------
Unit tests for EmbeddingGenerator (and future QdrantClientWrapper, IndexManager).
No live API or Qdrant connection required — all external calls are mocked.
"""

import pytest
from unittest.mock import MagicMock, patch

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.vectordb.embedding_generator import (
    EmbeddingGenerator,
    EmbeddingError,
    DEFAULT_EMBEDDING_MODEL,
    VECTOR_DIMENSION,
    DEFAULT_BATCH_SIZE,
    _batch_count,
    _batches,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_API_KEY = "sk-test-not-real"


def _make_fake_vector(dim: int = VECTOR_DIMENSION) -> list:
    """Return a list of *dim* floats simulating a real embedding vector."""
    return [0.01 * i for i in range(dim)]


def _make_mock_response(texts: list) -> MagicMock:
    """
    Build a mock Mistral EmbeddingResponse matching len(texts) items.
    Each item has an .embedding attribute of VECTOR_DIMENSION floats.
    """
    response = MagicMock()
    response.data = [
        MagicMock(embedding=_make_fake_vector()) for _ in texts
    ]
    return response


# ---------------------------------------------------------------------------
# Module-level utility tests (_batches, _batch_count)
# ---------------------------------------------------------------------------

class TestBatchUtilities:
    def test_batch_count_exact_multiple(self):
        assert _batch_count(64, 32) == 2

    def test_batch_count_with_remainder(self):
        assert _batch_count(33, 32) == 2

    def test_batch_count_single_item(self):
        assert _batch_count(1, 32) == 1

    def test_batches_splits_correctly(self):
        items = list(range(10))
        batches = list(_batches(items, 3))
        assert batches == [[0,1,2], [3,4,5], [6,7,8], [9]]

    def test_batches_empty_list(self):
        assert list(_batches([], 5)) == []

    def test_batches_single_item(self):
        assert list(_batches(["a"], 5)) == [["a"]]

    def test_batches_size_larger_than_list(self):
        """When batch_size > len(items), one batch containing all items."""
        assert list(_batches([1, 2, 3], 100)) == [[1, 2, 3]]


# ---------------------------------------------------------------------------
# EmbeddingGenerator — initialisation
# ---------------------------------------------------------------------------

class TestEmbeddingGeneratorInit:
    def test_raises_if_no_api_key_set(self, monkeypatch):
        """No API key in env or constructor → EmbeddingError immediately."""
        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
        with pytest.raises(EmbeddingError, match="MISTRAL_API_KEY is not set"):
            EmbeddingGenerator(api_key=None)

    def test_accepts_explicit_api_key(self):
        """Explicit api_key bypasses env var requirement."""
        gen = EmbeddingGenerator(api_key=FAKE_API_KEY)
        assert gen is not None

    def test_default_model_is_mistral_embed(self):
        gen = EmbeddingGenerator(api_key=FAKE_API_KEY)
        assert gen.model == DEFAULT_EMBEDDING_MODEL

    def test_default_batch_size(self):
        gen = EmbeddingGenerator(api_key=FAKE_API_KEY)
        assert gen.batch_size == DEFAULT_BATCH_SIZE

    def test_custom_model_and_batch_size(self):
        gen = EmbeddingGenerator(
            api_key=FAKE_API_KEY,
            model="mistral-embed-v2",
            batch_size=16,
        )
        assert gen.model == "mistral-embed-v2"
        assert gen.batch_size == 16


# ---------------------------------------------------------------------------
# EmbeddingGenerator.generate() — input guards
# ---------------------------------------------------------------------------

class TestEmbeddingGeneratorGuards:
    def test_raises_on_empty_list(self):
        gen = EmbeddingGenerator(api_key=FAKE_API_KEY)
        with pytest.raises(ValueError, match="texts must not be empty"):
            gen.generate([])

    def test_raises_on_blank_string_in_list(self):
        gen = EmbeddingGenerator(api_key=FAKE_API_KEY)
        with pytest.raises(ValueError, match="blank strings at indices"):
            gen.generate(["valid text", "   ", "also valid"])

    def test_raises_on_empty_string_in_list(self):
        gen = EmbeddingGenerator(api_key=FAKE_API_KEY)
        with pytest.raises(ValueError, match="blank strings at indices"):
            gen.generate(["valid", ""])


# ---------------------------------------------------------------------------
# EmbeddingGenerator.generate() — successful path (mocked API)
# ---------------------------------------------------------------------------

class TestEmbeddingGeneratorSuccess:
    @patch("src.vectordb.embedding_generator.Mistral")
    def test_returns_list_of_vectors(self, mock_mistral_cls):
        texts = ["Article 5 prohibits...", "High-risk AI systems must..."]
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = _make_mock_response(texts)
        mock_mistral_cls.return_value = mock_client

        gen = EmbeddingGenerator(api_key=FAKE_API_KEY)
        vectors = gen.generate(texts)

        assert isinstance(vectors, list)
        assert len(vectors) == len(texts)

    @patch("src.vectordb.embedding_generator.Mistral")
    def test_each_vector_has_correct_dimension(self, mock_mistral_cls):
        texts = ["chunk one", "chunk two", "chunk three"]
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = _make_mock_response(texts)
        mock_mistral_cls.return_value = mock_client

        gen = EmbeddingGenerator(api_key=FAKE_API_KEY)
        vectors = gen.generate(texts)

        for i, vec in enumerate(vectors):
            assert isinstance(vec, list), f"Vector {i} is not a list"
            assert len(vec) == VECTOR_DIMENSION, (
                f"Vector {i} has dimension {len(vec)}, expected {VECTOR_DIMENSION}"
            )

    @patch("src.vectordb.embedding_generator.Mistral")
    def test_output_length_matches_input_length(self, mock_mistral_cls):
        texts = [f"Legal text chunk {i}" for i in range(10)]
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = _make_mock_response(texts)
        mock_mistral_cls.return_value = mock_client

        gen = EmbeddingGenerator(api_key=FAKE_API_KEY)
        vectors = gen.generate(texts)

        assert len(vectors) == len(texts)

    @patch("src.vectordb.embedding_generator.Mistral")
    def test_batching_calls_api_correct_number_of_times(self, mock_mistral_cls):
        """For 70 texts with batch_size=32, API must be called 3 times."""
        texts = [f"chunk {i}" for i in range(70)]
        mock_client = MagicMock()

        def side_effect(**kwargs):
            batch = kwargs["inputs"]
            return _make_mock_response(batch)

        mock_client.embeddings.create.side_effect = side_effect
        mock_mistral_cls.return_value = mock_client

        gen = EmbeddingGenerator(api_key=FAKE_API_KEY, batch_size=32)
        vectors = gen.generate(texts)

        assert mock_client.embeddings.create.call_count == 3  # 32 + 32 + 6
        assert len(vectors) == 70


# ---------------------------------------------------------------------------
# EmbeddingGenerator — Fail Fast error handling
# ---------------------------------------------------------------------------

class TestEmbeddingGeneratorFailFast:
    @patch("src.vectordb.embedding_generator.Mistral")
    def test_raises_embedding_error_on_api_failure(self, mock_mistral_cls):
        """Any API exception must be wrapped and re-raised as EmbeddingError."""
        mock_client = MagicMock()
        mock_client.embeddings.create.side_effect = ConnectionError("Network down")
        mock_mistral_cls.return_value = mock_client

        gen = EmbeddingGenerator(api_key=FAKE_API_KEY)
        with pytest.raises(EmbeddingError, match="Mistral Embeddings API failed"):
            gen.generate(["some text"])

    @patch("src.vectordb.embedding_generator.Mistral")
    def test_raises_embedding_error_on_empty_data_response(self, mock_mistral_cls):
        """Empty .data in response must raise EmbeddingError — not silently return []."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_client.embeddings.create.return_value = mock_response
        mock_mistral_cls.return_value = mock_client

        gen = EmbeddingGenerator(api_key=FAKE_API_KEY)
        with pytest.raises(EmbeddingError, match="empty data list"):
            gen.generate(["some text"])

    @patch("src.vectordb.embedding_generator.Mistral")
    def test_raises_embedding_error_on_vector_count_mismatch(self, mock_mistral_cls):
        """If API returns fewer vectors than inputs, raise EmbeddingError."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        # Send 2 texts but only return 1 vector
        mock_response.data = [MagicMock(embedding=_make_fake_vector())]
        mock_client.embeddings.create.return_value = mock_response
        mock_mistral_cls.return_value = mock_client

        gen = EmbeddingGenerator(api_key=FAKE_API_KEY)
        with pytest.raises(EmbeddingError, match="Mismatch"):
            gen.generate(["text one", "text two"])

    @patch("src.vectordb.embedding_generator.Mistral")
    def test_raises_embedding_error_on_wrong_vector_dimension(self, mock_mistral_cls):
        """A vector of unexpected dimensionality must raise EmbeddingError."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        bad_vector = [0.1] * 384   # wrong — should be 1024
        mock_response.data = [MagicMock(embedding=bad_vector)]
        mock_client.embeddings.create.return_value = mock_response
        mock_mistral_cls.return_value = mock_client

        gen = EmbeddingGenerator(api_key=FAKE_API_KEY)
        with pytest.raises(EmbeddingError, match="Unexpected vector shape"):
            gen.generate(["one text"])

# ---------------------------------------------------------------------------
# QdrantClientWrapper — initialisation and collection management
# ---------------------------------------------------------------------------

from src.vectordb.qdrant_wrapper import QdrantClientWrapper

class TestQdrantClientWrapper:
    @patch("src.vectordb.qdrant_wrapper.QdrantClient")
    def test_init_success(self, mock_qdrant_cls):
        client = QdrantClientWrapper(url="http://fake:6333", collection_name="test_col")
        assert client is not None
        assert client.url == "http://fake:6333"
        assert client.collection_name == "test_col"
        mock_qdrant_cls.assert_called_once()

    @patch("src.vectordb.qdrant_wrapper.QdrantClient")
    def test_init_connection_error(self, mock_qdrant_cls):
        mock_qdrant_cls.side_effect = Exception("Network down")
        with pytest.raises(ConnectionError, match="Could not connect to Qdrant"):
            QdrantClientWrapper()

    @patch("src.vectordb.qdrant_wrapper.QdrantClient")
    def test_create_collection_if_not_exists_creates_when_missing(self, mock_qdrant_cls):
        mock_client_instance = MagicMock()
        mock_client_instance.collection_exists.return_value = False
        mock_qdrant_cls.return_value = mock_client_instance

        client = QdrantClientWrapper()
        client.create_collection_if_not_exists(vector_dimension=1024)

        mock_client_instance.collection_exists.assert_called_once_with(collection_name=client.collection_name)
        mock_client_instance.create_collection.assert_called_once()
        args, kwargs = mock_client_instance.create_collection.call_args
        assert kwargs["collection_name"] == client.collection_name
        assert kwargs["vectors_config"].size == 1024

    @patch("src.vectordb.qdrant_wrapper.QdrantClient")
    def test_create_collection_skips_if_exists(self, mock_qdrant_cls):
        mock_client_instance = MagicMock()
        mock_client_instance.collection_exists.return_value = True
        mock_qdrant_cls.return_value = mock_client_instance

        client = QdrantClientWrapper()
        client.create_collection_if_not_exists()

        mock_client_instance.create_collection.assert_not_called()

    @patch("src.vectordb.qdrant_wrapper.QdrantClient")
    def test_upsert_mismatch_raises_value_error(self, mock_qdrant_cls):
        client = QdrantClientWrapper()
        chunks = [{"text": "one"}, {"text": "two"}]
        vectors = [[0.1]*1024] # Only 1 vector
        
        with pytest.raises(ValueError, match="Mismatch in counts"):
            client.upsert(chunks, vectors)

    @patch("src.vectordb.qdrant_wrapper.QdrantClient")
    def test_upsert_empty_skips(self, mock_qdrant_cls):
        mock_client_instance = MagicMock()
        mock_qdrant_cls.return_value = mock_client_instance
        
        client = QdrantClientWrapper()
        client.upsert([], [])
        
        mock_client_instance.upsert.assert_not_called()

    @patch("src.vectordb.qdrant_wrapper.QdrantClient")
    def test_upsert_success(self, mock_qdrant_cls):
        mock_client_instance = MagicMock()
        mock_qdrant_cls.return_value = mock_client_instance
        
        client = QdrantClientWrapper()
        chunks = [{"text": "chunk one", "metadata": {"source": "doc1"}}]
        vectors = [[0.5] * 1024]
        
        client.upsert(chunks, vectors)
        
        mock_client_instance.upsert.assert_called_once()
        args, kwargs = mock_client_instance.upsert.call_args
        assert "points" in kwargs
        assert len(kwargs["points"]) == 1
        
        point = kwargs["points"][0]
        assert point.vector == vectors[0]
        assert point.payload["text"] == "chunk one"
        assert point.payload["source"] == "doc1"

    @patch("src.vectordb.qdrant_wrapper.QdrantClient")
    def test_search_no_filters(self, mock_qdrant_cls):
        mock_client_instance = MagicMock()
        mock_client_instance.query_points.return_value.points = ["mock_result_1", "mock_result_2"]
        mock_qdrant_cls.return_value = mock_client_instance
        
        client = QdrantClientWrapper()
        results = client.search(query_vector=[0.1]*1024, top_k=2)
        
        assert len(results) == 2
        mock_client_instance.query_points.assert_called_once()
        args, kwargs = mock_client_instance.query_points.call_args
        assert kwargs["query_filter"] is None

    @patch("src.vectordb.qdrant_wrapper.QdrantClient")
    def test_search_with_filters(self, mock_qdrant_cls):
        mock_client_instance = MagicMock()
        mock_qdrant_cls.return_value = mock_client_instance
        
        client = QdrantClientWrapper()
        client.search(query_vector=[0.1]*1024, top_k=2, filters={"article_number": "10"})
        
        mock_client_instance.query_points.assert_called_once()
        args, kwargs = mock_client_instance.query_points.call_args
        query_filter = kwargs["query_filter"]
        
        assert query_filter is not None
        assert len(query_filter.must) == 1
        assert query_filter.must[0].key == "article_number"
        assert query_filter.must[0].match.value == "10"


# ---------------------------------------------------------------------------
# IndexManager — pipeline orchestration
# ---------------------------------------------------------------------------

from src.vectordb.index_manager import IndexManager

class TestIndexManager:
    def test_index_document_pipeline_success(self):
        # Mocks
        mock_parser = MagicMock()
        mock_parser.parse.return_value = {"content": "mock content", "metadata": {"file_name": "test.pdf"}}
        
        mock_preprocessor = MagicMock()
        mock_chunks = [{"text": "chunk 1", "metadata": {}}, {"text": "chunk 2", "metadata": {}}]
        mock_preprocessor.chunk.return_value = mock_chunks
        
        mock_embedder = MagicMock()
        mock_vectors = [[0.1]*1024, [0.2]*1024]
        mock_embedder.generate.return_value = mock_vectors
        
        mock_qdrant = MagicMock()
        
        manager = IndexManager(
            parser=mock_parser,
            preprocessor=mock_preprocessor,
            embedder=mock_embedder,
            qdrant_client=mock_qdrant
        )
        
        # Verify collection creation is called during init
        mock_qdrant.create_collection_if_not_exists.assert_called_once()
        
        # Act
        num_indexed = manager.index_document("fake_path.pdf", "sme_doc")
        
        # Assertions
        assert num_indexed == 2
        
        mock_parser.parse.assert_called_once_with(file_path="fake_path.pdf")
        
        mock_preprocessor.chunk.assert_called_once_with(
            content="mock content",
            metadata={"file_name": "test.pdf"},
            document_source="sme_doc"
        )
        
        mock_embedder.generate.assert_called_once()
        args, kwargs = mock_embedder.generate.call_args
        assert kwargs["texts"] == ["chunk 1", "chunk 2"]
        
        mock_qdrant.upsert.assert_called_once_with(
            chunks=mock_chunks,
            vectors=mock_vectors
        )

    def test_index_document_empty_content_returns_zero(self):
        mock_parser = MagicMock()
        mock_parser.parse.return_value = {"content": "", "metadata": {}}
        
        manager = IndexManager(
            parser=mock_parser,
            preprocessor=MagicMock(),
            embedder=MagicMock(),
            qdrant_client=MagicMock()
        )
        
        assert manager.index_document("fake.pdf", "doc") == 0
        manager.preprocessor.chunk.assert_not_called()

    def test_index_document_no_chunks_returns_zero(self):
        mock_parser = MagicMock()
        mock_parser.parse.return_value = {"content": "text", "metadata": {}}
        
        mock_preprocessor = MagicMock()
        mock_preprocessor.chunk.return_value = []
        
        manager = IndexManager(
            parser=mock_parser,
            preprocessor=mock_preprocessor,
            embedder=MagicMock(),
            qdrant_client=MagicMock()
        )
        
        assert manager.index_document("fake.pdf", "doc") == 0
        manager.embedder.generate.assert_not_called()
