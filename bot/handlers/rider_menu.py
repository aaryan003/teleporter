"""
Rider Main Menu & Sub-Menu Bot Handler — Full operational flow for approved riders.

Sub-menus:
  - Availability Toggle (On/Off Duty)
  - Active Tasks + OTP Confirmation
  - View Optimized Route
  - Earnings
  - Stats
  - Profile + Shift Hours + Hub Change
"""

import re
import logging

import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config import settings
from keyboards.rider_kb import rider_main_menu_keyboard

router = Router()
logger = logging.getLogger(__name__)
API = settings.API_BASE_URL


# ── FSM States for Rider Sub-flows ────────────────────────

class RiderOTPFlow(StatesGroup):
    """Rider entering OTP for pickup/drop confirmation."""
    waiting_otp = State()


class RiderShiftFlow(StatesGroup):
    """Rider updating shift hours."""
    waiting_shift_start = State()
    waiting_shift_end = State()


# ── API Helper ─────────────────────────────────────────────

async def _api_call(method: str, endpoint: str, **kwargs) -> dict | list | None:
    """Call FastAPI backend."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if method == "GET":
                resp = await client.get(f"{API}{endpoint}", params=kwargs.get("params"))
            elif method == "POST":
                resp = await client.post(f"{API}{endpoint}", json=kwargs.get("json"))
            elif method == "PATCH":
                resp = await client.patch(f"{API}{endpoint}", json=kwargs.get("json"))
            elif method == "PUT":
                resp = await client.put(f"{API}{endpoint}", json=kwargs.get("json"))
            else:
                return None
            if resp.status_code in (200, 201):
                return resp.json()
            logger.warning("API error: %s %s → %s %s", method, endpoint, resp.status_code, resp.text[:200])
            return None
    except Exception as e:
        logger.error("API call error: %s %s: %s", method, endpoint, e)
        return None


async def _get_rider(telegram_id: int) -> dict | None:
    """Get rider by Telegram ID."""
    return await _api_call("GET", f"/api/riders/telegram/{telegram_id}")


def _home_button() -> list:
    """Standard home button row."""
    return [InlineKeyboardButton(text="🏠 Home", callback_data="rider_home")]


# ── Home / Main Menu ──────────────────────────────────────

@router.callback_query(F.data == "rider_home")
async def rider_home(callback: CallbackQuery, state: FSMContext):
    """Return to rider main menu."""
    await state.clear()
    await callback.answer()
    rider = await _get_rider(callback.from_user.id)
    if not rider:
        await callback.message.edit_text("❌ Rider profile not found. Please contact support.")
        return

    await callback.message.edit_text(
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏍️ <b>Teleporter Rider</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Welcome, <b>{rider['full_name']}</b>! 👋\n\n"
        f"Status: {'🟢 On Duty' if rider['status'] == 'ON_DUTY' else '🔴 Off Duty' if rider['status'] == 'OFF_DUTY' else '📦 ' + rider['status'].replace('_', ' ').title()}",
        reply_markup=rider_main_menu_keyboard(rider['status']),
    )


# ── Availability Toggle ───────────────────────────────────

@router.callback_query(F.data == "rider_go_on_duty")
async def go_on_duty(callback: CallbackQuery):
    """Set rider status to ON_DUTY."""
    await callback.answer()
    rider = await _get_rider(callback.from_user.id)
    if not rider:
        await callback.message.edit_text("❌ Rider not found.")
        return

    result = await _api_call("PATCH", f"/api/riders/{rider['id']}/status", json={"status": "ON_DUTY"})
    if result:
        await callback.message.edit_text(
            "✅ <b>You are now ON DUTY!</b>\n\n"
            "You'll receive delivery notifications.\n"
            "Have a great shift! 💪",
            reply_markup=rider_main_menu_keyboard("ON_DUTY"),
        )
    else:
        await callback.message.edit_text("❌ Failed to update status. Try again.")


@router.callback_query(F.data == "rider_go_off_duty")
async def go_off_duty(callback: CallbackQuery):
    """Set rider status to OFF_DUTY."""
    await callback.answer()
    rider = await _get_rider(callback.from_user.id)
    if not rider:
        await callback.message.edit_text("❌ Rider not found.")
        return

    result = await _api_call("PATCH", f"/api/riders/{rider['id']}/status", json={"status": "OFF_DUTY"})
    if result:
        await callback.message.edit_text(
            "👋 <b>You are now OFF DUTY.</b>\n\n"
            "No new tasks will be assigned.\n"
            "Rest well! 😊",
            reply_markup=rider_main_menu_keyboard("OFF_DUTY"),
        )
    else:
        await callback.message.edit_text("❌ Failed to update status. Try again.")


# ── Active Tasks ───────────────────────────────────────────

@router.callback_query(F.data == "rider_active_tasks")
async def show_active_tasks(callback: CallbackQuery):
    """Show rider's active tasks."""
    await callback.answer()
    rider = await _get_rider(callback.from_user.id)
    if not rider:
        await callback.message.edit_text("❌ Rider not found.")
        return

    tasks = await _api_call("GET", f"/api/riders/{rider['id']}/active-tasks")
    if not tasks:
        await callback.message.edit_text(
            "📦 <b>Active Tasks</b>\n\n"
            "No active tasks assigned right now.\n\n"
            "Tasks will appear here when they are assigned to you.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[_home_button()]),
        )
        return

    for task in tasks[:5]:  # Show up to 5 tasks
        task_type = task.get("task_type", "DELIVERY")
        status = task.get("status", "")
        order_num = task.get("order_number", "?")
        order_id = task.get("id", "")
        address = task.get("pickup_address") if task_type == "PICKUP" else task.get("drop_address", "")
        address_short = (address[:60] + "...") if address and len(address) > 60 else address

        type_emoji = "📦" if task_type == "PICKUP" else "🚚"
        status_emoji = {
            "PICKUP_RIDER_ASSIGNED": "🟡 Assigned",
            "PICKUP_EN_ROUTE": "🏃 En Route",
            "DELIVERY_RIDER_ASSIGNED": "🟡 Assigned",
            "OUT_FOR_DELIVERY": "🚚 Delivering",
        }.get(status, status.replace("_", " ").title())

        buttons = []
        if status in ("PICKUP_RIDER_ASSIGNED", "PICKUP_EN_ROUTE"):
            lat = task.get("pickup_lat")
            lng = task.get("pickup_lng")
            if lat and lng:
                maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"
                buttons.append([InlineKeyboardButton(text="📍 Get Directions", url=maps_url)])
            buttons.append([InlineKeyboardButton(text="✅ Confirm Pickup OTP", callback_data=f"rider_otp_pickup_{order_id}")])
        elif status in ("DELIVERY_RIDER_ASSIGNED", "OUT_FOR_DELIVERY"):
            lat = task.get("drop_lat")
            lng = task.get("drop_lng")
            if lat and lng:
                maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"
                buttons.append([InlineKeyboardButton(text="📍 Get Directions", url=maps_url)])
            buttons.append([InlineKeyboardButton(text="✅ Confirm Drop OTP", callback_data=f"rider_otp_drop_{order_id}")])

        buttons.append(_home_button())

        await callback.message.answer(
            f"{type_emoji} <b>{task_type}</b> — Order #{order_num}\n"
            f"📍 {address_short}\n"
            f"Status: {status_emoji}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        )

    # Delete the original menu message to avoid clutter
    try:
        await callback.message.delete()
    except Exception:
        pass


# ── OTP Confirmation Sub-flow ──────────────────────────────

@router.callback_query(F.data.startswith("rider_otp_"))
async def start_otp_flow(callback: CallbackQuery, state: FSMContext):
    """Prompt rider to enter OTP for pickup or drop."""
    parts = callback.data.split("_")  # rider_otp_pickup_{order_id} or rider_otp_drop_{order_id}
    otp_type = parts[2]  # "pickup" or "drop"
    order_id = "_".join(parts[3:])  # Handle UUIDs with dashes

    await state.set_state(RiderOTPFlow.waiting_otp)
    await state.update_data(otp_type=otp_type, order_id=order_id)

    await callback.answer()
    await callback.message.edit_text(
        f"🔑 Enter the <b>{otp_type}</b> OTP\n"
        f"(6-digit code from the customer):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="rider_active_tasks")],
        ]),
    )


