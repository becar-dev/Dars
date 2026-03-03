"""Asosiy bot handlerlari."""

from __future__ import annotations

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.db.database import Database
from app.keyboards.inline import (
    admin_catalog_keyboard,
    category_keyboard,
    main_menu_keyboard,
    models_keyboard,
    post_item_keyboard,
    products_keyboard,
    services_keyboard,
    status_keyboard,
    yes_no_active_keyboard,
)
from app.states.customer_flow import AdminCatalogStates, CustomerFlowStates

router = Router(name=__name__)


def _is_admin(user_id: int | None, admin_ids: set[int]) -> bool:
    return bool(user_id and user_id in admin_ids)


def _to_int(value: str) -> int | None:
    if not value.isdigit():
        return None
    return int(value)


async def safe_edit(callback: CallbackQuery, text: str, markup=None) -> None:
    if callback.message is None:
        await callback.answer()
        return
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            await callback.answer()
            return
        await callback.message.answer(text, reply_markup=markup)


def _menu_text() -> str:
    return "Assalomu alaykum! Kerakli bo‘limni tanlang:"


def _format_stats(title: str, stats: dict) -> str:
    top = stats.get("top_items", [])
    top_lines = [f"{idx}) {i['name']} — {i['count']} ta" for idx, i in enumerate(top, start=1)]
    while len(top_lines) < 3:
        top_lines.append(f"{len(top_lines)+1}) - — 0 ta")
    return (
        f"{title}\n\n"
        f"🧾 Buyurtmalar: {stats['orders_count']} ta\n"
        f"💰 Tushum: {stats['revenue']} so'm\n"
        f"📦 Itemlar: {stats['items_count']} ta\n"
        f"❓ Faqat narx so‘radi: {stats['asked_price_count']} ta\n"
        "🏆 Top 3:\n" + "\n".join(top_lines)
    )


@router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(_menu_text(), reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "menu:new_customer")
async def start_customer_flow(callback: CallbackQuery, state: FSMContext, admin_ids: set[int]) -> None:
    user_id = callback.from_user.id if callback.from_user else None
    await state.clear()
    await state.update_data(order_items=[], statuses=[])
    await state.set_state(CustomerFlowStates.choosing_category)
    await safe_edit(
        callback,
        "Kategoriya tanlang:",
        category_keyboard(is_admin=_is_admin(user_id, admin_ids)),
    )
    await callback.answer()


