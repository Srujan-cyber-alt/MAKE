"""
Provider Credential Manager for MAKE AI Video Phase 16.

Secure credential handling. Never exposes secrets to frontend or logs.
"""

from typing import Optional, Dict, List, Any
import os
import logging

logger = logging.getLogger(__name__)


class ProviderCredentialManager:
    def __init__(self):
        self._credentials: Dict[str, Dict[str, Any]] = {}

    def get_credential_status(self, provider_id: str) -> Dict[str, Any]:
        api_key = os.getenv(f"{provider_id.upper()}_API_KEY")
        if not api_key:
            return {"status": "not_configured", "message": "API key not configured"}
        return {"status": "configured", "message": "Credentials configured"}

    def validate_credentials(self, provider_id: str) -> Dict[str, Any]:
        status = self.get_credential_status(provider_id)
        if status["status"] == "not_configured":
            return {"valid": False, "status": "not_configured"}
        return {"valid": True, "status": "configured"}

    def get_provider_config(self, provider_id: str) -> Dict[str, Any]:
        return {
            "status": self.get_credential_status(provider_id)["status"],
            "api_base": os.getenv(f"{provider_id.upper()}_API_BASE", ""),
        }

    def redact_secrets(self, data: Dict[str, Any]) -> Dict[str, Any]:
        sensitive_keys = ["api_key", "api_key_encrypted", "secret", "password", "token", "credential"]
        redacted = dict(data)
        for key in list(redacted.keys()):
            if any(s in key.lower() for s in sensitive_keys):
                redacted[key] = "***REDACTED***"
        return redacted


provider_credential_manager = ProviderCredentialManager()
