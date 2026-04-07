"""
main.py (The Pilot / Executive Function)
-------
SME AI Auditor - Official Orchestration Pipeline.

Executes the End-to-End Coordination between the 'Brain' (Mistral AI) and the 
'Memory' (Qdrant) on a localized Ubuntu 16GB framework.
"""

import os
import sys
import uuid
import argparse
import gc
from datetime import datetime, timezone
import structlog

from langfuse import observe
from mistralai.client.sdk import Mistral

from src.parsers.docling_parser import DoclingParser
from src.vectordb.qdrant_wrapper import QdrantClientWrapper
from src.vectordb.index_manager import IndexManager
from src.retrieval.haystack_pipeline_builder import DocumentRetrievalPipeline
from src.analysis.ai_act_classifier import AIActClassifier
from src.analysis.data_act_checker import DataActChecker
from src.analysis.requirement_mapper import RequirementMapper
from src.analysis.gap_detector import GapDetector
from src.reporting.markdown_generator import MarkdownGenerator
from src.reporting.pdf_converter import PDFConverter
from src.observability.local_audit_logger import LocalAuditLogger

# Configure basic console logger
structlog.configure(
    processors=[structlog.processors.JSONRenderer()] if os.getenv("PROD") else [structlog.dev.ConsoleRenderer()]
)
logger = structlog.get_logger(__name__)


def verify_infrastructure(mistral_api_key: str):
    """
    Check-in Phase: Prevents wasted processing by ensuring API 'Brain' and 'Memory' are online.
    """
    logger.info("Initializing pre-flight infrastructure checks...")
    
    # 1. Mistral API Check
    try:
        if not mistral_api_key:
            raise ValueError("MISTRAL_API_KEY environment variable is missing.")
        client = Mistral(api_key=mistral_api_key)
        # Attempt a lightweight call to verify key validity
        client.models.list()
        logger.info("Mistral AI connectivity: ONLINE")
    except Exception as e:
        logger.error("Failed to connect to Mistral API. Aborting.", error=str(e))
        sys.exit(1)

    # 2. Qdrant Memory Check
    try:
        qdrant = QdrantClientWrapper()
        # Ensure collections exist or ping cluster
        qdrant.client.get_collections()
        logger.info("Qdrant Vector Database: ONLINE")
    except Exception as e:
        logger.error("Failed to connect to Qdrant Database. Aborting.", error=str(e))
        sys.exit(1)

        
@observe(name="sme_audit_execution", capture_input=False, capture_output=False)
def execute_audit(sme_docs_path: str, system_desc: str):
    """
    Core sequential orchestrator for the EU AI Act & Data Act compliance pipeline.
    Harden's as a 'Privacy Officer' by masking raw input data from cloud traces.
    """
    audit_trace_id = str(uuid.uuid4())
    logger.info("Initiating sequential audit pipeline", trace_id=audit_trace_id)
    
    # Forensic context for local encrypted storage
    full_forensic_context = {
        "system_desc_raw": system_desc,
        "sme_docs_path": sme_docs_path,
        "raw_ingested_text": ""
    }

    # ---------------------------------------------------------
    # START: Pre-flight Memory Verification (Regulatory Check)
    # ---------------------------------------------------------
    # IndexManager: Instantiates the "Memory" to confirm it exists and is ready
    index_mgr = IndexManager()
    logger.info("Memory Index Manager Verified: Collection is live.")
    del index_mgr 
    gc.collect()

    # ---------------------------------------------------------
    # 1. SME Context Ingestion Pipeline
    # ---------------------------------------------------------
    extracted_sme_text = system_desc
    if sme_docs_path and os.path.exists(sme_docs_path):
        logger.info("Ingesting SME technical documentation", path=sme_docs_path)
        parser = DoclingParser()
        docs = parser.parse_directory(sme_docs_path)
        extracted_sme_text += "\n\nExtracted SME Context:\n" + "\n".join([d["content"] for d in docs])
        logger.info("Docling ingestion complete", doc_count=len(docs))
        
        full_forensic_context["raw_ingested_text"] = extracted_sme_text
        
        del parser 
        gc.collect()

    # ---------------------------------------------------------
    # 2. EU Context Retrieval
    # ---------------------------------------------------------
    logger.info("Retrieving localized EU Regulatory Context")
    pipeline = DocumentRetrievalPipeline()
    
    ai_act_documents = pipeline.run_query(
        query=extracted_sme_text, 
        filters={"document_source": "eu_ai_act"}, 
        top_k=10  # Context Guard: Narrow retrieval
    )

    # ---------------------------------------------------------
    # 3. Mistral Dual-Act Reasoning Engines
    # ---------------------------------------------------------
    logger.info("Engaging Mistral AI Reasoners")
    
    ai_classifier = AIActClassifier()
    ai_act_report = ai_classifier.analyze_system(
        system_description=extracted_sme_text, 
        context_docs=ai_act_documents
    )
    
    data_checker = DataActChecker(pipeline=pipeline)
    data_act_report = data_checker.evaluate_data_obligations(
        system_description=extracted_sme_text
    )
    
    del pipeline
    gc.collect()

    # ---------------------------------------------------------
    # 4. Standards Mapping & Gap Detection
    # ---------------------------------------------------------
    logger.info("Executing Gap Detection and Engineering Mapping")
    
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

    # ---------------------------------------------------------
    # 5. Reporting Generation (MD -> PDF)
    # ---------------------------------------------------------
    logger.info("Building Immutable Reports")
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base_filename = f"audit_report_{timestamp}_{audit_trace_id[:8]}"
    
    md_gen = MarkdownGenerator(output_dir="reports")
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
        output_pdf_path=f"reports/{base_filename}.pdf"
    )

    # ---------------------------------------------------------
    # 6. LOCAL FORENSIC AUDIT SAVE (Encrypted)
    # ---------------------------------------------------------
    logger.info("Saving Encrypted Forensic Audit Trail locally")
    forensic_logger = LocalAuditLogger()
    
    # Store complete metadata and results for local forensic inspection
    full_forensic_context["ai_act_report"] = ai_act_report.model_dump()
    full_forensic_context["data_act_report"] = data_act_report
    full_forensic_context["remediation_plan"] = remediation_plan.model_dump()
    
    audit_file = forensic_logger.save_trace(
        trace_id=audit_trace_id, 
        data=full_forensic_context
    )
    
    logger.info("Audit Pipeline Complete!", report_url=pdf_filepath, forensic_audit=audit_file)


def main():
    parser = argparse.ArgumentParser(description="SME AI Auditor CLI Orchestrator")
    parser.add_argument("--docs", type=str, help="Path to SME documents folder.", default="")
    parser.add_argument("--system", type=str, help="Raw system description.", required=True)
    args = parser.parse_args()

    mistral_key = os.getenv("MISTRAL_API_KEY")

    verify_infrastructure(mistral_key)

    execute_audit(sme_docs_path=args.docs, system_desc=args.system)


if __name__ == "__main__":
    main()