@router.callback_query(F.data == "flow:cancel")
async def cancel_flow(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await safe_edit(callback, _menu_text(), main_menu_keyboard())
    await callback.answer("Bekor qilindi")


@router.callback_query(F.data == "flow:back_category")
async def back_category(callback: CallbackQuery, state: FSMContext, admin_ids: set[int]) -> None:
    user_id = callback.from_user.id if callback.from_user else None
    await state.set_state(CustomerFlowStates.choosing_category)
    await safe_edit(callback, "Kategoriya tanlang:", category_keyboard(_is_admin(user_id, admin_ids)))
    await callback.answer()


@router.callback_query(CustomerFlowStates.choosing_category, F.data == "cat:stationery")
async def choose_stationery(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    try:
        products = await db.get_products()
        await state.update_data(category="stationery")
        await state.set_state(CustomerFlowStates.choosing_product)
        await safe_edit(callback, "Mahsulotni tanlang:", products_keyboard(products))
    except Exception:
        logging.exception("Mahsulotlar yuklanmadi")
        await safe_edit(callback, "Xatolik yuz berdi. Qayta urinib ko‘ring.")
    await callback.answer()


@router.callback_query(CustomerFlowStates.choosing_category, F.data == "cat:service")
async def choose_service_cat(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    try:
        services = await db.get_services()
        await state.update_data(category="service")
        await state.set_state(CustomerFlowStates.choosing_service)
        await safe_edit(callback, "Uslugani tanlang:", services_keyboard(services))
    except Exception:
        logging.exception("Uslugalar yuklanmadi")
        await safe_edit(callback, "Xatolik yuz berdi. Qayta urinib ko‘ring.")
    await callback.answer()


@router.callback_query(CustomerFlowStates.choosing_product, F.data.startswith("product:"))
async def choose_product(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    product_id = int(callback.data.split(":", 1)[1])
    products = await db.get_products()
    product = next((p for p in products if p["id"] == product_id), None)
    if not product:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return

    models = await db.get_models_by_product(product_id)
    if not models:
        await callback.answer("Bu mahsulot uchun model yo‘q", show_alert=True)
        return

    await state.update_data(product_id=product_id, item_name=product["name"])
    await state.set_state(CustomerFlowStates.choosing_model)
    await safe_edit(callback, "Modelni tanlang:", models_keyboard(models))
    await callback.answer()


@router.callback_query(F.data == "flow:back_products")
async def back_products(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    products = await db.get_products()
    await state.set_state(CustomerFlowStates.choosing_product)
    await safe_edit(callback, "Mahsulotni tanlang:", products_keyboard(products))
    await callback.answer()


@router.callback_query(CustomerFlowStates.choosing_model, F.data.startswith("model:"))
async def choose_model(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    model_id = int(callback.data.split(":", 1)[1])
    data = await state.get_data()
    product_id = data.get("product_id")
    if not product_id:
        await callback.answer("Mahsulot qayta tanlansin", show_alert=True)
        return

    models = await db.get_models_by_product(int(product_id))
    model = next((m for m in models if m["id"] == model_id), None)
    if not model:
        await callback.answer("Model topilmadi", show_alert=True)
        return

    await state.update_data(model_name=model["model_name"], unit_price=model["unit_price"])
    await state.set_state(CustomerFlowStates.entering_quantity)
    await safe_edit(callback, "Soni nechta? (raqam, kamida 1)")
    await callback.answer()


@router.callback_query(CustomerFlowStates.choosing_service, F.data.startswith("service:"))
async def choose_service(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    service_id = int(callback.data.split(":", 1)[1])
    services = await db.get_services()
    service = next((s for s in services if s["id"] == service_id), None)
    if not service:
        await callback.answer("Usluga topilmadi", show_alert=True)
        return

    name = service["name"]
    await state.update_data(item_name=name, model_name=None)
    if name.lower() in {"nusxa", "kitob", "chop"}:
        await state.set_state(CustomerFlowStates.entering_quantity)
        await safe_edit(callback, "Necha bet? (raqam, kamida 1)")
    else:
        await state.set_state(CustomerFlowStates.entering_total_price)
        await safe_edit(callback, "Jami narxni kiriting (so'm):")
    await callback.answer()


@router.message(CustomerFlowStates.entering_quantity)
async def enter_quantity(message: Message, state: FSMContext) -> None:
    num = _to_int((message.text or "").strip())
    if num is None:
        await message.answer("Faqat raqam kiriting.")
        return
    if num < 1:
        await message.answer("Soni kamida 1 bo‘lishi kerak.")
        return

    data = await state.get_data()
    category = data.get("category")
    await state.update_data(quantity=num)

    if category == "stationery":
        unit = int(data["unit_price"])
        await _append_item(state, num, unit)
        await state.set_state(CustomerFlowStates.choosing_status)
        await message.answer("Mijoz holatini tanlang:", reply_markup=status_keyboard())
        return

    await state.set_state(CustomerFlowStates.entering_unit_price)
    await message.answer("1 bet narxini kiriting (so'm):")


@router.message(CustomerFlowStates.entering_unit_price)
async def enter_unit_price(message: Message, state: FSMContext) -> None:
    num = _to_int((message.text or "").strip())
    if num is None:
        await message.answer("Faqat raqam kiriting.")
        return
    if num < 0:
        await message.answer("Manfiy qiymat mumkin emas.")
        return

    data = await state.get_data()
    qty = int(data.get("quantity", 1))
    await _append_item(state, qty, num)
    await state.set_state(CustomerFlowStates.choosing_status)
    await message.answer("Mijoz holatini tanlang:", reply_markup=status_keyboard())


@router.message(CustomerFlowStates.entering_total_price)
async def enter_total_price(message: Message, state: FSMContext) -> None:
    total = _to_int((message.text or "").strip())
    if total is None:
        await message.answer("Faqat raqam kiriting.")
        return
    if total < 0:
        await message.answer("Manfiy qiymat mumkin emas.")
        return

    await _append_item(state, 1, total)
    await state.set_state(CustomerFlowStates.choosing_status)
    await message.answer("Mijoz holatini tanlang:", reply_markup=status_keyboard())


async def _append_item(state: FSMContext, quantity: int, unit_price: int) -> None:
    data = await state.get_data()
    items = list(data.get("order_items", []))
    items.append(
        {
            "category": data.get("category"),
            "item_name": data.get("item_name"),
            "model_name": data.get("model_name"),
            "quantity": quantity,
            "unit_price": unit_price,
            "line_total": quantity * unit_price,
        }
    )
    await state.update_data(order_items=items)


@router.callback_query(CustomerFlowStates.choosing_status, F.data.startswith("status:"))
async def choose_status(callback: CallbackQuery, state: FSMContext) -> None:
    status = callback.data.split(":", 1)[1]
    data = await state.get_data()
    items = list(data.get("order_items", []))
    cur = items[-1] if items else None

    if cur and int(cur["line_total"]) == 0 and status != "asked_price":
        await callback.answer("0 narx faqat 'Faqat narx so‘radi' uchun.", show_alert=True)
        return

    statuses = list(data.get("statuses", []))
    statuses.append(status)
    await state.update_data(statuses=statuses)
    await state.set_state(CustomerFlowStates.post_item)
    await safe_edit(callback, "✅ Qo‘shildi. Yana qo‘shasizmi?", post_item_keyboard())
    await callback.answer()


@router.callback_query(CustomerFlowStates.post_item, F.data == "flow:add_more")
async def add_more(callback: CallbackQuery, state: FSMContext, admin_ids: set[int]) -> None:
    user_id = callback.from_user.id if callback.from_user else None
    await state.set_state(CustomerFlowStates.choosing_category)
    await safe_edit(callback, "Kategoriya tanlang:", category_keyboard(_is_admin(user_id, admin_ids)))
    await callback.answer()


@router.callback_query(CustomerFlowStates.post_item, F.data == "flow:finish")
async def finish_order(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    try:
        data = await state.get_data()
        items = list(data.get("order_items", []))
        statuses = list(data.get("statuses", []))
        if not items:
            await callback.answer("Item yo‘q", show_alert=True)
            return

        status = statuses[-1] if statuses else "ordered"
        created_by = callback.from_user.id if callback.from_user else 0
        await db.create_order(created_by=created_by, status=status, items=items)

        await state.clear()
        await safe_edit(callback, "Buyurtma saqlandi ✅", main_menu_keyboard())
    except Exception:
        logging.exception("Buyurtma saqlashda xatolik")
        await safe_edit(callback, "Xatolik yuz berdi. Keyinroq qayta urinib ko‘ring.", main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:stats_7")
async def stats_7(callback: CallbackQuery, db: Database) -> None:
    stats = await db.safe_call(db.get_period_summary(days=7), {
        "orders_count": 0,
        "revenue": 0,
        "items_count": 0,
        "asked_price_count": 0,
        "top_items": [],
    })
    await safe_edit(callback, _format_stats("📊 7 kunlik statistika", stats), main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:stats_30")
async def stats_30(callback: CallbackQuery, db: Database) -> None:
    stats = await db.safe_call(db.get_period_summary(days=30), {
        "orders_count": 0,
        "revenue": 0,
        "items_count": 0,
        "asked_price_count": 0,
        "top_items": [],
    })
    await safe_edit(callback, _format_stats("📊 30 kunlik statistika", stats), main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:stats_all")
async def stats_all(callback: CallbackQuery, db: Database) -> None:
    stats = await db.safe_call(db.get_period_summary(days=None), {
        "orders_count": 0,
        "revenue": 0,
        "items_count": 0,
        "asked_price_count": 0,
        "top_items": [],
    })
    await safe_edit(callback, _format_stats("📈 To‘liq statistika", stats), main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:stats_date")
async def stats_by_date_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CustomerFlowStates.entering_date)
    await safe_edit(callback, "Sanani kiriting (YYYY-MM-DD):")
    await callback.answer()


@router.message(CustomerFlowStates.entering_date)
async def stats_by_date_input(message: Message, state: FSMContext, db: Database) -> None:
    text = (message.text or "").strip()
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        await message.answer("Format noto‘g‘ri. Masalan: 2026-03-03")
        return

    stats = await db.safe_call(db.get_date_summary(text), {
        "orders_count": 0,
        "revenue": 0,
        "items_count": 0,
        "asked_price_count": 0,
        "top_items": [],
    })
    await state.clear()
    await message.answer(_format_stats(f"📅 {text} statistikasi", stats), reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "admin:open")
async def admin_open(callback: CallbackQuery, state: FSMContext, admin_ids: set[int]) -> None:
    uid = callback.from_user.id if callback.from_user else None
    if not _is_admin(uid, admin_ids):
        await callback.answer("Bu bo‘lim faqat admin uchun", show_alert=True)
        return
    await state.set_state(AdminCatalogStates.choosing_admin_action)
    await safe_edit(callback, "Admin katalog boshqaruvi:", admin_catalog_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin:back")
async def admin_back(callback: CallbackQuery, state: FSMContext, admin_ids: set[int]) -> None:
    uid = callback.from_user.id if callback.from_user else None
    await state.set_state(CustomerFlowStates.choosing_category)
    await safe_edit(callback, "Kategoriya tanlang:", category_keyboard(_is_admin(uid, admin_ids)))
    await callback.answer()


@router.callback_query(AdminCatalogStates.choosing_admin_action, F.data == "admin:add_product")
async def admin_add_product_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminCatalogStates.entering_product_name)
    await safe_edit(callback, "Yangi mahsulot nomini kiriting:")
    await callback.answer()


@router.message(AdminCatalogStates.entering_product_name)
async def admin_add_product_input(message: Message, state: FSMContext, db: Database) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Nom kamida 2 belgi bo‘lsin")
        return
    await db.safe_call(db.admin_add_product(name), None)
    await state.set_state(AdminCatalogStates.choosing_admin_action)
    await message.answer("Mahsulot qo‘shildi ✅", reply_markup=admin_catalog_keyboard())


@router.callback_query(AdminCatalogStates.choosing_admin_action, F.data == "admin:add_model")
async def admin_add_model_pick_product(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    products = await db.get_products()
    await state.set_state(AdminCatalogStates.choosing_product_for_model)
    await safe_edit(callback, "Model qo‘shish uchun mahsulot tanlang:", products_keyboard(products))
    await callback.answer()


@router.callback_query(AdminCatalogStates.choosing_product_for_model, F.data.startswith("product:"))
async def admin_add_model_name(callback: CallbackQuery, state: FSMContext) -> None:
    pid = int(callback.data.split(":", 1)[1])
    await state.update_data(admin_product_id=pid)
    await state.set_state(AdminCatalogStates.entering_model_name)
    await safe_edit(callback, "Model nomini kiriting:")
    await callback.answer()


@router.message(AdminCatalogStates.entering_model_name)
async def admin_add_model_name_input(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 1:
        await message.answer("Model nomi bo‘sh bo‘lmasin")
        return
    await state.update_data(admin_model_name=name)
    await state.set_state(AdminCatalogStates.entering_model_price)
    await message.answer("Model narxini kiriting (so'm):")


@router.message(AdminCatalogStates.entering_model_price)
async def admin_add_model_price_input(message: Message, state: FSMContext, db: Database) -> None:
    price = _to_int((message.text or "").strip())
    if price is None or price < 0:
        await message.answer("Narx uchun musbat yoki 0 raqam kiriting")
        return
    data = await state.get_data()
    await db.safe_call(
        db.admin_add_model(int(data["admin_product_id"]), data["admin_model_name"], price),
        None,
    )
    await state.set_state(AdminCatalogStates.choosing_admin_action)
    await message.answer("Model qo‘shildi ✅", reply_markup=admin_catalog_keyboard())


@router.callback_query(AdminCatalogStates.choosing_admin_action, F.data == "admin:edit_product")
async def admin_edit_product_pick(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    products = await db.get_products()
    await state.set_state(AdminCatalogStates.choosing_product_to_edit)
    await safe_edit(callback, "Tahrirlash uchun mahsulot tanlang:", products_keyboard(products))
    await callback.answer()


@router.callback_query(AdminCatalogStates.choosing_product_to_edit, F.data.startswith("product:"))
async def admin_edit_product_input_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    pid = int(callback.data.split(":", 1)[1])
    await state.update_data(edit_product_id=pid)
    await state.set_state(AdminCatalogStates.entering_product_new_name)
    await safe_edit(callback, "Yangi nom kiriting:")
    await callback.answer()


@router.message(AdminCatalogStates.entering_product_new_name)
async def admin_edit_product_input(message: Message, state: FSMContext, db: Database) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Nom kamida 2 belgi")
        return
    data = await state.get_data()
    await db.safe_call(db.admin_edit_product(int(data["edit_product_id"]), name, True), None)
    await state.set_state(AdminCatalogStates.choosing_admin_action)
    await message.answer("Mahsulot yangilandi ✅", reply_markup=admin_catalog_keyboard())


@router.callback_query(AdminCatalogStates.choosing_admin_action, F.data == "admin:delete_product")
async def admin_delete_product_pick(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    products = await db.get_products()
    await state.set_state(AdminCatalogStates.choosing_product_to_delete)
    await safe_edit(callback, "O‘chirish uchun mahsulot tanlang:", products_keyboard(products))
    await callback.answer()


@router.callback_query(AdminCatalogStates.choosing_product_to_delete, F.data.startswith("product:"))
async def admin_delete_product_do(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    pid = int(callback.data.split(":", 1)[1])
    await db.safe_call(db.admin_soft_delete_product(pid), None)
    await state.set_state(AdminCatalogStates.choosing_admin_action)
    await safe_edit(callback, "Mahsulot nofaol qilindi ✅", admin_catalog_keyboard())
    await callback.answer()


@router.callback_query(AdminCatalogStates.choosing_admin_action, F.data == "admin:edit_model")
async def admin_edit_model_pick_product(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    products = await db.get_products()
    await state.set_state(AdminCatalogStates.choosing_model_to_edit)
    await safe_edit(callback, "Model tahriri uchun mahsulot tanlang:", products_keyboard(products))
    await callback.answer()


@router.callback_query(AdminCatalogStates.choosing_model_to_edit, F.data.startswith("product:"))
async def admin_edit_model_pick_model(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    pid = int(callback.data.split(":", 1)[1])
    models = await db.get_models_by_product(pid)
    if not models:
        await callback.answer("Model yo‘q", show_alert=True)
        return
    await state.update_data(edit_model_product_id=pid)
    await safe_edit(callback, "Model tanlang:", models_keyboard(models))
    await callback.answer()


@router.callback_query(AdminCatalogStates.choosing_model_to_edit, F.data.startswith("model:"))
async def admin_edit_model_name_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    mid = int(callback.data.split(":", 1)[1])
    await state.update_data(edit_model_id=mid)
    await state.set_state(AdminCatalogStates.entering_model_new_name)
    await safe_edit(callback, "Yangi model nomini kiriting:")
    await callback.answer()


@router.message(AdminCatalogStates.entering_model_new_name)
async def admin_edit_model_name_input(message: Message, state: FSMContext) -> None:
    val = (message.text or "").strip()
    if len(val) < 1:
        await message.answer("Nom bo‘sh bo‘lmasin")
        return
    await state.update_data(edit_model_name=val)
    await state.set_state(AdminCatalogStates.entering_model_new_price)
    await message.answer("Yangi narxni kiriting (so'm):")


@router.message(AdminCatalogStates.entering_model_new_price)
async def admin_edit_model_price_input(message: Message, state: FSMContext, db: Database) -> None:
    price = _to_int((message.text or "").strip())
    if price is None or price < 0:
        await message.answer("Narx noto‘g‘ri")
        return
    await message.answer("Faollik holatini tanlang:", reply_markup=yes_no_active_keyboard("modelstate"))
    await state.update_data(edit_model_price=price)


@router.callback_query(AdminCatalogStates.entering_model_new_price, F.data.startswith("modelstate:"))
async def admin_edit_model_active(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    state_value = callback.data.split(":", 1)[1]
    is_active = state_value == "active"
    data = await state.get_data()
    await db.safe_call(
        db.admin_edit_model(
            int(data["edit_model_id"]),
            data["edit_model_name"],
            int(data["edit_model_price"]),
            is_active,
        ),
        None,
    )
    await state.set_state(AdminCatalogStates.choosing_admin_action)
    await safe_edit(callback, "Model yangilandi ✅", admin_catalog_keyboard())
    await callback.answer()


@router.callback_query(AdminCatalogStates.choosing_admin_action, F.data == "admin:delete_model")
async def admin_delete_model_pick_product(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    products = await db.get_products()
    await state.set_state(AdminCatalogStates.choosing_model_to_delete)
    await safe_edit(callback, "Model o‘chirish uchun mahsulot tanlang:", products_keyboard(products))
    await callback.answer()


@router.callback_query(AdminCatalogStates.choosing_model_to_delete, F.data.startswith("product:"))
async def admin_delete_model_pick_model(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    pid = int(callback.data.split(":", 1)[1])
    models = await db.get_models_by_product(pid)
    await safe_edit(callback, "Model tanlang:", models_keyboard(models))
    await callback.answer()


@router.callback_query(AdminCatalogStates.choosing_model_to_delete, F.data.startswith("model:"))
async def admin_delete_model_do(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    mid = int(callback.data.split(":", 1)[1])
    await db.safe_call(db.admin_soft_delete_model(mid), None)
    await state.set_state(AdminCatalogStates.choosing_admin_action)
    await safe_edit(callback, "Model nofaol qilindi ✅", admin_catalog_keyboard())
    await callback.answer()