@router.message(RiderOTPFlow.waiting_otp)
async def verify_otp(message: Message, state: FSMContext):
    """Verify OTP entered by rider."""
    otp_code = (message.text or "").strip()
    if len(otp_code) != 6 or not otp_code.isdigit():
        await message.answer("❌ OTP must be exactly 6 digits. Try again:")
        return

    data = await state.get_data()
    otp_type = data["otp_type"]
    order_id = data["order_id"]

    rider = await _get_rider(message.from_user.id)
    if not rider:
        await message.answer("❌ Rider not found.")
        await state.clear()
        return

    # Call the appropriate confirm endpoint
    endpoint = f"/api/orders/{order_id}/confirm-pickup-otp" if otp_type == "pickup" else f"/api/orders/{order_id}/confirm-drop-otp"
    result = await _api_call("POST", endpoint, json={
        "otp": otp_code,
        "rider_id": rider["id"],
    })

    if result and result.get("valid"):
        await state.clear()
        if otp_type == "pickup":
            await message.answer(
                "✅ <b>Pickup Confirmed!</b>\n\n"
                "Parcel collected. Head to the warehouse. 📦",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[_home_button()]),
            )
        else:
            await message.answer(
                "✅ <b>Delivery Confirmed!</b>\n\n"
                "Package delivered successfully. Great job! 🎉",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[_home_button()]),
            )
    else:
        error = result.get("error", "Invalid OTP") if result else "Verification failed"
        await message.answer(
            f"❌ {error}\n\n"
            "Enter the 6-digit OTP again:",
        )


