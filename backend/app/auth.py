import hmac
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from starlette.requests import Request

from app.config import settings

router = APIRouter()
COOKIE_NAME = "news_session"
ADMIN_ID = uuid.uuid5(uuid.NAMESPACE_DNS, f"news-admin:{settings.NEWS_ADMIN_EMAIL.casefold()}")


@dataclass(frozen=True)
class User:
    id: uuid.UUID
    email: str
    role: str = "ADMIN"


class LoginInput(BaseModel):
    email: EmailStr
    password: str


def get_current_user(request: Request) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue")
    try:
        claims = jwt.decode(token, settings.NEWS_SESSION_SECRET, algorithms=["HS256"])
        if claims.get("sub") != str(ADMIN_ID):
            raise JWTError("Unknown user")
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired") from exc
    return User(id=ADMIN_ID, email=settings.NEWS_ADMIN_EMAIL)


def require_admin(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/login")
async def login(payload: LoginInput, response: Response) -> dict[str, str]:
    email_ok = hmac.compare_digest(payload.email.casefold(), settings.NEWS_ADMIN_EMAIL.casefold())
    password_ok = hmac.compare_digest(payload.password, settings.NEWS_ADMIN_PASSWORD)
    if not (email_ok and password_ok):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    token = jwt.encode({"sub": str(ADMIN_ID), "exp": expires}, settings.NEWS_SESSION_SECRET, algorithm="HS256")
    response.set_cookie(
        COOKIE_NAME, token, max_age=7 * 24 * 60 * 60, path="/api", httponly=True,
        secure=settings.NEWS_COOKIE_SECURE, samesite="lax",
    )
    return {"id": str(ADMIN_ID), "email": settings.NEWS_ADMIN_EMAIL, "role": "ADMIN"}


@router.post("/logout", status_code=204)
async def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/api")


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict[str, str]:
    return {"id": str(user.id), "email": user.email, "role": user.role}
