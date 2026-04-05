from typing import Dict, Any
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.input_format import InputFormat
from langfuse.decorators import observe
import structlog

logger = structlog.get_logger()

class DoclingParser:
    """
    A parser for converting documents to Markdown with metadata using Docling.
    Optimized for 16GB systems with focus on table fidelity and observability.
    Supports both PDF and DOCX input formats.
    """

    def __init__(self):
        """Initialize the parser with optimized PDF pipeline options."""
        self.converter = DocumentConverter()

        # Configure for 16GB system with table structure support
        self.pdf_options = PdfPipelineOptions(
            pdf_backend="pypdfium2",
            num_threads=1,
            do_table_structure=True
        )

        # Support both PDF and DOCX formats
        self.allowed_formats = [InputFormat.PDF, InputFormat.DOCX]

    @observe
    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a document file and return its content as Markdown with metadata.

        Args:
            file_path: Path to the document file to parse

        Returns:
            Dictionary containing:
            - 'content': Markdown representation of the document
            - 'metadata': Document metadata

        Raises:
            ValueError: If parsing fails
        """
        try:
            logger.info("Starting document parsing", file_path=file_path)

            # Convert document to Markdown
            result = self.converter.convert(
                file_path=file_path,
                output_format="markdown",
                pdf_options=self.pdf_options
            )

            metadata = {
                "file_path": file_path,
                "page_count": getattr(result, 'page_count', None),
                "has_tables": getattr(result, 'has_tables', False),
                "table_structure": getattr(result, 'table_structure', None)
            }

            logger.info("Document parsed successfully", file_path=file_path)
            return {
                "content": result.content,
                "metadata": metadata
            }

        except Exception as e:
            logger.error("Failed to parse document", file_path=file_path, error=str(e))
            raise ValueError(f"Document parsing failed: {str(e)}") from e
