"""Import a PrimeFlow Intelligence feed export into the standalone database."""

import argparse
import asyncio
import json
import uuid
from datetime import date, datetime
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert

from app.db import AppMetadata, Base, SessionLocal, engine
from app.intelligence.models import NewsAnalysis, NewsItem, NewsSource


def timestamp(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


async def import_export(path: Path) -> tuple[int, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        for source in payload["sources"]:
            values = {
                "id": uuid.UUID(source["id"]), "name": source["name"], "url": source["url"],
                "type": source["type"], "status": source.get("status", "ACTIVE"),
                "priority": source.get("priority", "NORMAL"), "categories": source.get("categories", []),
                "ai_instructions": source.get("ai_instructions"),
                "fetch_interval_minutes": source.get("fetch_interval_minutes", 60),
            }
            await db.execute(insert(NewsSource).values(**values).on_conflict_do_nothing(index_elements=[NewsSource.id]))
        for entry in payload["items"]:
            item = {
                "id": uuid.UUID(entry["id"]), "source_id": uuid.UUID(entry["sourceId"]),
                "external_id": entry.get("externalId"), "url": entry["url"], "title": entry["title"],
                "original_text": entry.get("originalText"), "published_at": timestamp(entry.get("publishedAt")),
                "image_url": entry.get("imageUrl"), "content_hash": entry.get("contentHash"),
                "created_at": timestamp(entry.get("createdAt")),
            }
            await db.execute(insert(NewsItem).values(**item).on_conflict_do_nothing(index_elements=[NewsItem.id]))
            analysis = entry["analysis"]
            await db.execute(insert(NewsAnalysis).values(
                news_item_id=item["id"], summary=analysis["summary"], category=analysis["category"],
                importance_score=analysis["importanceScore"], relevance_score=analysis["relevanceScore"],
                why_it_matters=analysis.get("whyItMatters"),
                deadline=date.fromisoformat(analysis["deadline"]) if analysis.get("deadline") else None,
                funding_amount=analysis.get("fundingAmount"), eligibility=analysis.get("eligibility"),
                opportunity_type=analysis.get("opportunityType"), tags=analysis.get("tags", []),
            ).on_conflict_do_nothing(index_elements=[NewsAnalysis.news_item_id]))
        await db.execute(insert(AppMetadata).values(
            key="primeflow_snapshot_imported", value=payload.get("exportedAt", "imported"),
        ).on_conflict_do_update(
            index_elements=[AppMetadata.key], set_={"value": payload.get("exportedAt", "imported")},
        ))
        await db.commit()
    await engine.dispose()
    return len(payload["sources"]), len(payload["items"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path)
    args = parser.parse_args()
    sources, items = asyncio.run(import_export(args.export))
    print(f"Processed {sources} sources and {items} articles (existing IDs skipped).")
