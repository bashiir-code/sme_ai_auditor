"""
data_act_checker.py
-------------------
Core Data Act compliance engine.

Uses Mistral Large to evaluate data sharing, interoperability, and cloud switching
requirements for SME AI/IoT systems using strictly isolated Data Act context.
"""

import os
import json
from typing import Dict, Any, Optional, List
import structlog

from langfuse import observe
from mistralai.client.sdk import Mistral
from haystack import Document

from src.retrieval.haystack_pipeline_builder import DocumentRetrievalPipeline
from src.analysis.ai_act_classifier import LLMReasoningError


logger = structlog.get_logger(__name__)


class DataActChecker:
    """
    Evaluates SME system descriptions specifically against the EU Data Act.
    """

    def __init__(
        self, 
        api_key: str | None = None, 
        model: str = "mistral-large-latest",
        pipeline: Optional[DocumentRetrievalPipeline] = None
    ):
        """
        Initialize the Data Act Checker.
        """
        resolved_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not resolved_key:
            raise ValueError(
                "MISTRAL_API_KEY is not set. "
                "Export it as an environment variable or pass it explicitly."
            )

        self._client = Mistral(api_key=resolved_key)
        # We use Mistral Large specifically for reasoning through interoperability/switching
        self.model = model
        self.temperature = 0.1
        
        # Injected or instantiated Retrieval Pipeline to isolate context search
        self.pipeline = pipeline or DocumentRetrievalPipeline()
        
        logger.info("DataActChecker initialized", model=self.model)

    @observe(name="data_act_classification")
    def evaluate_data_obligations(self, system_description: str) -> Dict[str, Any]:
        """
        Evaluate Data obligations by specifically seeking Data Act chunks.

        Retrieves isolated context tagged with act_type: "DATA_ACT", applies
        high-level LLM reasoning, and returns a structured JSON metrics dict.

        Args:
            system_description: SME's description of their data/IoT product.

        Returns:
            A parsed JSON dictionary outlining Data Act statuses.

        Raises:
            LLMReasoningError: If LLM output fails.
        """
        if not system_description or not system_description.strip():
            raise ValueError("system_description cannot be empty.")

        logger.info("Retrieving specific DATA_ACT context for evaluation")

        # 1. Context Isolation (strict filter applied)
        doc_results = self.pipeline.run_query(
            query=system_description,
            filters={"act_type": "DATA_ACT"},
            top_k=7
        )

        context_text = self._format_context(doc_results)

        # 2. Construct System Prompt checking Data Act specific metrics
        system_prompt = """
You are an expert EU Data Act compliance auditor.
Your goal is to evaluate the SME's data/IoT architecture against the provided Data Act excerpts.

CRITICAL INSTRUCTIONS:
1. Ground all reasoning ONLY in the provided Document excerpts.
2. If the user's system does not generate data, default to compliant.
3. You MUST output strictly valid JSON matching this structure:
{
  "is_data_provider": true/false,
  "data_sharing_compliant": true/false,
  "cloud_switching_compliant": true/false,
  "summary": "Brief explanation of findings",
  "missing_requirements": ["list of what they need to fix"]
}
"""

        user_prompt = f"""
Provided Data Act Context:
{context_text}

---
SME System Description:
{system_description}
"""

        # 3. Ask Mistral (Structured JSON Output)
        logger.debug("Prompting LLM for Data Act", model=self.model)
        try:
            response = self._client.chat.complete(
                model=self.model,
                temperature=self.temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
        except Exception as e:
            logger.error("Mistral API call failed during Data Act classification", error=str(e))
            raise LLMReasoningError(f"Mistral API failure: {e}") from e

        # 4. Extract standard dict
        raw_json_str = response.choices[0].message.content
        logger.debug("Received LLM response for Data Act", raw_payload_length=len(raw_json_str))

        try:
            payload = json.loads(raw_json_str)
        except json.JSONDecodeError as e:
            logger.error("Data Act JSON parse failed", error=str(e), raw_json=raw_json_str)
            raise LLMReasoningError(f"Invalid JSON from Mistral: {e}") from e

        # Sanity check standard keys
        required_keys = {"is_data_provider", "data_sharing_compliant", "cloud_switching_compliant", "summary"}
        if not required_keys.issubset(payload.keys()):
            raise LLMReasoningError(f"Missing required Data Act keys. Got: {list(payload.keys())}")

        logger.info(
            "Data Act classification complete", 
            is_data_provider=payload.get("is_data_provider")
        )
        return payload

    def _format_context(self, docs: List[Document]) -> str:
        """Combine Document text and metadata for the prompt."""
        if not docs:
            return "No isolated DATA_ACT context found in the database."

        parts = []
        for i, doc in enumerate(docs, start=1):
            article = doc.meta.get("article_number", "Unknown Article")
            text = doc.content.strip() if getattr(doc, 'content', None) else ""
            parts.append(f"[Document {i}] ({article}):\n\"{text}\"")
        return "\n\n".join(parts)
