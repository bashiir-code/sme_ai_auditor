"""
claude_classifier.py
--------------------
Compliance logic engine using Claude (via OpenRouter).
"""

import os
import json
import requests
from typing import List, Any
import structlog

from langfuse import observe
from haystack import Document
from src.analysis.schemas import AIActAuditReport

logger = structlog.get_logger(__name__)

class ClaudeClassifier:
    """
    Performs legal analysis using Claude 3.5 Sonnet via OpenRouter.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model or os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set.")

        logger.info("ClaudeClassifier initialized", model=self.model)

    @observe(name="claude_ai_act_classification")
    def analyze_system(self, system_description: str, context_docs: List[Document]) -> AIActAuditReport:
        context_text = self._format_context(context_docs[:10])
        schema_json = json.dumps(AIActAuditReport.model_json_schema(), indent=2)

        system_prompt = f"""
You are an expert EU AI Act compliance auditor. 
Analyze the SME's AI system against the provided legal excerpts.
Output strictly JSON matching this schema:
{schema_json}
"""

        user_prompt = f"Legal Context:\n{context_text}\n\nSME System:\n{system_description}"

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
            return AIActAuditReport.model_validate_json(raw_json)
        except Exception as e:
            logger.error("Claude API call failed", error=str(e))
            raise RuntimeError(f"Claude API failure: {e}")

    def _format_context(self, docs: List[Document]) -> str:
        parts = []
        for i, doc in enumerate(docs, start=1):
            parts.append(f"[Chunk {i}]: {doc.content}")
        return "\n\n".join(parts)
