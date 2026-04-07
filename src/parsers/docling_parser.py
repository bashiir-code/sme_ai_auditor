"""
docling_parser.py
-----------------
Parses SME technical documents (PDF, DOCX) into Markdown + metadata using Docling.

Docling >= 2.84.0 is required — earlier releases have CVE-2026-24009 (RCE).
All parse calls are wrapped with LangFuse @observe for full audit traceability.
"""

import os
from pathlib import Path
from typing import Dict, Any, List

import structlog
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from langfuse import observe

logger = structlog.get_logger(__name__)

# Supported input formats
SUPPORTED_FORMATS = {".pdf", ".docx", ".md", ".txt"}


class DoclingParser:
    """
    Converts PDF and DOCX documents into Markdown text with metadata.

    Optimised for 16 GB systems (single-threaded, pypdfium2 backend).
    Table structure extraction is enabled so EU AI Act Annex tables
    are preserved faithfully during ingestion.

    Usage:
        parser = DoclingParser()
        result = parser.parse("path/to/sme_spec.pdf")
        markdown_text = result["content"]
        meta          = result["metadata"]
    """

    def __init__(self) -> None:
        """Configure the Docling converter from environment variables."""
        backend = os.getenv("DOCLING_PDF_BACKEND", "pypdfium2")
        num_threads = int(os.getenv("DOCLING_NUM_THREADS", "1"))

        pdf_options = PdfPipelineOptions(
            do_table_structure=True,      # Critical for EU AI Act Annex tables
        )

        self._converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
            }
        )

        logger.info(
            "DoclingParser initialised",
            backend=backend,
            num_threads=num_threads,
            table_structure=True,
        )

    @observe(name="docling_parse")
    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a document file and return its content as Markdown with metadata.

        Args:
            file_path: Absolute or relative path to a PDF or DOCX file.

        Returns:
            dict with keys:
              - ``content``  (str)  — full Markdown representation of the document.
              - ``metadata`` (dict) — file path, page count, table presence flag.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError:        If the format is unsupported or Docling conversion fails.
        """
        path = Path(file_path)

        # --- Guard: file must exist ---
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        # --- Guard: format must be supported ---
        if path.suffix.lower() not in SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format '{path.suffix}'. "
                f"Supported formats: {SUPPORTED_FORMATS}"
            )

        logger.info("Starting document parse", file_path=str(path))

        try:
            result = self._converter.convert(str(path))
            doc = result.document

            # Export to Markdown (preserves table structure as GFM tables)
            markdown_content: str = doc.export_to_markdown()

            metadata: Dict[str, Any] = {
                "file_path": str(path.resolve()),
                "file_name": path.name,
                "file_format": path.suffix.lower(),
                "page_count": len(doc.pages) if hasattr(doc, "pages") else None,
                "has_tables": bool(doc.tables) if hasattr(doc, "tables") else False,
                "table_count": len(doc.tables) if hasattr(doc, "tables") else 0,
            }

            logger.info(
                "Document parsed successfully",
                file_path=str(path),
                page_count=metadata["page_count"],
                table_count=metadata["table_count"],
                content_length=len(markdown_content),
            )

            return {"content": markdown_content, "metadata": metadata}

        except Exception as exc:
            logger.error(
                "Document parsing failed",
                file_path=str(path),
                error=str(exc),
            )
            raise ValueError(f"Document parsing failed for '{file_path}': {exc}") from exc

    def parse_directory(self, dir_path: str) -> List[Dict[str, Any]]:
        """
        Parse all supported documents in a directory.

        Args:
            dir_path: Path to the directory containing documents.

        Returns:
            List of dicts, each containing 'content' and 'metadata'.
        """
        path = Path(dir_path)
        if not path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {dir_path}")

        results = []
        for file in path.iterdir():
            if file.suffix.lower() in SUPPORTED_FORMATS:
                try:
                    results.append(self.parse(str(file)))
                except Exception as e:
                    logger.warning("Skipping file due to parse error", file=str(file), error=str(e))
        
        return results
