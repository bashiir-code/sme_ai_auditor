import sys
import os
import pytest
from pydantic import ValidationError

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analysis.schemas import RiskCategory, ArticleReference, ComplianceFinding, AIActAuditReport

def test_risk_category_enum():
    """Test RiskCategory enum values and invalid values"""
    assert RiskCategory.PROHIBITED.value == "Prohibited"
    assert RiskCategory.HIGH_RISK.value == "High-Risk"
    assert RiskCategory.LIMITED.value == "Limited Risk"
    assert RiskCategory.MINIMAL.value == "Minimal Risk"

    # Test invalid enum value
    with pytest.raises(ValueError):
        RiskCategory("InvalidRisk")

def test_article_reference_model():
    """Test ArticleReference model creation, validation, and edge cases"""
    # Valid case
    article = ArticleReference(
        article="Article 5",
        title="Prohibited AI practices",
        description="AI systems that deploy subliminal techniques"
    )
    assert article.article == "Article 5"
    assert article.title == "Prohibited AI practices"
    assert article.description == "AI systems that deploy subliminal techniques"

    # Test empty strings (should fail)
    with pytest.raises(ValidationError):
        ArticleReference(article="", title="test", description="test")

    with pytest.raises(ValidationError):
        ArticleReference(article="Article 1", title="", description="test")

    # Test type validation
    with pytest.raises(ValidationError):
        ArticleReference(article=123, title="test", description="test")

def test_compliance_finding_model():
    """Test ComplianceFinding model with all fields and edge cases"""
    # Valid case with all fields
    finding = ComplianceFinding(
        criterion="User awareness of AI interaction",
        is_compliant=True,
        evidence="Section 2.1: 'Users are notified upon login...'",
        reasoning="The documentation explicitly states users are informed they are interacting with an AI."
    )
    assert finding.criterion == "User awareness of AI interaction"
    assert finding.is_compliant is True
    assert finding.evidence == "Section 2.1: 'Users are notified upon login...'"
    assert finding.reasoning == "The documentation explicitly states users are informed they are interacting with an AI."
    assert finding.gap_analysis is None

    # Test with gap analysis
    non_compliant_finding = ComplianceFinding(
        criterion="Data quality requirements",
        is_compliant=False,
        evidence="No documentation found about data cleaning processes",
        reasoning="Article 10 requires documented data governance measures",
        gap_analysis="Missing data quality documentation and processes"
    )
    assert non_compliant_finding.gap_analysis == "Missing data quality documentation and processes"

    # Test empty strings (should fail)
    with pytest.raises(ValidationError):
        ComplianceFinding(criterion="", is_compliant=True, evidence="test", reasoning="test")

    # Test type validation
    with pytest.raises(ValidationError):
        ComplianceFinding(criterion="test", is_compliant="yes", evidence="test", reasoning="test")

def test_ai_act_audit_report_model():
    """Test AIActAuditReport model with complete structure and edge cases"""
    article_ref = ArticleReference(
        article="Article 52",
        title="Transparency obligations",
        description="Requirements for AI system transparency"
    )

    finding = ComplianceFinding(
        criterion="User awareness of AI interaction",
        is_compliant=True,
        evidence="Section 2.1: 'Users are notified upon login...'",
        reasoning="The documentation explicitly states users are informed they are interacting with an AI."
    )

    # Valid case
    report = AIActAuditReport(
        system_name="SME-Chat-Bot-v1",
        risk_level=RiskCategory.LIMITED,
        primary_articles=[article_ref],
        findings=[finding],
        summary="The system meets the basic transparency requirements for general-purpose AI."
    )

    assert report.system_name == "SME-Chat-Bot-v1"
    assert report.risk_level == RiskCategory.LIMITED
    assert len(report.primary_articles) == 1
    assert len(report.findings) == 1
    assert report.summary == "The system meets the basic transparency requirements for general-purpose AI."

    # Test empty list validation
    with pytest.raises(ValidationError):
        AIActAuditReport(
            system_name="Test",
            risk_level=RiskCategory.MINIMAL,
            primary_articles=[],
            findings=[],
            summary="Test"
        )

    # Test type validation
    with pytest.raises(ValidationError):
        AIActAuditReport(
            system_name=123,
            risk_level=RiskCategory.MINIMAL,
            primary_articles=[article_ref],
            findings=[finding],
            summary="Test"
        )

def test_json_schema_generation():
    """Test that models can generate JSON schemas with detailed checks"""
    schema = AIActAuditReport.model_json_schema()

    # Basic structure checks
    assert "properties" in schema
    assert "required" in schema

    # Check all required fields
    required_fields = {"system_name", "risk_level", "primary_articles", "findings", "summary"}
    assert set(schema["required"]) == required_fields

    # Check nested model schemas
    assert "items" in schema["properties"]["primary_articles"]
    assert "$ref" in schema["properties"]["primary_articles"]["items"]

    assert "items" in schema["properties"]["findings"]
    assert "$ref" in schema["properties"]["findings"]["items"]

def test_model_serialization():
    """Test that models can be serialized to dict and JSON with round-trip validation"""
    article_ref = ArticleReference(
        article="Article 5",
        title="Prohibited AI practices",
        description="AI systems that deploy subliminal techniques"
    )

    finding = ComplianceFinding(
        criterion="Prohibited practices check",
        is_compliant=True,
        evidence="System does not use subliminal techniques",
        reasoning="Technical documentation confirms no subliminal techniques are used"
    )

    report = AIActAuditReport(
        system_name="Test-System",
        risk_level=RiskCategory.MINIMAL,
        primary_articles=[article_ref],
        findings=[finding],
        summary="System complies with minimal risk requirements"
    )

    # Test dict serialization
    report_dict = report.model_dump()
    assert report_dict["system_name"] == "Test-System"
    assert report_dict["risk_level"] == "Minimal Risk"
    assert len(report_dict["primary_articles"]) == 1
    assert len(report_dict["findings"]) == 1

    # Test JSON serialization
    report_json = report.model_dump_json()
    assert "Test-System" in report_json
    assert "Minimal Risk" in report_json

    # Test round-trip (dict -> model -> dict)
    reconstructed = AIActAuditReport.model_validate(report_dict)
    assert reconstructed.model_dump() == report_dict

def test_model_equality():
    """Test that models implement equality correctly"""
    article1 = ArticleReference(article="Article 5", title="Test", description="Test")
    article2 = ArticleReference(article="Article 5", title="Test", description="Test")
    article3 = ArticleReference(article="Article 6", title="Test", description="Test")

    assert article1 == article2
    assert article1 != article3

    finding1 = ComplianceFinding(
        criterion="Test",
        is_compliant=True,
        evidence="Test",
        reasoning="Test"
    )
    finding2 = ComplianceFinding(
        criterion="Test",
        is_compliant=True,
        evidence="Test",
        reasoning="Test"
    )

    assert finding1 == finding2

if __name__ == "__main__":
    pytest.main([__file__])
