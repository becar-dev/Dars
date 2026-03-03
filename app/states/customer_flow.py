"""FSM holatlari."""

from aiogram.fsm.state import State, StatesGroup


class CustomerFlowStates(StatesGroup):
    choosing_category = State()
    choosing_product = State()
    choosing_model = State()
    choosing_service = State()

    entering_quantity = State()
    entering_unit_price = State()
    entering_total_price = State()

    choosing_status = State()
    post_item = State()
    entering_date = State()


class AdminCatalogStates(StatesGroup):
    choosing_admin_action = State()
    entering_product_name = State()

    choosing_product_for_model = State()
    entering_model_name = State()
    entering_model_price = State()

    choosing_product_to_edit = State()
    entering_product_new_name = State()

    choosing_model_to_edit = State()
    entering_model_new_name = State()
    entering_model_new_price = State()

    choosing_product_to_delete = State()
    choosing_model_to_delete = State()
