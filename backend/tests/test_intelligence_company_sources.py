import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.db import AppMetadata
from app.intelligence.company_sources import ensure_company_sources
from app.intelligence.models import NewsSource


def test_install_adds_only_missing_company_and_preserves_existing_settings():
    existing = SimpleNamespace(url="https://www.linkedin.com/company/primexeu", status="PAUSED", fetch_interval_minutes=120)
    added = []
    db = SimpleNamespace(get=AsyncMock(return_value=None),
                         scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [existing])),
                         add=added.append, commit=AsyncMock())
    asyncio.run(ensure_company_sources(db))
    sources = [row for row in added if isinstance(row, NewsSource)]
    assert len(sources) == 1
    assert sources[0].url == "https://www.linkedin.com/company/mendex-ai/"
    assert existing.status == "PAUSED" and existing.fetch_interval_minutes == 120
    assert len([row for row in added if isinstance(row, AppMetadata)]) == 1
    db.commit.assert_awaited_once()


def test_install_does_not_recreate_intentionally_removed_company():
    db = SimpleNamespace(get=AsyncMock(return_value=AppMetadata(key="primex_mendex_sources_installed", value="done")), scalars=AsyncMock(), commit=AsyncMock())
    asyncio.run(ensure_company_sources(db))
    db.scalars.assert_not_awaited()
    db.commit.assert_not_awaited()
