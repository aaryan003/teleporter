"""
User Telegram Bot Handler — Booking flow, tracking, order history.

FSM Flow:
  /start → Register/Welcome → Main Menu
  Book Delivery → Pickup Address → Drop Address → Weight Tier
  → Price Estimate → Confirm & Pay → Select Pickup Slot → Done
"""

import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import settings
from states.user_states import BookingFlow
from keyboards.user_kb import (
    main_menu_keyboard, weight_tier_keyboard, confirm_keyboard,
    payment_method_keyboard, subscription_plans_keyboard, order_actions_keyboard,
)

router = Router()
API = settings.API_BASE_URL


async def _api_call(method: str, endpoint: str, **kwargs) -> dict | None:
    """Helper to call FastAPI backend."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if method == "GET":
                resp = await client.get(f"{API}{endpoint}", params=kwargs.get("params"))
            elif method == "POST":
                resp = await client.post(f"{API}{endpoint}", json=kwargs.get("json"))
            elif method == "PATCH":
                resp = await client.patch(f"{API}{endpoint}", json=kwargs.get("json"))
            else:
                return None
            if resp.status_code in (200, 201):
                return resp.json()
            return None
    except Exception as e:
        print(f"⚠️ API call error: {e}")
        return None


# ── /start ─────────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start — register or welcome back."""
    await state.clear()

    # Register or get user
    user = await _api_call("POST", "/api/users/", json={
        "telegram_id": message.from_user.id,
        "full_name": message.from_user.full_name,
        "telegram_username": message.from_user.username,
    })

    if user:
        await message.answer(
            f"👋 Welcome to <b>TeleporterBot Logistics</b>!\n\n"
            f"Hello <b>{message.from_user.first_name}</b>! "
            f"Fast, reliable, warehouse-backed deliveries at your fingertips.\n\n"
            f"What would you like to do?",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await message.answer(
            "👋 Welcome! Let's set up your account.\n"
            "Please share your phone number to get started.",
        )


# ── Main Menu Callbacks ───────────────────────────────────

@router.callback_query(F.data == "book_delivery")
async def start_booking(callback: CallbackQuery, state: FSMContext):
    """Start the booking flow."""
    await callback.answer()
    await state.set_state(BookingFlow.waiting_pickup_address)
    await callback.message.edit_text(
        "📦 <b>New Delivery</b>\n\n"
        "📍 Please send the <b>pickup address</b>.\n\n"
        "You can:\n"
        "• Type the full address\n"
        "• Send a 📍 location pin",
    )


@router.callback_query(F.data == "my_orders")
async def show_orders(callback: CallbackQuery):
    """Show user's order history."""
    await callback.answer()

    orders = await _api_call("GET", f"/api/orders/user/{callback.from_user.id}")

    if not orders:
        await callback.message.edit_text(
            "📋 <b>Your Orders</b>\n\n"
            "No orders yet! Book your first delivery.",
            reply_markup=main_menu_keyboard(),
        )
        return

    text = "📋 <b>Your Orders</b>\n\n"
    for order in orders[:10]:
        emoji = {"DELIVERED": "✅", "CANCELLED": "❌", "OUT_FOR_DELIVERY": "🚚"}.get(
            order["status"], "📦"
        )
        text += (
            f"{emoji} <code>{order['order_number']}</code>\n"
            f"   {order['pickup_address'][:30]}... → {order['drop_address'][:30]}...\n"
            f"   ₹{order['total_cost']} | {order['status'].replace('_', ' ').title()}\n\n"
        )

    await callback.message.edit_text(text, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "subscriptions")
async def show_subscriptions(callback: CallbackQuery):
    """Show subscription plans."""
    await callback.answer()
    await callback.message.edit_text(
        "💎 <b>Subscription Plans</b>\n\n"
        "Save on every delivery with a monthly plan!\n\n"
        "🎫 <b>Starter</b> — ₹99/month\n"
        "   • 5 free deliveries\n"
        "   • Priority support\n\n"
        "💼 <b>Business</b> — ₹499/month\n"
        "   • 25 free deliveries\n"
        "   • 5% discount on all orders\n"
        "   • API access\n\n"
        "🏢 <b>Enterprise</b> — ₹1,999/month\n"
        "   • Unlimited deliveries\n"
        "   • 10% discount on all orders\n"
        "   • Dedicated account manager\n"
        "   • SLA guarantees",
        reply_markup=subscription_plans_keyboard(),
    )


@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    """Show help information."""
    await callback.answer()
    await callback.message.edit_text(
        "ℹ️ <b>Help & Support</b>\n\n"
        "<b>How it works:</b>\n"
        "1️⃣ Send pickup & drop-off addresses\n"
        "2️⃣ Choose package weight\n"
        "3️⃣ Confirm price & pay\n"
        "4️⃣ Select a pickup time slot\n"
        "5️⃣ Our rider picks up your parcel\n"
        "6️⃣ Parcel goes to our warehouse\n"
        "7️⃣ Optimized delivery route assigned\n"
        "8️⃣ Delivered to recipient! 🎉\n\n"
        "<b>Commands:</b>\n"
        "/start — Main menu\n"
        "/orders — Your order history\n"
        "/help — This message\n\n"
        "📞 Support: Contact @TeleporterBotSupport",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Return to main menu."""
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "📦 <b>TeleporterBot Logistics</b>\n\nWhat would you like to do?",
        reply_markup=main_menu_keyboard(),
    )


# ── Booking Flow: Pickup Address ──────────────────────────

@router.message(BookingFlow.waiting_pickup_address)
async def receive_pickup_address(message: Message, state: FSMContext):
    """Receive pickup address (text or location)."""
    if message.location:
        address = f"{message.location.latitude},{message.location.longitude}"
        await state.update_data(pickup_address=address, pickup_type="location")
    else:
        await state.update_data(pickup_address=message.text, pickup_type="text")

    await state.set_state(BookingFlow.waiting_drop_address)
    await message.answer(
        "✅ Pickup address recorded!\n\n"
        "📍 Now send the <b>drop-off address</b>.",
    )


# ── Booking Flow: Drop Address ────────────────────────────

@router.message(BookingFlow.waiting_drop_address)
async def receive_drop_address(message: Message, state: FSMContext):
    """Receive drop-off address."""
    if message.location:
        address = f"{message.location.latitude},{message.location.longitude}"
        await state.update_data(drop_address=address)
    else:
        await state.update_data(drop_address=message.text)

    await state.set_state(BookingFlow.waiting_weight_tier)
    await message.answer(
        "✅ Drop-off address recorded!\n\n"
        "📦 How heavy is your package?",
        reply_markup=weight_tier_keyboard(),
    )


# ── Booking Flow: Weight Tier ─────────────────────────────

@router.callback_query(F.data.startswith("weight_"), BookingFlow.waiting_weight_tier)
async def receive_weight(callback: CallbackQuery, state: FSMContext):
    """Receive weight tier selection."""
    await callback.answer()
    weight = callback.data.replace("weight_", "")
    await state.update_data(weight_tier=weight)

    # Get price estimate
    data = await state.get_data()
    estimate = await _api_call("POST", "/api/orders/estimate", json={
        "telegram_id": callback.from_user.id,
        "pickup_address": data["pickup_address"],
        "drop_address": data["drop_address"],
        "weight_tier": weight,
        "is_express": False,
        "is_batch_eligible": True,
    })

    if not estimate:
        await callback.message.edit_text(
            "❌ Sorry, we couldn't calculate the price. Please try again.",
            reply_markup=main_menu_keyboard(),
        )
        await state.clear()
        return

    await state.update_data(estimate=estimate)
    await state.set_state(BookingFlow.confirm_estimate)

    vehicle_emoji = {"BIKE": "🏍️", "AUTO": "🛺", "VAN": "🚐"}.get(
        estimate.get("vehicle_type", "BIKE"), "🚚"
    )

    text = (
        f"💰 <b>Price Estimate</b>\n\n"
        f"📏 Distance: {estimate['distance_km']} km\n"
        f"⏱️ Duration: ~{estimate['duration_min']} min\n"
        f"{vehicle_emoji} Vehicle: {estimate.get('vehicle_type', 'BIKE')}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💵 Base cost: ₹{estimate['base_cost']}\n"
    )
    if estimate.get("surge_multiplier", 1.0) > 1.0:
        text += f"⚡ Surge: {estimate['surge_multiplier']}x — {estimate.get('surge_reason', '')}\n"
    if estimate.get("batch_discount", 0) > 0:
        text += f"🤝 Batch discount: -₹{estimate['batch_discount']}\n"

    text += (
        f"━━━━━━━━━━━━━━━━\n"
        f"<b>Total: ₹{estimate['total_cost']}</b>\n"
    )

    await callback.message.edit_text(text, reply_markup=confirm_keyboard())


# ── Booking Flow: Confirm ─────────────────────────────────

@router.callback_query(F.data == "confirm_order", BookingFlow.confirm_estimate)
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    """User confirms — show payment method options."""
    await callback.answer()
    await state.set_state(BookingFlow.waiting_payment)
    await callback.message.edit_text(
        "💳 <b>Choose Payment Method</b>\n\n"
        "How would you like to pay?",
        reply_markup=payment_method_keyboard(),
    )


@router.callback_query(F.data.startswith("pay_"), BookingFlow.waiting_payment)
async def handle_payment(callback: CallbackQuery, state: FSMContext):
    """User selects payment method — create order and confirm."""
    payment_mode = callback.data.replace("pay_", "")  # COD, CARD, or UPI
    await callback.answer(f"Processing {payment_mode} payment...")
    data = await state.get_data()

    # Create order via API
    order = await _api_call("POST", "/api/orders/", json={
        "telegram_id": callback.from_user.id,
        "pickup_address": data["pickup_address"],
        "drop_address": data["drop_address"],
        "weight_tier": data["weight_tier"],
        "is_express": data.get("is_express", False),
        "is_batch_eligible": data.get("is_batch_eligible", True),
        "payment_mode": payment_mode,
    })

    if not order:
        await callback.message.edit_text(
            "❌ Failed to create order. Please try again.",
            reply_markup=main_menu_keyboard(),
        )
        await state.clear()
        return

    # Confirm payment via API
    payment_result = await _api_call(
        "POST",
        f"/api/payments/confirm/{order['id']}?payment_mode={payment_mode}",
    )

    mode_labels = {
        "COD": "💵 Cash on Delivery",
        "CARD": "💳 Card (simulated)",
        "UPI": "📱 UPI (simulated)",
    }
    mode_label = mode_labels.get(payment_mode, payment_mode)

    if payment_result and payment_result.get("status") == "confirmed":
        otp_text = ""
        if payment_result.get("pickup_otp"):
            otp_text = (
                f"\n🔑 Pickup OTP: <code>{payment_result['pickup_otp']}</code>"
                f"\n🔑 Drop-off OTP: <code>{payment_result['drop_otp']}</code>"
                f"\n\n<i>Share these with the rider at pickup and delivery.</i>"
            )

        cod_note = ""
        if payment_mode == "COD":
            cod_note = f"\n\n💵 <b>Please keep ₹{order['total_cost']} ready</b> for the rider."

        await callback.message.edit_text(
            f"✅ <b>Order #{order['order_number']} Confirmed!</b>\n\n"
            f"🧾 Payment: {mode_label}\n"
            f"💰 Amount: ₹{order['total_cost']}"
            f"{cod_note}"
            f"{otp_text}\n\n"
            f"📦 We're scheduling your pickup now!",
        )
    else:
        await callback.message.edit_text(
            f"✅ <b>Order #{order['order_number']} Created!</b>\n\n"
            f"🧾 Payment: {mode_label}\n"
            f"💰 Amount: ₹{order['total_cost']}\n\n"
            f"⏳ Payment is being processed...",
        )

    await state.clear()


@router.callback_query(F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    """User cancels the booking."""
    await callback.answer("Order cancelled.")
    await state.clear()
    await callback.message.edit_text(
        "❌ Order cancelled.\n\nNo charges applied.",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "toggle_batch")
async def toggle_batch(callback: CallbackQuery, state: FSMContext):
    """Toggle batch eligibility for discount."""
    data = await state.get_data()
    current = data.get("is_batch_eligible", True)
    await state.update_data(is_batch_eligible=not current)

    status = "ON ✅" if not current else "OFF ❌"
    await callback.answer(f"Batch & Save: {status}")


# ── /orders shortcut ──────────────────────────────────────

@router.message(Command("orders"))
async def cmd_orders(message: Message):
    """Show order history."""
    orders = await _api_call("GET", f"/api/orders/user/{message.from_user.id}")

    if not orders:
        await message.answer("📋 No orders yet!")
        return

    text = "📋 <b>Your Orders</b>\n\n"
    for order in orders[:5]:
        text += f"📦 <code>{order['order_number']}</code> — {order['status'].replace('_', ' ').title()} — ₹{order['total_cost']}\n"

    await message.answer(text)


# ── /help ──────────────────────────────────────────────────

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Show help."""
    await message.answer(
        "ℹ️ <b>TeleporterBot Help</b>\n\n"
        "/start — Main menu & Book delivery\n"
        "/orders — View your orders\n"
        "/help — This message\n\n"
        "📞 Support: @TeleporterBotSupport",
    )
