"""Install the requested company monitors once, preserving existing settings."""
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AppMetadata
from app.intelligence.models import NewsSource
from app.intelligence.schemas import NewsSourceCreate

COMPANIES = (("PrimEx EU", "primexeu"), ("Mendex.ai", "mendex-ai"))
INSTALL_KEY = "primex_mendex_sources_installed"


async def ensure_company_sources(db: AsyncSession) -> None:
    if await db.get(AppMetadata, INSTALL_KEY):
        return
    sources = (await db.scalars(select(NewsSource).where(NewsSource.type == "LINKEDIN"))).all()
    existing = {
        urlparse(source.url).path.rstrip("/").casefold()
        for source in sources
        if urlparse(source.url).hostname in {"www.linkedin.com", "linkedin.com"}
    }
    for name, slug in COMPANIES:
        if f"/company/{slug}" not in existing:
            payload = NewsSourceCreate(
                name=name, type="LINKEDIN", url=f"https://www.linkedin.com/company/{slug}/",
                ai_instructions=f"Summarize the actual posts and reposts from {name}, including available engagement. Do not invent activity.",
            )
            db.add(NewsSource(**payload.model_dump(exclude={"email_enabled"})))
    db.add(AppMetadata(key=INSTALL_KEY, value="done"))
    await db.commit()
