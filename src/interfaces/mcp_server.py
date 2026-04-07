"""
mcp_server.py
-------------
The Agentic Interface Layer for the SME AI Auditor.
Exposes specialized compliance tools to Goose/Qwen via the Model Context Protocol (MCP).
"""

import os
import gc
import uuid
import structlog
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP

from src.parsers.docling_parser import DoclingParser
from src.analysis.ai_act_classifier import AIActClassifier
from src.analysis.data_act_checker import DataActChecker
from src.vectordb.qdrant_wrapper import QdrantClientWrapper
from src.retrieval.haystack_pipeline_builder import DocumentRetrievalPipeline
from src.web.audit_store import AuditSessionManager

logger = structlog.get_logger(__name__)

# Initialize MCP Server with SSE transport metadata as per senior architecture
mcp = FastMCP("SME AI Auditor")

# Shared State
session_manager = AuditSessionManager()

@mcp.tool()
async def heartbeat() -> Dict[str, str]:
    """
    Check if the SME AI Auditor's internal infrastructure is online.
    Returns:
        A status dictionary (online/offline) for the Memory Matrix (Qdrant).
    """
    qdrant = QdrantClientWrapper()
    is_online = qdrant.health_check()
    return {
        "status": "online" if is_online else "offline",
        "message": "Memory Matrix is ready." if is_online else "Maintenance Required: Qdrant unreachable."
    }

@mcp.tool()
async def ingest_sme_evidence(path: str) -> Dict[str, Any]:
    """
    High-fidelity ingestion of SME technical documents (PDF/DOCX) using Docling.
    
    Privacy Guard: This tool does NOT return raw text content to the agent.
    It returns a Summary Receipt and a local_audit_id for reference.
    
    Args:
        path: Path to the file or directory containing SME evidence.
    """
    audit_id = str(uuid.uuid4())
    logger.info("Goose initiated ingestion", path=path, audit_id=audit_id)
    
    parser = DoclingParser()
    
    try:
        if os.path.isdir(path):
            results = parser.parse_directory(path)
            extracted_text = "\n\n".join([r["content"] for r in results])
            processed_files = [r["metadata"]["file_name"] for r in results]
        else:
            result = parser.parse(path)
            extracted_text = result["content"]
            processed_files = [result["metadata"]["file_name"]]
            
        # Store raw text in local session store (survives memory reclamation)
        session_manager.save_session(audit_id, {
            "path": path,
            "extracted_text": extracted_text,
            "processed_files": processed_files
        })
        
        # Memory Reclamation (Crucial for 16GB limit)
        del parser
        gc.collect()
        
        return {
            "status": "success",
            "local_audit_id": audit_id,
            "processed_files": processed_files,
            "summary": f"Ingested {len(processed_files)} documents. Content stored in sovereign session cache."
        }
    except Exception as e:
        logger.error("Ingestion tool failed", error=str(e))
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def perform_dual_act_audit(local_audit_id: str, system_description: Optional[str] = None) -> Dict[str, Any]:
    """
    Runs an atomic, deterministic compliance audit against the EU AI Act and EU Data Act.
    
    Args:
        local_audit_id: The session ID returned by ingest_sme_evidence.
        system_description: Optional high-level summary if docs are missing or need context.
    """
    session = session_manager.get_session(local_audit_id)
    if not session:
        return {"status": "error", "message": "Invalid local_audit_id. Evidence must be ingested first."}
    
    full_context = session.get("extracted_text", "")
    if system_description:
        full_context = f"{system_description}\n\n{full_context}"
    
    logger.info("Goose initiated dual-act audit", audit_id=local_audit_id)
    
    # 1. Retrieval
    pipeline = DocumentRetrievalPipeline()
    ai_act_docs = pipeline.run_query(query=full_context, filters={"document_source": "eu_ai_act"}, top_k=10)
    
    # 2. AI Act Analysis (Mistral Reasoning)
    classifier = AIActClassifier()
    ai_act_report = classifier.analyze_system(system_description=full_context, context_docs=ai_act_docs)
    
    # 3. Data Act Analysis
    data_checker = DataActChecker(pipeline=pipeline)
    data_act_report = data_checker.evaluate_data_obligations(system_description=full_context)
    
    # 4. Memory Reclamation
    del pipeline
    gc.collect()
    
    return {
        "status": "complete",
        "risk_tier": ai_act_report.risk_level.value,
        "is_prohibited": ai_act_report.risk_level.value == "Prohibited",
        "ai_act_summary": ai_act_report.summary,
        "data_act_summary": data_act_report.get("summary"),
        "findings_count": len(ai_act_report.findings) if hasattr(ai_act_report, "findings") else 0
    }

@mcp.tool()
async def ask_legal_reference(query: str) -> List[Dict[str, Any]]:
    """
    Directly queries the Qdrant Vector Matrix for specific legal articles or transparency evidence.
    Use this to answer "Why" questions or fetch Article text for the user.
    
    Args:
        query: Specific regulatory query (e.g., "Article 5 prohibited practices").
    """
    pipeline = DocumentRetrievalPipeline()
    docs = pipeline.run_query(query=query, top_k=5)
    
    return [
        {
            "article": d.meta.get("article_number", "Unknown"),
            "section": d.meta.get("parent_section", "Unknown"),
            "content": d.content
        } for d in docs
    ]
