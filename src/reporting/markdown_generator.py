"""
markdown_generator.py
---------------------
Aggregates structured compliance schemas (AI Act, Data Act, Gaps) and templates 
them into a professional, human-readable Markdown report for the SME.
"""

import os
from datetime import datetime, timezone
import structlog
from typing import Dict, Any

from src.analysis.schemas import AIActAuditReport, RemediationPlan

logger = structlog.get_logger(__name__)


class MarkdownGenerator:
    """
    Translates technical Pydantic findings into an SME-facing Markdown Report.
    """

    def __init__(self, output_dir: str = "outputs"):
        """
        Initialize the Markdown Generator.
        
        Args:
            output_dir: The directory where reports will be saved.
        """
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
            
        logger.info("MarkdownGenerator initialized", output_dir=self.output_dir)

    def generate(
        self, 
        ai_act_report: AIActAuditReport, 
        data_act_data: Dict[str, Any], 
        gap_plan: RemediationPlan,
        trace_id: str = None,
        filename: str = "compliance_report.md"
    ) -> str:
        """
        Produce a unified Markdown string and save it to disk.

        Args:
            ai_act_report: The AI Act Classification conclusions.
            data_act_data: The JSON dictionary from the DataActChecker.
            gap_plan: The RemediationPlan isolating blockers.
            filename: The target output markdown file.

        Returns:
            The absolute filepath to the generated report.
        """
        logger.info("Generating Markdown compliance report", system_name=ai_act_report.system_name)
        
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # 1. Header & Summary Section
        report = []
        report.append(f"# SME AI Auditor - Official Compliance Report")
        report.append(f"**System Evaluated:** {ai_act_report.system_name}")
        report.append(f"**Date:** {timestamp}")
        if trace_id:
            report.append(f"**Audit Trace ID:** `{trace_id}`")
        
        deployable_badge = "🟩 **DEPLOYABLE**" if gap_plan.is_deployable else "🟥 **BLOCKED (DO NOT DEPLOY)**"
        report.append(f"\n## Overall Deployment Status")
        report.append(f"{deployable_badge}")
        
        report.append(f"\n## Executive Summary")
        report.append(f"{ai_act_report.summary}")
        
        # 2. AI Act Findings
        report.append(f"\n## 1. EU AI Act Classification")
        report.append(f"**Assigned Risk Tier:** `{ai_act_report.risk_level.value}`")
        
        report.append("\n### Key Legal Triggers")
        for ref in ai_act_report.primary_articles:
            report.append(f"- **{ref.article}**: {ref.title} - *{ref.description}*")
            
        report.append("\n### Assessed Findings")
        for finding in ai_act_report.findings:
            icon = "✅" if finding.is_compliant else "❌"
            report.append(f"- {icon} **{finding.criterion}**: {finding.reasoning} *(Evidence: {finding.evidence})*")

        # 3. Data Act Findings
        report.append(f"\n## 2. EU Data Act Obligations")
        is_provider = "Yes" if data_act_data.get("is_data_provider") else "No"
        report.append(f"- **Data Provider Status:** {is_provider}")
        
        share_icon = "✅" if data_act_data.get("data_sharing_compliant") else "❌"
        report.append(f"- **Data Sharing Readiness:** {share_icon}")
        
        cloud_icon = "✅" if data_act_data.get("cloud_switching_compliant") else "❌"
        report.append(f"- **Cloud Switching Compliance:** {cloud_icon}")
        
        if data_act_data.get("summary"):
            report.append(f"\n*Data Act Summary*: {data_act_data.get('summary')}")

        # 4. Actionable Remediation Plan
        report.append(f"\n## 3. Mandatory Remediation Gaps")
        if not gap_plan.actions:
            report.append("> 🎉 No mandatory compliance gaps detected. System conforms to engineering standards.")
        else:
            report.append(f"> Below is the prioritized technical roadmap for compliance.")
            
            for action in gap_plan.actions:
                # Assign emoji by priority
                if action.priority.lower() == "high":
                    priority_emoji = "🚨"
                elif action.priority.lower() == "medium":
                    priority_emoji = "⚠️"
                else:
                    priority_emoji = "ℹ️"
                    
                report.append(f"\n### {priority_emoji} [{action.priority}] {action.missing_requirement}")
                report.append(f"- **Standard Reference:** `{action.reference_standard}`")
                report.append(f"- **Violation Context:** {action.violation_context}")
                
                if action.trace_id_reference:
                    report.append(f"- *Audit Trace ID:* `{action.trace_id_reference}`")
        
        # 5. Compile and Write
        markdown_content = "\n".join(report)
        
        filepath = os.path.abspath(os.path.join(self.output_dir, filename))
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
        except Exception as e:
            logger.error("Failed to write markdown report", filepath=filepath, error=str(e))
            raise IOError(f"Could not write report to filesystem: {e}") from e
            
        logger.info("Markdown report successfully generated", output_file=filepath)
        return filepath
