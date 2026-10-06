import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.intelligence import collection
from app.intelligence.services import CollectedNewsItem


@pytest.mark.parametrize("subscribed,expected", [(True, True), (False, False)])
def test_email_subscription_keeps_activity_outside_category_filter(monkeypatch, subscribed, expected):
    source = SimpleNamespace(id=uuid4(), type="RSS", categories=["GRANTS"])
    stored = []
    db = SimpleNamespace(scalar=AsyncMock(side_effect=[None, source.id if subscribed else None]),
                         add=stored.append, flush=AsyncMock())
    analysis = SimpleNamespace(summary="News", category="BUSINESS", importanceScore=10, relevanceScore=10,
                               whyItMatters=None, deadline=None, fundingAmount=None, eligibility=None,
                               opportunityType=None, tags=[])
    monkeypatch.setattr(collection, "analyze_news_item", AsyncMock(return_value=analysis))
    post = CollectedNewsItem("email-news", "https://example.com/news", "News", "Body", None)
    assert asyncio.run(collection._store_post(db, source, post)) is expected
    assert len(stored) == (2 if subscribed else 0)


def test_engagement_refresh_keeps_existing_item_and_skips_ai(monkeypatch):
    item = SimpleNamespace(id=uuid4(), title="Original", original_text="Body", published_at=None, linkedin_data=None)
    db = SimpleNamespace(scalar=AsyncMock(return_value=item), get=AsyncMock(), add=lambda _: (_ for _ in ()).throw(AssertionError("duplicate")))
    analyze = AsyncMock()
    monkeypatch.setattr(collection, "analyze_news_item", analyze)
    post = CollectedNewsItem("42", "https://www.linkedin.com/posts/example_42", "Original", "Body", None, linkedin_data={"reactionCount": 7, "comments": []})
    assert asyncio.run(collection._store_post(db, SimpleNamespace(id=uuid4(), type="LINKEDIN"), post)) is False
    assert item.linkedin_data["reactionCount"] == 7
    assert item.linkedin_data["checkedAt"]
    analyze.assert_not_awaited()
    db.get.assert_not_awaited()


def test_edited_post_updates_same_item_and_analysis(monkeypatch):
    item_id = uuid4()
    item = SimpleNamespace(id=item_id, title="Original", original_text="Body", published_at=None, linkedin_data=None)
    saved_analysis = SimpleNamespace()
    db = SimpleNamespace(scalar=AsyncMock(return_value=item), get=AsyncMock(return_value=saved_analysis))
    analysis = SimpleNamespace(summary="Edited summary", category="BUSINESS", importanceScore=50, relevanceScore=60,
                               whyItMatters=None, deadline=None, fundingAmount=None, eligibility=None, opportunityType=None, tags=[])
    monkeypatch.setattr(collection, "analyze_news_item", AsyncMock(return_value=analysis))
    post = CollectedNewsItem("42", "https://www.linkedin.com/posts/example_42", "Edited", "Edited body", None, linkedin_data={"reactionCount": 8})
    assert asyncio.run(collection._store_post(db, SimpleNamespace(id=uuid4(), type="LINKEDIN"), post)) is False
    assert item.id == item_id
    assert item.title == "Edited" and item.original_text == "Edited body"
    assert saved_analysis.summary == "Edited summary"
    assert saved_analysis.analyzed_at


def test_scheduled_check_revisits_recent_posts_for_engagement(monkeypatch):
    source = SimpleNamespace(id=uuid4(), type="LINKEDIN", status="ACTIVE", pending_snapshot_id=None,
                             last_started_at=None, last_checked_at=datetime.now(timezone.utc), fetch_interval_minutes=60)
    db = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: source)), commit=AsyncMock())
    trigger = AsyncMock(return_value="sd_refresh123")
    monkeypatch.setattr(collection.settings, "BRIGHTDATA_API_TOKEN", "test-token")
    monkeypatch.setattr(collection, "BrightDataLinkedInAdapter", lambda *_: SimpleNamespace(trigger=trigger))
    assert asyncio.run(collection.check_source(db, source.id)) == "started"
    request = trigger.await_args.kwargs
    assert request["start_date"] == collection.collection_start_date(None, datetime.now(timezone.utc))
