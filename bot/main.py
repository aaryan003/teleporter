"""
TeleporterBot v2 — Telegram Bot Entry Point (aiogram 3.x)

Single bot codebase handling:
  - User flow: /start, booking, tracking, order history
  - Rider flow: task notifications, OTP entry, status (simplified)
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Update

from config import settings
from handlers.user import router as user_router
from handlers.rider import router as rider_router
from handlers.rider_onboarding import router as rider_onboarding_router
from handlers.rider_menu import router as rider_menu_router
from services.location_tracker import location_tracker_loop

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def ignore_message_not_modified_middleware(
    handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
    event: Update,
    data: dict[str, Any],
) -> Any:
    """Global middleware: silently drop 'message is not modified' errors."""
    try:
        return await handler(event, data)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return  # swallow silently — harmless double-tap
        raise


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

    # Global middleware — swallow harmless Telegram "not modified" errors
    dp.update.outer_middleware(ignore_message_not_modified_middleware)

    # Register routers — order matters: user first, then rider onboarding, then rider menu, then rider
    dp.include_router(user_router)
    dp.include_router(rider_onboarding_router)
    dp.include_router(rider_menu_router)
    dp.include_router(rider_router)

    # Start location tracker background task
    asyncio.create_task(location_tracker_loop(bot))

    # Start polling
    logger.info("✅ Bot is ready!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

