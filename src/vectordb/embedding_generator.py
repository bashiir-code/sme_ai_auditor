"""
embedding_generator.py
-----------------------
Converts text chunks into vector embeddings using the Mistral Embeddings API.

Design contract:
  - Fail Fast: Any API failure raises EmbeddingError immediately.
  - No fallback models. A vector from a different model would silently corrupt
    the Qdrant index and invalidate all similarity searches.
  - Batching: Large chunk lists are sent in configurable batches to stay within
    API rate limits without requiring callers to manage pagination.

Usage:
    gen = EmbeddingGenerator()
    vectors = gen.generate(["Article 5 prohibits...", "High-risk AI systems must..."])
    # vectors: list[list[float]] — one vector per input text
"""

import os
from typing import List

import structlog
from langfuse import observe
from mistralai.client.sdk import Mistral

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Custom exception — Fail Fast
# ---------------------------------------------------------------------------

class EmbeddingError(RuntimeError):
    """
    Raised when the Mistral Embeddings API call fails.
    Wraps the original exception for full stack traceability.
    Do NOT catch this silently — let it propagate and alert the operator.
    """


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# mistral-embed is Mistral's dedicated embedding model (1024-dim vectors).
# Vector dimension must stay consistent with the Qdrant collection config.
DEFAULT_EMBEDDING_MODEL: str = "mistral-embed"
VECTOR_DIMENSION: int = 1024        # must match Qdrant collection vector size
DEFAULT_BATCH_SIZE: int = 32        # safe default under Mistral rate limits


# ---------------------------------------------------------------------------
# EmbeddingGenerator
# ---------------------------------------------------------------------------

class EmbeddingGenerator:
    """
    Wraps the Mistral Embeddings API with batching, structured logging,
    and LangFuse tracing.

    Args:
        api_key:    Mistral API key. Defaults to MISTRAL_API_KEY env var.
        model:      Embedding model name. Default: "mistral-embed".
        batch_size: Number of texts per API call. Default: 32.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_EMBEDDING_MODEL,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        resolved_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not resolved_key:
            raise EmbeddingError(
                "MISTRAL_API_KEY is not set. "
                "Export it as an environment variable or pass it explicitly."
            )

        self._client = Mistral(api_key=resolved_key)
        self.model = model
        self.batch_size = batch_size

        logger.info(
            "EmbeddingGenerator initialised",
            model=self.model,
            batch_size=self.batch_size,
            vector_dimension=VECTOR_DIMENSION,
        )

    @observe(name="embedding_generate")
    def generate(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of text strings into vectors.

        Args:
            texts: Non-empty list of strings to embed.
                   Each string should be at most ~8 000 tokens (Mistral limit).

        Returns:
            list[list[float]] — one 1024-dimensional vector per input text,
            in the same order as *texts*.

        Raises:
            ValueError:      If *texts* is empty or contains any blank string.
            EmbeddingError:  If the Mistral API call fails for any reason.
        """
        # --- Guard: reject empty input ---
        if not texts:
            raise ValueError("texts must not be empty.")
        blank = [i for i, t in enumerate(texts) if not t or not t.strip()]
        if blank:
            raise ValueError(
                f"texts contains blank strings at indices: {blank}. "
                "Blank strings cannot be embedded."
            )

        logger.info(
            "Starting embedding generation",
            text_count=len(texts),
            model=self.model,
            batches=_batch_count(len(texts), self.batch_size),
        )

        all_vectors: List[List[float]] = []

        for batch_num, batch in enumerate(_batches(texts, self.batch_size), start=1):
            batch_vectors = self._embed_batch(batch, batch_num)
            all_vectors.extend(batch_vectors)

        logger.info(
            "Embedding generation complete",
            total_vectors=len(all_vectors),
            vector_dimension=VECTOR_DIMENSION,
        )

        return all_vectors

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _embed_batch(self, batch: List[str], batch_num: int) -> List[List[float]]:
        """Call the Mistral API for a single batch. Raises EmbeddingError on failure."""
        logger.debug(
            "Embedding batch",
            batch_num=batch_num,
            batch_size=len(batch),
        )
        try:
            response = self._client.embeddings.create(
                model=self.model,
                inputs=batch,
            )
        except Exception as exc:
            raise EmbeddingError(
                f"Mistral Embeddings API failed on batch {batch_num} "
                f"(model={self.model}, batch_size={len(batch)}): {exc}"
            ) from exc

        # Validate the response structure before trusting it
        if not response.data:
            raise EmbeddingError(
                f"Mistral returned an empty data list for batch {batch_num}. "
                "Cannot proceed — index would be corrupted."
            )
        if len(response.data) != len(batch):
            raise EmbeddingError(
                f"Mistral returned {len(response.data)} vectors for "
                f"{len(batch)} inputs in batch {batch_num}. "
                "Mismatch — index would be corrupted."
            )

        # Extract and validate each vector
        vectors: List[List[float]] = []
        for item in response.data:
            vec = item.embedding
            if not isinstance(vec, list) or len(vec) != VECTOR_DIMENSION:
                raise EmbeddingError(
                    f"Unexpected vector shape: expected list of {VECTOR_DIMENSION} floats, "
                    f"got {type(vec).__name__} of length {len(vec) if isinstance(vec, list) else 'N/A'}."
                )
            vectors.append(vec)

        return vectors


# ---------------------------------------------------------------------------
# Module-level utilities
# ---------------------------------------------------------------------------

def _batches(items: List[str], size: int):
    """Yield successive *size*-length chunks from *items*."""
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _batch_count(total: int, size: int) -> int:
    """Return the number of batches needed for *total* items at *size* each."""
    return (total + size - 1) // size
