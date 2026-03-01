"""
Rider Onboarding Bot Handler — 10-step guided application flow.

Flow:
  1. Full Name → 2. Phone → 3. Email (optional) → 4. Vehicle Type
  → 5. Vehicle Reg → 6. License Photo → 7. Aadhar Photo (optional)
  → 8. Preferred Zone → 9. Review & Confirm → 10. Submit
"""

import re
import logging

import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from config import settings
from states.rider_onboarding import RiderOnboarding

router = Router()
logger = logging.getLogger(__name__)
API = settings.API_BASE_URL

PHONE_RE = re.compile(r"^\+?\d{10,15}$")
EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


async def _api_call(method: str, endpoint: str, **kwargs) -> dict | list | None:
    """Helper to call FastAPI backend."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
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
            logger.warning("API error: %s %s → %s", method, endpoint, resp.status_code)
            return None
    except Exception as e:
        logger.error("API call error: %s", e)
        return None


# ── Entry Point: "Register as a Rider" callback ──────────

@router.callback_query(F.data == "register_rider")
async def start_rider_onboarding(callback: CallbackQuery, state: FSMContext):
    """Begin the rider onboarding FSM — with duplicate application guard."""
    await callback.answer()

    # Guard: check if user already has an application
    existing = await _api_call("GET", f"/api/rider-applications/telegram/{callback.from_user.id}")
    if existing:
        status = existing.get("status")
        if status == "PENDING":
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📞 Contact Support", url="https://t.me/TeleporterSupport")],
            ])
            await callback.message.edit_text(
                "⏳ <b>Application Under Review</b>\n\n"
                "You already have a pending application.\n"
                "Our team will review it within <b>24-48 hours</b>.\n\n"
                "We'll notify you right here once it's processed. 🔔",
                reply_markup=kb,
            )
            return
        elif status == "APPROVED":
            from keyboards.rider_kb import rider_main_menu_keyboard
            rider = await _api_call("GET", f"/api/riders/telegram/{callback.from_user.id}")
            if rider:
                await callback.message.edit_text(
                    "✅ <b>You're already an approved rider!</b>\n\n"
                    f"Welcome back, <b>{rider['full_name']}</b>! 👋\n\n"
                    f"Use the menu below to manage your availability.",
                    reply_markup=rider_main_menu_keyboard(rider["status"]),
                )
                return
        # REJECTED → fall through and allow re-application (API will reset the record)

    await state.clear()
    await state.set_state(RiderOnboarding.full_name)
    await callback.message.edit_text(
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🏍️ <b>Rider Registration</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Let's get you registered as a Teleporter rider!\n"
        "This will take about 2 minutes.\n\n"
        "<b>Step 1/9:</b> What is your <b>full name</b>?",
    )


# ── Step 1: Full Name ────────────────────────────────────

@router.message(RiderOnboarding.full_name)
async def process_full_name(message: Message, state: FSMContext):
    """Collect rider's full name."""
    name = message.text.strip() if message.text else ""
    if len(name) < 3:
        await message.answer(
            "⚠️ Name must be at least 3 characters. Please enter your full name:"
        )
        return

    await state.update_data(full_name=name)
    await state.set_state(RiderOnboarding.phone)
    await message.answer(
        f"👍 Hi <b>{name}</b>!\n\n"
        "<b>Step 2/9:</b> Enter your <b>phone number</b>\n"
        "(with country code, e.g. +91XXXXXXXXXX)",
    )


# ── Step 2: Phone ─────────────────────────────────────────

@router.message(RiderOnboarding.phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext):
    """Handle phone shared via Telegram contact."""
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = f"+{phone}"
    await state.update_data(phone=phone)
    await state.set_state(RiderOnboarding.email)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏩ Skip", callback_data="onboard_skip_email")],
    ])
    await message.answer(
        f"✅ Phone: <code>{phone}</code>\n\n"
        "<b>Step 3/9:</b> Enter your <b>email address</b> (optional):",
        reply_markup=kb,
    )


