import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.intelligence import digest_service
from app.intelligence.schemas import DigestSettingsInput


def row(source_name, url, created_at):
    item = SimpleNamespace(url=url, title=f"Notice {url.rsplit('/', 1)[-1]}", created_at=created_at)
    analysis = SimpleNamespace(summary="A useful opportunity.", deadline=None)
    source = SimpleNamespace(name=source_name)
    return item, analysis, source


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def all(self):
        return self.value


class FakeSession:
    def __init__(self, digest, rows):
        self.digest = digest
        self.rows = rows
        self.deliveries = []

    async def execute(self, query):
        entity = query.column_descriptions[0]["entity"]
        if entity is digest_service.NewsDigestSettings:
            return FakeResult(self.digest)
        return FakeResult(self.rows)

    async def scalars(self, _query):
        return FakeResult([delivery.url_hash for delivery in self.deliveries])

    def add(self, delivery):
        self.deliveries.append(delivery)

    async def commit(self):
        pass


def test_digest_groups_sources_and_sends_only_new_items(monkeypatch):
    sent = []

    async def fake_send(subject, body, html):
        sent.append((subject, body, html))

    monkeypatch.setattr(digest_service, "_send_digest", fake_send)
    digest = SimpleNamespace(times=["12:30", "17:00", "21:00"],
                             last_slot_at=datetime(2026, 9, 30, 10, 30, tzinfo=timezone.utc),
                             last_sent_at=None, last_error=None)
    first = row("Grants", "https://example.org/one", datetime(2026, 9, 30, 11, tzinfo=timezone.utc))
    duplicate = row("Business", "https://example.org/one", datetime(2026, 9, 30, 11, tzinfo=timezone.utc))
    second = row("Business", "https://example.org/two", datetime(2026, 9, 30, 12, tzinfo=timezone.utc))
    db = FakeSession(digest, [first, duplicate, second])
    user_id = uuid4()

    async def run():
        count = await digest_service.process_digest(db, user_id, datetime(2026, 9, 30, 15, 1, tzinfo=timezone.utc))
        assert count == 2
        assert len(sent) == 1
        assert "Grants" in sent[0][1] and "Business" in sent[0][1]
        assert sent[0][1].count("https://example.org/one") == 1
        assert len(db.deliveries) == 2

        third = row("Grants", "https://example.org/three", datetime(2026, 9, 30, 17, tzinfo=timezone.utc))
        db.rows.extend([third])
        count = await digest_service.process_digest(db, user_id, datetime(2026, 9, 30, 19, 1, tzinfo=timezone.utc))
        assert count == 1
        assert len(sent) == 2
        assert "https://example.org/three" in sent[1][1]
        assert "https://example.org/one" not in sent[1][1]

    asyncio.run(run())


def test_digest_times_are_unique_and_sorted():
    assert DigestSettingsInput(times=["21:00", "12:30", "17:00"]).times == ["12:30", "17:00", "21:00"]
    with pytest.raises(ValueError):
        DigestSettingsInput(times=["12:30", "12:30"])
