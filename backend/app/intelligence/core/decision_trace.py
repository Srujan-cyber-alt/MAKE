"""Decision Trace — persistent log of every reasoning decision.

Every decision is stored with full provenance (job_id, step, reasoning,
timestamp) so the full audit trail can be reconstructed.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import select, delete

from app.intelligence.database import get_db
from app.intelligence.models import DecisionRecordOrm
from app.intelligence.schemas import DecisionRecord


class DecisionTrace:
    """Records and retrieves decision records tied to jobs/intents."""

    def __init__(self) -> None:
        self._session_factory = None

    def _get_session(self):
        from app.intelligence.database import get_session_factory
        return get_session_factory()

    async def record(
        self,
        step: str,
        decision: str,
        reasoning: str,
        job_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> DecisionRecord:
        ts = timestamp or datetime.utcnow()
        async with self._get_session()() as session:
            orm = DecisionRecordOrm(
                job_id=job_id,
                step=step,
                decision=decision,
                reasoning=reasoning,
                details=details or {},
                timestamp=ts,
            )
            session.add(orm)
            await session.commit()
            await session.refresh(orm)

        return DecisionRecord(
            id=orm.id,
            job_id=orm.job_id,
            step=orm.step,
            decision=orm.decision,
            reasoning=orm.reasoning,
            timestamp=orm.timestamp,
            details=orm.details,
        )

    async def get_for_job(self, job_id: str) -> List[DecisionRecord]:
        async with self._get_session()() as session:
            result = await session.execute(
                select(DecisionRecordOrm)
                .where(DecisionRecordOrm.job_id == job_id)
                .order_by(DecisionRecordOrm.timestamp.asc())
            )
            rows = result.scalars().all()
        return [self._to_record(r) for r in rows]

    async def get_all(self, limit: int = 1000) -> List[DecisionRecord]:
        async with self._get_session()() as session:
            result = await session.execute(
                select(DecisionRecordOrm).order_by(DecisionRecordOrm.timestamp.desc()).limit(limit)
            )
            rows = result.scalars().all()
        return [self._to_record(r) for r in rows]

    async def clear_job(self, job_id: str) -> int:
        async with self._get_session()() as session:
            result = await session.execute(delete(DecisionRecordOrm).where(DecisionRecordOrm.job_id == job_id))
            await session.commit()
            return result.rowcount

    @staticmethod
    def _to_record(orm: DecisionRecordOrm) -> DecisionRecord:
        return DecisionRecord(
            id=orm.id,
            job_id=orm.job_id,
            step=orm.step,
            decision=orm.decision,
            reasoning=orm.reasoning,
            timestamp=orm.timestamp,
            details=orm.details,
        )
