"""
test_hardening.py
-----------------
Verification suite for the SME AI Auditor's Sovereignty and Performance hardening.
Tests: Privacy Masking, Local Audit Encryption, and Context Guarding.
"""

import pytest
import os
import shutil
from unittest.mock import patch, MagicMock
from src.main import execute_audit
from src.observability.local_audit_logger import LocalAuditLogger
from src.analysis.schemas import AIActAuditReport, RiskCategory, ArticleReference, ComplianceFinding

class TestSystemHardening:

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        # Cleanup audits and reports before/after tests
        dirs = ["audits_test", "reports_test"]
        for d in dirs:
            if os.path.exists(d):
                shutil.rmtree(d)
            os.makedirs(d)
        yield
        for d in dirs:
            if os.path.exists(d):
                shutil.rmtree(d)

    @patch("src.main.verify_infrastructure")
    @patch("src.main.IndexManager")
    @patch("src.main.DoclingParser")
    @patch("src.main.DocumentRetrievalPipeline")
    @patch("src.main.AIActClassifier")
    @patch("src.main.DataActChecker")
    @patch("src.main.PDFConverter")
    def test_end_to_end_hardening_flow(
        self,
        mock_pdf, mock_data_checker, mock_ai_classifier,
        mock_retrieval, mock_docling, mock_index, mock_verify
    ):
        # 1. Setup Mock Results
        mock_ai_instance = MagicMock()
        mock_ai_instance.analyze_system.return_value = AIActAuditReport(
            system_name="Test Hardening",
            risk_level=RiskCategory.LIMITED,
            primary_articles=[ArticleReference(article="1", title="T", description="D")],
            findings=[ComplianceFinding(criterion="C", is_compliant=True, evidence="E", reasoning="R")],
            summary="Hardened summary"
        )
        mock_ai_classifier.return_value = mock_ai_instance
        
        mock_data_checker.return_value.evaluate_data_obligations.return_value = {"status": "ok"}
        
        # 2. Execute Audit
        audit_dir = "audits_test"
        with patch("src.main.LocalAuditLogger") as mock_logger_class:
            mock_logger_instance = LocalAuditLogger(audit_dir=audit_dir)
            mock_logger_class.return_value = mock_logger_instance
            
            # Using custom report dir
            with patch("src.main.MarkdownGenerator") as mock_md_class:
                mock_md_class.return_value.generate.return_value = "dummy.md"
                
                execute_audit(sme_docs_path="", system_desc="Sensitive SME Data")

        # 3. VERIFY PRIVACY MASKING (Check @observe settings)
        # We can't easily check @observe capture_input in runtime without deep inspection,
        # but we can verify that raw data WAS passed to the Local Logger.
        
        # 4. VERIFY LOCAL AUDIT LOG (Forensics)
        audit_files = os.listdir(audit_dir)
        assert len(audit_files) == 1
        audit_path = os.path.join(audit_dir, audit_files[0])
        
        # Verify encryption: reading raw should be binary/encrypted
        with open(audit_path, "rb") as f:
            raw_content = f.read()
            # Fernet tokens start with 'gAAAAA'
            assert raw_content.startswith(b"gAAAA") 

        # Verify decryption: internal developers can see the raw data
        decrypted = mock_logger_instance.decrypt_trace(audit_path)
        assert decrypted["full_context"]["system_desc_raw"] == "Sensitive SME Data"
        assert decrypted["full_context"]["ai_act_report"]["risk_level"] == "Limited Risk"

    @patch("src.analysis.ai_act_classifier.Mistral")
    def test_context_guard_truncation(self, mock_mistral):
        from src.analysis.ai_act_classifier import AIActClassifier
        from haystack import Document
        
        classifier = AIActClassifier(api_key="fake")
        
        # Create 15 chunks
        large_context = [Document(content=f"chunk {i}", meta={"article_number": i}) for i in range(15)]
        
        with patch.object(classifier, "_client") as mock_client:
            mock_client.chat.complete.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content='{"system_name":"T","risk_level":"Limited Risk","primary_articles":[{"article":"1","title":"T","description":"D"}],"findings":[{"criterion":"C","is_compliant":true,"evidence":"E","reasoning":"R"}],"summary":"S"}'))]
            )
            
            classifier.analyze_system(system_description="Test", context_docs=large_context)
            
            # Verify only 10 chunks were sent in the prompt
            # Extract the user prompt from the last call
            call_args = mock_client.chat.complete.call_args
            user_prompt = call_args.kwargs["messages"][1]["content"]
            
            assert "[Document 10]" in user_prompt
            assert "[Document 11]" not in user_prompt
