"""
Notification Service — Send messages to users and riders via Telegram Bot API.
"""

import httpx
from config import settings

TELEGRAM_API = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"


async def send_telegram_message(
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
    reply_markup: dict | None = None,
) -> bool:
    """Send a message to a Telegram user/rider."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup

            resp = await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)
            return resp.status_code == 200
    except Exception as e:
        print(f"⚠️ Telegram notification error: {e}")
        return False


async def notify_user_order_status(
    telegram_id: int,
    order_number: str,
    status: str,
    extra_info: str = "",
):
    """Send order status update to user."""
    status_emojis = {
        "PAYMENT_CONFIRMED": "✅",
        "PICKUP_SCHEDULED": "📅",
        "PICKUP_RIDER_ASSIGNED": "🚴",
        "PICKUP_EN_ROUTE": "🏃",
        "PICKED_UP": "📦",
        "AT_WAREHOUSE": "🏪",
        "OUT_FOR_DELIVERY": "🚚",
        "DELIVERED": "🎉",
        "CANCELLED": "❌",
    }
    emoji = status_emojis.get(status, "📋")
    status_display = status.replace("_", " ").title()

    message = (
        f"{emoji} <b>Order #{order_number}</b>\n"
        f"Status: <b>{status_display}</b>\n"
    )
    if extra_info:
        message += f"\n{extra_info}"

    await send_telegram_message(telegram_id, message)


async def notify_rider_task(
    telegram_id: int,
    task_type: str,  # "PICKUP" or "DELIVERY"
    task_details: dict,
):
    """Send task assignment to rider."""
    if task_type == "PICKUP":
        message = (
            f"📦 <b>New Pickup Task</b>\n\n"
            f"📍 Address: {task_details.get('address', 'N/A')}\n"
            f"📋 Parcels: {task_details.get('count', 1)}\n"
            f"⏰ Slot: {task_details.get('slot', 'ASAP')}\n\n"
            f"🗺️ <a href=\"https://www.google.com/maps/dir/?api=1"
            f"&destination={task_details.get('lat', 0)},{task_details.get('lng', 0)}\">Navigate</a>"
        )
    else:
        stops = task_details.get("stops", [])
        message = (
            f"🚚 <b>Delivery Route Assigned</b>\n\n"
            f"📦 Parcels: {len(stops)}\n"
            f"📏 Total: {task_details.get('total_km', 0)} km\n"
            f"⏱️ Est: {task_details.get('total_min', 0)} min\n\n"
        )
        for i, stop in enumerate(stops, 1):
            message += f"{i}️⃣ {stop.get('address', 'N/A')}\n"

    await send_telegram_message(telegram_id, message)


async def notify_admin(message: str):
    """Send alert to admin via Telegram."""
    from config import settings as s
    admin_id = getattr(s, "ADMIN_TELEGRAM_ID", None)
    if admin_id:
        await send_telegram_message(int(admin_id), f"🔔 <b>Admin Alert</b>\n\n{message}")
