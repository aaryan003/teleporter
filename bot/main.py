import asyncio

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from bot.config import API_BASE_URL, TELEGRAM_BOT_TOKEN


class BookingStates(StatesGroup):
    waiting_pickup_location = State()
    waiting_drop_location = State()
    waiting_weight = State()


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🚚 Book delivery")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def location_kb(prompt: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=prompt, request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "👋 Welcome to TeleporterBot!\n"
        "Tap *Book delivery* to start.",
        reply_markup=main_menu_kb(),
        parse_mode="Markdown",
    )


async def start_booking(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "📍 Please share your *pickup location* using the button below.",
        reply_markup=location_kb("📍 Share pickup location"),
        parse_mode="Markdown",
    )
    await state.set_state(BookingStates.waiting_pickup_location)


async def pickup_location_received(message: Message, state: FSMContext) -> None:
    if not message.location:
        await message.answer(
            "Please use the button to share your *location*.", parse_mode="Markdown"
        )
        return

    await state.update_data(
        pickup_lat=message.location.latitude,
        pickup_lng=message.location.longitude,
    )
    await message.answer(
        "✅ Pickup location saved.\n"
        "Now share the *drop location* (where the parcel should go).",
        reply_markup=location_kb("📍 Share drop location"),
        parse_mode="Markdown",
    )
    await state.set_state(BookingStates.waiting_drop_location)


async def drop_location_received(message: Message, state: FSMContext) -> None:
    if not message.location:
        await message.answer(
            "Please use the button to share the *drop location*.", parse_mode="Markdown"
        )
        return

    await state.update_data(
        drop_lat=message.location.latitude,
        drop_lng=message.location.longitude,
    )
    await message.answer(
        "⚖️ Finally, send the approximate *weight in kg* (e.g. `1.5`).",
        parse_mode="Markdown",
    )
    await state.set_state(BookingStates.waiting_weight)


async def weight_received(message: Message, state: FSMContext) -> None:
    try:
        weight_kg = float(message.text)
    except (TypeError, ValueError):
        await message.answer("Please send a valid number for weight, e.g. 1.5")
        return

    data = await state.get_data()
    pickup_lat = data["pickup_lat"]
    pickup_lng = data["pickup_lng"]
    drop_lat = data["drop_lat"]
    drop_lng = data["drop_lng"]

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            preview_resp = await client.post(
                f"{API_BASE_URL}/orders/preview",
                json={
                    "pickup_lat": pickup_lat,
                    "pickup_lng": pickup_lng,
                    "drop_lat": drop_lat,
                    "drop_lng": drop_lng,
                    "weight_kg": weight_kg,
                    "vehicle_type": "BIKE",
                    "time_type": "STANDARD",
                    "is_batch_eligible": True,
                    "addons": [],
                },
            )
            preview_resp.raise_for_status()
            preview = preview_resp.json()

        total_cost = preview["total_cost"]
        distance_km = preview["distance_km"]
        await message.answer(
            f"✅ Estimated price: ₹{total_cost:.2f} for ~{distance_km:.1f} km.\n"
            "This is a price estimate only.",
            reply_markup=main_menu_kb(),
        )
    except Exception:
        await message.answer(
            "⚠️ Could not reach the pricing server. Please try again later.",
            reply_markup=main_menu_kb(),
        )

    await state.clear()


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()

    dp.message.register(cmd_start, Command("start"))
    dp.message.register(start_booking, F.text == "🚚 Book delivery")
    dp.message.register(
        pickup_location_received,
        BookingStates.waiting_pickup_location,
        F.location,
    )
    dp.message.register(
        drop_location_received,
        BookingStates.waiting_drop_location,
        F.location,
    )
    dp.message.register(weight_received, BookingStates.waiting_weight)

    asyncio.run(dp.start_polling(bot))


if __name__ == "__main__":
    main()

