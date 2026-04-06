"""
tests/unit/test_retrieval.py
----------------------------
Unit tests for Haystack 2.x Retrieval components.
"""

import pytest
from unittest.mock import MagicMock, patch

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from haystack import Document
from src.retrieval.retrievers import QdrantRetriever


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class MockScoredPoint:
    def __init__(self, id, score, payload):
        self.id = id
        self.score = score
        self.payload = payload


# ---------------------------------------------------------------------------
# QdrantRetriever Tests
# ---------------------------------------------------------------------------

class TestQdrantRetriever:
    def test_init_success(self):
        mock_qdrant = MagicMock()
        retriever = QdrantRetriever(qdrant_client=mock_qdrant)
        assert retriever.qdrant_client == mock_qdrant

    def test_run_empty_vector_raises_value_error(self):
        retriever = QdrantRetriever(qdrant_client=MagicMock())
        with pytest.raises(ValueError, match="query_vector cannot be empty"):
            retriever.run(query_vector=[])

    def test_run_search_failure_raises_runtime_error(self):
        mock_qdrant = MagicMock()
        mock_qdrant.search.side_effect = RuntimeError("DB down")
        
        retriever = QdrantRetriever(qdrant_client=mock_qdrant)
        with pytest.raises(RuntimeError, match="QdrantRetriever search failed"):
            retriever.run(query_vector=[0.1, 0.2])

    def test_run_success_translates_points_to_documents(self):
        mock_qdrant = MagicMock()
        mock_points = [
            MockScoredPoint(
                id="uuid-1",
                score=0.95,
                payload={"text": "chunk 1", "article_number": "Article 10"}
            ),
            MockScoredPoint(
                id="uuid-2",
                score=0.88,
                payload={"text": "chunk 2"} # No extra metadata
            )
        ]
        mock_qdrant.search.return_value = mock_points
        
        retriever = QdrantRetriever(qdrant_client=mock_qdrant)
        
        # Act
        result = retriever.run(query_vector=[0.5] * 1024, top_k=2, filters={"source": "eu_ai_act"})
        
        # Assert Qdrant client was called correctly
        mock_qdrant.search.assert_called_once_with(
            query_vector=[0.5] * 1024,
            top_k=2,
            filters={"source": "eu_ai_act"}
        )
        
        # Assert output structure
        assert "documents" in result
        docs = result["documents"]
        assert len(docs) == 2
        
        # Verify translation from ScoredPoint to Document
        assert isinstance(docs[0], Document)
        assert docs[0].id == "uuid-1"
        assert docs[0].score == 0.95
        assert docs[0].content == "chunk 1"
        assert docs[0].meta == {"article_number": "Article 10"} # Text should be popped
        
        assert isinstance(docs[1], Document)
        assert docs[1].id == "uuid-2"
        assert docs[1].score == 0.88
        assert docs[1].content == "chunk 2"
        assert docs[1].meta == {}


# ---------------------------------------------------------------------------
# QueryProcessor Tests
# ---------------------------------------------------------------------------

from src.retrieval.query_processor import QueryProcessor

class TestQueryProcessor:
    def test_init_success(self):
        mock_embedder = MagicMock()
        qp = QueryProcessor(embedder=mock_embedder)
        assert qp.embedder == mock_embedder

    def test_run_empty_query_raises_value_error(self):
        qp = QueryProcessor(embedder=MagicMock())
        with pytest.raises(ValueError, match="query cannot be empty"):
            qp.run(query="")

    def test_run_whitespace_query_raises_value_error(self):
        qp = QueryProcessor(embedder=MagicMock())
        with pytest.raises(ValueError, match="query cannot be empty"):
            qp.run(query="   \n  ")

    def test_run_embedding_failure_raises_runtime_error(self):
        mock_embedder = MagicMock()
        mock_embedder.generate.side_effect = RuntimeError("API down")
        
        qp = QueryProcessor(embedder=mock_embedder)
        with pytest.raises(RuntimeError, match="Query processing failed"):
            qp.run(query="test query")

    def test_run_success_returns_correct_dict(self):
        mock_embedder = MagicMock()
        # embedder returns a list of vectors
        mock_vector = [0.1, 0.2, 0.3]
        mock_embedder.generate.return_value = [mock_vector]
        
        qp = QueryProcessor(embedder=mock_embedder)
        result = qp.run(
            query="Find article 5",
            top_k=3,
            filters={"document_source": "eu_ai_act"}
        )
        
        mock_embedder.generate.assert_called_once_with(["Find article 5"])
        
        assert "query_vector" in result
        assert result["query_vector"] == mock_vector
        assert "top_k" in result
        assert result["top_k"] == 3
        assert "filters" in result
        assert result["filters"] == {"document_source": "eu_ai_act"}


# ---------------------------------------------------------------------------
# DocumentRetrievalPipeline Tests
# ---------------------------------------------------------------------------

from src.retrieval.haystack_pipeline_builder import DocumentRetrievalPipeline

class TestDocumentRetrievalPipeline:
    @patch("src.retrieval.haystack_pipeline_builder.Pipeline")
    def test_pipeline_construction_and_run(self, mock_pipeline_cls):
        mock_pipeline_instance = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline_instance
        
        # Act: Init pipeline 
        pipeline_wrapper = DocumentRetrievalPipeline(
            query_processor=MagicMock(),
            retriever=MagicMock()
        )
        
        # Verify pipeline structure
        assert mock_pipeline_instance.add_component.call_count == 2
        assert mock_pipeline_instance.connect.call_count == 3
        
        # Setup run mock
        mock_doc = Document(content="test content")
        mock_pipeline_instance.run.return_value = {
            "qdrant_retriever": {
                "documents": [mock_doc]
            }
        }
        
        # Act: Run query
        docs = pipeline_wrapper.run_query(
            query="High-risk AI systems",
            filters={"source": "eu_ai_act"},
            top_k=2
        )
        
        # Assertions
        assert len(docs) == 1
        assert docs[0].content == "test content"
        
        # Verify pipeline.run was called correctly
        mock_pipeline_instance.run.assert_called_once()
        args, kwargs = mock_pipeline_instance.run.call_args
        
        data = args[0]
        assert "query_processor" in data
        qp_data = data["query_processor"]
        assert qp_data["query"] == "High-risk AI systems"
        assert qp_data["filters"] == {"source": "eu_ai_act"}
        assert qp_data["top_k"] == 2

    @patch("src.retrieval.haystack_pipeline_builder.Pipeline")
    def test_run_query_empty_string_returns_empty_list(self, mock_pipeline_cls):
        mock_pipeline_instance = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline_instance
        
        pipeline_wrapper = DocumentRetrievalPipeline(
            query_processor=MagicMock(),
            retriever=MagicMock()
        )
        
        # Should return empty without hitting the pipeline
        docs = pipeline_wrapper.run_query("   ")
        assert len(docs) == 0
        mock_pipeline_instance.run.assert_not_called()

    @patch("src.retrieval.haystack_pipeline_builder.Pipeline")
    def test_run_query_pipeline_failure_raises_runtime_error(self, mock_pipeline_cls):
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.run.side_effect = Exception("DAG Error")
        mock_pipeline_cls.return_value = mock_pipeline_instance
        
        pipeline_wrapper = DocumentRetrievalPipeline(
            query_processor=MagicMock(),
            retriever=MagicMock()
        )
        
        with pytest.raises(RuntimeError, match="Failed to execute retrieval pipeline"):
            pipeline_wrapper.run_query("Valid query")


