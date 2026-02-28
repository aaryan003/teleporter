"""
Application configuration from environment variables.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://teleporter:teleporter_secret@db:5432/teleporter"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Maps / Geocoding
    GOOGLE_MAPS_API_KEY: str = ""   # legacy, no longer used
    GEOAPIFY_API_KEY: str = ""

    # Razorpay
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    # n8n
    N8N_WEBHOOK_URL: str = "http://n8n:5678"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""

    # AI
    OPENAI_API_KEY: str = ""

    # JWT
    JWT_SECRET: str = "change_this"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # Business rules
    BUSINESS_HOURS_START: int = 8   # 8 AM
    BUSINESS_HOURS_END: int = 20    # 8 PM
    CUTOFF_BUFFER_MIN: int = 90     # minutes before close — no new slots
    MAX_PARCELS_PER_ROUTE: int = 5
    BATCH_THRESHOLD: int = 5         # parcels before triggering route optimizer
    MAX_DETOUR_KM: float = 2.0       # for return-trip pickups
    MAX_RETURN_PICKUPS: int = 3

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
