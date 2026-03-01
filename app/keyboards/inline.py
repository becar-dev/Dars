"""Inline keyboard builders used by bot handlers."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

MAIN_MENU_BUTTONS = [
    ("➕ Add New Customer", "menu:add_customer"),
    ("📊 Today's Statistics", "menu:today_stats"),
    ("📅 Weekly Statistics", "menu:weekly_stats"),
    ("📦 Service Report", "menu:service_report"),
]

SERVICES = [
    "Business Card",
    "Banner",
    "Lamination",
    "Copy/Print",
    "Scanning",
    "Design",
    "Stationery Sale",
]

CUSTOMER_STATUSES = [
    "Asked price only",
    "Placed order",
    "Urgent client",
    "Returning customer",
]


def build_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Create menu keyboard shown on /start and after each action."""

    builder = InlineKeyboardBuilder()
    for text, callback_data in MAIN_MENU_BUTTONS:
        builder.button(text=text, callback_data=callback_data)
    builder.adjust(1)
    return builder.as_markup()


def build_services_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard with available print shop services."""

    builder = InlineKeyboardBuilder()
    for service in SERVICES:
        builder.button(text=service, callback_data=f"service:{service}")
    builder.adjust(2)
    return builder.as_markup()


def build_statuses_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for selecting customer interaction status."""

    builder = InlineKeyboardBuilder()
    for status in CUSTOMER_STATUSES:
        builder.button(text=status, callback_data=f"status:{status}")
    builder.adjust(1)
    return builder.as_markup()
