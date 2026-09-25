"""Rank potentially actionable opportunities for a Kosovo AI company."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from app.intelligence.models import NewsAnalysis, NewsItem, NewsSource

RESULT_NOTICE = re.compile(
    r"\b(lista|list[ëe]?|p[ëe]rfitues|beneficiar|award(?:ed|s)?|results?|selected applicants)\b",
    re.IGNORECASE,
)
AI_FIT = re.compile(
    r"\b(ai|genai|artificial intelligence|machine learning|inteligjenc[ëe] artificiale)\b",
    re.IGNORECASE,
)
TECH_FIT = re.compile(
    r"\b(cybersecurity|cybersecure|digital(?:isation|ization)?|software|technology|tech|ict|startup|"
    r"digjital\w*|teknologji\w*|kibernetik\w*)\b",
    re.IGNORECASE,
)


def opportunity_focus_score(
    item: NewsItem, source: NewsSource, analysis: NewsAnalysis, *, today: date | None = None,
) -> int:
    """Return zero for stale/non-call items, otherwise a relative display score.

    The score is a discovery aid, not a claim that the company is eligible.
    """
    if analysis.category not in {"GRANT", "TENDER"} or RESULT_NOTICE.search(item.title):
        return 0
    current_day = today or datetime.now(timezone.utc).date()
    if analysis.deadline and analysis.deadline < current_day:
        return 0
    published = item.published_at or item.created_at
    if not analysis.deadline and published.date() < current_day - timedelta(days=21):
        return 0

    tags = analysis.tags or []
    kosovo = (
        "rks-gov.net" in source.url.lower()
        or "kiesa" in source.name.lower()
        or any(tag.casefold() == "kosovo" for tag in tags)
    )
    topic_text = " ".join([item.title, *tags])
    technology_fit = 30 if AI_FIT.search(item.title) else 10 if TECH_FIT.search(topic_text) else 0
    if not kosovo and not technology_fit:
        return 0
    return 100 + analysis.relevance_score // 5 + (40 if kosovo else 0) + technology_fit + (10 if analysis.deadline else 0)
