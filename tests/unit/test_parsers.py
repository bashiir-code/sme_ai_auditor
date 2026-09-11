"""
tests/unit/test_parsers.py
--------------------------
Unit tests for DoclingParser and DocumentPreprocessor.
All tests run without live files — Docling internals are mocked.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.parsers.docling_parser import DoclingParser, SUPPORTED_FORMATS


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_mock_doc(markdown: str = "# Test\n\nSome text.", tables: list = None):
    """Build a minimal mock of the Docling Document object."""
    doc = MagicMock()
    doc.export_to_markdown.return_value = markdown
    doc.pages = [MagicMock()]           # 1 page
    doc.tables = tables if tables is not None else [MagicMock()]  # 1 table
    return doc


def _make_mock_result(markdown: str = "# Test\n\nSome text."):
    """Build a mock Docling ConversionResult."""
    result = MagicMock()
    result.document = _make_mock_doc(markdown)
    return result


# ---------------------------------------------------------------------------
# DoclingParser — instantiation
# ---------------------------------------------------------------------------

class TestDoclingParserInit:
    def test_creates_instance_without_error(self):
        """Parser should initialise with no exceptions."""
        parser = DoclingParser()
        assert parser is not None

    def test_converter_is_set(self):
        """Internal converter attribute must be present after init."""
        parser = DoclingParser()
        assert hasattr(parser, "_converter")


# ---------------------------------------------------------------------------
# DoclingParser — guard rails
# ---------------------------------------------------------------------------

class TestDoclingParserGuards:
    def test_raises_file_not_found_for_missing_file(self, tmp_path):
        """Non-existent file must raise FileNotFoundError."""
        parser = DoclingParser()
        with pytest.raises(FileNotFoundError, match="Document not found"):
            parser.parse(str(tmp_path / "does_not_exist.pdf"))

    def test_raises_value_error_for_unsupported_format(self, tmp_path):
        """Unsupported extensions must raise ValueError."""
        bad_file = tmp_path / "doc.exe"
        bad_file.write_text("some content")
        parser = DoclingParser()
        with pytest.raises(ValueError, match="Unsupported format"):
            parser.parse(str(bad_file))

    @pytest.mark.parametrize("ext", [".pdf", ".docx"])
    def test_supported_formats_constant_includes_ext(self, ext):
        """SUPPORTED_FORMATS must contain PDF and DOCX."""
        assert ext in SUPPORTED_FORMATS


# ---------------------------------------------------------------------------
# DoclingParser — successful parse
# ---------------------------------------------------------------------------

class TestDoclingParserSuccess:
    @patch("src.parsers.docling_parser.DocumentConverter")
    def test_returns_content_and_metadata_keys(self, mock_converter_cls, tmp_path):
        """parse() must return a dict with 'content' and 'metadata' keys."""
        # Arrange
        mock_converter_cls.return_value.convert.return_value = _make_mock_result()
        pdf = tmp_path / "spec.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")  # file must exist for the guard

        parser = DoclingParser()
        result = parser.parse(str(pdf))

        assert "content" in result
        assert "metadata" in result

    @patch("src.parsers.docling_parser.DocumentConverter")
    def test_content_is_string(self, mock_converter_cls, tmp_path):
        """'content' value must be a string."""
        mock_converter_cls.return_value.convert.return_value = _make_mock_result("# Hello")
        pdf = tmp_path / "spec.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")

        parser = DoclingParser()
        result = parser.parse(str(pdf))

        assert isinstance(result["content"], str)
        assert "Hello" in result["content"]

    @patch("src.parsers.docling_parser.DocumentConverter")
    def test_metadata_contains_expected_fields(self, mock_converter_cls, tmp_path):
        """metadata dict must have file_path, page_count, has_tables, table_count."""
        mock_converter_cls.return_value.convert.return_value = _make_mock_result()
        pdf = tmp_path / "report.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")

        parser = DoclingParser()
        result = parser.parse(str(pdf))
        meta = result["metadata"]

        assert "file_path" in meta
        assert "file_name" in meta
        assert "file_format" in meta
        assert "page_count" in meta
        assert "has_tables" in meta
        assert "table_count" in meta

    @patch("src.parsers.docling_parser.DocumentConverter")
    def test_metadata_file_format_is_lowercase_suffix(self, mock_converter_cls, tmp_path):
        """file_format should be the lowercase extension."""
        mock_converter_cls.return_value.convert.return_value = _make_mock_result()
        pdf = tmp_path / "spec.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")

        parser = DoclingParser()
        result = parser.parse(str(pdf))

        assert result["metadata"]["file_format"] == ".pdf"

    @patch("src.parsers.docling_parser.DocumentConverter")
    def test_raises_value_error_on_converter_exception(self, mock_converter_cls, tmp_path):
        """If Docling raises internally, parse() must wrap it in a ValueError."""
        mock_converter_cls.return_value.convert.side_effect = RuntimeError("Docling boom")
        pdf = tmp_path / "broken.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")

        parser = DoclingParser()
        with pytest.raises(ValueError, match="Document parsing failed"):
            parser.parse(str(pdf))


# ---------------------------------------------------------------------------
# DocumentPreprocessor tests
# ---------------------------------------------------------------------------

from src.parsers.document_preprocessor import (
    DocumentPreprocessor,
    CHUNK_SIZE_TOKENS,
    OVERLAP_TOKENS,
    CHUNK_SIZE_CHARS,
    OVERLAP_CHARS,
)

# Shared sample metadata (mirrors DoclingParser output)
SAMPLE_META = {
    "file_name": "eu_ai_act.pdf",
    "file_path": "/data/eu_ai_act/eu_ai_act.pdf",
    "file_format": ".pdf",
    "page_count": 100,
    "has_tables": True,
    "table_count": 5,
}


class TestDocumentPreprocessorConstants:
    def test_chunk_size_is_512_tokens(self):
        assert CHUNK_SIZE_TOKENS == 512

    def test_overlap_is_10_percent(self):
        """51 tokens ≈ 10% of 512."""
        ratio = OVERLAP_TOKENS / CHUNK_SIZE_TOKENS
        assert 0.09 <= ratio <= 0.11, f"Overlap ratio {ratio:.2%} is outside 9–11%"

    def test_chars_are_4x_tokens(self):
        """Character window must be exactly 4× the token window."""
        assert CHUNK_SIZE_CHARS == CHUNK_SIZE_TOKENS * 4
        assert OVERLAP_CHARS == OVERLAP_TOKENS * 4


class TestDocumentPreprocessorGuards:
    def test_raises_on_empty_content(self):
        pp = DocumentPreprocessor()
        with pytest.raises(ValueError, match="content must not be empty"):
            pp.chunk(content="", metadata=SAMPLE_META, document_source="eu_ai_act")

    def test_raises_on_whitespace_only_content(self):
        pp = DocumentPreprocessor()
        with pytest.raises(ValueError, match="content must not be empty"):
            pp.chunk(content="   \n  ", metadata=SAMPLE_META, document_source="eu_ai_act")

    def test_raises_on_empty_document_source(self):
        pp = DocumentPreprocessor()
        with pytest.raises(ValueError, match="document_source must not be empty"):
            pp.chunk(content="Some legal text.", metadata=SAMPLE_META, document_source="")

    def test_raises_on_blank_document_source(self):
        pp = DocumentPreprocessor()
        with pytest.raises(ValueError, match="document_source must not be empty"):
            pp.chunk(content="Some legal text.", metadata=SAMPLE_META, document_source="   ")


class TestDocumentPreprocessorChunking:
    def _make_content(self, approx_chars: int) -> str:
        """Generate a legal-ish text block of roughly approx_chars characters."""
        word = "compliance "  # 11 chars
        return (word * (approx_chars // len(word) + 1))[:approx_chars]

    def test_short_content_produces_single_chunk(self):
        """Content shorter than CHUNK_SIZE_CHARS must produce exactly 1 chunk."""
        pp = DocumentPreprocessor()
        content = self._make_content(500)   # well under 2048 chars
        chunks = pp.chunk(content=content, metadata=SAMPLE_META, document_source="sme_doc")
        assert len(chunks) == 1

    def test_long_content_produces_multiple_chunks(self):
        """Content of ~3 × chunk size should produce more than 1 chunk."""
        pp = DocumentPreprocessor()
        content = self._make_content(CHUNK_SIZE_CHARS * 3)
        chunks = pp.chunk(content=content, metadata=SAMPLE_META, document_source="eu_ai_act")
        assert len(chunks) > 1

    def test_each_chunk_text_not_longer_than_chunk_size(self):
        """No individual chunk may exceed CHUNK_SIZE_CHARS characters."""
        pp = DocumentPreprocessor()
        content = self._make_content(CHUNK_SIZE_CHARS * 4)
        chunks = pp.chunk(content=content, metadata=SAMPLE_META, document_source="eu_ai_act")
        for ch in chunks:
            assert len(ch["text"]) <= CHUNK_SIZE_CHARS, (
                f"Chunk too large: {len(ch['text'])} chars (max {CHUNK_SIZE_CHARS})"
            )

    def test_first_chunk_overlap_with_prev_is_false(self):
        """The very first chunk has no predecessor — flag must be False."""
        pp = DocumentPreprocessor()
        content = self._make_content(CHUNK_SIZE_CHARS * 3)
        chunks = pp.chunk(content=content, metadata=SAMPLE_META, document_source="eu_ai_act")
        assert chunks[0]["metadata"]["overlap_with_prev"] is False

    def test_subsequent_chunks_overlap_with_prev_is_true(self):
        """All chunks after the first must have overlap_with_prev=True."""
        pp = DocumentPreprocessor()
        content = self._make_content(CHUNK_SIZE_CHARS * 3)
        chunks = pp.chunk(content=content, metadata=SAMPLE_META, document_source="eu_ai_act")
        for ch in chunks[1:]:
            assert ch["metadata"]["overlap_with_prev"] is True

    def test_chunk_index_is_sequential(self):
        """chunk_index must be 0, 1, 2, … in order."""
        pp = DocumentPreprocessor()
        content = self._make_content(CHUNK_SIZE_CHARS * 3)
        chunks = pp.chunk(content=content, metadata=SAMPLE_META, document_source="eu_ai_act")
        for i, ch in enumerate(chunks):
            assert ch["metadata"]["chunk_index"] == i

    def test_chunk_total_matches_len(self):
        """chunk_total in every chunk's metadata must equal len(chunks)."""
        pp = DocumentPreprocessor()
        content = self._make_content(CHUNK_SIZE_CHARS * 3)
        chunks = pp.chunk(content=content, metadata=SAMPLE_META, document_source="eu_ai_act")
        for ch in chunks:
            assert ch["metadata"]["chunk_total"] == len(chunks)


