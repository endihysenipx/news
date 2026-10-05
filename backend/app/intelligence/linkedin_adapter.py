"""Bright Data LinkedIn post discovery. Credentials stay on the backend."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

from app.intelligence.models import NewsSource
from app.intelligence.services import CollectedNewsItem

API_BASE = "https://api.brightdata.com/datasets/v3/"
SNAPSHOT_ID = re.compile(r"^(?:s|sd)_[A-Za-z0-9]+$")


class LinkedInCollectionError(RuntimeError):
    pass


def _post_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or not (
        parsed.hostname == "linkedin.com" or parsed.hostname.endswith(".linkedin.com")
    ):
        return None
    if not (parsed.path.startswith("/posts/") or parsed.path.startswith("/feed/update/")):
        return None
    return urlunparse(("https", "www.linkedin.com", parsed.path, "", "", ""))[:2000]


def _belongs_to_source(record: dict, source: NewsSource) -> bool:
    source_path = urlparse(getattr(source, "url", "")).path.strip("/").split("/")
    if len(source_path) < 2 or source_path[0] != "in":
        return True
    profile_id = source_path[1].casefold()
    reposter = record.get("reposted_by") or record.get("shared_by")
    if isinstance(reposter, dict):
        reposter = reposter.get("url") or reposter.get("user_url") or reposter.get("user_id")
    if isinstance(reposter, str):
        reposter_path = urlparse(reposter).path.strip("/").split("/")
        if reposter.casefold() == profile_id or (
            _linkedin_url(reposter) and reposter_path == ["in", source_path[1]]
        ):
            return True
    author_id = record.get("user_id")
    if isinstance(author_id, str) and author_id:
        return author_id.casefold() == profile_id
    author_url = record.get("use_url") or record.get("user_url")
    if isinstance(author_url, str):
        author_path = urlparse(author_url).path.strip("/").split("/")
        if len(author_path) >= 2 and author_path[0] == "in":
            return author_path[1].casefold() == profile_id
    return False


def _published(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def _text(value: object, limit: int = 4000) -> str | None:
    if not isinstance(value, str):
        return None
    if re.search(r"</?[a-zA-Z][^>]*>", value):
        soup = BeautifulSoup(value[:100000], "html.parser")
        for element in soup(["script", "style"]):
            element.decompose()
        value = soup.get_text(" ", strip=True)
    return " ".join(value.split())[:limit] or None


def _linkedin_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.hostname not in {"linkedin.com", "www.linkedin.com"}:
        return None
    return urlunparse(("https", "www.linkedin.com", parsed.path, "", parsed.query, ""))[:2000]


def _count(record: dict, *keys: str) -> int | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int) and value >= 0:
            return value
        if isinstance(value, str) and re.fullmatch(r"\d+", value.replace(",", "").strip()):
            return int(value.replace(",", "").strip())
    return None


def _activity(record: dict) -> dict:
    """Keep only observed activity; missing counts are unknown, never zero."""
    repost = record.get("repost")
    repost = repost if isinstance(repost, dict) else {}
    original_text = _text(repost.get("repost_text") or repost.get("post_text") or repost.get("text"), 20000)
    original_url = _post_url(repost.get("repost_url") or repost.get("url") or repost.get("post_url") or record.get("original_post_url"))
    post_type = str(record.get("post_type") or "").casefold()
    kind = "REPOST" if post_type in {"repost", "share", "reshare", "shared_post"} or original_text or original_url else "ARTICLE" if post_type == "article" else "POST"
    raw_comments = record.get("top_visible_comments")
    if not isinstance(raw_comments, list):
        raw_comments = record.get("comments")
    comments = []
    seen = set()
    for comment in raw_comments[:100] if isinstance(raw_comments, list) else []:
        if isinstance(comment, str):
            comment = {"text": comment}
        if not isinstance(comment, dict):
            continue
        body = _text(comment.get("comment") or comment.get("text") or comment.get("comment_text") or comment.get("content"))
        if not body:
            continue
        author = comment.get("author") or comment.get("user")
        if isinstance(author, dict):
            author = author.get("name")
        author = _text(comment.get("user_name") or comment.get("name") or author, 200)
        url = _linkedin_url(comment.get("url") or comment.get("comment_url"))
        key = (author, body, url)
        if key in seen:
            continue
        seen.add(key)
        published = _published(comment.get("comment_date") or comment.get("date_posted") or comment.get("date") or comment.get("published_at"))
        comments.append({"author": author, "text": body, "url": url, "publishedAt": published.isoformat() if published else None})
    checked = _published(record.get("timestamp"))
    return {
        "kind": kind,
        "authorName": _text(record.get("user_name") or record.get("company_name"), 200),
        "authorUrl": _linkedin_url(record.get("use_url") or record.get("user_url") or record.get("company_url")),
        "reactionCount": _count(record, "num_likes", "num_reactions"),
        "commentCount": _count(record, "num_comments"),
        "repostCount": _count(record, "num_reposts", "num_shares"),
        "comments": comments,
        "originalPostText": original_text,
        "originalPostUrl": original_url,
        "originalAuthor": _text(repost.get("repost_user_name"), 200),
        "checkedAt": checked.isoformat() if checked else None,
    }


def parse_posts(records: object, source: NewsSource) -> list[CollectedNewsItem]:
    if not isinstance(records, list):
        raise LinkedInCollectionError("The provider returned an unexpected snapshot format.")
    posts: list[CollectedNewsItem] = []
    for record in records:
        if not isinstance(record, dict) or record.get("error"):
            continue
        url = _post_url(record.get("url") or record.get("post_url"))
        if not url or not _belongs_to_source(record, source):
            continue
        body = record.get("post_text") or record.get("text") or record.get("headline") or ""
        body = " ".join(body.split()) if isinstance(body, str) else ""
        activity = _activity(record)
        if activity["kind"] == "REPOST" and activity["originalPostText"]:
            body = f"{body}\nShared post: {activity['originalPostText']}".strip()
        title = record.get("title")
        if not isinstance(title, str) or not title.strip():
            title = body[:140].rstrip(" .") + ("…" if len(body) > 140 else "") if body else f"Post by {source.name}"
        identifier = record.get("id") or record.get("post_id") or url
        posts.append(CollectedNewsItem(
            external_id=str(identifier)[:500], url=url, title=title.strip()[:500],
            original_text=body[:20_000] or None,
            published_at=_published(record.get("date_posted") or record.get("published_at")),
            linkedin_data=activity,
        ))
    if records and not posts:
        raise LinkedInCollectionError("Provider returned no usable direct post links for this source.")
    return posts


class BrightDataLinkedInAdapter:
    def __init__(self, token: str, dataset_id: str) -> None:
        self.token = token
        self.dataset_id = dataset_id

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=API_BASE, timeout=httpx.Timeout(25.0), follow_redirects=False,
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"},
        )

    def _json(self, response: httpx.Response) -> object:
        try:
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            detail = ""
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    value = payload.get("error") or payload.get("message")
                    if isinstance(value, str):
                        detail = value.replace(self.token, "[redacted]")[:250]
            except ValueError:
                # Some provider failures (including inactive accounts) are plain text.
                detail = _text(response.text.replace(self.token, "[redacted]"), 250) or ""
            if "customer is not active" in detail.casefold():
                detail = "Bright Data account is inactive. Activate the account in Bright Data to resume LinkedIn checks."
            suffix = f" {detail}" if detail else ""
            raise LinkedInCollectionError(f"Provider request failed (HTTP {response.status_code}).{suffix}") from exc
        except ValueError as exc:
            raise LinkedInCollectionError("Provider returned invalid JSON.") from exc

    async def trigger(self, source: NewsSource, *, start_date: str, end_date: str) -> str:
        discovery = "company_url" if urlparse(source.url).path.startswith("/company/") else "profile_url"
        async with self._client() as client:
            response = await client.post(
                "trigger",
                params={"dataset_id": self.dataset_id, "type": "discover_new", "discover_by": discovery, "limit_per_input": 100},
                json=[{"url": source.url, "start_date": start_date, "end_date": end_date}],
            )
        payload = self._json(response)
        snapshot_id = payload.get("snapshot_id") if isinstance(payload, dict) else None
        if not isinstance(snapshot_id, str) or not SNAPSHOT_ID.fullmatch(snapshot_id):
            raise LinkedInCollectionError("Provider did not return a valid snapshot ID.")
        return snapshot_id

    async def progress(self, snapshot_id: str) -> str:
        if not SNAPSHOT_ID.fullmatch(snapshot_id):
            raise LinkedInCollectionError("Invalid snapshot ID.")
        async with self._client() as client:
            response = await client.get(f"progress/{snapshot_id}")
        payload = self._json(response)
        state = payload.get("status") if isinstance(payload, dict) else None
        if state not in {"starting", "running", "ready", "failed"}:
            raise LinkedInCollectionError("Provider returned an unknown collection status.")
        return state

    async def download(self, snapshot_id: str, source: NewsSource) -> list[CollectedNewsItem]:
        if not SNAPSHOT_ID.fullmatch(snapshot_id):
            raise LinkedInCollectionError("Invalid snapshot ID.")
        async with self._client() as client:
            response = await client.get(f"snapshot/{snapshot_id}", params={"format": "json"})
        return parse_posts(self._json(response), source)
