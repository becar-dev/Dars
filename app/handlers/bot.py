"""Telegram bot handlers for menu, FSM flow, and reports."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.db.database import Database
from app.keyboards.inline import (
    build_main_menu_keyboard,
    build_services_keyboard,
    build_statuses_keyboard,
)
from app.states.customer_flow import CustomerLogStates

router = Router(name=__name__)


def _main_menu_text() -> str:
    return (
        "Welcome to PrintShop Micro-CRM Bot 👋\n"
        "Use the menu below to add customers and view statistics."
    )


@router.message(CommandStart())
async def start_command_handler(message: Message, state: FSMContext) -> None:
    """Show the main menu and reset any active state."""

    await state.clear()
    await message.answer(_main_menu_text(), reply_markup=build_main_menu_keyboard())


@router.callback_query(F.data == "menu:add_customer")
async def add_customer_entry(callback: CallbackQuery, state: FSMContext) -> None:
    """Start FSM flow with service selection."""

    await state.clear()
    await state.set_state(CustomerLogStates.choosing_service)
    await callback.message.edit_text(
        "Step 1/3: Choose service type:", reply_markup=build_services_keyboard()
    )
    await callback.answer()


@router.callback_query(CustomerLogStates.choosing_service, F.data.startswith("service:"))
async def select_service(callback: CallbackQuery, state: FSMContext) -> None:
    """Save service and ask for customer status."""

    service = callback.data.split(":", 1)[1]
    await state.update_data(service=service)
    await state.set_state(CustomerLogStates.choosing_status)
    await callback.message.edit_text(
        "Step 2/3: Select customer status:", reply_markup=build_statuses_keyboard()
    )
    await callback.answer()


@router.callback_query(CustomerLogStates.choosing_status, F.data.startswith("status:"))
async def select_status(callback: CallbackQuery, state: FSMContext) -> None:
    """Save status and ask for order amount."""

    status = callback.data.split(":", 1)[1]
    await state.update_data(status=status)
    await state.set_state(CustomerLogStates.entering_amount)
    await callback.message.edit_text(
        "Step 3/3: Enter order amount (numbers only, 0 is allowed):"
    )
    await callback.answer()


@router.message(CustomerLogStates.entering_amount)
async def save_customer_amount(
    message: Message, state: FSMContext, db: Database
) -> None:
    """Validate numeric input, save data, and return to menu."""

    raw_amount = (message.text or "").strip()
    if not raw_amount.isdigit():
        await message.answer("⚠️ Amount must be a non-negative number. Try again:")
        return

    amount = int(raw_amount)
    data = await state.get_data()
    service = data["service"]
    status = data["status"]

    db.add_customer_log(service=service, status=status, amount=amount)

    await state.clear()
    await message.answer(
        "Customer successfully saved ✅", reply_markup=build_main_menu_keyboard()
    )


@router.callback_query(F.data == "menu:today_stats")
async def today_statistics(callback: CallbackQuery, db: Database) -> None:
    """Show today's business metrics."""

    stats = db.fetch_today_statistics()
    text = (
        "📊 Today's Statistics\n\n"
        f"Total visitors: {stats['total_visitors']}\n"
        f"Number of real orders: {stats['real_orders']}\n"
        f"Price inquiries: {stats['price_inquiries']}\n"
        f"Total revenue today: {stats['revenue']}"
    )
    await callback.message.edit_text(text, reply_markup=build_main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:weekly_stats")
async def weekly_statistics(callback: CallbackQuery, db: Database) -> None:
    """Show weekly summary metrics."""

    stats = db.fetch_weekly_statistics()
    text = (
        "📅 Weekly Statistics (last 7 days)\n\n"
        f"Total visitors last 7 days: {stats['total_visitors']}\n"
        f"Total revenue: {stats['revenue']}\n"
        f"Most requested service: {stats['most_requested_service']}"
    )
    await callback.message.edit_text(text, reply_markup=build_main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:service_report")
async def service_report(callback: CallbackQuery, db: Database) -> None:
    """Show per-service analytics report."""

    report = db.fetch_service_report()
    if not report:
        text = "📦 Service Report\n\nNo data yet. Add your first customer interaction."
    else:
        rows = ["📦 Service Report\n"]
        for row in report:
            rows.append(
                "\n".join(
                    [
                        f"• {row['service']}",
                        f"  - Requested: {row['requested_count']}",
                        f"  - Actual orders: {row['actual_orders']}",
                        f"  - Revenue: {row['revenue']}",
                    ]
                )
            )
            rows.append("")
        text = "\n".join(rows).strip()

    await callback.message.edit_text(text, reply_markup=build_main_menu_keyboard())
    await callback.answer()
