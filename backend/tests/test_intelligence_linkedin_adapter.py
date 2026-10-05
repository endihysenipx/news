import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest

from app.intelligence.collection import collection_start_date
from app.intelligence.linkedin_adapter import BrightDataLinkedInAdapter, LinkedInCollectionError, parse_posts
from app.intelligence.schemas import NewsSourceCreate


def test_posts_keep_only_direct_links_and_parse_publication_date():
    source = SimpleNamespace(name="Example")
    posts = parse_posts([
        {"id": "42", "url": "https://www.linkedin.com/posts/example_update-42", "post_text": "A new grant opened.", "date_posted": "2026-09-24T09:00:00Z"},
        {"id": "43", "url": "https://www.linkedin.com/in/example/", "post_text": "Profile page"},
    ], source)
    assert len(posts) == 1
    assert posts[0].url.endswith("example_update-42")
    assert posts[0].published_at.isoformat() == "2026-09-24T09:00:00+00:00"


def test_profile_discovery_accepts_locale_links_but_excludes_other_authors():
    source = SimpleNamespace(name="Example", url="https://www.linkedin.com/in/example/")
    posts = parse_posts([
        {"id": "42", "url": "https://de.linkedin.com/posts/example_news-activity-42-abc", "user_id": "example", "post_text": "Our update"},
        {"id": "43", "url": "https://de.linkedin.com/posts/other_news-activity-43-abc", "user_id": "other", "post_text": "Someone else's update"},
        {"id": "44", "url": "https://fr.linkedin.com/posts/example_news-activity-44-abc", "use_url": "https://fr.linkedin.com/in/example/", "post_text": "Another update"},
        {"id": "45", "url": "https://linkedin.com.evil.test/posts/example_news-activity-45-abc", "user_id": "example"},
    ], source)
    assert [post.external_id for post in posts] == ["42", "44"]
    assert [post.url for post in posts] == [
        "https://www.linkedin.com/posts/example_news-activity-42-abc",
        "https://www.linkedin.com/posts/example_news-activity-44-abc",
    ]


def test_linkedin_source_requires_profile_or_company_page():
    valid = {"name": "Example", "type": "LINKEDIN", "url": "https://www.linkedin.com/company/example/"}
    assert NewsSourceCreate(**valid).type == "LINKEDIN"
    with pytest.raises(ValueError):
        NewsSourceCreate(**{**valid, "url": "https://www.linkedin.com/feed/"})


def test_provider_trigger_uses_profile_discovery_and_snapshot_flow():
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/trigger"):
            return httpx.Response(200, json={"snapshot_id": "sd_example123"})
        if request.url.path.endswith("/progress/sd_example123"):
            return httpx.Response(200, json={"status": "ready"})
        return httpx.Response(200, json=[{"id": "42", "url": "https://www.linkedin.com/feed/update/urn:li:activity:42", "user_id": "example", "post_text": "New opportunity"}])

    adapter = BrightDataLinkedInAdapter("test-token", "test-dataset")
    adapter._client = lambda: httpx.AsyncClient(
        base_url="https://api.brightdata.com/datasets/v3/",
        transport=httpx.MockTransport(respond),
        headers={"Authorization": "Bearer test-token"},
    )
    source = SimpleNamespace(name="Example", url="https://www.linkedin.com/in/example/")

    async def exercise() -> None:
        snapshot = await adapter.trigger(source, start_date="2026-09-23", end_date="2026-09-24")
        assert snapshot == "sd_example123"
        assert await adapter.progress(snapshot) == "ready"
        assert len(await adapter.download(snapshot, source)) == 1

    asyncio.run(exercise())
    assert requests[0].url.params["discover_by"] == "profile_url"


def test_provider_rejects_results_without_post_links():
    with pytest.raises(LinkedInCollectionError):
        parse_posts([{"url": "https://www.linkedin.com/in/example/"}], SimpleNamespace(name="Example"))


def test_provider_error_keeps_actionable_message_without_echoing_token():
    adapter = BrightDataLinkedInAdapter("private-token", "test-dataset")
    response = httpx.Response(
        400,
        json={"error": "Invalid input for private-token"},
        request=httpx.Request("POST", "https://api.brightdata.com/datasets/v3/trigger"),
    )
    with pytest.raises(LinkedInCollectionError, match=r"HTTP 400.*Invalid input for \[redacted\]"):
        adapter._json(response)


