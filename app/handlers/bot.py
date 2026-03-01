"""Telegram bot handlers for menu, multi-item FSM flow, and reports (Uzbek)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.db.database import Database
from app.keyboards.inline import (
    build_catalog_keyboard,
    build_category_keyboard,
    build_main_menu_keyboard,
    build_post_item_keyboard,
    build_status_keyboard,
)
from app.states.customer_flow import CustomerLogStates

router = Router(name=__name__)


def _is_non_negative_int(value: str) -> bool:
    return value.isdigit()


async def _safe_edit_or_answer(callback: CallbackQuery, text: str, reply_markup=None) -> None:
    """Avoid crashing on edit edge-cases and fallback to answer message."""

    if callback.message is None:
        await callback.answer()
        return

    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            await callback.answer()
            return
        # Fallback to plain message in other edit-related edge cases.
        await callback.message.answer(text, reply_markup=reply_markup)


def _get_user_id(message_or_callback: Message | CallbackQuery) -> int | None:
    user = message_or_callback.from_user
    return user.id if user else None


def _main_menu_text() -> str:
    return (
        "Assalomu alaykum! Printshop + Kantselyariya mini-CRM botiga xush kelibsiz 👋\n"
        "Kerakli bo‘limni tanlang:"
    )


@router.message(CommandStart())
async def start_command_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(_main_menu_text(), reply_markup=build_main_menu_keyboard())


@router.callback_query(F.data == "menu:new_customer")
async def add_customer_entry(
    callback: CallbackQuery,
    state: FSMContext,
    admin_ids: set[int],
) -> None:
    await state.clear()
    await state.update_data(order_items=[], statuses=[], admin_ids=admin_ids)
    await state.set_state(CustomerLogStates.choosing_category)
    await _safe_edit_or_answer(
        callback,
        "Kategoriya tanlang:",
        reply_markup=build_category_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "flow:cancel")
async def cancel_flow(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _safe_edit_or_answer(callback, _main_menu_text(), reply_markup=build_main_menu_keyboard())
    await callback.answer("Bekor qilindi")


@router.callback_query(CustomerLogStates.choosing_category, F.data.startswith("category:"))
async def choose_category(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    category = callback.data.split(":", 1)[1]
    await state.update_data(category=category)
    await state.set_state(CustomerLogStates.choosing_catalog_item)

    items = db.get_catalog_items(category)
    user_id = _get_user_id(callback)
    data = await state.get_data()
    admin_ids = data.get("admin_ids", set())
    can_add = bool(user_id in admin_ids)

    text = "Xizmatni tanlang:" if category == "service" else "Mahsulotni tanlang:"
    await _safe_edit_or_answer(
        callback,
        text,
        reply_markup=build_catalog_keyboard(category=category, items=items, can_add=can_add),
    )
    await callback.answer()


@router.callback_query(F.data == "flow:back_to_category")
async def back_to_category(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CustomerLogStates.choosing_category)
    await _safe_edit_or_answer(callback, "Kategoriya tanlang:", reply_markup=build_category_keyboard())
    await callback.answer()


@router.callback_query(CustomerLogStates.choosing_catalog_item, F.data == "catalog:add")
async def add_catalog_item_prompt(
    callback: CallbackQuery,
    state: FSMContext,
    admin_ids: set[int],
) -> None:
    user_id = _get_user_id(callback)
    if user_id not in admin_ids:
        await callback.answer("Bu amal faqat admin uchun.", show_alert=True)
        return

    data = await state.get_data()
    category = data.get("category")
    if category == "service":
        prompt = "Yangi xizmat nomini kiriting:"
    else:
        prompt = "Yangi mahsulot nomini kiriting:"
    await state.set_state(CustomerLogStates.adding_catalog_item_name)
    await _safe_edit_or_answer(callback, prompt)
    await callback.answer()


@router.message(CustomerLogStates.adding_catalog_item_name)
async def add_catalog_item_name(
    message: Message,
    state: FSMContext,
    db: Database,
    admin_ids: set[int],
) -> None:
    user_id = _get_user_id(message)
    if user_id not in admin_ids:
        await message.answer("Bu amal faqat admin uchun.")
        return

    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Nom juda qisqa. Qayta kiriting:")
        return

    data = await state.get_data()
    category = data.get("category", "service")
    db.add_catalog_item(category, name)

    await state.set_state(CustomerLogStates.choosing_catalog_item)
    items = db.get_catalog_items(category)
    user_id = _get_user_id(message)
    admin_ids = data.get("admin_ids", set())
    can_add = bool(user_id in admin_ids)
    text = "Xizmatni tanlang:" if category == "service" else "Mahsulotni tanlang:"
    await message.answer(
        f"✅ Qo‘shildi: {name}\n\n{text}",
        reply_markup=build_catalog_keyboard(category=category, items=items, can_add=can_add),
    )


@router.callback_query(CustomerLogStates.choosing_catalog_item, F.data.startswith("pick_item:"))
async def pick_catalog_item(callback: CallbackQuery, state: FSMContext) -> None:
    item_name = callback.data.split(":", 1)[1]
    data = await state.get_data()
    category = data.get("category", "service")

    await state.update_data(item_name=item_name)

    if category == "service" and item_name.lower() == "nusxa/chop":
        await state.set_state(CustomerLogStates.entering_quantity)
        await _safe_edit_or_answer(callback, "Nusxa/Chop: necha bet? (raqam)")
    elif category == "stationery":
        await state.set_state(CustomerLogStates.entering_quantity)
        await _safe_edit_or_answer(callback, "Soni nechta? (raqam)")
    else:
        await state.set_state(CustomerLogStates.entering_total_price)
        await _safe_edit_or_answer(callback, "Jami summani kiriting (so‘mda):")

    await callback.answer()


@router.message(CustomerLogStates.entering_quantity)
async def enter_quantity(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not _is_non_negative_int(raw):
        await message.answer("Faqat raqam kiriting. Masalan: 10")
        return
    quantity = int(raw)
    if quantity < 1:
        await message.answer("Soni 1 dan katta bo‘lishi kerak.")
        return

    await state.update_data(quantity=quantity)
    data = await state.get_data()
    item_name = data.get("item_name", "")
    if str(item_name).lower() == "nusxa/chop":
        await state.set_state(CustomerLogStates.entering_unit_price)
        await message.answer("1 bet narxini kiriting (so‘mda):")
    else:
        await state.set_state(CustomerLogStates.entering_unit_price)
        await message.answer("1 dona narxini kiriting (so‘mda):")


@router.message(CustomerLogStates.entering_unit_price)
async def enter_unit_price(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not _is_non_negative_int(raw):
        await message.answer("Faqat raqam kiriting. Masalan: 10")
        return
    unit_price = int(raw)
    if unit_price < 0:
        await message.answer("Manfiy qiymat bo‘lishi mumkin emas.")
        return

    data = await state.get_data()
    quantity = int(data.get("quantity", 1))
    line_total = quantity * unit_price

    await _save_item_into_session(state, unit_price=unit_price, quantity=quantity, line_total=line_total)
    await state.set_state(CustomerLogStates.choosing_status)
    await message.answer("Mijoz holatini tanlang:", reply_markup=build_status_keyboard())


@router.message(CustomerLogStates.entering_total_price)
async def enter_total_price(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not _is_non_negative_int(raw):
        await message.answer("Faqat raqam kiriting. Masalan: 10")
        return
    total = int(raw)
    if total < 0:
        await message.answer("Manfiy qiymat bo‘lishi mumkin emas.")
        return

    await _save_item_into_session(state, quantity=1, unit_price=total, line_total=total)
    await state.set_state(CustomerLogStates.choosing_status)
    await message.answer("Mijoz holatini tanlang:", reply_markup=build_status_keyboard())


async def _save_item_into_session(
    state: FSMContext,
    quantity: int,
    unit_price: int,
    line_total: int,
) -> None:
    data = await state.get_data()
    current_items = list(data.get("order_items", []))
    current_items.append(
        {
            "category": data.get("category"),
            "item_name": data.get("item_name"),
            "quantity": quantity,
            "unit_price": unit_price,
            "line_total": line_total,
        }
    )
    await state.update_data(order_items=current_items)


@router.callback_query(CustomerLogStates.choosing_status, F.data.startswith("status:"))
async def choose_status(callback: CallbackQuery, state: FSMContext) -> None:
    status = callback.data.split(":", 1)[1]
    data = await state.get_data()

    # Business rule: 0 summa faqat "asked_price" holatida ruxsat.
    order_items = list(data.get("order_items", []))
    current_item = order_items[-1] if order_items else None
    if current_item and int(current_item.get("line_total", 0)) == 0 and status != "asked_price":
        await callback.answer(
            "0 summa faqat 'Faqat narx so‘radi' holatida mumkin.",
            show_alert=True,
        )
        return

    statuses = list(data.get("statuses", []))
    statuses.append(status)
    await state.update_data(statuses=statuses)

    await state.set_state(CustomerLogStates.post_item_action)
    await _safe_edit_or_answer(
        callback,
        "✅ Qo‘shildi. Yana qo‘shamizmi yoki yakunlaymizmi?",
        reply_markup=build_post_item_keyboard(),
    )
    await callback.answer()


@router.callback_query(CustomerLogStates.post_item_action, F.data == "flow:add_another")
async def add_another_item(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CustomerLogStates.choosing_category)
    await _safe_edit_or_answer(callback, "Kategoriya tanlang:", reply_markup=build_category_keyboard())
    await callback.answer()


@router.callback_query(CustomerLogStates.post_item_action, F.data == "flow:finish")
async def finish_order(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    items: list[dict] = data.get("order_items", [])
    statuses: list[str] = data.get("statuses", [])

    if not items:
        await callback.answer("Element yo‘q", show_alert=True)
        return

    final_status = statuses[-1] if statuses else "ordered"
    customer_type = "returning" if final_status == "returned" else "walk_in"

    # asked_price can be zero, others remain whatever operator entered (>=0 validated)
    db.create_order(status=final_status, customer_type=customer_type, items=items)

    await state.clear()
    await _safe_edit_or_answer(callback, "Buyurtma saqlandi ✅", reply_markup=build_main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:today_stats")
async def today_statistics(callback: CallbackQuery, db: Database) -> None:
    stats = db.fetch_today_statistics()
    text = (
        "📊 Bugungi statistika\n\n"
        f"• Bugun buyurtmalar soni: {stats['orders_count']}\n"
        f"• Bugun itemlar soni: {stats['items_count']}\n"
        f"• Bugungi jami tushum: {stats['revenue']} so‘m\n"
        f"• 'Faqat narx so‘radi': {stats['asked_price_count']}\n"
        f"• Eng ko‘p so‘ralgan: {stats['top_item']}"
    )
    await _safe_edit_or_answer(callback, text, reply_markup=build_main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:weekly_stats")
async def weekly_statistics(callback: CallbackQuery, db: Database) -> None:
    stats = db.fetch_weekly_statistics()
    top3_text = ", ".join(stats["top3"]) if stats["top3"] else "Ma'lumot yo‘q"
    text = (
        "📅 Haftalik statistika (oxirgi 7 kun)\n\n"
        f"• Buyurtmalar soni: {stats['orders_count']}\n"
        f"• Jami tushum: {stats['revenue']} so‘m\n"
        f"• Top 3 xizmat/mahsulot: {top3_text}"
    )
    await _safe_edit_or_answer(callback, text, reply_markup=build_main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:service_report")
async def service_report(callback: CallbackQuery, db: Database) -> None:
    report = db.fetch_service_report()
    if not report:
        text = "📦 Hisobot\n\nHozircha ma'lumot yo‘q."
    else:
        rows = ["📦 Hisobot (xizmat/mahsulot)\n"]
        for row in report:
            category_name = "Xizmat" if row["category"] == "service" else "Kantselyariya"
            rows.append(
                "\n".join(
                    [
                        f"• [{category_name}] {row['item_name']}",
                        f"  - Soni: {row['count']}",
                        f"  - Jami tushum: {row['revenue']} so‘m",
                        f"  - O‘rtacha chek: {row['avg_check']} so‘m",
                    ]
                )
            )
            rows.append("")
        text = "\n".join(rows).strip()

    await _safe_edit_or_answer(callback, text, reply_markup=build_main_menu_keyboard())
    await callback.answer()
