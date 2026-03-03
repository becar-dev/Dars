"""Inline tugmalar."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


STATUSES = [
    ("Faqat narx so‘radi", "asked_price"),
    ("Buyurtma berdi", "ordered"),
    ("Shoshildi", "urgent"),
    ("Qaytib keldi", "returned"),
]


def main_menu_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➕ Yangi mijoz", callback_data="menu:new_customer")
    b.button(text="📊 7 kunlik statistika", callback_data="menu:stats_7")
    b.button(text="📊 30 kunlik statistika", callback_data="menu:stats_30")
    b.button(text="📈 To‘liq statistika", callback_data="menu:stats_all")
    b.button(text="📅 Sana bo‘yicha statistika", callback_data="menu:stats_date")
    b.adjust(1)
    return b.as_markup()


def category_keyboard(is_admin: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🗂 Kantselyariya", callback_data="cat:stationery")
    b.button(text="🖨 Usluga", callback_data="cat:service")
    if is_admin:
        b.button(text="⚙️ Admin katalog", callback_data="admin:open")
    b.button(text="❌ Bekor qilish", callback_data="flow:cancel")
    b.adjust(2, 1, 1)
    return b.as_markup()


def products_keyboard(products: list[dict]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for p in products:
        b.button(text=p["name"], callback_data=f"product:{p['id']}")
    b.button(text="⬅️ Orqaga", callback_data="flow:back_category")
    b.button(text="❌ Bekor qilish", callback_data="flow:cancel")
    b.adjust(2)
    return b.as_markup()


def models_keyboard(models: list[dict]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for m in models:
        b.button(text=f"{m['model_name']} — {m['unit_price']} so'm", callback_data=f"model:{m['id']}")
    b.button(text="⬅️ Orqaga", callback_data="flow:back_products")
    b.button(text="❌ Bekor qilish", callback_data="flow:cancel")
    b.adjust(1)
    return b.as_markup()


def services_keyboard(services: list[dict]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in services:
        b.button(text=s["name"], callback_data=f"service:{s['id']}")
    b.button(text="⬅️ Orqaga", callback_data="flow:back_category")
    b.button(text="❌ Bekor qilish", callback_data="flow:cancel")
    b.adjust(2)
    return b.as_markup()


def status_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for label, value in STATUSES:
        b.button(text=label, callback_data=f"status:{value}")
    b.button(text="❌ Bekor qilish", callback_data="flow:cancel")
    b.adjust(1)
    return b.as_markup()


def post_item_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➕ Yana qo‘shish", callback_data="flow:add_more")
    b.button(text="✅ Yakunlash", callback_data="flow:finish")
    b.button(text="❌ Bekor qilish", callback_data="flow:cancel")
    b.adjust(1)
    return b.as_markup()


def admin_catalog_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➕ Mahsulot qo‘shish", callback_data="admin:add_product")
    b.button(text="✏️ Mahsulot tahrirlash", callback_data="admin:edit_product")
    b.button(text="🗑 Mahsulot o‘chirish", callback_data="admin:delete_product")
    b.button(text="➕ Model qo‘shish", callback_data="admin:add_model")
    b.button(text="✏️ Model tahrirlash", callback_data="admin:edit_model")
    b.button(text="🗑 Model o‘chirish", callback_data="admin:delete_model")
    b.button(text="⬅️ Orqaga", callback_data="admin:back")
    b.adjust(1)
    return b.as_markup()


def yes_no_active_keyboard(prefix: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Faol", callback_data=f"{prefix}:active")
    b.button(text="🚫 Nofaol", callback_data=f"{prefix}:inactive")
    b.adjust(2)
    return b.as_markup()
