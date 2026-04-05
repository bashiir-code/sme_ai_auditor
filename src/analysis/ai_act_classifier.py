from typing import List, Dict, Any
from mistralai.client import Mistral
from mistralai.client.models import ChatCompletionRequestMessage
from langfuse import observe
import structlog
from src.analysis.schemas import AIActAuditReport, ComplianceFinding, ArticleReference
import json

logger = structlog.get_logger()

class AIActClassifier:
    """
    AI Act compliance classifier that integrates with Mistral AI API.
    Implements the 'Red Line' check for prohibited systems and maps findings to harmonized standards.
    """

    def __init__(self, api_key: str, model: str = "mistral-large-latest"):
        """
        Initialize the classifier with Mistral AI client.

        Args:
            api_key: Mistral AI API key
            model: Mistral model to use (default: mistral-large-latest)
        """
        self.client = Mistral(api_key=api_key)
        self.model = model
        self.red_line_articles = ["Article 5"]  # Prohibited AI practices

    @observe
    def classify_system(self, system_description: str, evidence_text: str) -> AIActAuditReport:
        """
        Classify an AI system against EU AI Act requirements.

        Args:
            system_description: Description of the AI system
            evidence_text: Supporting documentation/text for analysis

        Returns:
            AIActAuditReport with validated compliance findings

        Raises:
            ValueError: If classification fails due to API errors or invalid responses
        """
        try:
            logger.info("Starting AI Act classification",
                       system=system_description[:50] + "...")

            # Step 1: Red Line Check (Article 5 Prohibitions)
            red_line_findings = self._check_prohibited_practices(system_description, evidence_text)
            if red_line_findings:
                logger.warning("Prohibited practice detected", findings=red_line_findings)
                return AIActAuditReport(
                    system_description=system_description,
                    compliance_status="Prohibited",
                    findings=red_line_findings,
                    relevant_articles=[ArticleReference(article="Article 5", description="Prohibited AI practices")],
                    harmonized_standards=[]
                )

            # Step 2: Full compliance analysis
            compliance_findings = self._analyze_compliance(system_description, evidence_text)

            # Step 3: Map to harmonized standards
            harmonized_standards = self._map_to_standards(compliance_findings)

            # Determine overall status
            status = self._determine_compliance_status(compliance_findings)

            logger.info("Classification completed",
                       status=status,
                       findings_count=len(compliance_findings))

            return AIActAuditReport(
                system_description=system_description,
                compliance_status=status,
                findings=compliance_findings,
                relevant_articles=self._extract_relevant_articles(compliance_findings),
                harmonized_standards=harmonized_standards
            )

        except Exception as e:
            logger.error("Classification failed",
                        error=str(e),
                        system=system_description[:50])
            raise ValueError(f"AI Act classification failed: {str(e)}") from e

    def _check_prohibited_practices(self, system_description: str, evidence_text: str) -> List[ComplianceFinding]:
        """Check for Article 5 prohibited practices (Red Line check)."""
        prompt = f"""
        You are an EU AI Act compliance expert. Analyze the following AI system for PROHIBITED practices under Article 5:

        System: {system_description}

        Evidence: {evidence_text}

        Instructions:
        1. Check ONLY for Article 5 prohibitions (no other analysis)
        2. If ANY prohibited practice is found, return findings immediately
        3. For each finding, provide:
           - The specific prohibited practice
           - Exact evidence from the text
           - Risk level (always 'Prohibited' for Article 5)
        4. Return empty list if no prohibitions found

        Respond ONLY with valid JSON matching this schema:
        {{
            "findings": [
                {{
                    "requirement": "string",
                    "compliance_status": "string",
                    "evidence": "string",
                    "risk_category": "string",
                    "article_reference": "string"
                }}
            ]
        }}
        """

        response = self._call_mistral_api(prompt)
        findings_data = json.loads(response)

        return [
            ComplianceFinding(
                requirement=f["requirement"],
                compliance_status=f["compliance_status"],
                evidence=f["evidence"],
                risk_category=f["risk_category"],
                article_reference=f["article_reference"]
            )
            for f in findings_data.get("findings", [])
        ]

    def _analyze_compliance(self, system_description: str, evidence_text: str) -> List[ComplianceFinding]:
        """Perform full compliance analysis against AI Act requirements."""
        prompt = f"""
        You are an EU AI Act compliance expert. Perform comprehensive compliance analysis:

        System: {system_description}

        Evidence: {evidence_text}

        Instructions:
        1. Analyze against ALL applicable AI Act articles (except Article 5 already checked)
        2. For each finding, provide:
           - Specific requirement
           - Compliance status (Compliant/Non-Compliant/Partial)
           - Exact evidence from text
           - Risk category (Low/Medium/High)
           - Relevant article reference
        3. Be specific about which articles apply

        Respond ONLY with valid JSON matching this schema:
        {{
            "findings": [
                {{
                    "requirement": "string",
                    "compliance_status": "string",
                    "evidence": "string",
                    "risk_category": "string",
                    "article_reference": "string"
                }}
            ]
        }}
        """

        response = self._call_mistral_api(prompt)
        findings_data = json.loads(response)

        return [
            ComplianceFinding(
                requirement=f["requirement"],
                compliance_status=f["compliance_status"],
                evidence=f["evidence"],
                risk_category=f["risk_category"],
                article_reference=f["article_reference"]
            )
            for f in findings_data.get("findings", [])
        ]

    def _map_to_standards(self, findings: List[ComplianceFinding]) -> List[str]:
        """Map compliance findings to CEN/CENELEC harmonized standards."""
        standards_map = {
            "Article 6": ["EN IEC 62304", "EN ISO 13485"],
            "Article 8": ["EN ISO 9241-210", "EN ISO 14971"],
            "Article 9": ["EN ISO 12100", "EN 60204-1"],
            "Article 10": ["EN ISO 13849", "EN 62061"],
            "Article 13": ["EN ISO 25010", "EN ISO 9126"]
        }

        relevant_standards = set()
        for finding in findings:
            for article, standards in standards_map.items():
                if article in finding.article_reference:
                    relevant_standards.update(standards)

        return sorted(list(relevant_standards))

    def _determine_compliance_status(self, findings: List[ComplianceFinding]) -> str:
        """Determine overall compliance status based on findings."""
        if any(f.compliance_status == "Non-Compliant" for f in findings):
            return "Non-Compliant"
        if any(f.compliance_status == "Partial" for f in findings):
            return "Conditional"
        return "Compliant"

    def _extract_relevant_articles(self, findings: List[ComplianceFinding]) -> List[ArticleReference]:
        """Extract unique article references from findings."""
        articles = set()
        for finding in findings:
            articles.add(finding.article_reference)

        return [
            ArticleReference(
                article=article,
                description=f"AI Act {article} requirements"
            )
            for article in sorted(articles)
        ]

    def _call_mistral_api(self, prompt: str) -> str:
        """Helper method to call Mistral API with error handling."""
        try:
            messages = [ChatCompletionRequestMessage(role="user", content=prompt)]
            response = self.client.chat(
                model=self.model,
                messages=messages,
                temperature=0.1,  # Low temperature for deterministic legal analysis
                max_tokens=2000
            )

            if not response.choices or not response.choices[0].message.content:
                raise ValueError("Empty response from Mistral API")

            return response.choices[0].message.content

        except Exception as e:
            logger.error("Mistral API call failed", error=str(e))
            raise ValueError(f"API call failed: {str(e)}") from e
