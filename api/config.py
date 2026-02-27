import os
from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://teleporter:teleporter@db:5432/teleporter",
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    google_maps_api_key: str | None = os.getenv("GOOGLE_MAPS_API_KEY")
    razorpay_key_id: str | None = os.getenv("RAZORPAY_KEY_ID")
    razorpay_key_secret: str | None = os.getenv("RAZORPAY_KEY_SECRET")
    jwt_secret: str = os.getenv("JWT_SECRET", "changeme")
    telegram_bot_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

