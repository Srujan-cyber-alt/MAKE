from typing import Any, Dict, Optional
from uuid import UUID
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class ExecutionResult:
    task_id: str
    status: ExecutionStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    attempts: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
