"""FSM states for user booking flow."""

from aiogram.fsm.state import StatesGroup, State


class BookingFlow(StatesGroup):
    """User delivery booking state machine."""
    waiting_pickup_address = State()
    waiting_pickup_slot = State()
    waiting_drop_address = State()
    waiting_recipient_name = State()   # NEW: who receives the parcel?
    waiting_recipient_phone = State()  # NEW: recipient's phone number
    waiting_package_size = State()
    confirm_estimate = State()
    waiting_payment = State()
    select_pickup_slot = State()


class UserRegistration(StatesGroup):
    """User registration state machine."""
    waiting_phone = State()
