"""
haystack_pipeline_builder.py
----------------------------
Builder for the search orchestration pipeline.

Connects the Mistral text embedding component (QueryProcessor) with the
Qdrant retrieval component (QdrantRetriever) in a Haystack 2.x Pipeline.
"""

from typing import Dict, Any, List, Optional
import structlog
from langfuse import observe
from haystack import Pipeline, Document

from src.retrieval.query_processor import QueryProcessor
from src.retrieval.retrievers import QdrantRetriever
from src.vectordb.qdrant_client import QdrantClientWrapper


logger = structlog.get_logger(__name__)


class DocumentRetrievalPipeline:
    """
    Orchestrates a Haystack 2.x Directed Acyclic Graph (DAG) for Document Retrieval.

    Wiring:
        QueryProcessor.query_vector -> QdrantRetriever.query_vector
    """

    def __init__(
        self,
        query_processor: Optional[QueryProcessor] = None,
        retriever: Optional[QdrantRetriever] = None,
    ):
        """
        Initialize the retrieval pipeline components.
        Provides dependency injection for testing.
        """
        self.query_processor = query_processor or QueryProcessor()
        self.retriever = retriever or QdrantRetriever()
        
        self.pipeline = self._build_pipeline()
        logger.info("DocumentRetrievalPipeline initialized")

    def _build_pipeline(self) -> Pipeline:
        """Construct the Haystack 2.x pipeline DAG."""
        pipeline = Pipeline()
        
        # Add components to the pipeline
        pipeline.add_component("query_processor", self.query_processor)
        pipeline.add_component("qdrant_retriever", self.retriever)
        
        # Connect the output of the embedder to the input of the retriever
        pipeline.connect("query_processor.query_vector", "qdrant_retriever.query_vector")
        
        # The top_k and filters from QueryProcessor are passed through, so we connect those as well.
        pipeline.connect("query_processor.top_k", "qdrant_retriever.top_k")
        pipeline.connect("query_processor.filters", "qdrant_retriever.filters")
        
        logger.debug("Haystack retrieval pipeline wired successfully")
        return pipeline

    @observe(name="retrieval_pipeline_run", capture_input=False)
    def run_query(self, query: str, filters: Optional[Dict[str, Any]] = None, top_k: int = 5) -> List[Document]:
        """
        Executes an end-to-end vector search against the compliance database.

        Args:
            query: Natural language query string.
            filters: Optional dictionary for strict metadata filtering (e.g. {"document_source": "eu_ai_act"}).
            top_k: Maximum number of relevant chunks to return.

        Returns:
            A validated list of Haystack Document objects containing the relevant legal text.
        """
        if not query or not query.strip():
            logger.warning("Empty query provided to DocumentRetrievalPipeline")
            return []

        logger.info(
            "Running retrieval pipeline",
            query=query,
            filters=filters,
            top_k=top_k
        )

        try:
            # Haystack 2.x expects a dictionary where keys are component names 
            # and values are specific input data for that component.
            results = self.pipeline.run(
                {
                    "query_processor": {
                        "query": query,
                        "top_k": top_k,
                        "filters": filters
                    }
                }
            )
        except Exception as e:
            logger.error("Retrieval pipeline execution failed", error=str(e))
            raise RuntimeError(f"Failed to execute retrieval pipeline: {e}") from e

        # Extract the documents from the final component in the DAG
        documents = results.get("qdrant_retriever", {}).get("documents", [])
        
        logger.info(
            "Retrieval pipeline complete",
            documents_returned=len(documents)
        )
        
        return documents
