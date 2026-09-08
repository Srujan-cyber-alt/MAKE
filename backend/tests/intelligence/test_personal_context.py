"""Tests for Personal Context (consent-gated)."""

import pytest

from app.intelligence.core.personal_context import PersonalContext
from app.intelligence.schemas import PersonalContextStatus


class TestPersonalContext:
    @pytest.fixture
    def ctx(self, intel_db):
        return PersonalContext()

    @pytest.mark.asyncio
    async def test_store_requires_approval_by_default(self, ctx):
        record = await ctx.store_context("name", {"value": "Alice"})
        assert record.status == PersonalContextStatus.PENDING_APPROVAL

    @pytest.mark.asyncio
    async def test_auto_approve_non_sensitive(self, ctx):
        record = await ctx.store_context("theme", {"dark": True}, auto_approve=True)
        assert record.status == PersonalContextStatus.APPROVED

    @pytest.mark.asyncio
    async def test_approve_context(self, ctx):
        record = await ctx.store_context("full_name", {"value": "Alice Smith"})
        assert record.status == PersonalContextStatus.PENDING_APPROVAL
        approved = await ctx.approve_context(record.id, "user")
        assert approved.status == PersonalContextStatus.APPROVED
        assert approved.approved_at is not None
        assert approved.approved_by == "user"

    @pytest.mark.asyncio
    async def test_reject_context(self, ctx):
        record = await ctx.store_context("phone", {"value": "555-1234"})
        rejected = await ctx.reject_context(record.id)
        assert rejected.status == PersonalContextStatus.REJECTED

    @pytest.mark.asyncio
    async def test_get_approved(self, ctx):
        await ctx.store_context("setting", {"dark": True}, auto_approve=True)
        await ctx.store_context("name", {"value": "Alice"})  # pending
        approved = await ctx.get_approved()
        assert len(approved) == 1

    @pytest.mark.asyncio
    async def test_get_pending(self, ctx):
        await ctx.store_context("name", {"value": "Alice"})
        pending = await ctx.get_pending()
        assert len(pending) == 1
        assert pending[0].status == PersonalContextStatus.PENDING_APPROVAL

    @pytest.mark.asyncio
    async def test_rejected_not_in_approved(self, ctx):
        record = await ctx.store_context("secret", {"value": "data"})
        await ctx.reject_context(record.id)
        approved = await ctx.get_approved()
        assert all(r.status == PersonalContextStatus.APPROVED for r in approved)
        assert len(approved) == 0

    @pytest.mark.asyncio
    async def test_scope_isolation(self, ctx):
        await ctx.store_context("key1", {"v": 1}, scope="user_a", auto_approve=True)
        await ctx.store_context("key1", {"v": 2}, scope="user_b", auto_approve=True)
        a = await ctx.get_approved(scope="user_a")
        b = await ctx.get_approved(scope="user_b")
        assert len(a) == 1 and a[0].data["v"] == 1
        assert len(b) == 1 and b[0].data["v"] == 2

    @pytest.mark.asyncio
    async def test_approve_nonexistent(self, ctx):
        result = await ctx.approve_context("nonexistent", "user")
        assert result is None
