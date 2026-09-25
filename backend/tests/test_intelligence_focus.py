from datetime import date, datetime, timezone
from types import SimpleNamespace

from app.intelligence.focus import opportunity_focus_score
from app.intelligence.priority import analyzed_news_priority, news_priority


TODAY = date(2026, 9, 25)


def news(title, category="GRANT", deadline=None, published=date(2026, 9, 20), tags=None, source="KIESA"):
    item = SimpleNamespace(title=title, published_at=datetime.combine(published, datetime.min.time(), timezone.utc), created_at=None)
    origin = SimpleNamespace(name=source, url="https://kiesa.rks-gov.net" if source == "KIESA" else "https://example.eu")
    analysis = SimpleNamespace(category=category, deadline=deadline, relevance_score=70, tags=tags or [])
    return item, origin, analysis


def test_kosovo_ai_call_ranks_above_other_opportunities():
    local = opportunity_focus_score(*news("AI grant for Kosovo SMEs", tags=["AI", "Kosovo"]), today=TODAY)
    international = opportunity_focus_score(*news("AI grant for SMEs", tags=["AI"], source="EU Digital"), today=TODAY)
    assert local > international >= 100
    assert news_priority("NORMAL", 60, 70, local) == "HIGH"


def test_explicit_ai_call_ranks_above_general_technology_call():
    ai = opportunity_focus_score(*news("AI cybersecurity grant", deadline=date(2027, 1, 14), source="EU Digital"), today=TODAY)
    cybersecurity = opportunity_focus_score(*news("Cybersecurity grant", deadline=date(2027, 1, 14), source="EU Digital"), today=TODAY)
    assert ai > cybersecurity
    assert news_priority("NORMAL", 60, 70, ai) == "HIGH"
    assert news_priority("NORMAL", 60, 70, cybersecurity) == "NORMAL"
    regulation_mention = opportunity_focus_score(*news("Cybersecurity capacity grant", deadline=date(2027, 1, 14), tags=["AI Act"], source="EU Digital"), today=TODAY)
    assert regulation_mention == cybersecurity


def test_results_and_expired_calls_are_not_promoted():
    assert opportunity_focus_score(*news("LISTA PRELIMINARE E PËRFITUESVE për grantet AI"), today=TODAY) == 0
    assert opportunity_focus_score(*news("AI grant", deadline=date(2026, 9, 1)), today=TODAY) == 0
    assert opportunity_focus_score(*news("AI grant", published=date(2026, 8, 1)), today=TODAY) == 0
    assert opportunity_focus_score(*news("AI regulation", category="REGULATION"), today=TODAY) == 0
    assert opportunity_focus_score(*news("Study visits tender", source="EU Trade"), today=TODAY) == 0


def test_expired_grant_cannot_remain_high_priority():
    item, source, analysis = news("AI grant", deadline=date(2026, 9, 1))
    source.priority = "NORMAL"
    analysis.importance_score = 90
    analysis.relevance_score = 90
    assert analyzed_news_priority(item, source, analysis) == "NORMAL"
