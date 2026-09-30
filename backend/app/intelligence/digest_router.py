"""Settings and test delivery for the source email report."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import User, get_current_user
from app.config import settings
from app.db import get_db
from app.intelligence.digest_service import ensure_digest_settings, send_digest_test
from app.intelligence.schemas import DigestSettingsInput

router = APIRouter()
logger = logging.getLogger(__name__)


def _settings_out(digest) -> dict:
    return {"times": digest.times, "timezone": "Europe/Budapest", "recipient": settings.NEWS_EMAIL_RECIPIENT,
            "lastSentAt": digest.last_sent_at, "lastError": digest.last_error,
            "emailConfigured": bool(settings.EMAIL_USER and settings.EMAIL_PASSWORD)}


@router.get("/digest-settings")
async def get_digest_settings(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    digest = await ensure_digest_settings(db, user.id)
    await db.commit()
    return _settings_out(digest)


@router.put("/digest-settings")
async def update_digest_settings(payload: DigestSettingsInput, db: AsyncSession = Depends(get_db),
                                 user: User = Depends(get_current_user)) -> dict:
    digest = await ensure_digest_settings(db, user.id)
    digest.times = payload.times
    digest.last_slot_at = datetime.now(timezone.utc)
    await db.commit()
    return _settings_out(digest)


@router.post("/digest-settings/test", status_code=status.HTTP_204_NO_CONTENT)
async def test_digest_email(_: User = Depends(get_current_user)) -> Response:
    if not settings.EMAIL_USER or not settings.EMAIL_PASSWORD:
        raise HTTPException(status_code=503, detail="SMTP is not configured on the server.")
    try:
        await send_digest_test()
    except Exception as exc:
        logger.exception("Digest test email failed")
        raise HTTPException(status_code=502, detail="Test email failed. Check the SMTP settings and server logs.") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
