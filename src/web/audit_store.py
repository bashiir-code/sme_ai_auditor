"""
audit_store.py
--------------
Persistent session storage for SME AI Auditor Pilot.
Ensures audits survive uvicorn reloads by backing up to JSON.
"""

import os
import json
import structlog
from typing import Dict, Any, Optional

logger = structlog.get_logger(__name__)

class AuditSessionManager:
    """
    Manages audit metadata (system descriptions, file paths) persistently.
    """
    def __init__(self, storage_path: str = "uploads/sessions.json"):
        self.storage_path = storage_path
        self._ensure_storage()
        
    def _ensure_storage(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if not os.path.exists(self.storage_path):
            with open(self.storage_path, "w") as f:
                json.dump({}, f)

    def _read(self) -> Dict[str, Any]:
        try:
            with open(self.storage_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to read audit sessions", error=str(e))
            return {}

    def _write(self, data: Dict[str, Any]):
        try:
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save audit sessions", error=str(e))

    def save_session(self, audit_id: str, params: Dict[str, Any]):
        """Persist a new audit session."""
        data = self._read()
        data[audit_id] = params
        self._write(data)
        logger.info("Audit session saved", audit_id=audit_id)

    def get_session(self, audit_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an existing audit session."""
        data = self._read()
        return data.get(audit_id)

    def delete_session(self, audit_id: str):
        """Cleanup a session after stream completion."""
        data = self._read()
        if audit_id in data:
            del data[audit_id]
            self._write(data)
            logger.info("Audit session finalized", audit_id=audit_id)
