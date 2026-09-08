"""User-approved Personal Context.

Sensitive personal information is never stored without explicit,
product-level approval. Each context entry has a status lifecycle:
    PENDING_APPROVAL → APPROVED | REJECTED
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import select, delete

from app.intelligence.schemas import PersonalContextRecord, PersonalContextStatus
from app.intelligence.models import PersonalContextOrm


class PersonalContext:
    """Manages user-approved personal context entries."""

    def _session(self):
        from app.intelligence.database import get_session_factory
        return get_session_factory()

    async def store_context(
        self,
        key: str,
        data: Dict[str, Any],
        scope: str = "default",
        auto_approve: bool = False,
        approved_by: Optional[str] = None,
    ) -> PersonalContextRecord:
        """Store a personal context entry.

        Unless ``auto_approve`` is True (for non-sensitive data), the entry
        starts in PENDING_APPROVAL and must be explicitly approved.
        """
        status = PersonalContextStatus.APPROVED if auto_approve else PersonalContextStatus.PENDING_APPROVAL
        async with self._session()() as session:
            orm = PersonalContextOrm(
                key=key,
                scope=scope,
                data=data,
                status=status,
                approved_at=datetime.utcnow() if auto_approve else None,
                approved_by=approved_by,
            )
            session.add(orm)
            await session.commit()
            await session.refresh(orm)
        return self._to_record(orm)

    async def approve_context(self, entry_id: str, approved_by: str) -> Optional[PersonalContextRecord]:
        async with self._session()() as session:
            orm = await session.get(PersonalContextOrm, entry_id)
            if orm is None:
                return None
            orm.status = PersonalContextStatus.APPROVED
            orm.approved_at = datetime.utcnow()
            orm.approved_by = approved_by
            orm.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(orm)
        return self._to_record(orm)

    async def reject_context(self, entry_id: str, reason: Optional[str] = None) -> Optional[PersonalContextRecord]:
        async with self._session()() as session:
            orm = await session.get(PersonalContextOrm, entry_id)
            if orm is None:
                return None
            orm.status = PersonalContextStatus.REJECTED
            orm.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(orm)
        return self._to_record(orm)

    async def get_approved(
        self,
        scope: str = "default",
        key: Optional[str] = None,
    ) -> List[PersonalContextRecord]:
        async with self._session()() as session:
            stmt = select(PersonalContextOrm).where(
                PersonalContextOrm.status == PersonalContextStatus.APPROVED,
                PersonalContextOrm.scope == scope,
            )
            if key:
                stmt = stmt.where(PersonalContextOrm.key == key)
            stmt = stmt.order_by(PersonalContextOrm.created_at.desc())
            result = await session.execute(stmt)
            rows = result.scalars().all()
        return [self._to_record(r) for r in rows]

    async def get_pending(self, scope: str = "default") -> List[PersonalContextRecord]:
        async with self._session()() as session:
            stmt = select(PersonalContextOrm).where(
                PersonalContextOrm.status == PersonalContextStatus.PENDING_APPROVAL,
                PersonalContextOrm.scope == scope,
            ).order_by(PersonalContextOrm.created_at.desc())
            result = await session.execute(stmt)
            rows = result.scalars().all()
        return [self._to_record(r) for r in rows]

    async def get_all(self, scope: str = "default") -> List[PersonalContextRecord]:
        async with self._session()() as session:
            stmt = select(PersonalContextOrm).where(
                PersonalContextOrm.scope == scope
            ).order_by(PersonalContextOrm.created_at.desc())
            result = await session.execute(stmt)
            rows = result.scalars().all()
        return [self._to_record(r) for r in rows]

    async def clear_all(self, scope: str = "default") -> int:
        async with self._session()() as session:
            result = await session.execute(
                delete(PersonalContextOrm).where(PersonalContextOrm.scope == scope)
            )
            await session.commit()
            return result.rowcount

    @staticmethod
    def _to_record(orm: PersonalContextOrm) -> PersonalContextRecord:
        return PersonalContextRecord(
            id=orm.id,
            key=orm.key,
            scope=orm.scope,
            data=orm.data,
            status=orm.status,
            approved_at=orm.approved_at,
            approved_by=orm.approved_by,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