# ── View Route ─────────────────────────────────────────────

@router.callback_query(F.data == "rider_view_route")
async def view_current_route(callback: CallbackQuery):
    """Show rider's current optimized route."""
    await callback.answer()
    rider = await _get_rider(callback.from_user.id)
    if not rider:
        await callback.message.edit_text("❌ Rider not found.")
        return

    route = await _api_call("GET", f"/api/riders/{rider['id']}/current-route")
    if not route:
        await callback.message.edit_text(
            "🗺️ <b>Current Route</b>\n\n"
            "No active route assigned right now.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[_home_button()]),
        )
        return

    sequence = route.get("optimized_sequence", [])
    total_km = route.get("total_distance_km", 0)
    total_min = route.get("total_duration_min", 0)

    stops_text = ""
    waypoints = []
    for i, stop in enumerate(sequence):
        addr = stop.get("drop_address", "Unknown")[:50]
        dist = stop.get("distance_from_prev_km", 0)
        stops_text += f"\n{i + 1}. 📍 {addr}"
        if dist:
            stops_text += f" (~{dist:.1f}km)"
        lat = stop.get("drop_lat")
        lng = stop.get("drop_lng")
        if lat and lng:
            waypoints.append(f"{lat},{lng}")

    text = (
        f"🗺️ <b>Your Delivery Route</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📏 Total: {total_km:.1f} km | ⏱️ ~{total_min} min\n"
        f"📦 Parcels: {route.get('total_parcels', len(sequence))}\n"
        f"\n<b>Stops:</b>{stops_text}"
    )

    buttons = []
    if waypoints:
        maps_url = "https://www.google.com/maps/dir/" + "/".join(waypoints)
        buttons.append([InlineKeyboardButton(text="🗺️ Open Full Route in Maps", url=maps_url)])
    buttons.append(_home_button())

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("rider_view_route_"))
async def view_specific_route(callback: CallbackQuery):
    """View a specific route (from notification callback)."""
    # Just redirect to the general route view
    await view_current_route(callback)


# ── Earnings ───────────────────────────────────────────────

@router.callback_query(F.data == "rider_earnings")
async def show_earnings(callback: CallbackQuery):
    """Show rider's earnings summary."""
    await callback.answer()
    rider = await _get_rider(callback.from_user.id)
    if not rider:
        await callback.message.edit_text("❌ Rider not found.")
        return

    earnings = await _api_call("GET", f"/api/riders/{rider['id']}/earnings")
    if not earnings:
        await callback.message.edit_text(
            "💰 <b>My Earnings</b>\n\n"
            "No earnings data available yet.\n"
            "Complete deliveries to start earning!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[_home_button()]),
        )
        return

    text = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💰 <b>My Earnings</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Today: ₹{earnings.get('today', 0):.0f} ({earnings.get('deliveries_today', 0)} deliveries)\n"
        f"📅 This Week: ₹{earnings.get('this_week', 0):.0f} ({earnings.get('deliveries_week', 0)} deliveries)\n"
        f"🗓️ This Month: ₹{earnings.get('this_month', 0):.0f} ({earnings.get('deliveries_month', 0)} deliveries)\n"
        f"🏆 All Time: ₹{earnings.get('total_all_time', 0):.0f}\n\n"
        f"⭐ Rating: {earnings.get('avg_rating', 5.0):.2f}/5.00"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 View Recent Deliveries", callback_data="rider_recent_deliveries")],
        _home_button(),
    ])

    await callback.message.edit_text(text, reply_markup=kb)


