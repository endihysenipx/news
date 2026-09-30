"""One scheduled email containing new updates from subscribed sources."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, time, timedelta, timezone
from html import escape
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import SessionLocal
from app.intelligence.email_service import _smtp_reachable
from app.intelligence.models import (
    NewsAnalysis, NewsDigestDelivery, NewsDigestSettings,
    NewsItem, NewsSource, NewsSourceEmailSubscription,
)
from app.mail import GmailService

logger = logging.getLogger(__name__)
DIGEST_ZONE = ZoneInfo("Europe/Budapest")
DEFAULT_TIMES = ["12:30", "17:00", "21:00"]


def latest_slot(now: datetime, times: list[str]) -> datetime:
    local_now = now.astimezone(DIGEST_ZONE)
    slots = []
    for offset in (0, -1):
        day = local_now.date() + timedelta(days=offset)
        for value in times:
            hour, minute = map(int, value.split(":"))
            slot = datetime.combine(day, time(hour, minute), DIGEST_ZONE).astimezone(timezone.utc)
            if slot <= now:
                slots.append(slot)
    return max(slots)


async def ensure_digest_settings(db: AsyncSession, user_id: uuid.UUID) -> NewsDigestSettings:
    digest = await db.get(NewsDigestSettings, user_id)
    if digest is None:
        digest = NewsDigestSettings(user_id=user_id, times=DEFAULT_TIMES.copy(), last_slot_at=datetime.now(timezone.utc))
        db.add(digest)
        await db.flush()
    return digest


def digest_content(entries: list[dict], slot: datetime) -> tuple[str, str, str]:
    local_slot = slot.astimezone(DIGEST_ZONE)
    stamp = local_slot.strftime("%d.%m.%Y %H:%M")
    count = len(entries)
    subject = f"[News Intelligence] {count} njoftime të reja · {local_slot:%H:%M}"
    sections: dict[str, list[dict]] = {}
    for entry in entries:
        sections.setdefault(entry["source_label"], []).append(entry)
    text_lines = [f"Raporti i njoftimeve · {stamp}", f"{count} njoftime të reja", ""]
    html_sections = []
    for source_name, group in sections.items():
        text_lines.extend([f"{source_name} ({len(group)})", "─" * 36])
        html_items = []
        for entry in group:
            item, analysis, source = entry["item"], entry["analysis"], entry["source"]
            details = [source.name]
            if analysis.deadline:
                details.append(f"Afati: {analysis.deadline:%d.%m.%Y}")
            text_lines.extend([item.title, " · ".join(details), analysis.summary, item.url, ""])
            meta = " · ".join(details)
            html_items.append(
                '<div style="padding:16px 0;border-top:1px solid #e6ece6">'
                f'<a href="{escape(item.url, quote=True)}" style="color:#245b38;font-size:16px;font-weight:600;text-decoration:none">{escape(item.title)}</a>'
                f'<p style="color:#687b6c;font-size:12px;margin:7px 0">{escape(meta)}</p>'
                f'<p style="color:#334638;font-size:14px;line-height:1.5;margin:0">{escape(analysis.summary)}</p>'
                '</div>'
            )
        text_lines.append("")
        html_sections.append(
            f'<section style="margin-top:25px"><h2 style="font-size:17px;color:#244a31">{escape(source_name)} <span style="color:#7d9181">({len(group)})</span></h2>'
            + "".join(html_items) + "</section>"
        )
    html = (
        '<div style="max-width:680px;margin:auto;padding:28px;font-family:Arial,sans-serif;color:#24342a">'
        f'<p style="color:#63866a;font-size:12px;font-weight:700;letter-spacing:2px">NEWS INTELLIGENCE</p>'
        f'<h1 style="font-size:25px;margin:8px 0">Raporti i njoftimeve</h1><p style="color:#718074">{escape(stamp)} · {count} njoftime të reja</p>'
        + "".join(html_sections) + "</div>"
    )
    return subject, "\n".join(text_lines), html


async def _send_digest(subject: str, body: str, html: str) -> None:
    mailer = GmailService()
    if mailer.port != 465 and not await _smtp_reachable(mailer.host, mailer.port):
        if not await _smtp_reachable(mailer.host, 465):
            raise ConnectionError("SMTP submission ports are unreachable")
        mailer.port = 465
    await mailer.send_verified(subject, [settings.NEWS_EMAIL_RECIPIENT], body, html=html)


async def send_digest_test() -> None:
    subject = "[News Intelligence] Test i raportit me email"
    body = "Ky është një email test. Raportet e planifikuara do të përmbajnë vetëm lajmet e reja nga burimet ku emaili është aktiv."
    html = ('<div style="max-width:600px;margin:auto;padding:28px;font-family:Arial,sans-serif;color:#24342a">'
            '<p style="color:#63866a;font-size:12px;font-weight:700;letter-spacing:2px">NEWS INTELLIGENCE</p>'
            '<h1 style="font-size:24px">Test i raportit me email</h1>'
            '<p>Konfigurimi i emailit po punon. Raportet e planifikuara do të përmbajnë vetëm lajmet e reja nga burimet ku emaili është aktiv.</p></div>')
    await _send_digest(subject, body, html)


async def process_digest(db: AsyncSession, user_id: uuid.UUID, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    digest = (await db.execute(select(NewsDigestSettings).where(NewsDigestSettings.user_id == user_id)
                               .with_for_update(skip_locked=True))).scalar_one_or_none()
    if digest is None:
        return 0
    slot = latest_slot(now, digest.times)
    if digest.last_slot_at >= slot:
        return 0
    by_url: dict[str, dict] = {}
    source_rows = (await db.execute(
        select(NewsItem, NewsAnalysis, NewsSource)
        .join(NewsAnalysis, NewsAnalysis.news_item_id == NewsItem.id)
        .join(NewsSource, NewsSource.id == NewsItem.source_id)
        .join(NewsSourceEmailSubscription, NewsSourceEmailSubscription.source_id == NewsSource.id)
        .where(NewsSourceEmailSubscription.user_id == user_id, NewsSource.status == "ACTIVE",
               NewsItem.created_at >= NewsSourceEmailSubscription.enabled_at, NewsItem.created_at <= slot)
        .order_by(NewsSource.name, NewsItem.created_at)
    )).all()
    for item, analysis, source in source_rows:
        by_url.setdefault(item.url, {"item": item, "analysis": analysis, "source": source, "source_label": source.name})
    hashes = {url: hashlib.sha256(url.encode("utf-8")).hexdigest() for url in by_url}
    delivered = set((await db.scalars(select(NewsDigestDelivery.url_hash).where(
        NewsDigestDelivery.user_id == user_id, NewsDigestDelivery.url_hash.in_(hashes.values())))).all()) if hashes else set()
    entries = []
    for url, entry in by_url.items():
        if hashes[url] not in delivered:
            entries.append(entry)
    if entries:
        subject, body, html = digest_content(entries, slot)
        try:
            await _send_digest(subject, body, html)
        except Exception as exc:
            digest.last_error = str(exc)[:500]
            await db.commit()
            raise
        for entry in entries:
            db.add(NewsDigestDelivery(user_id=user_id, url_hash=hashes[entry["item"].url], sent_at=now))
        digest.last_sent_at = now
    digest.last_slot_at = slot
    digest.last_error = None
    await db.commit()
    return len(entries)


async def run_digest_cycle() -> None:
    if not settings.EMAIL_USER or not settings.EMAIL_PASSWORD:
        return
    async with SessionLocal() as db:
        user_ids = (await db.scalars(select(NewsDigestSettings.user_id))).all()
    for user_id in user_ids:
        try:
            async with SessionLocal() as db:
                await process_digest(db, user_id)
        except Exception:
            logger.exception("Could not send digest for %s", user_id)
