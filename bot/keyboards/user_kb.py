"""Inline keyboard builders for user bot interactions."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu after /start."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Book a Delivery", callback_data="book_delivery")],
        [InlineKeyboardButton(text="📋 My Orders", callback_data="my_orders")],
        [InlineKeyboardButton(text="💎 Subscription Plans", callback_data="subscriptions")],
        [InlineKeyboardButton(text="ℹ️ Help", callback_data="help")],
    ])


def weight_tier_keyboard() -> InlineKeyboardMarkup:
    """Package weight selection."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪶 Light (<5 kg) — Bike", callback_data="weight_LIGHT")],
        [InlineKeyboardButton(text="📦 Medium (5-20 kg) — Auto", callback_data="weight_MEDIUM")],
        [InlineKeyboardButton(text="📦📦 Heavy (>20 kg) — Van", callback_data="weight_HEAVY")],
    ])


def confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirm or cancel order."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Confirm Order", callback_data="confirm_order"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_order"),
        ],
        [InlineKeyboardButton(text="🤝 Batch & Save (15% off)", callback_data="toggle_batch")],
    ])


def payment_method_keyboard() -> InlineKeyboardMarkup:
    """Payment method selection after order confirmation."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Cash on Delivery", callback_data="pay_COD")],
        [InlineKeyboardButton(text="💳 Card Payment", callback_data="pay_CARD")],
        [InlineKeyboardButton(text="📱 UPI Payment", callback_data="pay_UPI")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_order")],
    ])


def express_keyboard() -> InlineKeyboardMarkup:
    """Standard vs express delivery."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐢 Standard (Cheapest)", callback_data="speed_standard")],
        [InlineKeyboardButton(text="⚡ Express (2 hrs, 1.8x)", callback_data="speed_express")],
    ])


def pickup_slot_keyboard(slots: list[dict]) -> InlineKeyboardMarkup:
    """Dynamic pickup slot selection."""
    buttons = []
    for slot in slots[:8]:  # Max 8 slots shown
        label = f"🕐 {slot['start']} — {slot.get('capacity', '?')} left"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"slot_{slot['id']}")])

    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def subscription_plans_keyboard() -> InlineKeyboardMarkup:
    """Subscription plan selection."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎫 Starter — ₹99/mo (5 free)", callback_data="sub_STARTER")],
        [InlineKeyboardButton(text="💼 Business — ₹499/mo (25 free)", callback_data="sub_BUSINESS")],
        [InlineKeyboardButton(text="🏢 Enterprise — ₹1,999/mo (Unlimited)", callback_data="sub_ENTERPRISE")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu")],
    ])


def order_actions_keyboard(order_id: str) -> InlineKeyboardMarkup:
    """Actions on a specific order."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📍 Track Order", callback_data=f"track_{order_id}")],
        [InlineKeyboardButton(text="❌ Cancel Order", callback_data=f"cancel_{order_id}")],
    ])
