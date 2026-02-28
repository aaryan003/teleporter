"""
User Telegram Bot Handler — Booking flow, tracking, order history.

FSM Flow:
  /start → Register/Welcome → Main Menu
  Book Delivery → Pickup Address → Drop Address → Package Size
  → Price Estimate → Confirm & Pay → Done

Features:
  - Browsable order history (last 10 orders)
  - Per-order detail view with tracking
  - Live tracking with Google Maps link & rider ETA
  - All interactions via inline keyboards (no free-text except addresses)
"""

import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from config import settings
from states.user_states import BookingFlow, UserRegistration
from keyboards.user_kb import (
    main_menu_keyboard, package_size_keyboard, confirm_keyboard,
    payment_method_keyboard, subscription_plans_keyboard,
    order_actions_keyboard, order_list_keyboard, tracking_keyboard,
)

router = Router()
API = settings.API_BASE_URL


async def safe_edit(callback: CallbackQuery, text: str, **kwargs):
    """Edit message, silently ignoring 'message not modified' errors."""
    try:
        await callback.message.edit_text(text, **kwargs)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


async def _api_call(method: str, endpoint: str, **kwargs) -> dict | list | None:
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
            print(f"⚠️ API error: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"⚠️ API call error: {e}")
        return None


# ── /start ─────────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start — register or welcome back."""
    await state.clear()

    # Check if user exists
    print(f"🔍 Checking user: {message.from_user.id}")
    user = await _api_call("GET", f"/api/users/{message.from_user.id}")
    print(f"📊 User data: {user}")

    if user:
        # User exists - check if they have phone
        if user.get("phone"):
            # Existing user with phone - show welcome back message
            await message.answer(
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📦 <b>TeleporterBot Logistics</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Welcome back <b>{message.from_user.first_name}</b>! 👋\n\n"
                f"Fast, reliable, warehouse-backed\n"
                f"deliveries at your fingertips.\n\n"
                f"What would you like to do?",
                reply_markup=main_menu_keyboard(),
            )
        else:
            # User exists but no phone - ask for phone
            await state.set_state(UserRegistration.waiting_phone)
            kb = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="📱 Share Contact", request_contact=True)]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            await message.answer(
                "👋 Welcome back! Let's complete your profile.\n"
                "Please share your phone number to continue.",
                reply_markup=kb
            )
    else:
        # New user - create and ask for phone
        print(f"➕ Creating new user: {message.from_user.id}")
        user = await _api_call("POST", "/api/users/", json={
            "telegram_id": message.from_user.id,
            "full_name": message.from_user.full_name,
            "telegram_username": message.from_user.username,
        })
        print(f"✅ Created user: {user}")
        
        await state.set_state(UserRegistration.waiting_phone)
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Share Contact", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer(
            "👋 Welcome! Let's set up your account.\n"
            "Please share your phone number to get started.",
            reply_markup=kb
        )

@router.message(UserRegistration.waiting_phone, F.contact | F.text)
async def process_phone(message: Message, state: FSMContext):
    """Handle the user sharing their contact."""
    phone = message.contact.phone_number if message.contact else message.text
    
    user = await _api_call("PATCH", f"/api/users/{message.from_user.id}", json={
        "phone": phone
    })
    
    if user:
        await state.clear()
        await message.answer(
            "✅ <b>Registration complete!</b>\n\n"
            "Welcome to TeleporterBot. What would you like to do?",
            reply_markup=main_menu_keyboard()
        )
    else:
        await message.answer("⚠️ Failed to save your phone number. Please try again.")


# ── Main Menu Callbacks ───────────────────────────────────

@router.callback_query(F.data == "book_delivery")
async def start_booking(callback: CallbackQuery, state: FSMContext):
    """Start the booking flow."""
    await callback.answer()
    await state.set_state(BookingFlow.waiting_pickup_address)
    await callback.message.edit_text(
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📦 <b>New Delivery</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📍 Send the <b>pickup address</b>:\n\n"
        "• Type the full address, or\n"
        "• Send a 📍 location pin",
    )


# ── My Orders ─────────────────────────────────────────────

