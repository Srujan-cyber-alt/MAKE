"""
Approval Gates for MAKE AI Video Phase 18.

Structured approval workflow for productions.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class ApprovalGate:
    @staticmethod
    def create_gate(production_id: str, stage: str, required: bool = True) -> Dict[str, Any]:
        return {
            "gate_id": str(uuid.uuid4()),
            "production_id": production_id,
            "stage": stage,
            "status": "pending",
            "required": required,
            "created_at": datetime.utcnow().isoformat(),
            "decided_at": None,
            "decided_by": None,
            "notes": None,
        }

    @staticmethod
    def approve(gate: Dict[str, Any], user_id: str, notes: str = None) -> Dict[str, Any]:
        gate["status"] = "approved"
        gate["decided_at"] = datetime.utcnow().isoformat()
        gate["decided_by"] = user_id
        gate["notes"] = notes
        return gate

    @staticmethod
    def reject(gate: Dict[str, Any], user_id: str, notes: str = None) -> Dict[str, Any]:
        gate["status"] = "rejected"
        gate["decided_at"] = datetime.utcnow().isoformat()
        gate["decided_by"] = user_id
        gate["notes"] = notes
        return gate

    @staticmethod
    def get_required_gates(goal: str) -> List[str]:
        return [
            "brief",
            "story",
            "storyboard",
            "generation",
            "edit",
            "audio",
            "color",
            "qc",
            "final",
        ]


approval_gate = ApprovalGate()
