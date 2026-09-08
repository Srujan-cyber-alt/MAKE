"""Tests for Approval Gates."""

import pytest
from app.intelligence.agent.approval_gate import (
    ApprovalGate, ApprovalRequest, ApprovalState, ApprovalType
)


class TestApprovalGate:
    def test_create_approval_gate(self):
        gate = ApprovalGate()
        assert gate is not None

    def test_request_approval(self):
        gate = ApprovalGate()
        request = gate.request_approval(
            mission_id="mission_1",
            strategy={"action": "start"},
            reason="Need human sign-off",
        )
        assert request is not None
        assert request.state == ApprovalState.WAITING

    def test_approve_request(self):
        gate = ApprovalGate()
        request = gate.request_approval(
            mission_id="mission_1",
            strategy={"action": "start"},
            reason="Need human sign-off",
        )
        updated = gate.approve(request.id, approver="admin")
        assert updated.state == ApprovalState.APPROVED

    def test_reject_request(self):
        gate = ApprovalGate()
        request = gate.request_approval(
            mission_id="mission_1",
            strategy={"action": "start"},
            reason="Need human sign-off",
        )
        updated = gate.reject(request.id, approver="admin", reason="Not approved")
        assert updated.state == ApprovalState.REJECTED

    def test_approval_expiry(self):
        gate = ApprovalGate()
        request = gate.request_approval(
            mission_id="mission_1",
            strategy={"action": "start"},
            reason="Need human sign-off",
            timeout_seconds=0,
        )
        gate._process_expired()
        assert request.state == ApprovalState.EXPIRED

    def test_approval_type_values(self):
        assert ApprovalType.MISSION_APPROVAL.value == "mission_approval"
        assert ApprovalType.TASK_APPROVAL.value == "task_approval"

    def test_approval_state_values(self):
        assert ApprovalState.WAITING.value == "waiting"
        assert ApprovalState.APPROVED.value == "approved"
        assert ApprovalState.REJECTED.value == "rejected"
        assert ApprovalState.EXPIRED.value == "expired"
