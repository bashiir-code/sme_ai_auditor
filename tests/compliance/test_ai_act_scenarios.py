import pytest
import os
from src.parsers.docling_parser import DoclingParser
from src.analysis.ai_act_classifier import AIActClassifier
from src.analysis.schemas import RiskCategory


def test_evidence_pack_prohibition_check():
    # 1. Setup paths
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    evidence_path = os.path.join(base_dir, "data/sme_docs_examples/AI_Compliance_Advisor_Evidence_Pack.md")

    # 2. Ingest (Docling) - Optimized for 16GB
    parser = DoclingParser()
    parsed_data = parser.parse(evidence_path)
    content = parsed_data["content"]

    # 3. Analyze (Mistral AI API)
    classifier = AIActClassifier()
    report = classifier.analyze(content)

    # 4. Senior Assertions
    assert report is not None
    # The evidence pack explicitly mentions Biometric ID in the matrix
    assert report.risk_level == RiskCategory.PROHIBITED
    assert any("Biometric" in finding.evidence for finding in report.findings)