@router.message(RiderOnboarding.phone)
async def process_phone_text(message: Message, state: FSMContext):
    """Handle phone entered as text."""
    phone = (message.text or "").strip().replace(" ", "").replace("-", "")
    if not PHONE_RE.match(phone):
        await message.answer(
            "⚠️ Invalid phone number. Please enter with country code, e.g. +919876543210"
        )
        return

    if not phone.startswith("+"):
        phone = f"+{phone}"

    await state.update_data(phone=phone)
    await state.set_state(RiderOnboarding.email)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏩ Skip", callback_data="onboard_skip_email")],
    ])
    await message.answer(
        f"✅ Phone: <code>{phone}</code>\n\n"
        "<b>Step 3/9:</b> Enter your <b>email address</b> (optional):",
        reply_markup=kb,
    )


# ── Step 3: Email (optional) ─────────────────────────────

@router.callback_query(F.data == "onboard_skip_email")
async def skip_email(callback: CallbackQuery, state: FSMContext):
    """Skip email step."""
    await callback.answer()
    await state.update_data(email=None)
    await state.set_state(RiderOnboarding.vehicle_type)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏍️ Bike", callback_data="vehicle_BIKE")],
        [InlineKeyboardButton(text="🚐 Mini Van", callback_data="vehicle_MINI_VAN")],
        [InlineKeyboardButton(text="🚛 Mini Truck", callback_data="vehicle_MINI_TRUCK")],
        [InlineKeyboardButton(text="🚚 Truck", callback_data="vehicle_TRUCK")],
    ])
    await callback.message.edit_text(
        "<b>Step 4/9:</b> What <b>vehicle</b> will you use for delivery?",
        reply_markup=kb,
    )


@router.message(RiderOnboarding.email)
async def process_email(message: Message, state: FSMContext):
    """Collect rider email."""
    email = (message.text or "").strip()
    if email and not EMAIL_RE.match(email):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏩ Skip", callback_data="onboard_skip_email")],
        ])
        await message.answer(
            "⚠️ Invalid email format. Please enter a valid email or tap Skip:",
            reply_markup=kb,
        )
        return

    await state.update_data(email=email if email else None)
    await state.set_state(RiderOnboarding.vehicle_type)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏍️ Bike", callback_data="vehicle_BIKE")],
        [InlineKeyboardButton(text="🚐 Mini Van", callback_data="vehicle_MINI_VAN")],
        [InlineKeyboardButton(text="🚛 Mini Truck", callback_data="vehicle_MINI_TRUCK")],
        [InlineKeyboardButton(text="🚚 Truck", callback_data="vehicle_TRUCK")],
    ])
    await message.answer(
        "<b>Step 4/9:</b> What <b>vehicle</b> will you use for delivery?",
        reply_markup=kb,
    )


# ── Step 4: Vehicle Type ─────────────────────────────────

@router.callback_query(F.data.startswith("vehicle_"), RiderOnboarding.vehicle_type)
async def process_vehicle_type(callback: CallbackQuery, state: FSMContext):
    """Select vehicle type."""
    vehicle = callback.data.replace("vehicle_", "")
    await callback.answer()

    vehicle_labels = {
        "BIKE": "🏍️ Bike",
        "MINI_VAN": "🚐 Mini Van",
        "MINI_TRUCK": "🚛 Mini Truck",
        "TRUCK": "🚚 Truck",
    }

    await state.update_data(vehicle_type=vehicle)
    await state.set_state(RiderOnboarding.vehicle_reg)
    await callback.message.edit_text(
        f"✅ Vehicle: {vehicle_labels.get(vehicle, vehicle)}\n\n"
        "<b>Step 5/9:</b> Enter your <b>vehicle registration number</b>\n"
        "(e.g. GJ01AB1234):",
    )


# ── Step 5: Vehicle Registration ─────────────────────────

@router.message(RiderOnboarding.vehicle_reg)
async def process_vehicle_reg(message: Message, state: FSMContext):
    """Collect vehicle registration number."""
    reg = (message.text or "").strip().upper()
    if len(reg) < 5 or not re.match(r"^[A-Z0-9\- ]+$", reg):
        await message.answer(
            "⚠️ Vehicle registration must be at least 5 alphanumeric characters.\n"
            "Example: GJ01AB1234"
        )
        return

    await state.update_data(vehicle_reg=reg)
    await state.set_state(RiderOnboarding.license_photo)
    await message.answer(
        f"✅ Registration: <code>{reg}</code>\n\n"
        "<b>Step 6/9:</b> Please send a <b>clear photo</b> of your <b>Driving License</b>.\n\n"
        "📸 <i>Make sure all text is readable and the photo is not blurry.</i>",
    )


