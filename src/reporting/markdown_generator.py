"""
markdown_generator.py
---------------------
Aggregates structured compliance schemas (AI Act, Data Act, Gaps) and templates
them into a professional, human-readable Markdown report for the SME.
"""

import os
from datetime import datetime, timezone
import structlog
from typing import Dict, Any, Optional
from src.analysis.schemas import AIActAuditReport, RemediationPlan

logger = structlog.get_logger(__name__)


class MarkdownGenerator:
    """
    Translates technical Pydantic findings into an SME-facing Markdown Report.
    Clean, professional output — no emoji, structured for regulatory review.
    """

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
        logger.info("MarkdownGenerator initialized", output_dir=self.output_dir)

    def generate(
        self,
        ai_act_report: AIActAuditReport,
        data_act_data: Dict[str, Any],
        gap_plan: RemediationPlan,
        claude_ai_act: Optional[AIActAuditReport] = None,
        claude_data_act: Optional[Dict[str, Any]] = None,
        trace_id: str = None,
        filename: str = "compliance_report.md"
    ) -> str:
        """
        Produce a unified Markdown string and save it to disk.
        """
        logger.info("Generating Markdown compliance report", system_name=ai_act_report.system_name)

        timestamp = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC")
        short_id = trace_id[:8] if trace_id else "N/A"
        deployment_status = "APPROVED FOR DEPLOYMENT" if gap_plan.is_deployable else "BLOCKED — DO NOT DEPLOY"
        risk_level = ai_act_report.risk_level.value.upper()

        report = []

        # ── COVER / HEADER ───────────────────────────────────────────────────
        report.append("# EU AI Act & Data Act Compliance Assessment Report")
        report.append("")
        report.append("---")
        report.append("")

        # ── REPORT METADATA TABLE ────────────────────────────────────────────
        report.append("## Report Information")
        report.append("")
        report.append("| Field | Value |")
        report.append("|---|---|")
        report.append(f"| System Under Assessment | {ai_act_report.system_name} |")
        report.append(f"| Assessment Date | {timestamp} |")
        report.append(f"| Risk Classification | {risk_level} |")
        report.append(f"| Deployment Status | **{deployment_status}** |")
        report.append(f"| Audit Trace ID | `{trace_id if trace_id else 'N/A'}` |")
        report.append(f"| Report Reference | SME-{short_id.upper()} |")
        report.append("")

        # ── EXECUTIVE SUMMARY ────────────────────────────────────────────────
        report.append("---")
        report.append("")
        report.append("## Executive Summary")
        report.append("")
        report.append(ai_act_report.summary)
        report.append("")

        # ── COMPLIANCE SCORECARD ─────────────────────────────────────────────
        total_findings = len(ai_act_report.findings)
        compliant_count = sum(1 for f in ai_act_report.findings if f.is_compliant)
        non_compliant_count = total_findings - compliant_count
        gap_count = len(gap_plan.actions)
        high_gaps = sum(1 for a in gap_plan.actions if a.priority.lower() == "high")
        medium_gaps = sum(1 for a in gap_plan.actions if a.priority.lower() == "medium")
        low_gaps = sum(1 for a in gap_plan.actions if a.priority.lower() == "low")

        report.append("---")
        report.append("")
        report.append("## Compliance Scorecard")
        report.append("")
        report.append("| Metric | Result |")
        report.append("|---|---|")
        report.append(f"| Total Requirements Assessed | {total_findings} |")
        report.append(f"| Requirements Met | {compliant_count} |")
        report.append(f"| Requirements Failed | {non_compliant_count} |")
        report.append(f"| Total Remediation Actions | {gap_count} |")
        report.append(f"| High Priority Gaps | {high_gaps} |")
        report.append(f"| Medium Priority Gaps | {medium_gaps} |")
        report.append(f"| Low Priority Gaps | {low_gaps} |")
        report.append(f"| Data Provider Status | {'Yes' if data_act_data.get('is_data_provider') else 'No'} |")
        report.append(f"| Data Sharing Compliant | {'Yes' if data_act_data.get('data_sharing_compliant') else 'No'} |")
        report.append(f"| Cloud Switching Compliant | {'Yes' if data_act_data.get('cloud_switching_compliant') else 'No'} |")
        report.append("")

        # ── SECTION 1: EU AI ACT CLASSIFICATION ─────────────────────────────
        report.append("---")
        report.append("")
        report.append("## Section 1: EU AI Act Classification")
        report.append("")
        report.append(f"**Assigned Risk Tier:** `{risk_level}`")
        report.append("")

        if ai_act_report.primary_articles:
            report.append("### Applicable Legal Articles")
            report.append("")
            report.append("| Article | Title | Description |")
            report.append("|---|---|---|")
            for ref in ai_act_report.primary_articles:
                report.append(f"| {ref.article} | {ref.title} | {ref.description} |")
            report.append("")

        # ── FINDINGS TABLE ───────────────────────────────────────────────────
        report.append("### Detailed Compliance Findings")
        report.append("")
        report.append("| # | Criterion | Status | Reasoning | Evidence |")
        report.append("|---|---|---|---|---|")
        for i, finding in enumerate(ai_act_report.findings, 1):
            status = "PASS" if finding.is_compliant else "FAIL"
            report.append(
                f"| {i} | {finding.criterion} | {status} | {finding.reasoning} | {finding.evidence} |"
            )
        report.append("")

        # ── SECTION 2: EU DATA ACT ───────────────────────────────────────────
        report.append("---")
        report.append("")
        report.append("## Section 2: EU Data Act Obligations")
        report.append("")

        report.append("| Obligation | Status |")
        report.append("|---|---|")
        report.append(f"| Data Provider Classification | {'Classified as Data Provider' if data_act_data.get('is_data_provider') else 'Not a Data Provider'} |")
        report.append(f"| Data Sharing Readiness | {'Compliant' if data_act_data.get('data_sharing_compliant') else 'Non-Compliant'} |")
        report.append(f"| Cloud Switching Compliance | {'Compliant' if data_act_data.get('cloud_switching_compliant') else 'Non-Compliant'} |")
        report.append("")

        if data_act_data.get("summary"):
            report.append("**Assessment Notes:**")
            report.append("")
            report.append(f"> {data_act_data.get('summary')}")
            report.append("")

        # ── SECTION 2b: CLAUDE PARALLEL PERSPECTIVE ─────────────────────────
        if claude_ai_act or claude_data_act:
            report.append("---")
            report.append("")
            report.append("## Section 2b: Claude (OpenRouter) Parallel Perspective")
            report.append("")
            report.append(
                "> This section provides a second opinion from Claude 3.5 Sonnet "
                "to ensure regulatory robustness through dual-model validation."
            )
            report.append("")

            if claude_ai_act:
                report.append(f"**Claude Risk Tier:** `{claude_ai_act.risk_level.value.upper()}`")
                report.append("")
                report.append("**Claude's Executive Summary:**")
                report.append(f"> {claude_ai_act.summary}")
                report.append("")

            if claude_data_act:
                report.append("**Claude's Data Act Evaluation:**")
                report.append(f"| Obligation | Status |")
                report.append("|---|---|")
                report.append(f"| Data Provider | {'Yes' if claude_data_act.get('is_data_provider') else 'No'} |")
                report.append(f"| Ready | {'Yes' if claude_data_act.get('data_sharing_compliant') else 'No'} |")
                report.append("")
                report.append(f"> {claude_data_act.get('summary')}")
                report.append("")


        # ── SECTION 3: REMEDIATION PLAN ─────────────────────────────────────
        report.append("---")
        report.append("")
        report.append("## Section 3: Mandatory Remediation Plan")
        report.append("")

        if not gap_plan.actions:
            report.append(
                "> No mandatory compliance gaps detected. "
                "The system conforms to assessed engineering and legal standards."
            )
        else:
            report.append(
                f"> The following {gap_count} action(s) must be addressed before deployment. "
                "Items are ordered by priority."
            )
            report.append("")

            for i, action in enumerate(gap_plan.actions, 1):
                priority_label = action.priority.upper()
                report.append(f"### Action {i} — [{priority_label}] {action.missing_requirement}")
                report.append("")
                report.append("| Field | Detail |")
                report.append("|---|---|")
                report.append(f"| Priority | {priority_label} |")
                report.append(f"| Standard Reference | `{action.reference_standard}` |")
                report.append(f"| Violation Context | {action.violation_context} |")
                if action.trace_id_reference:
                    report.append(f"| Audit Trace Reference | `{action.trace_id_reference}` |")
                report.append("")

        # ── FOOTER ───────────────────────────────────────────────────────────
        report.append("---")
        report.append("")
        report.append("## Legal Disclaimer")
        report.append("")
        report.append(
            "This report has been generated automatically by the SME AI Auditor system "
            "and constitutes a technical assessment only. It does not constitute legal advice. "
            "Organizations should consult qualified legal counsel before making compliance decisions. "
            "This document is confidential and intended solely for the assessed organization."
        )
        report.append("")
        report.append(f"*Generated by SME AI Auditor | Trace ID: `{trace_id}`*")

        # ── WRITE TO DISK ────────────────────────────────────────────────────
        markdown_content = "\n".join(report)
        filepath = os.path.abspath(os.path.join(self.output_dir, filename))
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown_content)
        except Exception as e:
            logger.error("Failed to write markdown report", filepath=filepath, error=str(e))
            raise IOError(f"Could not write report to filesystem: {e}") from e

        logger.info("Markdown report successfully generated", output_file=filepath)
        return filepath
