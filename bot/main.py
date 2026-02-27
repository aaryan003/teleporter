"""
TeleporterBot v2 — Telegram Bot Entry Point (aiogram 3.x)

Single bot codebase handling:
  - User flow: /start, booking, tracking, order history
  - Rider flow: task notifications, OTP entry, status (simplified)
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from config import settings
from handlers.user import router as user_router
from handlers.rider import router as rider_router

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Initialize and start the bot."""
    logger.info("🚀 TeleporterBot v2 starting...")

    # Redis FSM storage
    storage = RedisStorage.from_url(settings.REDIS_URL)

    # Bot instance
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Dispatcher
    dp = Dispatcher(storage=storage)

    # Register routers
    dp.include_router(user_router)
    dp.include_router(rider_router)

    # Start polling
    logger.info("✅ Bot is ready!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
