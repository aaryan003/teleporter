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


def calendar_keyboard(year: int, month: int) -> InlineKeyboardMarkup:
    """Generate a calendar for date selection."""
    now = datetime.now(TZ)
    buttons = []
    
    # Month/Year header with navigation
    month_name = datetime(year, month, 1).strftime("%B %Y")
    prev_month = month - 1 if month > 1 else 12
    prev_year = year - 1 if month == 1 else year
    next_month = month + 1 if month < 12 else 1
    next_year = year + 1 if month == 12 else year
    
    buttons.append([
        InlineKeyboardButton(text="◀️", callback_data=f"cal_nav_{prev_year}_{prev_month}"),
        InlineKeyboardButton(text=f"📅 {month_name}", callback_data="cal_ignore"),
        InlineKeyboardButton(text="▶️", callback_data=f"cal_nav_{next_year}_{next_month}"),
    ])
    
    # Day headers
    buttons.append([
        InlineKeyboardButton(text="Mon", callback_data="cal_ignore"),
        InlineKeyboardButton(text="Tue", callback_data="cal_ignore"),
        InlineKeyboardButton(text="Wed", callback_data="cal_ignore"),
        InlineKeyboardButton(text="Thu", callback_data="cal_ignore"),
        InlineKeyboardButton(text="Fri", callback_data="cal_ignore"),
        InlineKeyboardButton(text="Sat", callback_data="cal_ignore"),
        InlineKeyboardButton(text="Sun", callback_data="cal_ignore"),
    ])
    
    # Calendar days
    first_day = datetime(year, month, 1)
    last_day = datetime(year, month + 1, 1) - timedelta(days=1) if month < 12 else datetime(year + 1, 1, 1) - timedelta(days=1)
    
    # Calculate starting weekday (Monday = 0)
    start_weekday = first_day.weekday()
    
    # Fill empty cells before first day
    week_row = []
    for _ in range(start_weekday):
        week_row.append(InlineKeyboardButton(text=" ", callback_data="cal_ignore"))
    
    # Add days of the month
    for day in range(1, last_day.day + 1):
        current_date = datetime(year, month, day, tzinfo=TZ)
        
        # Skip past dates
        if current_date.date() < now.date():
            day_text = f"~{day}~"
            callback = "cal_ignore"
        elif current_date.date() == now.date():
            day_text = f"📅 {day}"
            callback = f"cal_date_{year}_{month}_{day}"
        else:
            day_text = f"{day}"
            callback = f"cal_date_{year}_{month}_{day}"
        
        week_row.append(InlineKeyboardButton(text=day_text, callback_data=callback))
        
        # Start new week after Sunday
        if len(week_row) == 7:
            buttons.append(week_row)
            week_row = []
    
    # Fill remaining cells in last week
    while len(week_row) < 7:
        week_row.append(InlineKeyboardButton(text=" ", callback_data="cal_ignore"))
    if week_row:
        buttons.append(week_row)
    
    # Add back button
    buttons.append([InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def time_slots_keyboard(year: int, month: int, day: int) -> InlineKeyboardMarkup:
    """Show time slots for a specific date."""
    selected_date = datetime(year, month, day, tzinfo=TZ)
    date_label = selected_date.strftime("%A, %B %d, %Y")
    
    buttons = []
    
    # Time slots for the selected date
    time_slots = [
        (9, 0, "9:00 AM - 12:00 PM"),
        (12, 0, "12:00 PM - 3:00 PM"),
        (15, 0, "3:00 PM - 6:00 PM"),
        (18, 0, "6:00 PM - 9:00 PM"),
    ]
    
    now = datetime.now(TZ)
    
    for h, m, label in time_slots:
        slot_start = datetime(year, month, day, h, m, tzinfo=TZ)
        
        # Skip past slots for today
        if selected_date.date() == now.date() and slot_start <= now:
            continue
        
        btn_label = f"🕐 {label}"
        callback_data = f"slot_{year}_{month}_{day}_{h}_{m}"
        buttons.append([InlineKeyboardButton(text=btn_label, callback_data=callback_data)])
    
    # Navigation buttons
    buttons.append([
        InlineKeyboardButton(text="📅 Back to Calendar", callback_data=f"cal_nav_{year}_{month}"),
        InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_menu"),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def parse_calendar_callback(callback_data: str) -> dict | None:
    """Parse calendar callback data and return action info."""
    if callback_data.startswith("cal_nav_"):
        parts = callback_data.replace("cal_nav_", "").split("_")
        if len(parts) == 2:
            return {"action": "navigate", "year": int(parts[0]), "month": int(parts[1])}
    
    elif callback_data.startswith("cal_date_"):
        parts = callback_data.replace("cal_date_", "").split("_")
        if len(parts) == 3:
            return {"action": "select_date", "year": int(parts[0]), "month": int(parts[1]), "day": int(parts[2])}
    
    elif callback_data.startswith("slot_"):
        parts = callback_data.replace("slot_", "").split("_")
        if len(parts) == 5:
            year, month, day, hour, minute = map(int, parts)
            slot_datetime = datetime(year, month, day, hour, minute, tzinfo=TZ)
            return {
                "action": "select_slot",
                "datetime": slot_datetime.isoformat(),
                "year": year,
                "month": month,
                "day": day,
                "hour": hour,
                "minute": minute
            }
    
    return None


def pickup_timeslot_keyboard() -> InlineKeyboardMarkup:
    """Legacy function - now redirects to calendar."""
    now = datetime.now(TZ)
    return calendar_keyboard(now.year, now.month)


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
