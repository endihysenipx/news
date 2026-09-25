from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    NEWS_DB_PASSWORD: str | None = None
    NEWS_DATABASE_URL: str | None = None
    NEWS_ADMIN_EMAIL: str
    NEWS_ADMIN_PASSWORD: str
    NEWS_SESSION_SECRET: str
    NEWS_COOKIE_SECURE: bool = False
    NEWS_PUBLIC_ORIGIN: str = "http://localhost:3101"
    NEWS_EMAIL_RECIPIENT: str = "180primex.eu@gmail.com"
    NEWS_ENABLE_COLLECTION: bool = True
    NEWS_AUTO_IMPORT_SNAPSHOT: bool = True
    OPENAI_API_KEY: str | None = None
    INTELLIGENCE_AI_MODEL: str = "gpt-5.4-nano"
    BRIGHTDATA_API_TOKEN: str | None = None
    BRIGHTDATA_LINKEDIN_POSTS_DATASET_ID: str = "gd_lyy3tktm25m4avu764"
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_USER: str | None = None
    EMAIL_PASSWORD: str | None = None

    @model_validator(mode="after")
    def database_connection(self) -> "Settings":
        if not self.NEWS_DATABASE_URL:
            if not self.NEWS_DB_PASSWORD:
                raise ValueError("Set NEWS_DB_PASSWORD or NEWS_DATABASE_URL in news/.env")
            self.NEWS_DATABASE_URL = f"postgresql+asyncpg://news:{self.NEWS_DB_PASSWORD}@localhost:5433/news"
        return self


settings = Settings()
