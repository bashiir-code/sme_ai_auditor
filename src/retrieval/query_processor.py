"""
query_processor.py
------------------
Haystack 2.x compatible component for processing text queries.

Takes a natural language query, embeds it into a vector using EmbeddingGenerator,
and passes the vector (plus top_k and filters) exactly as expected by the QdrantRetriever.
"""

import structlog
from typing import Dict, Any, Optional, List

from haystack import component

from src.vectordb.embedding_generator import EmbeddingGenerator

logger = structlog.get_logger(__name__)


@component
class QueryProcessor:
    """
    Translates a text query into a vector representation for retrieval.
    """

    def __init__(self, embedder: Optional[EmbeddingGenerator] = None):
        """
        Initialize the QueryProcessor.
        Allows dependency injection of the EmbeddingGenerator for testing.
        """
        self.embedder = embedder or EmbeddingGenerator()
        logger.info("QueryProcessor initialized")

    @component.output_types(
        query_vector=List[float],
        top_k=int,
        filters=Optional[Dict[str, Any]]
    )
    def run(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes the query embedding.

        Args:
            query: The natural language string to search for.
            top_k: Number of results requested. Passed through to the retriever.
            filters: Optional metadata filters. Passed through to the retriever.

        Returns:
            A dictionary matching the input requirements of QdrantRetriever.

        Raises:
            ValueError: If the query is empty or just whitespace.
            RuntimeError: If embedding generation fails.
        """
        if not query or not query.strip():
            raise ValueError("query cannot be empty or whitespace.")

        logger.debug(
            "Processing text query",
            query_length=len(query),
            top_k=top_k,
            filters=filters
        )

        try:
            # embedder.generate takes a list and returns a list of vectors.
            vectors = self.embedder.generate([query])
            query_vector = vectors[0]
        except Exception as e:
            logger.error("Failed to generate embedding for query", error=str(e))
            raise RuntimeError(f"Query processing failed: {e}") from e

        logger.info("Query successfully embedded")

        return {
            "query_vector": query_vector,
            "top_k": top_k,
            "filters": filters
        }
