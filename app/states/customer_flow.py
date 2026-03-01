"""FSM states for customer logging conversation."""

from aiogram.fsm.state import State, StatesGroup


class CustomerLogStates(StatesGroup):
    """Step-by-step flow to save one customer interaction."""

    choosing_service = State()
    choosing_status = State()
    entering_amount = State()
