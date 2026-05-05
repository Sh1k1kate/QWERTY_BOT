from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from keyboards import inv_menu, items_pagination_kb
from github_api import get_file_content, save_file_content
import math

router = Router()

ITEMS_PER_PAGE = 10

# --------------------- Состояния FSM ---------------------
class InventoryEdit(StatesGroup):
    waiting_for_quantity = State()

class InventorySearch(StatesGroup):
    waiting_for_query = State()

class BarcodeSearch(StatesGroup):
    waiting_for_barcode = State()

# --------------------- Вспомогательные функции ---------------------
async def load_master():
    data = await get_file_content("products_master.json")
    return data.get("products", []) if data else []

async def load_inventory():
    data = await get_file_content("inventory_data.json")
    return data.get("items", []) if data else []

async def save_inventory(items: list):
    await save_file_content("inventory_data.json", {"items": items})

def build_items_page(items: list, page: int = 0, per_page: int = ITEMS_PER_PAGE):
    total = len(items)
    total_pages = math.ceil(total / per_page) if total else 1
    start = page * per_page
    end = start + per_page
    chunk = items[start:end]

    text = ""
    for item in chunk:
        diff = item["factQuantity"] - item["systemQuantity"]
        status = "⚠️" if diff != 0 else "✅"
        text += (
            f"{status} <b>{item['name']}</b>\n"
            f"   Категория: {item['category']}\n"
            f"   Учёт: {item['systemQuantity']} | Факт: {item['factQuantity']} "
            f"({diff:+.0f})\n\n"
        )

    text += f"Страница {page+1} из {total_pages} (показано {start+1}–{min(end, total)} из {total})"
    return text, total_pages, chunk  # возвращаем chunk для клавиатуры

# --------------------- Меню и общие команды ---------------------
@router.message(F.text == "📊 Инвентаризация")
async def show_inv_menu(message: types.Message):
    await message.answer("Управление инвентаризацией:", reply_markup=inv_menu)

# --------------------- Просмотр товаров ---------------------
@router.message(F.text == "📋 Все товары")
async def show_all_items(message: types.Message, state: FSMContext):
    items = await load_inventory()
    await state.update_data(inv_items=items, current_page=0)
    text, total_pages, chunk = build_items_page(items, 0)
    kb = items_pagination_kb(0, total_pages, chunk)
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("inv_page_"))
async def paginate_items(callback: types.CallbackQuery, state: FSMContext):
    page = int(callback.data.split("_")[2])
    data = await state.get_data()
    items = data.get("inv_items", [])
    text, total_pages, chunk = build_items_page(items, page)
    kb = items_pagination_kb(page, total_pages, chunk)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

# --------------------- Только расхождения ---------------------
@router.message(F.text == "⚠️ Только расхождения")
async def show_mismatches(message: types.Message, state: FSMContext):
    items = await load_inventory()
    mismatches = [i for i in items if i["factQuantity"] != i["systemQuantity"]]
    await state.update_data(inv_items=mismatches, current_page=0)
    if not mismatches:
        await message.answer("Расхождений нет! 🎉", reply_markup=inv_menu)
    else:
        text, total_pages, chunk = build_items_page(mismatches, 0)
        kb = items_pagination_kb(0, total_pages, chunk)
        await message.answer(text, parse_mode="HTML", reply_markup=kb)

# --------------------- Поиск по названию ---------------------
@router.message(F.text == "🔍 Поиск по названию")
async def search_start(message: types.Message, state: FSMContext):
    await state.set_state(InventorySearch.waiting_for_query)
    await message.answer("Введите часть названия товара:", reply_markup=ReplyKeyboardRemove())

@router.message(InventorySearch.waiting_for_query)
async def search_execute(message: types.Message, state: FSMContext):
    query = message.text.strip().lower()
    items = await load_inventory()
    matches = [i for i in items if query in i["name"].lower()]
    await state.clear()
    if not matches:
        await message.answer("Ничего не найдено.", reply_markup=inv_menu)
    else:
        await state.update_data(inv_items=matches, current_page=0)
        text, total_pages, chunk = build_items_page(matches, 0)
        kb = items_pagination_kb(0, total_pages, chunk)
        await message.answer(text, parse_mode="HTML", reply_markup=kb)

