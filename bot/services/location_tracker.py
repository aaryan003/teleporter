"""
Location Tracker — Background task that periodically prompts on-duty riders
to share their live location via Telegram, then posts it to the API.

Spec Section 9.1: "Bot requests location every LOCATION_UPDATE_INTERVAL_SEC
from riders with status ON_DUTY or ON_DELIVERY."

This runs as an asyncio background task inside the bot process.
"""

import asyncio
import logging

import httpx
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from config import settings

logger = logging.getLogger(__name__)
API = settings.API_BASE_URL


async def _get_active_riders() -> list[dict]:
    """Fetch riders currently on duty or on delivery."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            riders = []
            for status in ("ON_DUTY", "ON_DELIVERY", "ON_PICKUP"):
                resp = await client.get(f"{API}/api/riders/", params={"status": status})
                if resp.status_code == 200:
                    riders.extend(resp.json())
            return riders
    except Exception as e:
        logger.error("Failed to fetch active riders: %s", e)
        return []


async def _push_location_to_api(rider_id: str, lat: float, lng: float) -> bool:
    """POST rider's location update to API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(
                f"{API}/api/riders/{rider_id}/location",
                json={"lat": lat, "lng": lng},
            )
            return resp.status_code == 200
    except Exception as e:
        logger.error("Failed to push location for rider %s: %s", rider_id, e)
        return False


async def request_location_from_rider(bot: Bot, telegram_id: int) -> bool:
    """
    Send a Telegram request-location keyboard to rider.
    The rider taps "Share Location" and the bot captures it.
    """
    try:
        location_button = KeyboardButton(text="📍 Share Location", request_location=True)
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[location_button]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await bot.send_message(
            chat_id=telegram_id,
            text="📍 Please share your current location:",
            reply_markup=keyboard,
        )
        return True
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        # Expected for riders who haven't started the bot or have blocked it.
        # Telegram requires users to initiate a conversation first.
        logger.warning(
            "Cannot reach rider %s — they may not have started the bot yet: %s",
            telegram_id, e.message,
        )
        return False
    except Exception as e:
        logger.error("Failed to request location from %s: %s", telegram_id, e)
        return False


async def location_tracker_loop(bot: Bot):
    """
    Background loop that runs every LOCATION_UPDATE_INTERVAL_SEC.
    For each active rider, requests location sharing.

    Note: The actual location capture is handled by a message handler
    in rider_menu.py that listens for location messages.
    """
    interval = getattr(settings, "LOCATION_UPDATE_INTERVAL_SEC", 120)
    logger.info("📍 Location tracker started (interval=%ds)", interval)

    while True:
        try:
            riders = await _get_active_riders()
            if riders:
                logger.info("📍 Requesting location from %d active riders", len(riders))
                for rider in riders:
                    await request_location_from_rider(bot, rider["telegram_id"])
                    await asyncio.sleep(0.1)  # Rate-limit Telegram API calls
        except Exception as e:
            logger.error("Location tracker loop error: %s", e)

        await asyncio.sleep(interval)
