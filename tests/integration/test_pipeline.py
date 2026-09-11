"""
test_pipeline.py
----------------
Integration tests for the SME AI Auditor End-to-End Orchestrator (src/main.py).
"""

import pytest
import os
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.main import execute_audit, verify_infrastructure
from src.analysis.schemas import (
    AIActAuditReport, 
    RiskCategory, 
    ArticleReference, 
    ComplianceFinding
)

class TestEndToEndPipeline:

    @patch("src.main.Mistral")
    @patch("src.main.QdrantClientWrapper")
    def test_verify_infrastructure_success(self, mock_qdrant, mock_mistral):
        # Should not raise any exceptions
        verify_infrastructure(mistral_api_key="fake-key")
        
        mock_mistral.assert_called_once_with(api_key="fake-key")
        mock_qdrant.assert_called_once()

    @patch("src.main.LocalAuditLogger")
    @patch("src.main.verify_infrastructure")
    @patch("src.main.IndexManager")
    @patch("src.main.DoclingParser")
    @patch("src.main.DocumentRetrievalPipeline")
    @patch("src.main.AIActClassifier")
    @patch("src.main.DataActChecker")
    @patch("src.main.RequirementMapper")
    @patch("src.main.GapDetector")
    @patch("src.main.MarkdownGenerator")
    @patch("src.main.PDFConverter")
    def test_execute_audit_flow(
        self, 
        mock_pdf, mock_md, mock_detector, mock_mapper, 
        mock_data_checker, mock_ai_classifier, 
        mock_retrieval, mock_docling, mock_index_mgr, mock_verify, mock_audit_logger
    ):
        # 1. Setup Mocks
        mock_retriever_instance = MagicMock()
        mock_retrieval.return_value = mock_retriever_instance
        
        mock_ai_instance = MagicMock()
        mock_ai_instance.analyze_system.return_value = AIActAuditReport(
            system_name="Test",
            risk_level=RiskCategory.HIGH_RISK,
            primary_articles=[
                ArticleReference(article="Art 1", title="T", description="D")
            ],
            findings=[
                ComplianceFinding(criterion="C", is_compliant=True, evidence="E", reasoning="R")
            ],
            summary="Mock summary"
        )
        mock_ai_classifier.return_value = mock_ai_instance
        
        mock_data_instance = MagicMock()
        mock_data_instance.evaluate_data_obligations.return_value = {}
        mock_data_checker.return_value = mock_data_instance
        
        mock_mapper_instance = MagicMock()
        mock_mapper_instance.map_requirements.return_value = []
        mock_mapper.return_value = mock_mapper_instance
        
        mock_detector_instance = MagicMock()
        mock_plan = MagicMock()
        mock_plan.actions = []
        mock_detector_instance.generate_plan.return_value = mock_plan
        mock_detector.return_value = mock_detector_instance
        
        mock_md_instance = MagicMock()
        mock_md_instance.generate.return_value = "dummy.md"
        mock_md.return_value = mock_md_instance
        
        # 2. Execute
        execute_audit(sme_docs_path="", system_desc="HR Scanner")
        
        # 3. Assert Integration Flow
        # Verify Retrieval happened
        mock_retriever_instance.run_query.assert_called_once_with(
            query="HR Scanner", 
            filters={"document_source": "eu_ai_act"}, 
            top_k=10
        )
        
        # Verify both classifiers were triggered sequentially
        mock_ai_instance.analyze_system.assert_called_once()
        mock_data_instance.evaluate_data_obligations.assert_called_once_with(system_description="HR Scanner")
        
        # Verify Mapping and Gaps
        mock_mapper_instance.map_requirements.assert_called_once_with(risk_level=RiskCategory.HIGH_RISK)
        mock_detector_instance.generate_plan.assert_called_once()
        
        # Verify PDF reporting happened at the end
        mock_md_instance.generate.assert_called_once()
        mock_pdf_instance = mock_pdf.return_value
        mock_pdf_instance.convert_markdown_to_pdf.assert_called_once()

        # Verify the encrypted forensic trail was written
        mock_audit_logger.return_value.save_trace.assert_called_once()