# ── Step 6: License Photo ────────────────────────────────

@router.message(RiderOnboarding.license_photo, F.photo)
async def process_license_photo(message: Message, state: FSMContext):
    """Collect license photo — accept only photo messages."""
    # Store the highest resolution photo's file_id
    photo = message.photo[-1]  # Largest size
    await state.update_data(license_file_id=photo.file_id)
    await state.set_state(RiderOnboarding.aadhar_photo)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏩ Skip", callback_data="onboard_skip_aadhar")],
    ])
    await message.answer(
        "✅ License photo received!\n\n"
        "<b>Step 7/9:</b> Optionally, send a photo of your <b>Aadhar card</b> "
        "for faster verification.",
        reply_markup=kb,
    )


@router.message(RiderOnboarding.license_photo)
async def license_photo_invalid(message: Message, state: FSMContext):
    """Handle non-photo input for license step."""
    await message.answer(
        "⚠️ Please send a <b>photo</b> of your driving license.\n"
        "Use the camera or gallery — don't send it as a file.",
    )


# ── Step 7: Aadhar Photo (optional) ──────────────────────

@router.callback_query(F.data == "onboard_skip_aadhar")
async def skip_aadhar(callback: CallbackQuery, state: FSMContext):
    """Skip Aadhar photo step."""
    await callback.answer()
    await state.update_data(aadhar_file_id=None)
    await _show_warehouse_selection(callback.message, state, edit=True)


@router.message(RiderOnboarding.aadhar_photo, F.photo)
async def process_aadhar_photo(message: Message, state: FSMContext):
    """Collect Aadhar photo."""
    photo = message.photo[-1]
    await state.update_data(aadhar_file_id=photo.file_id)
    await _show_warehouse_selection(message, state, edit=False)