class TestDocumentPreprocessorMetadata:
    def test_all_required_metadata_keys_present(self):
        """Every chunk must carry all mandatory Qdrant metadata keys."""
        required_keys = {
            "chunk_index", "chunk_total",
            "article_number", "parent_section",
            "document_source", "file_name",
            "file_path", "page_count", "overlap_with_prev",
        }
        pp = DocumentPreprocessor()
        chunks = pp.chunk(
            content="Some short legal text for metadata test.",
            metadata=SAMPLE_META,
            document_source="eu_data_act",
        )
        for ch in chunks:
            assert required_keys.issubset(ch["metadata"].keys()), (
                f"Missing keys: {required_keys - ch['metadata'].keys()}"
            )

    def test_document_source_propagated_correctly(self):
        pp = DocumentPreprocessor()
        chunks = pp.chunk(
            content="Some text.",
            metadata=SAMPLE_META,
            document_source="cen_cenelec",
        )
        for ch in chunks:
            assert ch["metadata"]["document_source"] == "cen_cenelec"

    def test_file_name_propagated_from_meta(self):
        pp = DocumentPreprocessor()
        chunks = pp.chunk(
            content="Some text.",
            metadata=SAMPLE_META,
            document_source="eu_ai_act",
        )
        for ch in chunks:
            assert ch["metadata"]["file_name"] == "eu_ai_act.pdf"

    def test_article_number_extracted_from_heading(self):
        """A chunk containing '## Article 10' must have article_number='Article 10'."""
        pp = DocumentPreprocessor()
        content = "## Article 10\n\nProviders of high-risk AI systems shall establish a quality system."
        chunks = pp.chunk(content=content, metadata=SAMPLE_META, document_source="eu_ai_act")
        assert chunks[0]["metadata"]["article_number"] == "Article 10"

    def test_parent_section_extracted_from_heading(self):
        """A chunk containing a Chapter heading must populate parent_section."""
        pp = DocumentPreprocessor()
        content = "# Chapter III\n\n## Article 10\n\nRequirements for high-risk AI systems."
        chunks = pp.chunk(content=content, metadata=SAMPLE_META, document_source="eu_ai_act")
        assert chunks[0]["metadata"]["parent_section"] == "Chapter III"

    def test_article_number_none_when_no_heading_found(self):
        """Content with no article heading must have article_number=None."""
        pp = DocumentPreprocessor()
        content = "This is an introductory preamble with no article heading."
        chunks = pp.chunk(content=content, metadata=SAMPLE_META, document_source="eu_ai_act")
        assert chunks[0]["metadata"]["article_number"] is None

    def test_article_carries_forward_to_next_chunk(self):
        """
        If chunk N contains '## Article 5' but chunk N+1 has no heading,
        chunk N+1 must still report article_number='Article 5' (carry-forward).
        """
        pp = DocumentPreprocessor()
        # Force two chunks: header in first, plain text floods the second
        header = "## Article 5\n\nProhibited AI practices.\n\n"
        filler = "x " * (CHUNK_SIZE_CHARS // 2)   # enough to push into second chunk
        content = header + filler
        chunks = pp.chunk(content=content, metadata=SAMPLE_META, document_source="eu_ai_act")

        if len(chunks) > 1:
            assert chunks[1]["metadata"]["article_number"] == "Article 5", (
                "Article number must carry forward to chunks that lack their own heading."
            )