@router.callback_query(F.data == "my_orders")
async def show_orders(callback: CallbackQuery):
    """Show user's recent orders as a browsable list."""
    await callback.answer()

    orders = await _api_call("GET", f"/api/orders/user/{callback.from_user.id}", params={"limit": 10})

    if not orders:
        await safe_edit(
            callback,
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 <b>Your Orders</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "No orders yet! 📦\n"
            "Book your first delivery to get started.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await safe_edit(
        callback,
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 <b>Your Orders</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Tap an order to view details\n"
        "or track your delivery:",
        reply_markup=order_list_keyboard(orders),
    )


# ── Order Detail View ─────────────────────────────────────

@router.callback_query(F.data.startswith("order_"))
async def show_order_detail(callback: CallbackQuery):
    """Show detailed view of a specific order."""
    await callback.answer()
    parts = callback.data.split("_", 2)
    order_id = parts[2] if len(parts) > 2 else parts[1]

    order = await _api_call("GET", f"/api/orders/{order_id}")
    if not order:
        await callback.message.edit_text(
            "❌ Could not load order details.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await _render_order_detail(callback, order, order_id)


async def _render_order_detail(callback: CallbackQuery, order: dict, order_id: str):
    """Render the order detail message."""
    status_emoji = {
        "DELIVERED": "✅", "COMPLETED": "✅",
        "CANCELLED": "❌", "REFUNDED": "💸",
        "OUT_FOR_DELIVERY": "🚚", "AT_WAREHOUSE": "🏪",
        "PICKED_UP": "📦", "PICKUP_EN_ROUTE": "🏃",
        "ORDER_PLACED": "🆕", "PAYMENT_CONFIRMED": "💰",
        "PICKUP_SCHEDULED": "📅", "PICKUP_RIDER_ASSIGNED": "🚴",
        "DELIVERY_RIDER_ASSIGNED": "🛵", "IN_TRANSIT_TO_WAREHOUSE": "🚗",
    }.get(order.get("status", ""), "📦")

    vehicle_emoji = {
        "BIKE": "🏍️", "MINI_VAN": "🚐",
        "MINI_TRUCK": "🚛", "TRUCK": "🚚",
    }.get(order.get("vehicle", ""), "🚚")

    size_label = {
        "SMALL": "📦 Small",
        "MEDIUM": "📦 Medium",
        "LARGE": "📦📦 Large",
        "BULKY": "🚛 Bulky",
    }.get(order.get("package_size", ""), order.get("package_size", "N/A"))

    payment_emoji = {
        "PENDING": "⏳", "PAID": "✅",
        "REFUNDED": "💸", "FAILED": "❌",
    }.get(order.get("payment", ""), "")

    date_str = ""
    if order.get("created_at"):
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(order["created_at"].replace("Z", "+00:00"))
            date_str = dt.strftime("%b %d, %I:%M %p")
        except Exception:
            date_str = order["created_at"][:16]

    text = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 <b>Order #{order['order_number']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{status_emoji} Status: <b>{order['status'].replace('_', ' ').title()}</b>\n"
        f"📅 Placed: {date_str}\n\n"
        f"📍 <b>Pickup:</b>\n"
        f"   {order['pickup_address'][:60]}\n\n"
        f"📍 <b>Drop-off:</b>\n"
        f"   {order['drop_address'][:60]}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{size_label}  •  {vehicle_emoji} {order.get('vehicle', 'N/A')}\n"
    )

    if order.get("distance_km"):
        text += f"📏 {order['distance_km']} km  •  ⏱️ ~{order.get('duration_min', '?')} min\n"

    text += (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Total: ${order['total_cost']}</b>\n"
        f"{payment_emoji} Payment: {order.get('payment', 'N/A')}"
    )

    if order.get("payment_mode"):
        mode_label = {"COD": "Cash", "CARD": "Card", "UPI": "UPI"}.get(order["payment_mode"], order["payment_mode"])
        text += f" ({mode_label})"

    if order.get("delivered_at"):
        text += f"\n✅ Delivered: {order['delivered_at'][:16]}"

    await callback.message.edit_text(
        text,
        reply_markup=order_actions_keyboard(order_id),
    )


# ── Order Detail (from detail_ callback) ──────────────────