def test_first_check_covers_recent_posts_then_uses_incremental_window():
    now = datetime(2026, 9, 24, 9, 0, tzinfo=timezone.utc)
    assert collection_start_date(None, now) == "2026-07-26"
    assert collection_start_date(datetime(2026, 9, 20, tzinfo=timezone.utc), now) == "2026-09-19"


@pytest.mark.parametrize("content_type", ["text/plain", "text/html"])
def test_inactive_provider_account_has_actionable_error(content_type):
    adapter = BrightDataLinkedInAdapter("private-token", "test-dataset")
    response = httpx.Response(400, text="Customer is not active", headers={"content-type": content_type},
                              request=httpx.Request("POST", "https://api.brightdata.com/datasets/v3/trigger"))
    with pytest.raises(LinkedInCollectionError, match=r"HTTP 400.*account is inactive.*Activate"):
        adapter._json(response)


def test_plain_text_provider_errors_redact_token_and_strip_html():
    adapter = BrightDataLinkedInAdapter("private-token", "test-dataset")
    response = httpx.Response(400, text="<p>Invalid private-token</p><script>secret()</script>",
                              request=httpx.Request("POST", "https://api.brightdata.com/datasets/v3/trigger"))
    with pytest.raises(LinkedInCollectionError, match=r"HTTP 400.*Invalid \[redacted\]") as error:
        adapter._json(response)
    assert "secret()" not in str(error.value)


def test_linkedin_activity_preserves_reposts_comments_and_unknown_counts():
    source = SimpleNamespace(name="Company", url="https://www.linkedin.com/company/company/")
    post = parse_posts([{
        "url": "https://www.linkedin.com/posts/company_update-42",
        "post_text": "Our thoughts on this announcement",
        "num_likes": 0, "num_comments": "1,234", "num_reposts": None,
        "repost": {"repost_url": "https://www.linkedin.com/posts/original_update-1", "repost_text": "<p>Original announcement</p>", "repost_user_name": "Original author"},
        "top_visible_comments": [
            {"user_name": "Reader", "comment": "Useful news", "comment_date": "2026-10-01T10:00:00Z", "comment_url": "https://www.linkedin.com/feed/update/urn:li:activity:42?commentUrn=1"},
            {"user_name": "Reader", "comment": "Useful news", "comment_url": "https://www.linkedin.com/feed/update/urn:li:activity:42?commentUrn=1"},
            {"comment": "", "user_name": "Empty"},
        ],
    }], source)[0]
    activity = post.linkedin_data
    assert activity["kind"] == "REPOST"
    assert activity["reactionCount"] == 0
    assert activity["commentCount"] == 1234
    assert activity["repostCount"] is None
    assert activity["originalPostText"] == "Original announcement"
    assert "Shared post: Original announcement" in post.original_text
    assert activity["originalAuthor"] == "Original author"
    assert len(activity["comments"]) == 1
    assert activity["comments"][0]["publishedAt"] == "2026-10-01T10:00:00+00:00"
    from app.intelligence.schemas import LinkedInActivityOut
    assert LinkedInActivityOut.model_validate(activity).kind == "REPOST"


def test_original_post_text_and_empty_repost_object_do_not_mark_regular_posts_as_reposts():
    activity = parse_posts([{
        "url": "https://www.linkedin.com/posts/company_update-42",
        "post_text": "Our post", "original_post_text": "Our post<br>",
        "post_type": "post", "repost": {"repost_text": None, "repost_url": None},
        "num_likes": True, "num_comments": -1, "top_visible_comments": 5,
    }], SimpleNamespace(name="Company"))[0].linkedin_data
    assert activity["kind"] == "POST"
    assert activity["originalPostText"] is None
    assert activity["reactionCount"] is None
    assert activity["commentCount"] is None
    assert activity["comments"] == []


def test_activity_rejects_untrusted_comment_links_and_strips_html():
    activity = parse_posts([{
        "url": "https://www.linkedin.com/posts/company_update-42",
        "top_visible_comments": [{"comment": "<b>Useful</b><script>bad()</script>", "comment_url": "javascript:alert(1)"}],
    }], SimpleNamespace(name="Company"))[0].linkedin_data
    assert activity["comments"][0]["url"] is None
    assert activity["comments"][0]["text"] == "Useful"
