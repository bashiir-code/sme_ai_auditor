"""
gap_detector.py
---------------
Deterministic diff logic engine prioritizing Missing Compliance Standards vs. Existing SME System architecture.

Runs pure Python execution (No LLM inference) for maximal optimization and deterministic tracking.
"""

import uuid
from typing import List, Dict, Any
import structlog
from langfuse import observe

from src.analysis.schemas import (
    AIActAuditReport, 
    HarmonizedStandardRequirement, 
    RemediationPlan, 
    RemediationAction,
    RiskCategory
)

logger = structlog.get_logger(__name__)


class GapDetector:
    """
    Synthesizes facts from the AI Act, Data Act, and mapped Engineering Standards
    to strictly produce an actionable gap remediation plan.
    """

    def __init__(self):
        logger.info("GapDetector initialized (Lean, LLM-free configuration)")

    @observe(name="generate_remediation_plan")
    def generate_plan(
        self, 
        ai_act_report: AIActAuditReport, 
        data_act_data: Dict[str, Any], 
        mapped_requirements: List[HarmonizedStandardRequirement]
    ) -> RemediationPlan:
        """
        Produce prioritized list of unmet requirements based on Set Difference logic.
        
        Args:
            ai_act_report: The verified AI Act Audit (with ComplianceFindings).
            data_act_data: Result map from DataActChecker.
            mapped_requirements: The list of mandatory standards for the risk tier.

        Returns:
            A strictly validated RemediationPlan.
        """
        logger.info(
            "Detecting gaps", 
            risk=ai_act_report.risk_level.value,
            num_requirements=len(mapped_requirements)
        )
        
        # We generate a deterministic trace reference for this component run.
        current_trace_id = str(uuid.uuid4())

        actions: List[RemediationAction] = []
        
        # -------------------------------------------------------------
        # 1. Prohibited AI Hard-Block
        # -------------------------------------------------------------
        if ai_act_report.risk_level == RiskCategory.PROHIBITED:
            actions.append(
                RemediationAction(
                    priority="High",
                    missing_requirement="Cease Operations",
                    reference_standard="AI Act Article 5",
                    violation_context=f"LLM determined system prohibited: {ai_act_report.summary}",
                    trace_id_reference=current_trace_id
                )
            )
            # Short circuit: deployable = False, only gap is to cease operations
            return RemediationPlan(actions=actions, is_deployable=False)

        # -------------------------------------------------------------
        # 2. Extract specific LLM Non-compliant Findings from AI Act
        # -------------------------------------------------------------
        # Gaps identified directly by the LLM 
        for finding in ai_act_report.findings:
            if not finding.is_compliant:
                actions.append(
                    RemediationAction(
                        priority="High" if ai_act_report.risk_level == RiskCategory.HIGH_RISK else "Medium",
                        missing_requirement=finding.criterion,
                        reference_standard="AI Act Generic Finding",
                        violation_context=f"Evidence: {finding.evidence} | Reasoning: {finding.reasoning}",
                        trace_id_reference=current_trace_id
                    )
                )

        # -------------------------------------------------------------
        # 3. SET DIFFERENCE LOGIC for Technical Standards
        # -------------------------------------------------------------
        # The true engine power: If the mapper mandates a standard, but the LLM
        # findings did not show successful compliance covering that topic, 
        # it is a missing technical gap.
        
        # Build a set of words from compliant findings for a primitive text-overlap check.
        # In a massive production system, this could be a semantic vector match.
        compliant_texts = " ".join([f.criterion.lower() for f in ai_act_report.findings if f.is_compliant])
        
        for req in mapped_requirements:
            if not req.is_mandatory:
                continue
                
            # If standard keywords don't appear anywhere in the compliant LLM findings, flag it.
            # Example: Standard requires "Human Oversight Mechanism". 
            # If the LLM didn't find that compliant, it's a gap!
            # We use a simple heuristic overlap here to prove the architectural concept.
            title_keywords = set(req.title.lower().split())
            
            # Remove minor stop words for better overlap
            title_keywords -= {"the", "and", "or", "a", "of", "system", "management"}
            
            # If the intersection is extremely poor, we flag it as an unfulfilled requirement
            match_found = any(k in compliant_texts for k in title_keywords) if title_keywords else False
            
            if not match_found:
                actions.append(
                    RemediationAction(
                        priority="High" if ai_act_report.risk_level == RiskCategory.HIGH_RISK else "Medium",
                        missing_requirement=f"Implement {req.title}",
                        reference_standard=req.standard_id,
                        violation_context=f"Mapped mandatory requirement not evidenced by system design.",
                        trace_id_reference=current_trace_id
                    )
                )

        # -------------------------------------------------------------
        # 4. Integrate Data Act Gaps
        # -------------------------------------------------------------
        if not data_act_data.get("data_sharing_compliant", True):
            actions.append(
                RemediationAction(
                    priority="High",
                    missing_requirement="Data sharing mechanism",
                    reference_standard="EU Data Act - Sharing",
                    violation_context=str(data_act_data.get("missing_requirements", "Sharing failure")),
                    trace_id_reference=current_trace_id
                )
            )
            
        if not data_act_data.get("cloud_switching_compliant", True):
            actions.append(
                RemediationAction(
                    priority="Medium",
                    missing_requirement="Cloud switching mechanism",
                    reference_standard="EU Data Act - Cloud Switching",
                    violation_context=str(data_act_data.get("missing_requirements", "Switching failure")),
                    trace_id_reference=current_trace_id
                )
            )

        # -------------------------------------------------------------
        # 5. Finalize Deployability
        # -------------------------------------------------------------
        is_deployable = True
        if any(action.priority == "High" for action in actions):
            is_deployable = False
            
        logger.info(
            "Remediation plan generated", 
            total_gaps=len(actions),
            deployable=is_deployable
        )
        
        return RemediationPlan(actions=actions, is_deployable=is_deployable)
