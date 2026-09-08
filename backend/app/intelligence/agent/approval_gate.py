from typing import Any, Dict, List, Optional, Callable
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import asyncio


class ApprovalAction(str, Enum):
    APPROVE = "approve"
    DENY = "deny"
    ESCALATE = "escalate"
    CONDITIONAL = "conditional"


class ApprovalState(str, Enum):
    WAITING = "waiting"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalType(str, Enum):
    MISSION_APPROVAL = "mission_approval"
    TASK_APPROVAL = "task_approval"
    STRATEGY_APPROVAL = "strategy_approval"
    EXECUTION_APPROVAL = "execution_approval"


@dataclass
class ApprovalRequest:
    id: UUID = field(default_factory=uuid4)
    mission_id: UUID = None
    task_id: Optional[str] = None
    state: ApprovalState = ApprovalState.WAITING
    approval_type: ApprovalType = ApprovalType.MISSION_APPROVAL
    request_data: Dict[str, Any] = field(default_factory=dict)
    response_data: Optional[Dict[str, Any]] = None
    requested_by: str = ""
    approved_by: Optional[str] = None
    reason: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class ApprovalGate:
    def __init__(self) -> None:
        self._requests: Dict[UUID, ApprovalRequest] = {}
        self._reviewers: Dict[str, Callable] = {}

    def register_reviewer(self, reviewer_id: str, reviewer_func: Callable) -> None:
        self._reviewers[reviewer_id] = reviewer_func

    async def request_approval(
        self,
        mission_id: UUID,
        strategy: Any,
        reason: str = "",
        timeout_seconds: Optional[float] = None,
    ) -> ApprovalRequest:
        request = ApprovalRequest(
            mission_id=mission_id,
            state=ApprovalState.WAITING,
            approval_type=ApprovalType.MISSION_APPROVAL,
            request_data=strategy if isinstance(strategy, dict) else {"strategy": str(strategy)},
            reason=reason,
            expires_at=datetime.utcnow() + timedelta(seconds=timeout_seconds) if timeout_seconds else None,
        )
        self._requests[request.id] = request
        return request

    async def approve(self, request_id: UUID, approver: str) -> ApprovalRequest:
        request = self._requests.get(request_id)
        if not request:
            raise ValueError("Approval request not found")
        if request.state == ApprovalState.EXPIRED:
            raise ValueError("Approval request expired")
        request.state = ApprovalState.APPROVED
        request.approved_by = approver
        request.updated_at = datetime.utcnow()
        return request

    async def reject(self, request_id: UUID, approver: str, reason: str = "") -> ApprovalRequest:
        request = self._requests.get(request_id)
        if not request:
            raise ValueError("Approval request not found")
        request.state = ApprovalState.REJECTED
        request.approved_by = approver
        request.reason = reason
        request.updated_at = datetime.utcnow()
        return request

    def get_request(self, request_id: UUID) -> Optional[ApprovalRequest]:
        return self._requests.get(request_id)

    def _process_expired(self) -> None:
        now = datetime.utcnow()
        for request in self._requests.values():
            if request.state == ApprovalState.WAITING and request.expires_at and now > request.expires_at:
                request.state = ApprovalState.EXPIRED
                request.updated_at = now
