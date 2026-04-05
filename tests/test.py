import pytest
from src.analysis.schemas import RiskCategory, ArticleReference, ComplianceFinding, AIActAuditReport

def test_risk_category_enum():
    """Test RiskCategory enum values"""
    assert RiskCategory.PROHIBITED.value == "Prohibited"
    assert RiskCategory.HIGH_RISK.value == "High-Risk"
    assert RiskCategory.LIMITED.value == "Limited Risk"
    assert RiskCategory.MINIMAL.value == "Minimal Risk"

def test_article_reference_model():
    """Test ArticleReference model creation and validation"""
    article = ArticleReference(
        article="Article 5",
        title="Prohibited AI practices",
        description="AI systems that deploy subliminal techniques"
    )
    assert article.article == "Article 5"
    assert article.title == "Prohibited AI practices"
    assert article.description == "AI systems that deploy subliminal techniques"

    # Test validation
    with pytest.raises(ValueError):
        ArticleReference(article="", title="test", description="test")

def test_compliance_finding_model():
    """Test ComplianceFinding model with all fields"""
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

def test_ai_act_audit_report_model():
    """Test AIActAuditReport model with complete structure"""
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

def test_json_schema_generation():
    """Test that models can generate JSON schemas"""
    schema = AIActAuditReport.schema()
    assert "properties" in schema
    assert "system_name" in schema["properties"]
    assert "risk_level" in schema["properties"]
    assert "primary_articles" in schema["properties"]
    assert "findings" in schema["properties"]
    assert "summary" in schema["properties"]

def test_model_serialization():
    """Test that models can be serialized to dict and JSON"""
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
    report_dict = report.dict()
    assert report_dict["system_name"] == "Test-System"
    assert report_dict["risk_level"] == "Minimal Risk"

    # Test JSON serialization
    report_json = report.json()
    assert "Test-System" in report_json
    assert "Minimal Risk" in report_json

if __name__ == "__main__":
    pytest.main([__file__])
