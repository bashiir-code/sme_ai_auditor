"""
qdrant_client.py
----------------
Wrapper around the Qdrant Vector Database client.

Handles connection setup, collection management, upserting embedded chunks,
and vector search with metadata filtering.

Design contract:
  - Configured purely via environment variables (QDRANT_URL, QDRANT_COLLECTION_NAME).
  - Strongly typed schemas for records (PointStruct).
  - Explicit error handling if Qdrant is unreachable.
"""

import os
from typing import List, Optional, Any, Dict
import uuid

import structlog
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

logger = structlog.get_logger(__name__)


class QdrantClientWrapper:
    """
    Wrapper for Qdrant operations customized for SME AI Auditor.

    Usage:
        client = QdrantClientWrapper()
        client.create_collection_if_not_exists(vector_dimension=1024)
        client.upsert(chunks, vectors)
        results = client.search(query_vector, top_k=5, filters={"article_number": "Article 10"})
    """

    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None, collection_name: Optional[str] = None):
        """Initialize the Qdrant client from env vars or overrides."""
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self.collection_name = collection_name or os.getenv("QDRANT_COLLECTION_NAME", "sme_ai_auditor_compliance")

        # Support in-memory or persistent local storage if specified
        client_kwargs = {}
        if self.url == ":memory:":
            client_kwargs["location"] = ":memory:"
            logger.info("Initializing in-memory QdrantClient")
        elif self.url.startswith("/") or self.url.startswith("./"):
            client_kwargs["path"] = self.url
            logger.info("Initializing persistent local QdrantClient", path=self.url)
        else:
            client_kwargs["url"] = self.url
            if self.api_key:
                client_kwargs["api_key"] = self.api_key

        try:
            self._client = QdrantClient(**client_kwargs)
            logger.info("QdrantClient initialized", url=self.url, collection=self.collection_name)
        except Exception as e:
            logger.error("Failed to initialize QdrantClient", error=str(e), url=self.url)
            raise ConnectionError(f"Could not connect to Qdrant at {self.url}: {e}") from e

    def health_check(self) -> bool:
        """Check if the Qdrant server is reachable and responsive."""
        try:
            collections = self._client.get_collections()
            return collections is not None
        except Exception as e:
            logger.error("Qdrant health check failed", error=str(e))
            return False

    def create_collection_if_not_exists(self, vector_dimension: int = 1024) -> None:
        """
        Creates the vector collection if it doesn't already exist.
        VECTOR_DIMENSION defaults to 1024 (mistral-embed).
        """
        try:
            if not self._client.collection_exists(collection_name=self.collection_name):
                logger.info(
                    "Collection does not exist. Creating new collection.", 
                    collection=self.collection_name, 
                    vector_dimension=vector_dimension
                )
                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_dimension,
                        distance=models.Distance.COSINE
                    )
                )
            else:
                logger.debug("Collection already exists.", collection=self.collection_name)
        except Exception as e:
            logger.error("Failed to check or create collection", error=str(e), collection=self.collection_name)
            raise RuntimeError(f"Could not initialize Qdrant collection: {e}") from e

    def upsert(self, chunks: List[Dict[str, Any]], vectors: List[List[float]]) -> None:
        """
        Upsert a batch of text chunks and their corresponding vectors to Qdrant.

        Args:
            chunks: List of dictionaries, each containing 'text' and 'metadata'.
                    Produced by `DocumentPreprocessor`.
            vectors: List of float arrays, produced by `EmbeddingGenerator`.

        Raises:
            ValueError: If lengths of chunks and vectors don't match.
            RuntimeError: If upsert operation fails.
        """
        if not chunks or not vectors:
            logger.warning("Empty chunks or vectors provided to upsert. Skipping.")
            return

        if len(chunks) != len(vectors):
            raise ValueError(
                f"Mismatch in counts: {len(chunks)} chunks vs {len(vectors)} vectors."
            )

        points = []
        for chunk, vector in zip(chunks, vectors):
            # Qdrant requires UUIDs or Integers for point IDs.
            # Using UUID4 for simplicity, although deterministic IDs could be generated 
            # if updating existing chunks is a requirement.
            point_id = str(uuid.uuid4())
            
            # Combine text and metadata into the Qdrant payload
            payload = chunk.get("metadata", {}).copy()
            payload["text"] = chunk.get("text", "")

            point = models.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
            points.append(point)

        logger.info("Upserting points to Qdrant", count=len(points), collection=self.collection_name)
        try:
            self._client.upsert(
                collection_name=self.collection_name,
                points=points
            )
        except Exception as e:
            logger.error("Qdrant upsert failed", error=str(e), count=len(points))
            raise RuntimeError(f"Failed to upsert points to Qdrant: {e}") from e

    def search(self, query_vector: List[float], top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        Search for the top_k most similar vectors, optionally applying metadata filters.

        Args:
            query_vector: The embedded query.
            top_k: Number of results to return.
            filters: Dictionary of exact-match filters, e.g., {"article_number": "Article 10"}.

        Returns:
            List of ScoredPoint objects from Qdrant.
        """
        qdrant_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                if value is not None:
                    conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        )
                    )
            if conditions:
                qdrant_filter = models.Filter(must=conditions)

        logger.debug("Searching Qdrant", top_k=top_k, filters=filters)
        try:
            results = self._client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=qdrant_filter,
                limit=top_k
            )
            return results.points
        except Exception as e:
            logger.error("Qdrant search failed", error=str(e))
            raise RuntimeError(f"Failed to search Qdrant: {e}") from e

    def delete_collection(self) -> None:
        """Deletes the collection. Destructive operation."""
        try:
            logger.warning("Deleting collection", collection=self.collection_name)
            self._client.delete_collection(collection_name=self.collection_name)
        except Exception as e:
            logger.error("Failed to delete collection", error=str(e))
            raise RuntimeError(f"Could not delete collection {self.collection_name}: {e}") from e