@router.message(RiderOnboarding.aadhar_photo)
async def aadhar_photo_invalid(message: Message, state: FSMContext):
    """Handle non-photo input for Aadhar step."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏩ Skip", callback_data="onboard_skip_aadhar")],
    ])
    await message.answer(
        "⚠️ Please send a <b>photo</b> of your Aadhar card, or tap Skip.",
        reply_markup=kb,
    )


# ── Step 8: Preferred Zone (Warehouse) ───────────────────

async def _show_warehouse_selection(target, state: FSMContext, edit: bool = False):
    """Fetch warehouses and show inline selection keyboard."""
    warehouses = await _api_call("GET", "/api/warehouses/")
    if not warehouses:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏩ Skip (No Preference)", callback_data="warehouse_none")],
        ])
        text = (
            "<b>Step 8/9:</b> Select your preferred <b>operating hub</b>.\n\n"
            "⚠️ No active warehouses found. You can skip this step."
        )
    else:
        buttons = []
        for wh in warehouses:
            label = f"🏭 {wh['name']}"
            if wh.get("city"):
                label += f" ({wh['city']})"
            buttons.append([
                InlineKeyboardButton(text=label, callback_data=f"warehouse_{wh['id']}")
            ])
        buttons.append([
            InlineKeyboardButton(text="⏩ No Preference", callback_data="warehouse_none")
        ])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        text = "<b>Step 8/9:</b> Select your preferred <b>operating hub</b>:"

    await state.set_state(RiderOnboarding.preferred_zone)

    if edit and hasattr(target, 'edit_text'):
        await target.edit_text(text, reply_markup=kb)
    else:
        await target.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("warehouse_"), RiderOnboarding.preferred_zone)
async def process_warehouse(callback: CallbackQuery, state: FSMContext):
    """Select preferred warehouse."""
    await callback.answer()
    wh_id = callback.data.replace("warehouse_", "")

    if wh_id == "none":
        await state.update_data(preferred_warehouse_id=None)
    else:
        await state.update_data(preferred_warehouse_id=wh_id)

    await _show_confirmation(callback.message, state)


# ── Step 9: Review & Confirm ─────────────────────────────

async def _show_confirmation(message, state: FSMContext):
    """Display summary for review before submission."""
    data = await state.get_data()
    await state.set_state(RiderOnboarding.confirm_submission)

    vehicle_labels = {
        "BIKE": "🏍️ Bike",
        "MINI_VAN": "🚐 Mini Van",
        "MINI_TRUCK": "🚛 Mini Truck",
        "TRUCK": "🚚 Truck",
    }

    summary = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 <b>Application Summary</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>Name:</b> {data.get('full_name')}\n"
        f"📱 <b>Phone:</b> {data.get('phone')}\n"
        f"📧 <b>Email:</b> {data.get('email') or 'Not provided'}\n"
        f"🚗 <b>Vehicle:</b> {vehicle_labels.get(data.get('vehicle_type'), data.get('vehicle_type'))}\n"
        f"🔢 <b>Registration:</b> {data.get('vehicle_reg')}\n"
        f"📄 <b>License:</b> {'✅ Uploaded' if data.get('license_file_id') else '❌ Missing'}\n"
        f"🪪 <b>Aadhar:</b> {'✅ Uploaded' if data.get('aadhar_file_id') else 'Skipped'}\n"
        f"🏭 <b>Hub:</b> {'Selected' if data.get('preferred_warehouse_id') else 'No preference'}\n\n"
        "Does everything look correct?"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Submit Application", callback_data="onboard_submit"),
            InlineKeyboardButton(text="✏️ Edit Details", callback_data="onboard_edit"),
        ],
    ])

    await message.edit_text(summary, reply_markup=kb)


@router.callback_query(F.data == "onboard_edit", RiderOnboarding.confirm_submission)
async def edit_application(callback: CallbackQuery, state: FSMContext):
    """Restart the onboarding flow from Step 1."""
    await callback.answer("Starting over — your photos are saved.")
    await state.set_state(RiderOnboarding.full_name)
    await callback.message.edit_text(
        "✏️ <b>Let's update your details.</b>\n\n"
        "<b>Step 1/9:</b> What is your <b>full name</b>?",
    )


# ── Step 10: Submit ───────────────────────────────────────

@router.callback_query(F.data == "onboard_submit", RiderOnboarding.confirm_submission)
async def submit_application(callback: CallbackQuery, state: FSMContext):
    """Submit the rider application to the backend."""
    await callback.answer("Submitting...")
    data = await state.get_data()

    payload = {
        "telegram_id": callback.from_user.id,
        "full_name": data["full_name"],
        "phone": data["phone"],
        "email": data.get("email"),
        "vehicle": data["vehicle_type"],
        "vehicle_reg": data.get("vehicle_reg"),
        "license_file_id": data.get("license_file_id"),
        "aadhar_file_id": data.get("aadhar_file_id"),
        "preferred_warehouse_id": data.get("preferred_warehouse_id"),
    }

    result = await _api_call("POST", "/api/rider-applications/", json=payload)

    if result:
        await state.clear()
        success_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📞 Contact Support", url="https://t.me/TeleporterSupport")],
        ])
        await callback.message.edit_text(
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎉 <b>Application Submitted!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Our team will review your application within <b>24-48 hours</b>.\n\n"
            "We'll notify you right here once it's processed.\n"
            "No need to check back — we'll send you a message! 🔔",
            reply_markup=success_kb,
        )
        logger.info(
            "Rider application submitted: telegram_id=%s, name=%s",
            callback.from_user.id,
            data["full_name"],
        )
    else:
        error_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Try Again", callback_data="onboard_submit")],
            [InlineKeyboardButton(text="📞 Contact Support", url="https://t.me/TeleporterSupport")],
        ])
        await callback.message.edit_text(
            "⚠️ <b>Submission Failed</b>\n\n"
            "There was an error submitting your application.\n"
            "This may happen if you already have an application on file.\n\n"
            "Please try again or contact support.",
            reply_markup=error_kb,
        )
        logger.error(
            "Rider application submission failed: telegram_id=%s",
            callback.from_user.id,
        )