@router.callback_query(F.data.startswith("detail_"))
async def show_order_detail_from_detail(callback: CallbackQuery):
    """Show detailed view from the detail button."""
    await callback.answer()
    order_id = callback.data.replace("detail_", "")

    order = await _api_call("GET", f"/api/orders/{order_id}")
    if not order:
        await callback.message.edit_text(
            "❌ Could not load order details.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await _render_order_detail(callback, order, order_id)


# ── Live Tracking ──────────────────────────────────────────

@router.callback_query(F.data.startswith("track_"))
async def track_order(callback: CallbackQuery):
    """Show live tracking info with rider location and ETA."""
    await callback.answer("Loading tracking...")
    order_id = callback.data.replace("track_", "")

    tracking = await _api_call("GET", f"/api/orders/{order_id}/track")
    if not tracking:
        await callback.message.edit_text(
            "❌ Could not load tracking info.\n"
            "The order may not have an assigned rider yet.",
            reply_markup=order_actions_keyboard(order_id),
        )
        return

    status_emoji = {
        "PICKUP_RIDER_ASSIGNED": "🚴", "PICKUP_EN_ROUTE": "🏃",
        "OUT_FOR_DELIVERY": "🚚", "DELIVERY_RIDER_ASSIGNED": "🛵",
        "DELIVERED": "✅", "AT_WAREHOUSE": "🏪",
    }.get(tracking.get("status", ""), "📦")

    vehicle_emoji = {
        "BIKE": "🏍️", "MINI_VAN": "🚐",
        "MINI_TRUCK": "🚛", "TRUCK": "🚚",
    }.get(tracking.get("rider_vehicle", ""), "🚚")

    text = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>Live Tracking</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 Order: <code>{tracking['order_number']}</code>\n"
        f"{status_emoji} Status: <b>{tracking['status'].replace('_', ' ').title()}</b>\n\n"
    )

    if tracking.get("rider_name"):
        text += (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Your Rider</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"   {tracking['rider_name']}\n"
            f"   {vehicle_emoji} {tracking.get('rider_vehicle', 'N/A')}\n"
        )
        if tracking.get("rider_phone"):
            text += f"   📞 {tracking['rider_phone']}\n"
        text += "\n"

    if tracking.get("estimated_arrival_min") is not None:
        eta = tracking["estimated_arrival_min"]
        if eta <= 5:
            eta_text = "🟢 <b>Almost there!</b> (~{} min)".format(eta)
        elif eta <= 15:
            eta_text = "🟡 <b>~{} min away</b>".format(eta)
        else:
            eta_text = "🔵 <b>~{} min away</b>".format(eta)
        text += f"⏱️ ETA: {eta_text}\n\n"

    if tracking.get("drop_address"):
        text += (
            f"📍 <b>Delivering to:</b>\n"
            f"   {tracking['drop_address'][:60]}\n\n"
        )

    if not tracking.get("rider_name"):
        text += (
            "⏳ <i>No rider assigned yet.</i>\n"
            "<i>We'll notify you when a rider is on the way!</i>\n\n"
        )

    if tracking.get("last_location_update"):
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(tracking["last_location_update"].replace("Z", "+00:00"))
            text += f"🕐 <i>Last updated: {dt.strftime('%I:%M %p')}</i>\n"
        except Exception:
            pass

    await callback.message.edit_text(
        text,
        reply_markup=tracking_keyboard(order_id, tracking.get("google_maps_url")),
    )


# ── Subscriptions ─────────────────────────────────────────

@router.callback_query(F.data == "subscriptions")
async def show_subscriptions(callback: CallbackQuery):
    """Show subscription plans."""
    await callback.answer()
    await callback.message.edit_text(
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💎 <b>Subscription Plans</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Save on every delivery with a\n"
        "monthly plan!\n\n"
        "🎫 <b>Starter</b> — $9.99/month\n"
        "   • 5 free deliveries\n"
        "   • Priority support\n\n"
        "💼 <b>Business</b> — $49.99/month\n"
        "   • 25 free deliveries\n"
        "   • 5% discount on all orders\n\n"
        "🏢 <b>Enterprise</b> — $199.99/month\n"
        "   • Unlimited deliveries\n"
        "   • 10% off everything\n"
        "   • Dedicated support",
        reply_markup=subscription_plans_keyboard(),
    )


# ── Help ──────────────────────────────────────────────────

