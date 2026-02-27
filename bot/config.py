"""Bot configuration from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = ""
    API_BASE_URL: str = "http://api:8000"
    REDIS_URL: str = "redis://redis:6379/0"
    ADMIN_TELEGRAM_ID: str = ""

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
