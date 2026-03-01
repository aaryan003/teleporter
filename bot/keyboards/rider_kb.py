"""Inline keyboard builders for rider bot interactions."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def rider_main_menu_keyboard(current_status: str = "OFF_DUTY") -> InlineKeyboardMarkup:
    """Rider main menu — dynamic based on current duty status."""
    buttons = []

    # Row 1: Availability toggle — show only the relevant toggle
    if current_status in ("OFF_DUTY",):
        buttons.append([InlineKeyboardButton(text="🟢 Go On Duty", callback_data="rider_go_on_duty")])
    else:
        buttons.append([InlineKeyboardButton(text="🔴 Go Off Duty", callback_data="rider_go_off_duty")])

    # Row 2: Active Tasks + View Route
    buttons.append([
        InlineKeyboardButton(text="📦 My Active Tasks", callback_data="rider_active_tasks"),
        InlineKeyboardButton(text="🗺️ View Route", callback_data="rider_view_route"),
    ])

    # Row 3: Earnings + Stats
    buttons.append([
        InlineKeyboardButton(text="💰 My Earnings", callback_data="rider_earnings"),
        InlineKeyboardButton(text="📊 My Stats", callback_data="rider_stats"),
    ])

    # Row 4: Profile + Help
    buttons.append([
        InlineKeyboardButton(text="⚙️ My Profile", callback_data="rider_profile"),
        InlineKeyboardButton(text="❓ Help", callback_data="rider_help"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def rider_task_keyboard(order_id: str) -> InlineKeyboardMarkup:
    """Rider task notification — acknowledge only (no reject)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ On My Way", callback_data=f"rider_ack_{order_id}")],
        [InlineKeyboardButton(text="🚨 Report Issue", callback_data=f"rider_issue_{order_id}")],
    ])


def rider_otp_keyboard(order_id: str, otp_type: str) -> InlineKeyboardMarkup:
    """Prompt rider to enter OTP."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🔑 Enter {otp_type.title()} OTP", callback_data=f"enter_otp_{otp_type}_{order_id}")],
    ])


def rider_return_pickup_keyboard(order_id: str, detour_km: float) -> InlineKeyboardMarkup:
    """Offer return-trip pickup to rider."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"📦 Accept Pickup (+{detour_km}km, +$5)",
            callback_data=f"return_accept_{order_id}",
        )],
        [InlineKeyboardButton(text="⏩ Skip, Head to Warehouse", callback_data="return_skip")],
    ])