# ── Recent Deliveries ──────────────────────────────────────

@router.callback_query(F.data.startswith("rider_recent_deliveries"))
async def show_recent_deliveries(callback: CallbackQuery):
    """Show paginated delivery history."""
    await callback.answer()
    rider = await _get_rider(callback.from_user.id)
    if not rider:
        await callback.message.edit_text("❌ Rider not found.")
        return

    # Parse page offset from callback
    offset = 0
    if "_p" in callback.data:
        try:
            offset = int(callback.data.split("_p")[-1])
        except ValueError:
            offset = 0

    deliveries = await _api_call("GET", f"/api/riders/{rider['id']}/deliveries", params={"limit": 5, "offset": offset})
    if not deliveries:
        await callback.message.edit_text(
            "📋 <b>Recent Deliveries</b>\n\nNo delivery history found.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[_home_button()]),
        )
        return

    text = "📋 <b>Recent Deliveries</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for d in deliveries:
        order_num = d.get("order_number", "?")
        pickup_short = (d.get("pickup_address", "?")[:25] + "...") if d.get("pickup_address", "") and len(d.get("pickup_address", "")) > 25 else d.get("pickup_address", "?")
        drop_short = (d.get("drop_address", "?")[:25] + "...") if d.get("drop_address", "") and len(d.get("drop_address", "")) > 25 else d.get("drop_address", "?")
        date = d.get("delivered_at", d.get("created_at", ""))[:10]
        earned = d.get("earned", 0)
        text += f"\n📦 #{order_num}\n   {pickup_short} → {drop_short}\n   📅 {date} | ₹{earned:.0f}\n"

    buttons = []
    if len(deliveries) >= 5:
        buttons.append([InlineKeyboardButton(text="📋 Load More", callback_data=f"rider_recent_deliveries_p{offset + 5}")])
    buttons.append(_home_button())

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


# ── Stats ──────────────────────────────────────────────────

@router.callback_query(F.data == "rider_stats")
async def show_stats(callback: CallbackQuery):
    """Show rider performance stats."""
    await callback.answer()
    rider = await _get_rider(callback.from_user.id)
    if not rider:
        await callback.message.edit_text("❌ Rider not found.")
        return

    stats = await _api_call("GET", f"/api/riders/{rider['id']}/stats")
    if not stats:
        await callback.message.edit_text(
            "📊 <b>My Stats</b>\n\nNo stats available yet.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[_home_button()]),
        )
        return

    text = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 <b>Performance Scorecard</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Completion Rate: {stats.get('completion_rate', 0):.1f}%\n"
        f"⏱️ On-Time Rate: {stats.get('on_time_rate', 0):.1f}%\n"
        f"🛣️ Total KM Ridden: {stats.get('total_km_ridden', 0):.1f} km\n"
        f"📦 Avg Deliveries/Day: {stats.get('avg_deliveries_per_day', 0):.1f}\n"
        f"💰 Best Day Earnings: ₹{stats.get('best_day_earnings', 0):.0f}\n"
        f"🔥 Current Streak: {stats.get('streak_days', 0)} days"
    )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[_home_button()]),
    )


# ── Profile ────────────────────────────────────────────────

