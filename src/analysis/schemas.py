from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class RiskCategory(str, Enum):
    PROHIBITED = "Prohibited"
    HIGH_RISK = "High-Risk"
    LIMITED = "Limited Risk"
    MINIMAL = "Minimal Risk"

class ArticleReference(BaseModel):
    article: str = Field(..., description="The specific Article number (e.g., 'Article 5')")
    title: str = Field(..., description="The title of the legal provision")
    description: str = Field(..., description="Short summary of the requirement")

class ComplianceFinding(BaseModel):
    criterion: str = Field(..., description="The specific rule or standard being checked")
    is_compliant: bool = Field(..., description="Binary compliance status")
    evidence: str = Field(..., description="Textual evidence from the SME documentation")
    reasoning: str = Field(..., description="Legal reasoning supporting the finding")
    gap_analysis: Optional[str] = Field(None, description="Detailed gap if non-compliant")

class AIActAuditReport(BaseModel):
    """
    Final structured output for the AI Act classification process.
    Supports auditability by proving how the AI reached legal conclusions.
    """
    system_name: str
    risk_level: RiskCategory
    primary_articles: List[ArticleReference]
    findings: List[ComplianceFinding]
    summary: str = Field(..., description="High-level executive summary for the SME")
    
    class Config:
        # Senior Tip: Enables JSON schema generation for Haystack 2.x output parsers
        json_schema_extra = {
            "example": {
                "system_name": "SME-Chat-Bot-v1",
                "risk_level": "Limited Risk",
                "primary_articles": [{"article": "Article 52", "title": "Transparency obligations"}],
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