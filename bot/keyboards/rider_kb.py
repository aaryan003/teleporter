"""Inline keyboard builders for rider bot interactions (simplified)."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


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
            text=f"📦 Accept Pickup (+{detour_km}km, +₹20)",
            callback_data=f"return_accept_{order_id}",
        )],
        [InlineKeyboardButton(text="⏩ Skip, Head to Warehouse", callback_data="return_skip")],
    ])
