import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.intelligence import router as news_router


@pytest.mark.parametrize("activity_kind", [None, "POST", "REPOST"])
def test_company_feed_filters_source_and_activity_before_limit(activity_kind):
    statements = []
    source_id = uuid4()

    class FakeDB:
        async def execute(self, query):
            statements.append(query)
            return SimpleNamespace(all=lambda: [])

    asyncio.run(news_router.list_items(db=FakeDB(), user=SimpleNamespace(id=uuid4()),
                                      source_id=source_id, activity_kind=activity_kind))
    compiled = statements[-1].compile(dialect=postgresql.dialect())
    query = str(compiled)
    assert "intelligence_sources.id =" in query
    assert source_id in compiled.params.values()
    assert query.index("WHERE") < query.index("LIMIT")
    if activity_kind:
        assert "linkedin_data" in query
        assert "LINKEDIN" in compiled.params.values()
        assert "REPOST" in compiled.params.values() if activity_kind == "REPOST" else ["POST", "ARTICLE"] in compiled.params.values()


def test_company_refresh_schedules_only_the_selected_source(monkeypatch):
    source_id = uuid4()
    statements = []
    checked = []

    class FakeDB:
        async def execute(self, query):
            statements.append(query)
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [
                SimpleNamespace(id=source_id, type="LINKEDIN")
            ]))

    async def fake_checks(ids):
        checked.extend(ids)

    monkeypatch.setattr(news_router, "_check_all_task", None)
    monkeypatch.setattr(news_router, "_check_all_sources", fake_checks)
    monkeypatch.setattr(news_router, "linkedin_configured", lambda: True)

    async def run():
        result = await news_router.check_all_sources_now(db=FakeDB(), _=None, source_id=source_id)
        await news_router._check_all_task
        assert result["total"] == 1

    asyncio.run(run())
    compiled = statements[0].compile(dialect=postgresql.dialect())
    assert "intelligence_sources.id =" in str(compiled)
    assert source_id in compiled.params.values()
    assert checked == [source_id]


def test_combined_company_feed_applies_both_sources_before_limit():
    statements = []
    ids = [uuid4(), uuid4()]

    class FakeDB:
        async def execute(self, query):
            statements.append(query)
            return SimpleNamespace(all=lambda: [])

    asyncio.run(news_router.list_items(db=FakeDB(), user=SimpleNamespace(id=uuid4()), source_ids=ids))
    compiled = statements[-1].compile(dialect=postgresql.dialect())
    assert "intelligence_sources.id IN" in str(compiled)
    assert ids in compiled.params.values()
    assert str(compiled).index("WHERE") < str(compiled).index("LIMIT")


def test_combined_company_refresh_schedules_only_requested_sources(monkeypatch):
    ids = [uuid4(), uuid4()]
    statements = []
    checked = []

    class FakeDB:
        async def execute(self, query):
            statements.append(query)
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [
                SimpleNamespace(id=source_id, type="LINKEDIN") for source_id in ids
            ]))

    async def fake_checks(source_ids):
        checked.extend(source_ids)

    monkeypatch.setattr(news_router, "_check_all_task", None)
    monkeypatch.setattr(news_router, "_check_all_sources", fake_checks)
    monkeypatch.setattr(news_router, "linkedin_configured", lambda: True)

    async def run():
        result = await news_router.check_all_sources_now(db=FakeDB(), _=None, source_ids=ids)
        await news_router._check_all_task
        assert result["total"] == 2

    asyncio.run(run())
    compiled = statements[0].compile(dialect=postgresql.dialect())
    assert ids in compiled.params.values()
    assert "intelligence_sources.id IN" in str(compiled)
    assert checked == ids