@router.callback_query(F.data == "rider_profile")
async def show_profile(callback: CallbackQuery):
    """Show rider profile."""
    await callback.answer()
    rider = await _get_rider(callback.from_user.id)
    if not rider:
        await callback.message.edit_text("❌ Rider not found.")
        return

    status_map = {
        "ON_DUTY": "🟢 On Duty",
        "OFF_DUTY": "🔴 Off Duty",
        "ON_DELIVERY": "🚚 On Delivery",
        "ON_PICKUP": "📦 On Pickup",
    }

    vehicle_labels = {
        "BIKE": "🏍️ Bike",
        "MINI_VAN": "🚐 Mini Van",
        "MINI_TRUCK": "🚛 Mini Truck",
        "TRUCK": "🚚 Truck",
    }

    text = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚙️ <b>My Profile</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>Name:</b> {rider['full_name']}\n"
        f"🆔 <b>Employee ID:</b> {rider['employee_id']}\n"
        f"📱 <b>Phone:</b> {rider['phone']}\n"
        f"🚗 <b>Vehicle:</b> {vehicle_labels.get(rider['vehicle'], rider['vehicle'])}\n"
        f"🔢 <b>Registration:</b> {rider.get('vehicle_reg', 'N/A')}\n"
        f"📍 <b>Status:</b> {status_map.get(rider['status'], rider['status'])}\n"
        f"⏰ <b>Shift:</b> {rider['shift_start']} — {rider['shift_end']}\n"
        f"⭐ <b>Rating:</b> {rider['rating']}/5.00\n"
        f"📦 <b>Total Deliveries:</b> {rider['total_deliveries']}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Update Shift Hours", callback_data="rider_update_shift"),
            InlineKeyboardButton(text="🏭 Change Hub", callback_data="rider_change_hub"),
        ],
        _home_button(),
    ])

    await callback.message.edit_text(text, reply_markup=kb)


# ── Update Shift Hours ─────────────────────────────────────

@router.callback_query(F.data == "rider_update_shift")
async def start_shift_update(callback: CallbackQuery, state: FSMContext):
    """Start shift hours update flow."""
    await callback.answer()
    await state.set_state(RiderShiftFlow.waiting_shift_start)
    await callback.message.edit_text(
        "⏰ <b>Update Shift Hours</b>\n\n"
        "Enter your <b>shift start time</b> (HH:MM format):\n"
        "Example: 08:00",
    )


@router.message(RiderShiftFlow.waiting_shift_start)
async def process_shift_start(message: Message, state: FSMContext):
    """Collect shift start time."""
    time_str = (message.text or "").strip()
    if not re.match(r"^\d{2}:\d{2}$", time_str):
        await message.answer("⚠️ Invalid format. Enter time as HH:MM (e.g. 08:00):")
        return

    parts = time_str.split(":")
    h, m = int(parts[0]), int(parts[1])
    if h < 0 or h > 23 or m < 0 or m > 59:
        await message.answer("⚠️ Invalid time. Hours 00-23, minutes 00-59. Try again:")
        return

    await state.update_data(shift_start=time_str)
    await state.set_state(RiderShiftFlow.waiting_shift_end)
    await message.answer(
        f"✅ Start: {time_str}\n\n"
        "Now enter your <b>shift end time</b> (HH:MM format):",
    )


@router.message(RiderShiftFlow.waiting_shift_end)
async def process_shift_end(message: Message, state: FSMContext):
    """Collect shift end time and save."""
    time_str = (message.text or "").strip()
    if not re.match(r"^\d{2}:\d{2}$", time_str):
        await message.answer("⚠️ Invalid format. Enter time as HH:MM (e.g. 20:00):")
        return

    parts = time_str.split(":")
    h, m = int(parts[0]), int(parts[1])
    if h < 0 or h > 23 or m < 0 or m > 59:
        await message.answer("⚠️ Invalid time. Try again:")
        return

    data = await state.get_data()
    start_str = data["shift_start"]

    # Basic validation: end should be after start
    start_parts = start_str.split(":")
    sh, sm = int(start_parts[0]), int(start_parts[1])
    if (h * 60 + m) <= (sh * 60 + sm):
        await message.answer("⚠️ End time must be after start time. Try again:")
        return

    rider = await _get_rider(message.from_user.id)
    if not rider:
        await message.answer("❌ Rider not found.")
        await state.clear()
        return

    result = await _api_call(
        "PATCH",
        f"/api/riders/{rider['id']}/shift",
        json={"shift_start": start_str, "shift_end": time_str},
    )

    await state.clear()
    if result:
        await message.answer(
            f"✅ <b>Shift Updated!</b>\n\n"
            f"⏰ {start_str} — {time_str}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[_home_button()]),
        )
    else:
        await message.answer(
            "❌ Failed to update shift. Try again later.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[_home_button()]),
        )


# ── Change Hub ─────────────────────────────────────────────

