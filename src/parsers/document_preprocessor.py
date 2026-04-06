"""
document_preprocessor.py
------------------------
Splits Markdown documents (output of DoclingParser) into 512-token chunks
with 10% overlap (~51 tokens), and attaches structured Qdrant-ready metadata.

Metadata per chunk:
  - article_number   : Detected from Markdown headings (e.g. "Article 10")
  - parent_section   : Detected chapter/section heading above the article
  - document_source  : Caller-supplied label (e.g. "eu_ai_act", "sme_doc")
  - file_name        : Source filename from DoclingParser metadata
  - chunk_index      : Position of this chunk in the document (0-based)
  - chunk_total      : Total number of chunks produced
  - overlap_with_prev: True if this chunk shares tokens with the previous one

Design note:
  Chunk size and overlap are deliberately kept at 512 / 51 tokens.
  Larger context is reconstructed on demand by the Haystack retriever using
  Qdrant metadata filters (article_number, parent_section, document_source)
  rather than by increasing chunk size upfront.
"""

import re
from typing import List, Dict, Any, Optional

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHUNK_SIZE_TOKENS: int = 512      # target tokens per chunk
OVERLAP_TOKENS: int = 51          # 10 % of 512, rounded up
# We approximate 1 token ≈ 4 characters (conservative for legal English)
CHARS_PER_TOKEN: int = 4

CHUNK_SIZE_CHARS: int = CHUNK_SIZE_TOKENS * CHARS_PER_TOKEN   # 2048
OVERLAP_CHARS: int = OVERLAP_TOKENS * CHARS_PER_TOKEN                            # 204

# Regex patterns for EU legal document structure
_ARTICLE_PATTERN = re.compile(
    r"^#+\s*(Article\s+\d+[a-z]?(?:\s*[–\-]\s*[^\n]*)?)",
    re.IGNORECASE | re.MULTILINE,
)
_SECTION_PATTERN = re.compile(
    r"^#+\s*((?:Chapter|Section|Title|Annex)\s+[IVXLCDM\d]+[^\n]*)",
    re.IGNORECASE | re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_article(text: str) -> Optional[str]:
    """Return the first Article heading found in *text*, or None."""
    m = _ARTICLE_PATTERN.search(text)
    return m.group(1).strip() if m else None


def _extract_section(text: str) -> Optional[str]:
    """Return the first Chapter/Section/Title/Annex heading found in *text*, or None."""
    m = _SECTION_PATTERN.search(text)
    return m.group(1).strip() if m else None


def _split_into_chunks(text: str) -> List[str]:
    """
    Split *text* into overlapping character-level windows that approximate
    CHUNK_SIZE_TOKENS tokens (at CHARS_PER_TOKEN chars/token).

    Windows slide forward by (CHUNK_SIZE_CHARS - OVERLAP_CHARS) each step.
    Each window is word-boundary aligned: we do not cut mid-word.
    """
    stride = CHUNK_SIZE_CHARS - OVERLAP_CHARS   # 2048 - 204 = 1844 chars
    chunks: List[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + CHUNK_SIZE_CHARS

        if end < text_len:
            # Walk back to the nearest whitespace so we don't cut a word
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start += stride
        if start >= text_len:
            break

    return chunks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class DocumentPreprocessor:
    """
    Converts the output of DoclingParser into Qdrant-ready chunks.

    Usage:
        preprocessor = DocumentPreprocessor()
        chunks = preprocessor.chunk(
            content=parsed_result["content"],
            metadata=parsed_result["metadata"],
            document_source="eu_ai_act",
        )
        # Each item in chunks is ready to be embedded and upserted into Qdrant.
    """

    def chunk(
        self,
        content: str,
        metadata: Dict[str, Any],
        document_source: str,
    ) -> List[Dict[str, Any]]:
        """
        Split *content* into overlapping 512-token chunks with rich metadata.

        Args:
            content:         Markdown string from DoclingParser.parse()["content"].
            metadata:        Metadata dict from DoclingParser.parse()["metadata"].
            document_source: Semantic label for the source document.
                             Use one of: "eu_ai_act", "eu_data_act",
                             "cen_cenelec", "sme_doc".

        Returns:
            List of chunk dicts each with keys "text" and "metadata".

        Raises:
            ValueError: If *content* is empty or *document_source* is blank.
        """
        if not content or not content.strip():
            raise ValueError("content must not be empty.")
        if not document_source or not document_source.strip():
            raise ValueError("document_source must not be empty.")

        logger.info(
            "Starting document chunking",
            document_source=document_source,
            file_name=metadata.get("file_name", "unknown"),
            content_length=len(content),
        )

        raw_chunks = _split_into_chunks(content)
        total = len(raw_chunks)

        # Track the last seen article / section so heading context
        # carries forward into chunks that don't restate the heading.
        current_article: Optional[str] = None
        current_section: Optional[str] = None
        result: List[Dict[str, Any]] = []

        for idx, chunk_text in enumerate(raw_chunks):
            # Update context trackers whenever a heading is found in this chunk
            detected_article = _extract_article(chunk_text)
            detected_section = _extract_section(chunk_text)

            if detected_article:
                current_article = detected_article
            if detected_section:
                current_section = detected_section

            chunk_meta: Dict[str, Any] = {
                "chunk_index": idx,
                "chunk_total": total,
                "article_number": current_article,
                "parent_section": current_section,
                "document_source": document_source,
                "file_name": metadata.get("file_name", "unknown"),
                "file_path": metadata.get("file_path", ""),
                "page_count": metadata.get("page_count"),
                "overlap_with_prev": idx > 0,      # first chunk has no predecessor
            }

            result.append({"text": chunk_text, "metadata": chunk_meta})

        logger.info(
            "Chunking complete",
            document_source=document_source,
            chunk_total=total,
            chunk_size_tokens=CHUNK_SIZE_TOKENS,
            overlap_tokens=OVERLAP_TOKENS,
        )

        return result
