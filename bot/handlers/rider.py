"""
Rider Telegram Bot Handler — Simplified task-based flow for company employees.

No registration, no accept/reject. Riders get assigned tasks directly.
Flow: Task notification → Acknowledge → Navigate → Enter OTP → Done
"""

import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config import settings
from keyboards.rider_kb import rider_task_keyboard, rider_return_pickup_keyboard

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


# ── FSM States ─────────────────────────────────────────────

class RiderOTP(StatesGroup):
    """Rider entering OTP."""
    waiting_otp = State()


# ── /start for riders ─────────────────────────────────────

@router.message(Command("status"))
async def cmd_rider_status(message: Message):
    """Show rider's current status and active tasks."""
    rider = await _api_call("GET", f"/api/riders/telegram/{message.from_user.id}")

    if not rider:
        await message.answer(
            "❌ You are not registered as a rider.\n"
            "Contact your manager to be added to the system."
        )
        return

    status_emoji = {
        "ON_DUTY": "🟢",
        "OFF_DUTY": "🔴",
        "ON_DELIVERY": "🚚",
        "ON_PICKUP": "📦",
    }

    await message.answer(
        f"🚴 <b>Rider Dashboard</b>\n\n"
        f"👤 {rider['full_name']} ({rider['employee_id']})\n"
        f"📱 Status: {status_emoji.get(rider['status'], '⚪')} {rider['status'].replace('_', ' ').title()}\n"
        f"🏍️ Vehicle: {rider['vehicle']}\n"
        f"📦 Current load: {rider['current_load']}/{rider['max_capacity']}\n"
        f"⭐ Rating: {rider['rating']}\n"
        f"📊 Total deliveries: {rider['total_deliveries']}\n\n"
        f"Shift: {rider['shift_start']} — {rider['shift_end']}",
    )


# ── /clockin and /clockout ────────────────────────────────

@router.message(Command("clockin"))
async def cmd_clock_in(message: Message):
    """Rider clocks in for their shift."""
    rider = await _api_call("GET", f"/api/riders/telegram/{message.from_user.id}")
    if not rider:
        await message.answer("❌ You are not registered as a rider.")
        return

    result = await _api_call("PATCH", f"/api/riders/{rider['id']}/status", params={"status": "ON_DUTY"})
    if result:
        await message.answer(
            "🟢 <b>You're clocked in!</b>\n\n"
            "You'll receive task notifications automatically.\n"
            "Have a great shift! 💪",
        )
    else:
        await message.answer("❌ Failed to clock in. Try again.")


@router.message(Command("clockout"))
async def cmd_clock_out(message: Message):
    """Rider clocks out of their shift."""
    rider = await _api_call("GET", f"/api/riders/telegram/{message.from_user.id}")
    if not rider:
        await message.answer("❌ You are not registered as a rider.")
        return

    result = await _api_call("PATCH", f"/api/riders/{rider['id']}/status", params={"status": "OFF_DUTY"})
    if result:
        await message.answer(
            "🔴 <b>You're clocked out!</b>\n\n"
            "Great work today! See you next shift. 👋",
        )


# ── Task Acknowledgment ───────────────────────────────────

@router.callback_query(F.data.startswith("rider_ack_"))
async def acknowledge_task(callback: CallbackQuery):
    """Rider acknowledges a task assignment."""
    order_id = callback.data.replace("rider_ack_", "")
    await callback.answer("Task acknowledged! Navigate to the pickup/delivery point.")

    await callback.message.edit_text(
        f"✅ <b>Task Acknowledged</b>\n\n"
        f"Order: <code>{order_id[:8]}</code>\n\n"
        f"Navigate to the location and enter the OTP when you arrive.\n\n"
        f"📍 <i>Use the navigation link sent with the task.</i>",
    )


@router.callback_query(F.data.startswith("rider_issue_"))
async def report_issue(callback: CallbackQuery):
    """Rider reports an issue with a task."""
    order_id = callback.data.replace("rider_issue_", "")
    await callback.answer("Issue reported!")

    await callback.message.edit_text(
        f"🚨 <b>Issue Reported</b>\n\n"
        f"Order: <code>{order_id[:8]}</code>\n\n"
        f"Your manager has been notified. "
        f"Please describe the issue by sending a message.",
    )

    # TODO: Trigger n8n issue-escalation workflow


# ── OTP Entry ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("enter_otp_"))
async def prompt_otp(callback: CallbackQuery, state: FSMContext):
    """Prompt rider to enter OTP."""
    parts = callback.data.split("_")
    otp_type = parts[2]   # "pickup" or "drop"
    order_id = parts[3]

    await state.set_state(RiderOTP.waiting_otp)
    await state.update_data(otp_type=otp_type, order_id=order_id)

    await callback.answer()
    await callback.message.edit_text(
        f"🔑 Enter the <b>{otp_type}</b> OTP\n"
        f"(6-digit code from the customer):",
    )


@router.message(RiderOTP.waiting_otp)
async def verify_rider_otp(message: Message, state: FSMContext):
    """Verify OTP entered by rider."""
    data = await state.get_data()
    otp_code = message.text.strip()

    if len(otp_code) != 6 or not otp_code.isdigit():
        await message.answer("❌ OTP must be exactly 6 digits. Try again:")
        return

    # Get rider info
    rider = await _api_call("GET", f"/api/riders/telegram/{message.from_user.id}")

    result = await _api_call("POST", f"/api/orders/{data['order_id']}/otp/verify", json={
        "order_id": data["order_id"],
        "otp_type": data["otp_type"],
        "otp_code": otp_code,
        "rider_id": rider["id"] if rider else "",
    })

    if result and result.get("valid"):
        await state.clear()
        otp_type = data["otp_type"]
        if otp_type == "pickup":
            await message.answer(
                "✅ <b>Pickup Confirmed!</b>\n\n"
                "Parcel collected. Head to the warehouse.",
            )
        else:
            await message.answer(
                "✅ <b>Delivery Confirmed!</b>\n\n"
                "Package delivered successfully. Great job! 🎉",
            )
    else:
        error = result.get("error", "Invalid OTP") if result else "Verification failed"
        await message.answer(f"❌ {error}")


# ── Return Trip Pickup ─────────────────────────────────────

@router.callback_query(F.data.startswith("return_accept_"))
async def accept_return_pickup(callback: CallbackQuery):
    """Rider accepts a return-trip pickup."""
    order_id = callback.data.replace("return_accept_", "")
    await callback.answer("Pickup accepted! Bonus ₹20 added.")

    await callback.message.edit_text(
        f"📦 <b>Return-Trip Pickup Accepted!</b>\n\n"
        f"Order: <code>{order_id[:8]}</code>\n"
        f"💰 Bonus: ₹20\n\n"
        f"Navigate to pickup and collect the parcel on your way back.",
    )


@router.callback_query(F.data == "return_skip")
async def skip_return_pickup(callback: CallbackQuery):
    """Rider skips return-trip pickup."""
    await callback.answer("Heading back to warehouse.")
    await callback.message.edit_text(
        "🏠 <b>Heading to Warehouse</b>\n\n"
        "No return pickups. Drive safe! 🚗",
    )
