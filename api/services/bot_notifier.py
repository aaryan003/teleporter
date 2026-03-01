"""
Bot Notification Service — Sends Telegram messages from the FastAPI backend.

All outbound Telegram notifications are routed through this module.
Failures are logged but NEVER raise exceptions — fire-and-forget.
"""

import logging
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)


async def send_message(
    telegram_id: int,
    text: str,
    reply_markup: dict | None = None,
    parse_mode: str = "HTML",
) -> bool:
    """
    Send a Telegram message to a specific user via Bot API.

    Args:
        telegram_id: Recipient's Telegram user ID.
        text: Message text (HTML formatting supported).
        reply_markup: Optional inline keyboard markup dict.
        parse_mode: Telegram parse mode (default: HTML).

    Returns:
        True if message was sent successfully, False otherwise.
    """
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.error("BOT_TOKEN not configured — cannot send notification")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": telegram_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                logger.info(
                    "Notification sent: telegram_id=%s, text_preview='%s'",
                    telegram_id,
                    text[:80],
                )
                return True
            else:
                logger.warning(
                    "Notification failed: telegram_id=%s, status=%s, body=%s",
                    telegram_id,
                    resp.status_code,
                    resp.text[:200],
                )
                return False
    except Exception as e:
        logger.error(
            "Notification error: telegram_id=%s, error=%s",
            telegram_id,
            str(e),
        )
        return False


# ── Notification Templates ─────────────────────────────────

async def notify_application_received(telegram_id: int) -> bool:
    """5.2.1 — Sent to rider after application submission."""
    text = (
        "✅ <b>Application Received!</b>\n\n"
        "We've received your rider application. "
        "Our team will review it within 24-48 hours.\n\n"
        "We'll notify you right here once it's processed."
    )
    return await send_message(telegram_id, text)


async def notify_application_approved(
    telegram_id: int,
    full_name: str,
    employee_id: str,
) -> bool:
    """5.2.2 — Sent on admin APPROVE."""
    text = (
        f"🎉 <b>Congratulations {full_name}!</b>\n\n"
        f"Your rider application has been <b>APPROVED</b>.\n"
        f"Employee ID: <code>{employee_id}</code>\n\n"
        f"Tap the button below to open your Rider Dashboard and go on duty!"
    )
    markup = {
        "inline_keyboard": [
            [{"text": "🚴 Open Rider Dashboard", "callback_data": "rider_home"}],
        ]
    }
    return await send_message(telegram_id, text, reply_markup=markup)


async def notify_application_rejected(
    telegram_id: int,
    admin_note: str | None = None,
) -> bool:
    """5.2.3 — Sent on admin REJECT."""
    reason = admin_note or "No specific reason provided."
    text = (
        "❌ <b>Application Not Approved</b>\n\n"
        f"We could not approve your rider application.\n"
        f"Reason: {reason}\n\n"
        "You can re-apply after addressing the above or contact support for help."
    )
    markup = {
        "inline_keyboard": [
            [{"text": "🔄 Re-apply", "callback_data": "register_rider"}],
            [{"text": "📞 Contact Support", "url": "https://t.me/TeleporterSupport"}],
        ]
    }
    return await send_message(telegram_id, text, reply_markup=markup)


async def notify_pickup_assigned(
    telegram_id: int,
    order_number: str,
    pickup_address: str,
    pickup_slot: str | None = None,
    order_id: str | None = None,
) -> bool:
    """5.2.4 — When pickup_rider_id set on order."""
    slot_text = f"\n⏰ Slot: {pickup_slot}" if pickup_slot else ""
    text = (
        f"📦 <b>New Pickup Task!</b>\n\n"
        f"Order: <code>#{order_number}</code>\n"
        f"📍 Pickup: {pickup_address}{slot_text}\n\n"
        f"Tap the button below to get directions."
    )
    markup = None
    if order_id:
        markup = {
            "inline_keyboard": [
                [
                    {"text": "📍 Get Directions", "callback_data": f"rider_directions_pickup_{order_id}"},
                    {"text": "✅ I'm On My Way", "callback_data": f"rider_onmyway_{order_id}"},
                ],
            ]
        }
    return await send_message(telegram_id, text, reply_markup=markup)


async def notify_delivery_assigned(
    telegram_id: int,
    total_parcels: int,
    total_distance_km: float | None = None,
    route_id: str | None = None,
) -> bool:
    """5.2.5 — When delivery route assigned to rider."""
    dist_text = f"\n📏 Total distance: {total_distance_km:.1f} km" if total_distance_km else ""
    text = (
        f"🚚 <b>Delivery Route Ready!</b>\n\n"
        f"📦 {total_parcels} parcels assigned to you.{dist_text}\n\n"
        f"Tap below to view your optimized route."
    )
    markup = None
    if route_id:
        markup = {
            "inline_keyboard": [
                [{"text": "🗺️ View Route", "callback_data": f"rider_view_route_{route_id}"}],
            ]
        }
    return await send_message(telegram_id, text, reply_markup=markup)
