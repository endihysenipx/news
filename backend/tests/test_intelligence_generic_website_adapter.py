import asyncio
from unittest.mock import AsyncMock

import httpx

from app.intelligence.generic_website_adapter import (
    GenericWebsiteAdapter, GenericWebsiteError, Page, discover_links,
    parse_html_article, sitemap_links,
)
from app.intelligence.collection import category_allowed


def test_discovery_keeps_only_same_site_articles_and_advertised_feed():
    html = '''<link rel="alternate" type="application/rss+xml" href="/feed.xml">
    <nav><a href="/about">About the organisation</a></nav>
    <main><article><a href="/calls/grant-for-startups">Grant for startups</a></article>
    <a href="https://other.example/grant">Grant from another site</a></main>'''
    links, feeds = discover_links(html, "https://example.org/news")
    assert links == [("https://example.org/calls/grant-for-startups", "Grant for startups")]
    assert feeds == ["https://example.org/feed.xml"]


def test_sitemap_rejects_external_and_entity_urls():
    xml = b'<urlset><url><loc>https://example.org/grants/new-call</loc></url><url><loc>http://127.0.0.1/grant</loc></url></urlset>'
    assert sitemap_links(xml, "https://example.org") == ["https://example.org/grants/new-call"]
    assert sitemap_links(b'<!DOCTYPE x [<!ENTITY a SYSTEM "file:///etc/passwd">]><urlset/>', "https://example.org") == []


def test_article_extracts_content_and_publication_date():
    page = Page("https://example.org/grants/new-call", b'<meta property="article:published_time" content="2026-09-29T10:00:00Z"><main><h1>New grant for SMEs</h1><p>Applications are now open for technology companies in Kosovo. The deadline is 30 October.</p></main>', "text/html")
    post = parse_html_article(page, "New grant")
    assert post is not None
    assert post.title == "New grant for SMEs"
    assert post.published_at.isoformat() == "2026-09-29T10:00:00+00:00"


def test_redirect_to_another_host_is_not_fetched(monkeypatch):
    adapter = GenericWebsiteAdapter("https://example.org/news")
    monkeypatch.setattr("app.intelligence.generic_website_adapter._check_public_dns", AsyncMock())
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(302, headers={"location": "https://other.example/private"})))
    try:
        try:
            asyncio.run(adapter._get(client, adapter.source_url))
        except GenericWebsiteError as exc:
            assert "outside" in str(exc)
        else:
            assert False, "Cross-site redirect was accepted"
    finally:
        asyncio.run(client.aclose())


def test_grant_only_source_rejects_other_news():
    assert category_allowed(["Grants"], "GRANT")
    assert not category_allowed(["Grants"], "TENDER")
    assert not category_allowed(["Grants"], "NEWS")
    assert category_allowed([], "NEWS")
