"""
index_manager.py
----------------
Orchestrates the document ingestion pipeline.

Coordinates the following steps:
1. Parse document (DoclingParser)
2. Chunk text and extract metadata (DocumentPreprocessor)
3. Generate vectors via Mistral API (EmbeddingGenerator)
4. Upsert points to vector DB (QdrantClientWrapper)
"""

import structlog
from typing import List, Dict, Any, Optional

from src.parsers.docling_parser import DoclingParser
from src.parsers.document_preprocessor import DocumentPreprocessor
from src.vectordb.embedding_generator import EmbeddingGenerator
from src.vectordb.qdrant_client import QdrantClientWrapper

logger = structlog.get_logger(__name__)

class IndexManager:
    """
    Manages the end-to-end flow of ingesting documents into Qdrant.
    """

    def __init__(
        self,
        parser: Optional[DoclingParser] = None,
        preprocessor: Optional[DocumentPreprocessor] = None,
        embedder: Optional[EmbeddingGenerator] = None,
        qdrant_client: Optional[QdrantClientWrapper] = None,
    ):
        """
        Initialize the IndexManager.
        Dependency injection is supported for testing or custom configurations.
        """
        self.parser = parser or DoclingParser()
        self.preprocessor = preprocessor or DocumentPreprocessor()
        self.embedder = embedder or EmbeddingGenerator()
        self.qdrant_client = qdrant_client or QdrantClientWrapper()
        
        # Ensure the collection exists upon manager creation
        self.qdrant_client.create_collection_if_not_exists()

    def index_document(self, file_path: str, document_source: str) -> int:
        """
        End-to-end document indexing operation.

        Args:
            file_path: Absolute or relative path to the document file.
            document_source: Semantic label for Qdrant filtering (e.g., 'eu_ai_act', 'sme_doc').

        Returns:
            The number of chunks/points successfully indexed.

        Raises:
            ValueError: If parsing, chunking, or embedding operations fail early checks.
            EmbeddingError: If API limits or connection errors occur during embedding.
            RuntimeError: If vector DB operations fail.
        """
        logger.info("Initiating document indexing", file_path=file_path, document_source=document_source)

        # Step 1: Parse
        parse_result = self.parser.parse(file_path=file_path)
        content = parse_result.get("content", "")
        metadata = parse_result.get("metadata", {})
        
        if not content:
            logger.warning("Document yielded empty content", file_path=file_path)
            return 0

        # Step 2: Preprocess / Chunk
        chunks = self.preprocessor.chunk(
            content=content,
            metadata=metadata,
            document_source=document_source
        )

        if not chunks:
            logger.warning("No chunks produced from document content", file_path=file_path)
            return 0

        # Extract text components for embedder
        texts = [chunk["text"] for chunk in chunks]

        # Step 3: Embed
        vectors = self.embedder.generate(texts=texts)

        # Step 4: Upsert to Vector DB
        self.qdrant_client.upsert(chunks=chunks, vectors=vectors)

        logger.info(
            "Successfully indexed document",
            file_path=file_path,
            chunks_count=len(chunks)
        )

        return len(chunks)