@router.callback_query(F.data == "rider_change_hub")
async def show_hub_selection(callback: CallbackQuery):
    """Show warehouse list for hub change."""
    await callback.answer()
    warehouses = await _api_call("GET", "/api/warehouses/")
    if not warehouses:
        await callback.message.edit_text(
            "🏭 No active warehouses found.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[_home_button()]),
        )
        return

    buttons = []
    for wh in warehouses:
        label = f"🏭 {wh['name']}"
        if wh.get("city"):
            label += f" ({wh['city']})"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"rider_set_hub_{wh['id']}")])
    buttons.append(_home_button())

    await callback.message.edit_text(
        "🏭 <b>Change Operating Hub</b>\n\n"
        "Select your preferred warehouse:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("rider_set_hub_"))
async def set_hub(callback: CallbackQuery):
    """Set rider's preferred warehouse."""
    await callback.answer()
    wh_id = callback.data.replace("rider_set_hub_", "")
    rider = await _get_rider(callback.from_user.id)
    if not rider:
        await callback.message.edit_text("❌ Rider not found.")
        return

    result = await _api_call(
        "PATCH",
        f"/api/riders/{rider['id']}/warehouse",
        json={"warehouse_id": wh_id},
    )

    if result:
        await callback.message.edit_text(
            "✅ <b>Hub Updated!</b>\n\n"
            "Your preferred operating hub has been changed.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[_home_button()]),
        )
    else:
        await callback.message.edit_text(
            "❌ Failed to update hub. Try again.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[_home_button()]),
        )


# ── Help ───────────────────────────────────────────────────

@router.callback_query(F.data == "rider_help")
async def show_help(callback: CallbackQuery):
    """Show rider help information."""
    await callback.answer()
    text = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "❓ <b>Rider Help</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🟢 <b>Go On Duty</b> — Mark yourself available for deliveries\n"
        "🔴 <b>Go Off Duty</b> — Stop receiving new assignments\n\n"
        "📦 <b>Active Tasks</b> — View orders assigned to you\n"
        "🗺️ <b>View Route</b> — See your optimized delivery route\n\n"
        "💰 <b>Earnings</b> — Track your daily/weekly/monthly income\n"
        "📊 <b>Stats</b> — View your performance metrics\n\n"
        "⚙️ <b>Profile</b> — Update shift hours or change hub\n\n"
        "📞 Need help? Contact support: @TeleporterSupport"
    )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[_home_button()]),
    )


# ── Notification Action Callbacks ──────────────────────────

@router.callback_query(F.data.startswith("rider_onmyway_"))
async def on_my_way(callback: CallbackQuery):
    """Rider acknowledges pickup and starts en route."""
    order_id = callback.data.replace("rider_onmyway_", "")
    await callback.answer("On your way!")

    rider = await _get_rider(callback.from_user.id)
    if rider:
        await _api_call("PATCH", f"/api/orders/{order_id}/status", json={
            "status": "PICKUP_EN_ROUTE",
            "actor_type": "RIDER",
            "actor_id": rider["id"],
        })

    await callback.message.edit_text(
        "🏃 <b>On Your Way!</b>\n\n"
        f"Head to the pickup location.\n"
        f"Remember to collect the OTP from the customer.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 My Active Tasks", callback_data="rider_active_tasks")],
            _home_button(),
        ]),
    )


@router.callback_query(F.data.startswith("rider_directions_pickup_"))
async def get_pickup_directions(callback: CallbackQuery):
    """Open Google Maps for pickup directions."""
    order_id = callback.data.replace("rider_directions_pickup_", "")
    await callback.answer()
    # Redirect to active tasks where directions are available
    await show_active_tasks(callback)


# ── Location Sharing Handler ──────────────────────────────

@router.message(F.location)
async def handle_shared_location(message: Message):
    """
    Capture location shared by rider (from the request-location keyboard)
    and push it to the API as a location update.
    """
    rider = await _get_rider(message.from_user.id)
    if not rider:
        return  # Ignore location from non-riders

    lat = message.location.latitude
    lng = message.location.longitude

    result = await _api_call(
        "PATCH",
        f"/api/riders/{rider['id']}/location",
        json={"lat": lat, "lng": lng},
    )

    if result:
        logger.info(
            "Location updated: rider=%s lat=%s lng=%s",
            rider["employee_id"],
            lat,
            lng,
        )
    else:
        logger.warning("Failed to update location for rider %s", rider["id"])
