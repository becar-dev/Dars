"""Inline keyboard builders used by bot handlers (Uzbek UI)."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

MENU_BUTTONS = [
    ("➕ Yangi mijoz", "menu:new_customer"),
    ("📊 Bugungi statistika", "menu:today_stats"),
    ("📅 Haftalik statistika", "menu:weekly_stats"),
    ("📦 Hisobot (xizmat/mahsulot)", "menu:service_report"),
]

STATUS_BUTTONS = [
    ("Faqat narx so‘radi", "asked_price"),
    ("Buyurtma berdi", "ordered"),
    ("Shoshildi", "urgent"),
    ("Qaytib keldi", "returned"),
]


def build_main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, callback_data in MENU_BUTTONS:
        builder.button(text=text, callback_data=callback_data)
    builder.adjust(1)
    return builder.as_markup()


def build_category_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🖨 Xizmat", callback_data="category:service")
    builder.button(text="🗂 Kantselyariya", callback_data="category:stationery")
    builder.button(text="❌ Bekor qilish", callback_data="flow:cancel")
    builder.adjust(2, 1)
    return builder.as_markup()


def build_catalog_keyboard(
    category: str,
    items: list[str],
    can_add: bool,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.button(text=item, callback_data=f"pick_item:{item}")

    if can_add:
        add_text = "➕ Xizmat qo‘shish" if category == "service" else "➕ Mahsulot qo‘shish"
        builder.button(text=add_text, callback_data="catalog:add")

    builder.button(text="⬅️ Orqaga", callback_data="flow:back_to_category")
    builder.button(text="❌ Bekor qilish", callback_data="flow:cancel")
    builder.adjust(2)
    return builder.as_markup()


def build_status_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, value in STATUS_BUTTONS:
        builder.button(text=text, callback_data=f"status:{value}")
    builder.button(text="❌ Bekor qilish", callback_data="flow:cancel")
    builder.adjust(1)
    return builder.as_markup()


def build_post_item_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Yana qo‘shish", callback_data="flow:add_another")
    builder.button(text="✅ Yakunlash", callback_data="flow:finish")
    builder.button(text="❌ Bekor qilish", callback_data="flow:cancel")
    builder.adjust(1)
    return builder.as_markup()
