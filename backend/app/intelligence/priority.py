"""Derive an update's priority from its analysis and the source preference."""

from app.intelligence.focus import opportunity_focus_score
from app.intelligence.models import NewsAnalysis, NewsItem, NewsSource


def news_priority(source_priority: str, importance: int, relevance: int, focus_score: int = 0) -> str:
    if focus_score >= 145:
        return "HIGH"
    thresholds = {
        "HIGH": (70, 60),
        "NORMAL": (80, 70),
        "LOW": (90, 80),
    }
    minimum_importance, minimum_relevance = thresholds.get(source_priority, thresholds["NORMAL"])
    return "HIGH" if importance >= minimum_importance and relevance >= minimum_relevance else "NORMAL"


def analyzed_news_priority(item: NewsItem, source: NewsSource, analysis: NewsAnalysis) -> str:
    focus_score = opportunity_focus_score(item, source, analysis)
    if analysis.category in {"GRANT", "TENDER"} and not focus_score:
        return "NORMAL"
    return news_priority(source.priority, analysis.importance_score, analysis.relevance_score, focus_score)
