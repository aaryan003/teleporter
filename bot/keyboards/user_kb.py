"""Inline keyboard builders for user bot interactions."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Pickup timeslots: (start_hour, start_min, label)
PICKUP_SLOTS = [
    (9, 0, "9:00 AM - 12:00 PM"),
    (14, 0, "2:00 PM - 5:00 PM"),
    (18, 0, "6:00 PM - 9:00 PM"),
]
TZ = ZoneInfo("Asia/Kolkata")


def pickup_timeslot_keyboard() -> InlineKeyboardMarkup:
    """Pickup slot selection: next 2 days × 3 slots (9AM-12PM, 2PM-5PM, 6PM-9PM)."""
    now = datetime.now(TZ)
    buttons = []
    for day_offset in range(2):
        d = now.date() + timedelta(days=day_offset)
        day_label = "Today" if day_offset == 0 else "Tomorrow"
        for slot_idx, (h, m, label) in enumerate(PICKUP_SLOTS):
            slot_start = datetime(d.year, d.month, d.day, h, m, tzinfo=TZ)
            if day_offset == 0 and slot_start <= now:
                continue  # Skip past slots for today
            btn_label = f"📅 {day_label} · {label}"
            buttons.append([
                InlineKeyboardButton(
                    text=btn_label,
                    callback_data=f"pickup_slot_{day_offset}_{slot_idx}",
                )
            ])
    buttons.append([InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def parse_pickup_slot(callback_data: str) -> str | None:
    """
    Parse callback_data 'pickup_slot_D_S' into ISO datetime string.
    Returns None if invalid.
    """
    if not callback_data.startswith("pickup_slot_"):
        return None
    parts = callback_data.replace("pickup_slot_", "").split("_")
    if len(parts) != 2:
        return None
    try:
        day_offset = int(parts[0])
        slot_idx = int(parts[1])
        if slot_idx < 0 or slot_idx >= len(PICKUP_SLOTS):
            return None
        now = datetime.now(TZ)
        d = now.date() + timedelta(days=day_offset)
        h, m, _ = PICKUP_SLOTS[slot_idx]
        slot_start = datetime(d.year, d.month, d.day, h, m, tzinfo=TZ)
        return slot_start.isoformat()
    except (ValueError, IndexError):
        return None


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Book a Delivery", callback_data="book_delivery")],
        [InlineKeyboardButton(text="📋 My Orders", callback_data="my_orders")],
        [InlineKeyboardButton(text="💎 Subscriptions", callback_data="subscriptions"),
         InlineKeyboardButton(text="ℹ️ Help", callback_data="help")],
    ])


def package_size_keyboard() -> InlineKeyboardMarkup:
    """Package size selection — replaces weight tier."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📦 Small — fits in a bag",
            callback_data="size_SMALL",
        )],
        [InlineKeyboardButton(
            text="📦 Medium — backpack / shoe box",
            callback_data="size_MEDIUM",
        )],
        [InlineKeyboardButton(
            text="📦📦 Large — suitcase / TV box",
            callback_data="size_LARGE",
        )],
        [InlineKeyboardButton(
            text="🚛 Bulky — mattress / appliance",
            callback_data="size_BULKY",
        )],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_menu")],
    ])


def confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirm or cancel order."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Confirm Order", callback_data="confirm_order"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_order"),
        ],
        [InlineKeyboardButton(text="🤝 Batch & Save (15% off)", callback_data="toggle_batch")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_menu")],
    ])


def payment_method_keyboard() -> InlineKeyboardMarkup:
    """Payment method selection after order confirmation."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Cash on Delivery", callback_data="pay_COD")],
        [InlineKeyboardButton(text="💳 Card Payment", callback_data="pay_CARD"),
         InlineKeyboardButton(text="📱 UPI Payment", callback_data="pay_UPI")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_order")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_menu")],
    ])


def express_keyboard() -> InlineKeyboardMarkup:
    """Standard vs express delivery."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐢 Standard (Cheapest)", callback_data="speed_standard")],
        [InlineKeyboardButton(text="⚡ Express (2 hrs, 1.8x)", callback_data="speed_express")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_menu")],
    ])


def pickup_slot_keyboard(slots: list[dict]) -> InlineKeyboardMarkup:
    """Dynamic pickup slot selection."""
    buttons = []
    for slot in slots[:8]:  # Max 8 slots shown
        label = f"🕐 {slot['start']} — {slot.get('capacity', '?')} left"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"slot_{slot['id']}")])

    buttons.append([InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def subscription_plans_keyboard() -> InlineKeyboardMarkup:
    """Subscription plan selection."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎫 Starter — $9.99/mo (5 free)", callback_data="sub_STARTER")],
        [InlineKeyboardButton(text="💼 Business — $49.99/mo (25 free)", callback_data="sub_BUSINESS")],
        [InlineKeyboardButton(text="🏢 Enterprise — $199.99/mo (∞)", callback_data="sub_ENTERPRISE")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_menu")],
    ])


def order_actions_keyboard(order_id: str) -> InlineKeyboardMarkup:
    """Actions on a specific order."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📍 Track Order", callback_data=f"track_{order_id}")],
        [InlineKeyboardButton(text="📋 Full Details", callback_data=f"detail_{order_id}")],
        [InlineKeyboardButton(text="🔙 Back to Orders", callback_data="my_orders")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_menu")],
    ])


def order_list_keyboard(orders: list[dict]) -> InlineKeyboardMarkup:
    """List of orders as buttons."""
    buttons = []
    for order in orders[:10]:
        status_emoji = {
            "DELIVERED": "✅", "COMPLETED": "✅",
            "CANCELLED": "❌", "REFUNDED": "💸",
            "OUT_FOR_DELIVERY": "🚚", "AT_WAREHOUSE": "🏪",
            "PICKED_UP": "📦", "PICKUP_EN_ROUTE": "🏃",
            "ORDER_PLACED": "🆕", "PAYMENT_CONFIRMED": "💰",
        }.get(order.get("status", ""), "📦")

        btn_text = f"{status_emoji} {order['order_number']} — ${order['total_cost']}"
        buttons.append([InlineKeyboardButton(
            text=btn_text,
            callback_data=f"order_{order['id'][:8]}_{order['id']}",
        )])

    buttons.append([InlineKeyboardButton(text="🔙 Main Menu", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def tracking_keyboard(order_id: str, google_maps_url: str | None = None) -> InlineKeyboardMarkup:
    """Tracking view keyboard."""
    buttons = []
    if google_maps_url:
        buttons.append([InlineKeyboardButton(text="🗺️ Open in Google Maps", url=google_maps_url)])
    buttons.append([InlineKeyboardButton(text="🔄 Refresh Location", callback_data=f"track_{order_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 Back to Orders", callback_data="my_orders")])
    buttons.append([InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
