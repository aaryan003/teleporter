"""FSM states for rider onboarding multi-step flow."""

from aiogram.fsm.state import StatesGroup, State


class RiderOnboarding(StatesGroup):
    """Rider onboarding application state machine — 10 steps."""
    full_name = State()
    phone = State()
    email = State()
    vehicle_type = State()
    vehicle_reg = State()
    license_photo = State()
    aadhar_photo = State()
    preferred_zone = State()
    confirm_submission = State()
