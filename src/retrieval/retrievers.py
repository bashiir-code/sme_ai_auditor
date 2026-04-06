"""
retrievers.py
-------------
Haystack 2.x compatible retriever for Qdrant.

Wraps the QdrantClientWrapper to allow seamless integration into Haystack pipelines.
Translates Qdrant ScoredPoint objects into Haystack Document objects.
"""

import structlog
from typing import List, Dict, Any, Optional

from haystack import component, Document

from src.vectordb.qdrant_client import QdrantClientWrapper

logger = structlog.get_logger(__name__)


@component
class QdrantRetriever:
    """
    A Haystack component that retrieves documents from Qdrant based on a query vector.
    """

    def __init__(self, qdrant_client: Optional[QdrantClientWrapper] = None):
        """
        Initialize the retriever.
        If no client is provided, instantiates a default QdrantClientWrapper.
        """
        self.qdrant_client = qdrant_client or QdrantClientWrapper()
        logger.info("QdrantRetriever initialized")

    @component.output_types(documents=List[Document])
    def run(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[Document]]:
        """
        Executes the vector search against Qdrant.

        Args:
            query_vector: The embedded query vector (must match collection dimensions).
            top_k: The number of top results to retrieve.
            filters: Optional dictionary of exact-match metadata filters.

        Returns:
            A dictionary containing a "documents" key with a list of Haystack Documents.

        Raises:
            ValueError: If query_vector is empty.
            RuntimeError: If the underlying Qdrant search fails.
        """
        if not query_vector:
            raise ValueError("query_vector cannot be empty.")

        logger.debug(
            "Executing QdrantRetriever",
            top_k=top_k,
            vector_dimension=len(query_vector),
            filters=filters
        )

        try:
            # client.search returns a list of qdrant_client.models.ScoredPoint
            scored_points = self.qdrant_client.search(
                query_vector=query_vector,
                top_k=top_k,
                filters=filters
            )
        except Exception as e:
            logger.error("QdrantRetriever search failed", error=str(e))
            raise RuntimeError(f"QdrantRetriever search failed: {e}") from e

        documents: List[Document] = []
        for point in scored_points:
            # point.payload holds the text and metadata we packed during upsert
            payload = point.payload or {}
            
            # Extract text safely, removing it from metadata
            text = payload.pop("text", "")

            doc = Document(
                content=text,
                meta=payload,
                score=point.score,
                id=str(point.id)
            )
            documents.append(doc)

        logger.info(
            "QdrantRetriever search complete",
            results_found=len(documents)
        )

        return {"documents": documents}
