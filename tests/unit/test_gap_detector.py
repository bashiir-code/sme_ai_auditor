"""
tests/unit/test_gap_detector.py
-------------------------------
Unit tests for the GapDetector.
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.analysis.schemas import (
    AIActAuditReport, 
    HarmonizedStandardRequirement, 
    ComplianceFinding,
    RiskCategory,
    ArticleReference
)
from src.analysis.gap_detector import GapDetector

class TestGapDetector:

    def _dummy_article(self):
        return ArticleReference(article="Article 1", title="Title", description="Desc")

    def _dummy_finding(self):
        return ComplianceFinding(criterion="Test", is_compliant=True, evidence="Yes", reasoning="Yes")

    def test_prohibited_system_short_circuits(self):
        detector = GapDetector()
        
        report = AIActAuditReport(
            system_name="Bad System",
            risk_level=RiskCategory.PROHIBITED,
            primary_articles=[self._dummy_article()],
            findings=[self._dummy_finding()],
            summary="This system is terrible."
        )
        
        # Act
        plan = detector.generate_plan(
            ai_act_report=report,
            data_act_data={"data_sharing_compliant": True, "cloud_switching_compliant": True},
            mapped_requirements=[]
        )
        
        assert plan.is_deployable is False
        assert len(plan.actions) == 1
        assert plan.actions[0].priority == "High"
        assert plan.actions[0].missing_requirement == "Cease Operations"

    def test_detects_llm_findings(self):
        detector = GapDetector()
        
        report = AIActAuditReport(
            system_name="Test system",
            risk_level=RiskCategory.HIGH_RISK,
            primary_articles=[self._dummy_article()],
            summary="High risk system.",
            findings=[
                ComplianceFinding(
                    criterion="Data Bias checks",
                    is_compliant=False,
                    evidence="No bias checks exist",
                    reasoning="Required by AI Act"
                )
            ]
        )
        
        plan = detector.generate_plan(
            ai_act_report=report,
            data_act_data={"data_sharing_compliant": True, "cloud_switching_compliant": True},
            mapped_requirements=[]
        )
        
        assert plan.is_deployable is False
        assert len(plan.actions) == 1
        assert plan.actions[0].missing_requirement == "Data Bias checks"
        assert plan.actions[0].priority == "High"

    def test_set_difference_detects_missing_mandatory_standards(self):
        detector = GapDetector()
        
        report = AIActAuditReport(
            system_name="Test system",
            risk_level=RiskCategory.HIGH_RISK,
            primary_articles=[self._dummy_article()],
            summary="High risk.",
            # Only compliant for "Logging", NOT compliant/evidenced for "Oversight"
            findings=[
                ComplianceFinding(
                    criterion="Logging",
                    is_compliant=True,
                    evidence="Logs exist",
                    reasoning="Valid"
                )
            ]
        )
        
        mapped = [
            HarmonizedStandardRequirement(
                standard_id="EN-123",
                title="Human Oversight",
                description="Must have oversight",
                is_mandatory=True,
                verification_method="Check UI"
            )
        ]
        
        plan = detector.generate_plan(
            ai_act_report=report,
            data_act_data={"data_sharing_compliant": True, "cloud_switching_compliant": True},
            mapped_requirements=mapped
        )
        
        assert plan.is_deployable is False
        assert len(plan.actions) == 1
        assert "Human Oversight" in plan.actions[0].missing_requirement
        assert plan.actions[0].reference_standard == "EN-123"

    def test_integrates_data_act_failures(self):
        detector = GapDetector()
        
        report = AIActAuditReport(
            system_name="Test system",
            risk_level=RiskCategory.MINIMAL,
            primary_articles=[self._dummy_article()],
            summary="Minimal risk.",
            findings=[self._dummy_finding()]
        )
        
        # Fails both
        data_act_data = {
            "data_sharing_compliant": False,
            "cloud_switching_compliant": False,
            "missing_requirements": "No APIs built"
        }
        
        plan = detector.generate_plan(
            ai_act_report=report,
            data_act_data=data_act_data,
            mapped_requirements=[]
        )
        
        assert plan.is_deployable is False
        assert len(plan.actions) == 2
        
        sharing_gap = next(a for a in plan.actions if "Data sharing" in a.missing_requirement)
        assert sharing_gap.priority == "High"
        
        switch_gap = next(a for a in plan.actions if "Cloud switching" in a.missing_requirement)
        assert switch_gap.priority == "Medium"
