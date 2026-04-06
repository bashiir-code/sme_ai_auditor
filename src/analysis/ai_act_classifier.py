"""
ai_act_classifier.py
--------------------
Core compliance logic engine using the Mistral AI API.

Analyzes an SME's AI system description against retrieved legal chunks (EU AI Act),
categorises risk level, and detects Article 5 prohibited practices.
Returns a strictly validated AIActAuditReport Pydantic model.
"""

import os
import json
from typing import List, Any
import structlog

from langfuse import observe
from mistralai.client.sdk import Mistral
from haystack import Document

from src.analysis.schemas import AIActAuditReport, RiskCategory

logger = structlog.get_logger(__name__)


class LLMReasoningError(RuntimeError):
    """Raised when the LLM fails to return valid compliance JSON."""


class AIActClassifier:
    """
    Performs deterministic legal analysis using Mistral Large.
    """

    def __init__(self, api_key: str | None = None, model: str = "mistral-large-latest"):
        """
        Initialize the AI Act Classifier.
        """
        resolved_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not resolved_key:
            raise ValueError(
                "MISTRAL_API_KEY is not set. "
                "Export it as an environment variable or pass it explicitly."
            )

        self._client = Mistral(api_key=resolved_key)
        self.model = model
        # Temperature 0.1 for high determinism in legal reasoning
        self.temperature = 0.1
        
        logger.info("AIActClassifier initialized", model=self.model, temperature=self.temperature)

    @observe(name="ai_act_classification", capture_input=False)
    def analyze_system(self, system_description: str, context_docs: List[Document]) -> AIActAuditReport:
        """
        Analyze an AI system's compliance against the EU AI Act context.
        Ensures 16GB RAM overhead by capping context chunks to top-10 most relevant.
        """
        # Context Guard: Ensure the Brain isn't overloaded with low-rank noise
        context_docs = context_docs[:10]
        
        if not system_description or not system_description.strip():
            raise ValueError("system_description cannot be empty.")

        logger.info("Starting AI Act classification", num_context_docs=len(context_docs))

        # 1. Format Context
        context_text = self._format_context(context_docs)

        # 2. Extract JSON Schema for the Prompt
        # This tells the LLM EXACTLY what structure we need.
        schema_json = json.dumps(AIActAuditReport.model_json_schema(), indent=2)

        # 3. Construct System Prompt with specific Senior-level Instructions
        system_prompt = f"""
You are an expert EU AI Act compliance auditor and legal advisor.
Your task is to analyze the SME's AI system description against the provided legal excerpts.

CRITICAL INSTRUCTION - THE "ARTICLE 5" RED-LINE CHECK:
First, explicitly evaluate if the system violates any Prohibited Practices defined in Article 5 
(e.g., social scoring, dark patterns, subliminal techniques, unauthorized biometric ID).
If an Article 5 violation is detected, IMMEDIATELY flag the `risk_level` as "Prohibited" 
and focus your `summary` on exactly why it violates Article 5. You may short-circuit 
remaining analysis if it is strictly prohibited.

RULES:
1. ONLY utilize the provided context documents to ground your claims. Do not hallucinate legal articles.
2. Ensure you cite specific Article or Section references where possible matching the context metadata.
3. You MUST output your response strictly as a JSON object matching the schema below.

JSON SCHEMA:
{schema_json}
"""

        user_prompt = f"""
Provided Legal Context excerpts:
{context_text}

---
SME AI System Description:
{system_description}
"""

        # 4. Invoke LLM with Structured JSON Format
        logger.debug("Prompting Mistral LLM", model=self.model)
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
            logger.error("Mistral API call failed during classification", error=str(e))
            raise LLMReasoningError(f"Mistral API failure: {e}") from e

        # 5. Extract and Validate
        raw_json_str = response.choices[0].message.content
        logger.debug("Received LLM response", raw_payload_length=len(raw_json_str))

        try:
            report = AIActAuditReport.model_validate_json(raw_json_str)
        except Exception as e:
            logger.error(
                "Failed to parse or validate LLM JSON against schema",
                error=str(e),
                raw_json=raw_json_str
            )
            raise LLMReasoningError(f"Mismatched schema from LLM: {e}") from e

        logger.info(
            "AI Act classification complete", 
            risk_category=report.risk_level.value
        )
        return report

    def _format_context(self, docs: List[Document]) -> str:
        """Combine Document text and metadata into a prompt-friendly string."""
        if not docs:
            return "No relevant context found."

        parts = []
        for i, doc in enumerate(docs, start=1):
            article = doc.meta.get("article_number", "Unknown Article")
            section = doc.meta.get("parent_section", "Unknown Section")
            text = doc.content.strip() if getattr(doc, 'content', None) else ""
            
            parts.append(
                f"[Document {i}] (Metadata -> {section} | {article}):\n\"{text}\""
            )
        
        return "\n\n".join(parts)
