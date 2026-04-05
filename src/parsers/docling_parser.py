from typing import Dict, Any
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions # ✅ Senior/2026 Standard
from docling.document_converter.table_structure_model import TableStructureModel
from langfuse.decorators import observe
import structlog

logger = structlog.get_logger()

class DoclingParser:
    """
    A parser for converting documents to Markdown with metadata using Docling.
    Optimized for 16GB systems with focus on table fidelity and observability.
    """

    def __init__(self):
        """Initialize the parser with optimized PDF pipeline options."""
        self.converter = DocumentConverter()

        # Configure for 16GB system
        self.pdf_options = PdfPipelineOptions(
            provider="pypdfium2",
            num_threads=1,
            enable_table_structure_model=True
        )

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

            # Extract table structure information if available
            table_structure = None
            if hasattr(result, 'table_structure'):
                table_structure = TableStructureModel(result.table_structure)

            metadata = {
                "file_path": file_path,
                "page_count": getattr(result, 'page_count', None),
                "has_tables": table_structure is not None,
                "table_structure": table_structure
            }

            logger.info("Document parsed successfully", file_path=file_path)
            return {
                "content": result.content,
                "metadata": metadata
            }

        except Exception as e:
            logger.error("Failed to parse document", file_path=file_path, error=str(e))
            raise ValueError(f"Document parsing failed: {str(e)}") from e
