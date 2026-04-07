"""
app.py
------
The Web Pilot for the SME AI Auditor. 
FastAPI + Jinja2 + HTMX implementation for Finnish Industrial Compliance.
"""

import os
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, UploadFile, File, BackgroundTasks

# Initialize Environment
load_dotenv()
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Dict
import structlog

from src.core.orchestrator import AuditorOrchestrator
from src.vectordb.qdrant_wrapper import QdrantClientWrapper
from src.web.audit_store import AuditSessionManager
from src.interfaces.mcp_server import mcp
from mistralai.client.sdk import Mistral

logger = structlog.get_logger(__name__)

app = FastAPI(title="SME AI Auditor - Compliance Pilot")

# Mount MCP Server (SSE Transport)
app.mount("/mcp", mcp.sse_app)

# Ensure required directories exist
os.makedirs("reports", exist_ok=True)
os.makedirs("uploads", exist_ok=True)

# Mount reports for direct download
app.mount("/reports", StaticFiles(directory="reports"), name="reports")

# Setup templates
templates = Jinja2Templates(directory="src/web/templates")

# Pilot Instance
orchestrator = AuditorOrchestrator()

# Session Manager (JSON-backed persistence)
session_manager = AuditSessionManager()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main Pilot Deck Dashboard."""
    return templates.TemplateResponse(
        request=request, 
        name="dashboard.html", 
        context={}
    )


@app.get("/health", response_class=HTMLResponse)
async def health(request: Request):
    """Return HTMX partials for Memory and Reasoning health."""
    # 1. Mistral Check
    mistral_status = "online"
    try:
        client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
        # Using a lightweight call to check connectivity
        client.models.list()
    except Exception as e:
        logger.warning("Mistral health check failed", error=str(e))
        mistral_status = "offline"

    # 2. Qdrant Check
    qdrant_status = "online"
    try:
        qdrant = QdrantClientWrapper()
        if not qdrant.health_check():
            qdrant_status = "offline"
    except Exception as e:
        logger.warning("Qdrant health check failed", error=str(e))
        qdrant_status = "offline"

    return templates.TemplateResponse(
        request=request,
        name="partials/health_status.html", 
        context={
            "mistral_status": mistral_status, 
            "qdrant_status": qdrant_status
        }
    )


@app.get("/audit/stream/{audit_id}")
async def stream_audit_endpoint(audit_id: str):
    """
    SSE endpoint that streams the audit progress using stored parameters.
    """
    params = session_manager.get_session(audit_id)
    if not params:
        from fastapi import Response
        # Return 204 No Content. This natively instructs the browser's EventSource
        # to stop attempting to reconnect after the stream completes and the 
        # session is deleted in the finally block.
        return Response(status_code=204)

    async def event_generator():
        try:
            async for status in orchestrator.stream_audit(
                system_desc=params["system_description"], 
                sme_docs_path=params["sme_docs_path"]
            ):
                yield f"data: {status}\n\n"
        finally:
            # Persistent cleanup (Survives server restarts during the run)
            session_manager.delete_session(audit_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/audit/run", response_class=HTMLResponse)
async def start_audit_trigger(
    request: Request,
    system_description: str = Form(...),
    docs: List[UploadFile] = File(None)
):
    """
    Triggers the UI to connect to the SSE stream.
    """
    audit_id = str(uuid.uuid4())
    
    # 1. Handle File Uploads (Save to temp folder)
    temp_docs_dir = os.path.join("uploads", audit_id)
    os.makedirs(temp_docs_dir, exist_ok=True)
    
    saved_paths = []
    if docs:
        for doc in docs:
            if doc.filename:
                file_path = os.path.join(temp_docs_dir, doc.filename)
                with open(file_path, "wb") as f:
                    content = await doc.read()
                    f.write(content)
                saved_paths.append(file_path)

    # 2. Store parameters for the SSE stream persistently
    session_manager.save_session(audit_id, {
        "system_description": system_description,
        "sme_docs_path": temp_docs_dir if saved_paths else ""
    })

    # Trigger HTMX to connect to the SSE stream with the audit_id
    return f"""
    <div hx-ext="sse" sse-connect="/audit/stream/{audit_id}" sse-swap="message" hx-target="#audit-console" hx-swap="beforeend">
        <div class="text-blue-500 font-mono text-sm animate-pulse">Establishing Secure Pilot Link...</div>
    </div>
    """
