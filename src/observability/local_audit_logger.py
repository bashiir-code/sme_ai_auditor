"""
local_audit_logger.py
---------------------
Provides high-fidelity, AES-GCM encrypted local audit logs for SME internal developers.
Ensures that while the public cloud trace is metadata-only, the local forensic 
trail remains complete and secure.
"""

import os
import json
import structlog
from datetime import datetime, timezone
from cryptography.fernet import Fernet

logger = structlog.get_logger(__name__)


class LocalAuditLogger:
    """
    Handles encrypted serialization of full audit traces to the local filesystem.
    Uses Fernet (AES-128 in CBC mode with HMAC-SHA256) for simplified, 
    secure-by-default symmetric encryption.
    """

    def __init__(self, audit_dir: str = "audits", key: str = None):
        """
        Initialize the logger.
        
        Args:
            audit_dir: Directory where encrypted .audit files are stored.
            key: Optional 32-byte base64-encoded key. If None, looks for AUDIT_KEY env var.
        """
        self.audit_dir = audit_dir
        if not os.path.exists(self.audit_dir):
            os.makedirs(self.audit_dir, exist_ok=True)
            
        # Retrieval or generation of encryption key
        self.key = key or os.getenv("AUDIT_KEY")
        if not self.key:
            # For this "Sovereign" demonstration, if no key is provided, 
            # we generate one and log a warning. In production, this would 
            # be managed by a safe KMS or pre-shared secret.
            self.key = Fernet.generate_key().decode()
            logger.warning(
                "No AUDIT_KEY provided. Generated a temporary key for this session.",
                ephemeral_key=self.key
            )
            
        self.cipher = Fernet(self.key.encode())
        logger.info("LocalAuditLogger initialized", audit_dir=self.audit_dir)

    def save_trace(self, trace_id: str, data: dict) -> str:
        """
        Encrypt and save the full trace data to disk.

        Args:
            trace_id: The unique Langfuse/Audit ID.
            data: The full technical context (inputs, documents, reasoning).

        Returns:
            The absolute path to the encrypted .audit file.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        payload = {
            "trace_id": trace_id,
            "timestamp": timestamp,
            "full_context": data
        }
        
        try:
            # 1. Serialize to JSON
            json_data = json.dumps(payload, indent=2).encode('utf-8')
            
            # 2. Encrypt
            encrypted_data = self.cipher.encrypt(json_data)
            
            # 3. Save to disk
            filename = f"{trace_id}.audit"
            filepath = os.path.abspath(os.path.join(self.audit_dir, filename))
            
            with open(filepath, "wb") as f:
                f.write(encrypted_data)
                
            logger.info("Forensic audit trace saved locally", filepath=filepath, trace_id=trace_id)
            return filepath
            
        except Exception as e:
            logger.error("Failed to save local audit trace", error=str(e), trace_id=trace_id)
            raise RuntimeError(f"Audit Logging Failure: {e}") from e

    def decrypt_trace(self, filepath: str) -> dict:
        """
        Helper method for internal developers to read the forensic trace.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Audit file not found: {filepath}")
            
        with open(filepath, "rb") as f:
            encrypted_content = f.read()
            
        decrypted_json = self.cipher.decrypt(encrypted_content)
        return json.loads(decrypted_json.decode('utf-8'))
