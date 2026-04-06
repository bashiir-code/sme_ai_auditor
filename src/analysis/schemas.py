from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class RiskCategory(str, Enum):
    PROHIBITED = "Prohibited"
    HIGH_RISK = "High-Risk"
    LIMITED = "Limited Risk"
    MINIMAL = "Minimal Risk"

class ArticleReference(BaseModel):
    article: str = Field(..., min_length=1, description="The specific Article number (e.g., 'Article 5')")
    title: str = Field(..., min_length=1, description="The title of the legal provision")
    description: str = Field(..., min_length=1, description="Short summary of the requirement")

class ComplianceFinding(BaseModel):
    model_config = ConfigDict(strict=True)

    criterion: str = Field(..., min_length=1, description="The specific rule or standard being checked")
    is_compliant: bool = Field(..., description="Binary compliance status")
    evidence: str = Field(..., min_length=1, description="Textual evidence from the SME documentation")
    reasoning: str = Field(..., min_length=1, description="Legal reasoning supporting the finding")
    gap_analysis: Optional[str] = Field(None, description="Detailed gap if non-compliant")

class AIActAuditReport(BaseModel):
    """
    Final structured output for the AI Act classification process.
    Supports auditability by proving how the AI reached legal conclusions.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "system_name": "SME-Chat-Bot-v1",
                "risk_level": "Limited Risk",
                "primary_articles": [{"article": "Article 52", "title": "Transparency obligations", "description": "Transparency for AI systems"}],
                "findings": [
                    {
                        "criterion": "User awareness of AI interaction",
                        "is_compliant": True,
                        "evidence": "Section 2.1: 'Users are notified upon login...'",
                        "reasoning": "The documentation explicitly states users are informed they are interacting with an AI.",
                    }
                ],
                "summary": "The system meets the basic transparency requirements for general-purpose AI."
            }
        }
    )

    system_name: str = Field(..., min_length=1)
    risk_level: RiskCategory
    primary_articles: List[ArticleReference] = Field(..., min_length=1)
    findings: List[ComplianceFinding] = Field(..., min_length=1)
    summary: str = Field(..., min_length=1, description="High-level executive summary for the SME")


class HarmonizedStandardRequirement(BaseModel):
    """
    Standardized technical requirement drawn from 2026 CEN/CENELEC harmonized standards.
    Provides the SME with 'presumption of conformity'.
    """
    model_config = ConfigDict(strict=True)

    standard_id: str = Field(..., description="CEN/CENELEC Standard Reference (e.g., 'EN ISO/IEC 42001:2026')")
    title: str = Field(..., description="Title of the standard")
    description: str = Field(..., description="Details on what the SME must technically implement")
    is_mandatory: bool = Field(..., description="Whether this standard is mandatory for the given risk tier")
    verification_method: str = Field(..., description="How the auditor will verify implementation")

class RemediationAction(BaseModel):
    """
    Actionable fix identified by the Gap Detector.
    """
    model_config = ConfigDict(strict=True)

    priority: str = Field(..., description="'High', 'Medium', or 'Low'")
    missing_requirement: str = Field(..., description="What needs to be implemented")
    reference_standard: str = Field(..., description="The standard ID or legal baseline")
    violation_context: str = Field(..., description="Why the system was flagged (link to SME input)")
    trace_id_reference: Optional[str] = Field(None, description="Langfuse internal trace ID for sovereignty")

class RemediationPlan(BaseModel):
    """
    The final list of gaps prioritizing what the SME must fix.
    """
    model_config = ConfigDict(strict=True)
    
    actions: List[RemediationAction] = []
    is_deployable: bool = Field(..., description="False if PROHIBITED or High Priority legal blockers exist")

