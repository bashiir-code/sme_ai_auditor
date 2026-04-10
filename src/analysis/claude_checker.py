"""
claude_checker.py
-----------------
Data Act compliance engine using Claude (via OpenRouter).
"""

import os
import json
import requests
from typing import Dict, Any, Optional, List
import structlog

from langfuse import observe
from haystack import Document
from src.retrieval.haystack_pipeline_builder import DocumentRetrievalPipeline

logger = structlog.get_logger(__name__)

class ClaudeDataChecker:
    """
    Evaluates SME system descriptions specifically against the EU Data Act using Claude.
    """

    def __init__(
        self, 
        api_key: str | None = None, 
        model: str | None = None,
        pipeline: Optional[DocumentRetrievalPipeline] = None
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model or os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.pipeline = pipeline or DocumentRetrievalPipeline()
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set.")

        logger.info("ClaudeDataChecker initialized", model=self.model)

    @observe(name="claude_data_act_evaluation")
    def evaluate_data_obligations(self, system_description: str) -> Dict[str, Any]:
        doc_results = self.pipeline.run_query(
            query=system_description,
            filters={"act_type": "DATA_ACT"},
            top_k=7
        )

        context_text = self._format_context(doc_results)

        system_prompt = """
You are an expert EU Data Act compliance auditor.
Analyze the SME's system description against the provided Data Act excerpts.
Output strictly valid JSON:
{
  "is_data_provider": true/false,
  "data_sharing_compliant": true/false,
  "cloud_switching_compliant": true/false,
  "summary": "Brief explanation of findings",
  "missing_requirements": ["list of what they need to fix"]
}
"""

        user_prompt = f"Data Act Context:\n{context_text}\n\nSME System:\n{system_description}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"}
        }

        try:
            response = requests.post(self.url, headers=headers, json=data)
            response.raise_for_status()
            raw_json = response.json()['choices'][0]['message']['content']
            return json.loads(raw_json)
        except Exception as e:
            logger.error("Claude Data Act API call failed", error=str(e))
            raise RuntimeError(f"Claude API failure: {e}")

    def _format_context(self, docs: List[Document]) -> str:
        parts = []
        for i, doc in enumerate(docs, start=1):
            parts.append(f"[Chunk {i}]: {doc.content}")
        return "\n\n".join(parts)