@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    """Show help information."""
    await callback.answer()
    await callback.message.edit_text(
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "ℹ️ <b>How It Works</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "1️⃣ Enter pickup & drop-off address\n"
        "2️⃣ Select your package size\n"
        "3️⃣ Review price & confirm\n"
        "4️⃣ Choose payment method\n"
        "5️⃣ Our rider picks up your parcel\n"
        "6️⃣ Parcel goes to our hub\n"
        "7️⃣ Optimized delivery route\n"
        "8️⃣ Delivered! 🎉\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "<b>Commands:</b>\n"
        "/start — Main menu\n"
        "/orders — Order history\n"
        "/track — Track an order\n"
        "/help — This message\n\n"
        "📞 Support: @TeleporterSupport",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Return to main menu."""
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📦 <b>TeleporterBot Logistics</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "What would you like to do?",
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
        "📍 Now send the <b>drop-off address</b>:",
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

    await state.set_state(BookingFlow.waiting_recipient_name)
    await message.answer(
        "✅ Drop-off address recorded!\n\n"
        "👤 <b>Recipient's name?</b>\n"
        "<i>Who should we deliver this parcel to?</i>\n\n"
        "Type their full name, or send /skip to continue.",
    )


# ── Booking Flow: Recipient Name ───────────────────────────────

@router.message(BookingFlow.waiting_recipient_name)
async def receive_recipient_name(message: Message, state: FSMContext):
    """Receive recipient name (or skip)."""
    name = None if message.text and message.text.lower() == "/skip" else message.text
    await state.update_data(recipient_name=name)

    await state.set_state(BookingFlow.waiting_recipient_phone)
    name_ack = "✅ Got it!" if name else "⏭️ Skipped."
    await message.answer(
        f"{name_ack}\n\n"
        "📱 <b>Recipient's phone number?</b>\n"
        "<i>We'll use this to reach them if needed.\n"
        "If they're on Telegram, they'll receive the drop-off OTP automatically!</i>\n\n"
        "Type their number (e.g. +91 98765 43210), or send /skip.",
    )


# ── Booking Flow: Recipient Phone ─────────────────────────────

@router.message(BookingFlow.waiting_recipient_phone)
async def receive_recipient_phone(message: Message, state: FSMContext):
    """Receive recipient phone (or skip), then proceed to package size."""
    phone = None if message.text and message.text.lower() == "/skip" else message.text
    await state.update_data(recipient_phone=phone)

    await state.set_state(BookingFlow.waiting_package_size)
    phone_ack = "✅ Phone saved!" if phone else "⏭️ Skipped."
    await message.answer(
        f"{phone_ack}\n\n"
        "📦 <b>What's the package size?</b>\n\n"
        "<i>Pick the option that best describes\n"
        "your shipment:</i>",
        reply_markup=package_size_keyboard(),
    )


# ── Booking Flow: Package Size ────────────────────────────

@router.callback_query(F.data.startswith("size_"), BookingFlow.waiting_package_size)
async def receive_package_size(callback: CallbackQuery, state: FSMContext):
    """Receive package size selection."""
    await callback.answer()
    size = callback.data.replace("size_", "")
    await state.update_data(package_size=size)

    # Get price estimate
    data = await state.get_data()
    estimate = await _api_call("POST", "/api/orders/estimate", json={
        "telegram_id": callback.from_user.id,
        "pickup_address": data["pickup_address"],
        "drop_address": data["drop_address"],
        "package_size": size,
        "is_express": False,
        "is_batch_eligible": True,
    })

    if not estimate:
        await callback.message.edit_text(
            "❌ Sorry, we couldn't calculate the\n"
            "price. Please try again.",
            reply_markup=main_menu_keyboard(),
        )
        await state.clear()
        return

    await state.update_data(estimate=estimate)
    await state.set_state(BookingFlow.confirm_estimate)

    vehicle_emoji = {
        "BIKE": "🏍️", "MINI_VAN": "🚐",
        "MINI_TRUCK": "🚛", "TRUCK": "🚚",
    }.get(estimate.get("vehicle_type", "BIKE"), "🚚")

    size_label = {
        "SMALL": "📦 Small", "MEDIUM": "📦 Medium",
        "LARGE": "📦📦 Large", "BULKY": "🚛 Bulky",
    }.get(size, size)

    text = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Price Estimate</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📏 Distance: <b>{estimate['distance_km']} km</b>\n"
        f"⏱️ Duration: <b>~{estimate['duration_min']} min</b>\n"
        f"{vehicle_emoji} Vehicle: <b>{estimate.get('vehicle_type', 'BIKE')}</b>\n"
        f"📦 Size: {size_label}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 Base: ${estimate['base_cost']}\n"
    )

    if estimate.get("surge_multiplier", 1.0) > 1.0:
        text += f"⚡ Surge: {estimate['surge_multiplier']}x\n"
    if estimate.get("batch_discount", 0) > 0:
        text += f"🤝 Batch: -${estimate['batch_discount']}\n"

    text += (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>💰 TOTAL: ${estimate['total_cost']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )

    await callback.message.edit_text(text, reply_markup=confirm_keyboard())


# ── Booking Flow: Confirm ─────────────────────────────────

@router.callback_query(F.data == "confirm_order", BookingFlow.confirm_estimate)
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    """User confirms — show payment method options."""
    await callback.answer()
    await state.set_state(BookingFlow.waiting_payment)
    await callback.message.edit_text(
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💳 <b>Payment Method</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
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
        "package_size": data["package_size"],
        "is_express": data.get("is_express", False),
        "is_batch_eligible": data.get("is_batch_eligible", True),
        "payment_mode": payment_mode,
        "drop_contact_name": data.get("recipient_name"),
        "drop_contact_phone": data.get("recipient_phone"),
    })

    if not order:
        await callback.message.edit_text(
            "❌ Failed to create order.\n"
            "Please try again.",
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
        "CARD": "💳 Card",
        "UPI": "📱 UPI",
    }
    mode_label = mode_labels.get(payment_mode, payment_mode)

    if payment_result and payment_result.get("status") == "confirmed":
        otp_text = ""
        if payment_result.get("pickup_otp"):
            otp_text = (
                f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔑 Pickup OTP: <code>{payment_result['pickup_otp']}</code>\n"
                f"🔑 Drop-off OTP: <code>{payment_result['drop_otp']}</code>\n\n"
                f"<i>Share these with the rider\n"
                f"at pickup and delivery.</i>"
            )

        cod_note = ""
        if payment_mode == "COD":
            cod_note = f"\n\n💵 <b>Keep ${order['total_cost']} ready</b> for driver."

        await callback.message.edit_text(
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ <b>Order Confirmed!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📋 Order: <code>{order['order_number']}</code>\n"
            f"🧾 Payment: {mode_label}\n"
            f"💰 Amount: ${order['total_cost']}"
            f"{cod_note}"
            f"{otp_text}\n\n"
            f"📦 Scheduling your pickup now!",
            reply_markup=order_actions_keyboard(order['id']),
        )

        # ── Notify recipient on Telegram with their drop-off OTP ─────
        recipient_tg = order.get("drop_contact_telegram_id")
        if recipient_tg and payment_result.get("drop_otp"):
            try:
                recipient_name = order.get("drop_contact_name") or "there"
                await callback.bot.send_message(
                    chat_id=recipient_tg,
                    text=(
                        f"━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📦 <b>Parcel Coming Your Way!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"Hi <b>{recipient_name}</b>! 👋\n\n"
                        f"Someone is sending you a parcel via ZephyrHaulBot.\n\n"
                        f"📋 Order: <code>{order['order_number']}</code>\n"
                        f"📍 Delivering to: {order['drop_address'][:60]}\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"🔑 <b>Your Drop-off OTP: <code>{payment_result['drop_otp']}</code></b>\n\n"
                        f"<i>Share this OTP with the delivery rider\n"
                        f"when your parcel arrives. Do NOT share\n"
                        f"it before delivery.</i>"
                    ),
                )
            except Exception as e:
                print(f"⚠️ Could not notify recipient {recipient_tg}: {e}")
    else:
        await callback.message.edit_text(
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <b>Order #{order['order_number']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🧾 Payment: {mode_label}\n"
            f"💰 Amount: ${order['total_cost']}\n\n"
            f"⏳ Payment is being processed...",
            reply_markup=order_actions_keyboard(order['id']),
        )

    await state.clear()


@router.callback_query(F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    """User cancels the booking."""
    await callback.answer("Order cancelled.")
    await state.clear()
    await callback.message.edit_text(
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "❌ <b>Order Cancelled</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "No charges applied.",
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
    """Show order history via command."""
    orders = await _api_call("GET", f"/api/orders/user/{message.from_user.id}", params={"limit": 10})

    if not orders:
        await message.answer(
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 <b>Your Orders</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "No orders yet! 📦",
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer(
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 <b>Your Orders</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Tap an order to view details:",
        reply_markup=order_list_keyboard(orders),
    )


# ── /track shortcut ──────────────────────────────────────

@router.message(Command("track"))
async def cmd_track(message: Message):
    """Track most recent active order."""
    orders = await _api_call("GET", f"/api/orders/user/{message.from_user.id}", params={"limit": 5})

    if not orders:
        await message.answer(
            "📋 No orders to track!",
            reply_markup=main_menu_keyboard(),
        )
        return

    # Find most recent active (non-delivered, non-cancelled) order
    active_statuses = {
        "ORDER_PLACED", "PAYMENT_CONFIRMED", "PICKUP_SCHEDULED",
        "PICKUP_RIDER_ASSIGNED", "PICKUP_EN_ROUTE", "PICKED_UP",
        "IN_TRANSIT_TO_WAREHOUSE", "AT_WAREHOUSE",
        "ROUTE_OPTIMIZED", "DELIVERY_RIDER_ASSIGNED", "OUT_FOR_DELIVERY",
    }
    active_order = None
    for o in orders:
        if o.get("status") in active_statuses:
            active_order = o
            break

    if not active_order:
        await message.answer(
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📍 <b>Track Order</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "No active orders to track.\n"
            "All your orders are delivered! ✅",
            reply_markup=main_menu_keyboard(),
        )
        return

    # Get tracking info
    tracking = await _api_call("GET", f"/api/orders/{active_order['id']}/track")
    if not tracking:
        await message.answer(
            "❌ Could not load tracking info.",
            reply_markup=order_actions_keyboard(active_order["id"]),
        )
        return

    status_emoji = {
        "PICKUP_RIDER_ASSIGNED": "🚴", "PICKUP_EN_ROUTE": "🏃",
        "OUT_FOR_DELIVERY": "🚚", "DELIVERY_RIDER_ASSIGNED": "🛵",
    }.get(tracking.get("status", ""), "📦")

    text = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>Live Tracking</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 Order: <code>{tracking['order_number']}</code>\n"
        f"{status_emoji} <b>{tracking['status'].replace('_', ' ').title()}</b>\n\n"
    )

    if tracking.get("rider_name"):
        vehicle_emoji = {"BIKE": "🏍️", "MINI_VAN": "🚐", "MINI_TRUCK": "🚛", "TRUCK": "🚚"}.get(
            tracking.get("rider_vehicle", ""), "🚚"
        )
        text += f"👤 {tracking['rider_name']} • {vehicle_emoji}\n"

    if tracking.get("estimated_arrival_min") is not None:
        text += f"⏱️ ETA: <b>~{tracking['estimated_arrival_min']} min</b>\n"

    if not tracking.get("rider_name"):
        text += "⏳ <i>Waiting for rider assignment...</i>\n"

    await message.answer(
        text,
        reply_markup=tracking_keyboard(active_order["id"], tracking.get("google_maps_url")),
    )


# ── /help ──────────────────────────────────────────────────

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Show help."""
    await message.answer(
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "ℹ️ <b>TeleporterBot Help</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "/start — Main menu\n"
        "/orders — View your orders\n"
        "/track — Track active order\n"
        "/help — This message\n\n"
        "📞 Support: @TeleporterSupport",
        reply_markup=main_menu_keyboard(),
    )


# ── Fallback: show main menu without /start ────────────────

@router.message(StateFilter(None))
async def fallback_main_menu(message: Message, state: FSMContext):
    """When not in a flow, any message opens the main menu."""
    await state.clear()
    await message.answer(
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📦 <b>TeleporterBot Logistics</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "What would you like to do?",
        reply_markup=main_menu_keyboard(),
    )
