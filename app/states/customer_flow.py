"""FSM states for multi-item order logging flow."""

from aiogram.fsm.state import State, StatesGroup


class CustomerLogStates(StatesGroup):
    """Step-by-step flow to create an order with multiple items."""

    choosing_category = State()
    choosing_catalog_item = State()
    adding_catalog_item_name = State()

    entering_quantity = State()
    entering_unit_price = State()
    entering_total_price = State()

    choosing_status = State()
    post_item_action = State()
