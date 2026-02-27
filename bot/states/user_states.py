"""FSM states for user booking flow."""

from aiogram.fsm.state import StatesGroup, State


class BookingFlow(StatesGroup):
    """User delivery booking state machine."""
    waiting_pickup_address = State()
    waiting_drop_address = State()
    waiting_weight_tier = State()
    confirm_estimate = State()
    waiting_payment = State()
    select_pickup_slot = State()
