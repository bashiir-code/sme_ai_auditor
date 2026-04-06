"""
orchestrator.py
---------------
The 'Pilot' Executive Function: Decoupled from the CLI for multi-interface support.
Provides an async generator for real-time audit status streaming.
"""

import os
import uuid
import gc
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Any, List
import structlog

from langfuse import observe
from src.parsers.docling_parser import DoclingParser
from src.vectordb.qdrant_client import QdrantClientWrapper
from src.vectordb.index_manager import IndexManager
from src.retrieval.haystack_pipeline_builder import DocumentRetrievalPipeline
from src.analysis.ai_act_classifier import AIActClassifier
from src.analysis.data_act_checker import DataActChecker
from src.analysis.requirement_mapper import RequirementMapper
from src.analysis.gap_detector import GapDetector
from src.reporting.markdown_generator import MarkdownGenerator
from src.reporting.pdf_converter import PDFConverter
from src.observability.local_audit_logger import LocalAuditLogger

logger = structlog.get_logger(__name__)


class AuditorOrchestrator:
    """
    Stateful orchestrator that manages the lifecycle of a single compliance audit.
    """

    def __init__(self, output_dir: str = "reports", audit_dir: str = "audits"):
        self.output_dir = output_dir
        self.audit_dir = audit_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
            
        logger.info("AuditorOrchestrator initialized", output_dir=output_dir)

    async def stream_audit(self, system_desc: str, sme_docs_path: str = "") -> AsyncGenerator[str, None]:
        """
        Executes the audit pipeline and yields status updates as HTML fragments for HTMX.
        """
        audit_trace_id = str(uuid.uuid4())
        yield self._fmt_status("Initiating Pilot System...", "info", audit_trace_id)

        # Forensic context for local encrypted storage
        full_forensic_context = {
            "system_desc_raw": system_desc,
            "sme_docs_path": sme_docs_path,
            "raw_ingested_text": ""
        }

        # ---------------------------------------------------------
        # Phase 0: Pre-flight Memory Verification
        # ---------------------------------------------------------
        yield self._fmt_status("Verifying Local Memory (Qdrant)...", "info")
        try:
            index_mgr = IndexManager()
            del index_mgr
            gc.collect()
            yield self._fmt_status("Memory Matrix: ONLINE", "success")
        except Exception as e:
            yield self._fmt_status(f"Memory Matrix ERROR: {e}", "error")
            return

        # ---------------------------------------------------------
        # Phase 1: Ingestion
        # ---------------------------------------------------------
        extracted_sme_text = system_desc
        if sme_docs_path and os.path.exists(sme_docs_path):
            yield self._fmt_status("Ingesting SME technical documentation via Docling...", "info")
            try:
                parser = DoclingParser()
                docs = parser.parse_directory(sme_docs_path)
                extracted_sme_text += "\n\nExtracted SME Context:\n" + "\n".join([d["content"] for d in docs])
                full_forensic_context["raw_ingested_text"] = extracted_sme_text
                del parser
                gc.collect()
                yield self._fmt_status(f"Ingestion Complete: {len(docs)} documents parsed.", "success")
            except Exception as e:
                yield self._fmt_status(f"Ingestion ERROR: {e}", "error")
                return

        # ---------------------------------------------------------
        # Phase 2: Retrieval
        # ---------------------------------------------------------
        yield self._fmt_status("Retrieving localized EU Regulatory Context (AI Act)...", "info")
        pipeline = DocumentRetrievalPipeline()
        ai_act_documents = pipeline.run_query(
            query=extracted_sme_text, 
            filters={"document_source": "eu_ai_act"}, 
            top_k=10
        )
        yield self._fmt_status(f"Retrieved {len(ai_act_documents)} relevant legal provisions.", "success")

        # ---------------------------------------------------------
        # Phase 3: Reasoning
        # ---------------------------------------------------------
        yield self._fmt_status("Engaging Mistral 'Brain' for AI Act Classification...", "info")
        ai_classifier = AIActClassifier()
        ai_act_report = ai_classifier.analyze_system(
            system_description=extracted_sme_text, 
            context_docs=ai_act_documents
        )
        yield self._fmt_status(f"Risk Tier Identified: <b>{ai_act_report.risk_level.value}</b>", "success")

        yield self._fmt_status("Evaluating Data Act Obligations...", "info")
        data_checker = DataActChecker(pipeline=pipeline)
        data_act_report = data_checker.evaluate_data_obligations(
            system_description=extracted_sme_text
        )
        yield self._fmt_status("Data Act Analysis Complete.", "success")

        del pipeline
        gc.collect()

        # ---------------------------------------------------------
        # Phase 4: Gap Detection
        # ---------------------------------------------------------
        yield self._fmt_status("Calculating Compliance Gaps vs. CEN/CENELEC Standards...", "info")
        mapper = RequirementMapper()
        mandatory_standards = mapper.map_requirements(risk_level=ai_act_report.risk_level)
        
        detector = GapDetector()
        remediation_plan = detector.generate_plan(
            ai_act_report=ai_act_report,
            data_act_data=data_act_report,
            mapped_requirements=mandatory_standards
        )

        for action in remediation_plan.actions:
            action.trace_id_reference = audit_trace_id
            
        yield self._fmt_status(f"Detected <b>{len(remediation_plan.actions)}</b> remediation blockers.", "warning" if remediation_plan.actions else "success")

        # ---------------------------------------------------------
        # Phase 5: Reporting
        # ---------------------------------------------------------
        yield self._fmt_status("Generating Immutable A4 Audit Proof...", "info")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base_filename = f"audit_report_{timestamp}_{audit_trace_id[:8]}"
        
        md_gen = MarkdownGenerator(output_dir=self.output_dir)
        md_filepath = md_gen.generate(
            ai_act_report=ai_act_report,
            data_act_data=data_act_report,
            gap_plan=remediation_plan,
            trace_id=audit_trace_id,
            filename=f"{base_filename}.md"
        )
        
        pdf_conv = PDFConverter()
        pdf_filepath = pdf_conv.convert_markdown_to_pdf(
            md_filepath=md_filepath,
            output_pdf_path=os.path.join(self.output_dir, f"{base_filename}.pdf")
        )

        # ---------------------------------------------------------
        # Phase 6: Forensic Logging
        # ---------------------------------------------------------
        yield self._fmt_status("Securing Local Forensic Trail (Encrypted)...", "info")
        forensic_logger = LocalAuditLogger(audit_dir=self.audit_dir)
        full_forensic_context["ai_act_report"] = ai_act_report.model_dump()
        full_forensic_context["data_act_report"] = data_act_report
        full_forensic_context["remediation_plan"] = remediation_plan.model_dump()
        
        audit_file = forensic_logger.save_trace(trace_id=audit_trace_id, data=full_forensic_context)
        
        yield self._fmt_status(
            f"Audit Complete. <a href='/reports/{base_filename}.pdf' target='_blank' class='text-blue-400 underline'>Download PDF Report</a>", 
            "success"
        )

    def _fmt_status(self, message: str, level: str, trace_id: str = None) -> str:
        """Helper to format partial HTML for HTMX updates."""
        icon = {
            "info": "🔵",
            "success": "🟢",
            "warning": "🟡",
            "error": "🔴"
        }.get(level, "⚪")
        
        trace_blob = f"<span class='text-xs text-gray-500'>[ID: {trace_id[:8]}]</span> " if trace_id else ""
        return f"<div class='mb-2 p-2 border-l-2 border-gray-700 bg-gray-800/30 font-mono text-sm'>{icon} {trace_blob}{message}</div>"
