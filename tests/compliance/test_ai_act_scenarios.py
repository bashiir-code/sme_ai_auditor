import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.parsers.docling_parser import DoclingParser
from src.analysis.ai_act_classifier import AIActClassifier
from src.analysis.schemas import AIActAuditReport, RiskCategory
import structlog
import os

# Configure logging for test output
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

@pytest.fixture
def mock_mistral_client():
    """Fixture to mock Mistral AI client responses"""
    with patch('src.analysis.ai_act_classifier.MistralClient') as mock_client:
        yield mock_client

@pytest.fixture
def test_data_path():
    """Fixture providing path to test data"""
    return Path(__file__).parent.parent.parent / "data" / "sme_docs_examples" / "AI_Compliance_Advisor_Evidence_Pack.md"

def test_prohibited_practice_detection(mock_mistral_client, test_data_path):
    """
    Test that the classifier correctly identifies prohibited practices
    when biometric surveillance is mentioned in the evidence pack.
    """
    # Setup mock response for prohibited practice detection
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='''
        {
            "findings": [
                {
                    "requirement": "Prohibition of biometric identification",
                    "compliance_status": "Non-Compliant",
                    "evidence": "Real-time surveillance using facial recognition",
                    "risk_category": "Prohibited",
                    "article_reference": "Article 5"
                }
            ]
        }
        '''))
    ]
    mock_client_instance = mock_mistral_client.return_value
    mock_client_instance.chat.return_value = mock_response

    # Initialize components
    parser = DoclingParser()
    classifier = AIActClassifier(api_key="test_key")

    # Parse the evidence document
    parse_result = parser.parse(str(test_data_path))
    evidence_text = parse_result['content']

    # Classify the system
    report = classifier.classify_system(
        system_description="AI system with biometric identification capabilities",
        evidence_text=evidence_text
    )

    # Assertions
    assert isinstance(report, AIActAuditReport)
    assert report.compliance_status == "Prohibited"
    assert len(report.findings) > 0

    # Verify at least one finding is about prohibited practice
    prohibited_findings = [
        f for f in report.findings
        if f.risk_category == RiskCategory.PROHIBITED
        and "Article 5" in f.article_reference
    ]
    assert len(prohibited_findings) > 0, "Should detect prohibited biometric practices"

    # Verify evidence contains reference to Risk Classification Matrix
    matrix_references = [
        f for f in report.findings
        if "Risk Classification Matrix" in f.evidence
    ]
    assert len(matrix_references) > 0, "Should reference the Risk Classification Matrix"

def test_compliance_analysis_with_standards(mock_mistral_client, test_data_path):
    """
    Test that the classifier maps findings to harmonized standards
    and produces valid audit report structure.
    """
    # Setup mock response for compliance analysis
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='''
        {
            "findings": [
                {
                    "requirement": "Transparency obligations",
                    "compliance_status": "Compliant",
                    "evidence": "System provides clear user information as per Article 13",
                    "risk_category": "Low",
                    "article_reference": "Article 13"
                },
                {
                    "requirement": "Data quality management",
                    "compliance_status": "Partial",
                    "evidence": "Some data governance gaps identified in Risk Classification Matrix",
                    "risk_category": "Medium",
                    "article_reference": "Article 10"
                }
            ]
        }
        '''))
    ]
    mock_client_instance = mock_mistral_client.return_value
    mock_client_instance.chat.return_value = mock_response

    # Initialize components
    parser = DoclingParser()
    classifier = AIActClassifier(api_key="test_key")

    # Parse the evidence document
    parse_result = parser.parse(str(test_data_path))
    evidence_text = parse_result['content']

    # Classify the system
    report = classifier.classify_system(
        system_description="AI compliance advisor system",
        evidence_text=evidence_text
    )

    # Assertions
    assert isinstance(report, AIActAuditReport)
    assert report.compliance_status == "Conditional"  # Due to partial compliance
    assert len(report.findings) == 2
    assert len(report.harmonized_standards) > 0  # Should map to standards

    # Verify standards mapping
    expected_standards = ["EN ISO 25010", "EN ISO 9126"]  # For Article 13
    assert any(std in report.harmonized_standards for std in expected_standards)

    # Verify evidence references
    matrix_references = [
        f for f in report.findings
        if "Risk Classification Matrix" in f.evidence
    ]
    assert len(matrix_references) > 0, "Should reference the Risk Classification Matrix"

def test_document_parsing_integration(test_data_path):
    """
    Test that the parser correctly extracts content and metadata
    from the evidence pack document.
    """
    parser = DoclingParser()
    result = parser.parse(str(test_data_path))

    # Verify basic structure
    assert 'content' in result
    assert 'metadata' in result
    assert len(result['content']) > 0

    # Verify metadata contains expected fields
    metadata = result['metadata']
    assert 'file_path' in metadata
    assert 'page_count' in metadata
    assert 'has_tables' in metadata

    # Verify content contains expected sections
    content = result['content']
    assert "Risk Classification Matrix" in content
    assert "Compliance Evidence" in content or "Evidence" in content

@pytest.mark.skipif(
    not os.getenv('LANGFUSE_PUBLIC_KEY'),
    reason="Langfuse credentials not configured"
)
def test_observability_integration(mock_mistral_client, test_data_path):
    """
    Test that the classification process is properly observed
    and traced in Langfuse.
    """
    # This test requires actual Langfuse configuration
    # Setup mock response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='''
        {
            "findings": [
                {
                    "requirement": "Test requirement",
                    "compliance_status": "Compliant",
                    "evidence": "Test evidence from Risk Classification Matrix",
                    "risk_category": "Low",
                    "article_reference": "Article 6"
                }
            ]
        }
        '''))
    ]
    mock_client_instance = mock_mistral_client.return_value
    mock_client_instance.chat.return_value = mock_response

    # Initialize components
    parser = DoclingParser()
    classifier = AIActClassifier(api_key="test_key")

    # Parse and classify
    parse_result = parser.parse(str(test_data_path))
    report = classifier.classify_system(
        system_description="Test system",
        evidence_text=parse_result['content']
    )

    # The @observe decorator should have automatically
    # captured the execution trace in Langfuse
    assert isinstance(report, AIActAuditReport)
    # Actual observability verification would require
    # checking Langfuse dashboard or API