# --------------------- Редактирование фактического остатка ---------------------
@router.callback_query(F.data.startswith("edit_qty_"))
async def edit_quantity_prompt(callback: types.CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split("_")[2])
    items = await load_inventory()
    item = next((i for i in items if i["id"] == item_id), None)
    if not item:
        await callback.answer("Товар не найден", show_alert=True)
        return

    await state.update_data(edit_item_id=item_id, inv_items=items)
    await state.set_state(InventoryEdit.waiting_for_quantity)
    await callback.message.answer(
        f"Введите фактический остаток для товара:\n<b>{item['name']}</b>\n"
        f"Текущее значение: {item['factQuantity']}\n"
        "Для отмены введите /cancel",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    await callback.answer()

@router.message(InventoryEdit.waiting_for_quantity)
async def process_new_quantity(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено.", reply_markup=inv_menu)
        return

    try:
        new_qty = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите целое число.")
        return

    data = await state.get_data()
    item_id = data["edit_item_id"]
    items = await load_inventory()
    item = next((i for i in items if i["id"] == item_id), None)
    if item:
        item["factQuantity"] = new_qty
        await save_inventory(items)
        await message.answer(f"✅ Фактический остаток обновлён: {item['name']} = {new_qty}")
    else:
        await message.answer("Ошибка: товар не найден.")

    await state.clear()
    await message.answer("Возвращаемся в меню инвентаризации.", reply_markup=inv_menu)

# --------------------- Поиск по штрихкоду ---------------------
@router.message(F.text == "🔍 По штрихкоду")
async def barcode_search_start(message: types.Message, state: FSMContext):
    await state.set_state(BarcodeSearch.waiting_for_barcode)
    await message.answer("Введите штрихкод:", reply_markup=ReplyKeyboardRemove())

@router.message(BarcodeSearch.waiting_for_barcode)
async def barcode_search_execute(message: types.Message, state: FSMContext):
    barcode = message.text.strip()
    master = await load_master()
    inventory = await load_inventory()

    # Ищем товар в мастер-файле по штрихкоду
    product = next((p for p in master if p.get("barcode") == barcode), None)

    if product:
        # Ищем этот товар в инвентаризации по id
        inv_item = next((i for i in inventory if i["id"] == product["id"]), None)
        if inv_item:
            text = (
                f"🔍 Товар найден:\n"
                f"<b>{inv_item['name']}</b>\n"
                f"Категория: {inv_item['category']}\n"
                f"Учётный остаток: {inv_item['systemQuantity']}\n"
                f"Фактический: {inv_item['factQuantity']}\n"
                f"Штрихкод: {barcode}\n\n"
                f"Используйте ✏️ для изменения остатка."
            )
            await message.answer(text, parse_mode="HTML")
        else:
            await message.answer("Товар есть в мастер-файле, но отсутствует в инвентаризации. Загрузите данные.")
    else:
        await message.answer(
            f"Товар со штрихкодом {barcode} не найден в мастер-файле.\n"
            "Вы можете создать новый товар с этим штрихкодом через сайт или использовать /addproduct."
        )

    await state.clear()
    await message.answer("Меню инвентаризации:", reply_markup=inv_menu)

# --------------------- Сохранение и экспорт ---------------------
@router.message(F.text == "💾 Сохранить в GitHub")
async def save_to_github(message: types.Message):
    items = await load_inventory()
    try:
        await save_file_content("inventory_data.json", {"items": items}, "Save from bot")
        await message.answer("✅ Инвентаризация сохранена в GitHub")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.message(F.text == "📎 CSV расхождений")
async def export_mismatches_csv(message: types.Message):
    items = await load_inventory()
    mismatches = [i for i in items if i["factQuantity"] != i["systemQuantity"]]
    if not mismatches:
        await message.answer("Расхождений нет.")
        return
    csv = "Наименование;Категория;Учёт;Факт;Разница\n"
    for i in mismatches:
        csv += f"{i['name']};{i['category']};{i['systemQuantity']};{i['factQuantity']};{i['factQuantity']-i['systemQuantity']}\n"
    await message.answer_document(
        types.BufferedInputFile(csv.encode("utf-8-sig"), "mismatches.csv"),
        caption=f"Расхождений: {len(mismatches)}"
    )
