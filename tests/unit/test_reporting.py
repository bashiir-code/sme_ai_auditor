"""
tests/unit/test_reporting.py
----------------------------
Tests for Markdown and PDF reporting generators.
"""

import pytest
import os
import tempfile

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.analysis.schemas import (
    AIActAuditReport, 
    ComplianceFinding,
    RiskCategory,
    ArticleReference,
    RemediationPlan,
    RemediationAction
)
from src.reporting.markdown_generator import MarkdownGenerator

class TestMarkdownGenerator:

    def _dummy_ai_act_report(self):
        return AIActAuditReport(
            system_name="Smart Filter",
            risk_level=RiskCategory.LIMITED,
            primary_articles=[
                ArticleReference(article="Article 50", title="Transparency", description="Inform users")
            ],
            summary="System complies with transparency but lacks robust logging.",
            findings=[
                ComplianceFinding(
                    criterion="User Disclosure",
                    is_compliant=True,
                    evidence="Checkbox on login",
                    reasoning="Explicit consent gathered"
                )
            ]
        )

    def _dummy_data_act_data(self):
        return {
            "is_data_provider": True,
            "data_sharing_compliant": False,
            "cloud_switching_compliant": True,
            "summary": "Must implement APIs for SME data portability."
        }

    def _dummy_remediation_plan(self, deployable: bool = False):
        actions = []
        if not deployable:
            actions.append(
                RemediationAction(
                    priority="High",
                    missing_requirement="Data sharing API",
                    reference_standard="Data Act Art 4",
                    violation_context="No endpoints exposed out",
                    trace_id_reference="trace-1234"
                )
            )
        return RemediationPlan(
            actions=actions,
            is_deployable=deployable
        )

    def test_init_creates_directory(self):
        with tempfile.TemporaryDirectory() as base_dir:
            out_dir = os.path.join(base_dir, "reports")
            MarkdownGenerator(output_dir=out_dir)
            assert os.path.exists(out_dir)

    def test_generate_markdown_writes_file_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = MarkdownGenerator(output_dir=temp_dir)
            
            filepath = generator.generate(
                ai_act_report=self._dummy_ai_act_report(),
                data_act_data=self._dummy_data_act_data(),
                gap_plan=self._dummy_remediation_plan(deployable=False),
                filename="test_report.md"
            )
            
            assert os.path.exists(filepath)
            
            with open(filepath, 'r') as f:
                content = f.read()
                
            # Formatting checks
            assert "# SME AI Auditor - Official Compliance Report" in content
            assert "Smart Filter" in content
            assert "🟥 **BLOCKED (DO NOT DEPLOY)**" in content
            assert "Limited Risk" in content
            assert "Article 50" in content
            assert "✅ **User Disclosure**" in content
            
            # Data Act
            assert "**Data Provider Status:** Yes" in content
            assert "**Data Sharing Readiness:** ❌" in content
            
            # Gaps
            assert "🚨 [High] Data sharing API" in content
            assert "`trace-1234`" in content

    def test_generate_markdown_deployable_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = MarkdownGenerator(output_dir=temp_dir)
            
            filepath = generator.generate(
                ai_act_report=self._dummy_ai_act_report(),
                data_act_data=self._dummy_data_act_data(),
                gap_plan=self._dummy_remediation_plan(deployable=True),
                filename="success_report.md"
            )
            
            with open(filepath, 'r') as f:
                content = f.read()
                
            assert "🟩 **DEPLOYABLE**" in content
            assert "No mandatory compliance gaps detected." in content

# ---------------------------------------------------------------------------
# PDFConverter Tests
# ---------------------------------------------------------------------------

from src.reporting.pdf_converter import PDFConverter

class TestPDFConverter:

    def test_missing_markdown_raises_error(self):
        converter = PDFConverter()
        with pytest.raises(FileNotFoundError, match="Input markdown file not found"):
            converter.convert_markdown_to_pdf("/fake/path/doesnotexist.md", "/fake/path/out.pdf")

    def test_convert_markdown_to_pdf_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Create a dummy markdown file
            md_path = os.path.join(temp_dir, "test.md")
            pdf_path = os.path.join(temp_dir, "output.pdf")
            
            with open(md_path, "w") as f:
                f.write("# Hello World\n\nThis is a *test* of the **PDF Converter**.")
                
            converter = PDFConverter()
            result_path = converter.convert_markdown_to_pdf(md_path, pdf_path)
            
            assert result_path == os.path.abspath(pdf_path)
            assert os.path.exists(pdf_path)
            
            # The PDF file should have some weight (at least more than 0 bytes)
            assert os.path.getsize(pdf_path) > 1000  # WeasyPrint PDFs are generally > 1KB
