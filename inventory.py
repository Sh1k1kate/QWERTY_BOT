from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from keyboards import inv_menu, items_pagination_kb
from github_api import get_file_content, save_file_content
from states import InventorySearch
import math

router = Router()

ITEMS_PER_PAGE = 10

async def load_inventory():
    data = await get_file_content("inventory_data.json")
    return data if data else {"items": []}

async def save_inventory(items):
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
    return text, total_pages

@router.message(F.text == "📊 Инвентаризация")
async def show_inv_menu(message: types.Message):
    await message.answer("Управление инвентаризацией:", reply_markup=inv_menu)

@router.message(F.text == "📋 Все товары")
async def show_all_items(message: types.Message, state: FSMContext):
    inv = await load_inventory()
    items = inv.get("items", [])
    await state.update_data(inv_items=items, current_page=0)
    text, total_pages = build_items_page(items, 0)
    kb = items_pagination_kb(0, total_pages)
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("inv_page_"))
async def paginate_items(callback: types.CallbackQuery, state: FSMContext):
    page = int(callback.data.split("_")[2])
    data = await state.get_data()
    items = data.get("inv_items", [])
    text, total_pages = build_items_page(items, page)
    kb = items_pagination_kb(page, total_pages)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@router.message(F.text == "⚠️ Только расхождения")
async def show_mismatches(message: types.Message, state: FSMContext):
    inv = await load_inventory()
    items = inv.get("items", [])
    mismatches = [i for i in items if i["factQuantity"] != i["systemQuantity"]]
    await state.update_data(inv_items=mismatches, current_page=0)
    if not mismatches:
        await message.answer("Расхождений нет! 🎉", reply_markup=inv_menu)
    else:
        text, total_pages = build_items_page(mismatches, 0)
        kb = items_pagination_kb(0, total_pages) if total_pages > 1 else None
        await message.answer(text, parse_mode="HTML", reply_markup=kb or inv_menu)

@router.message(F.text == "🔍 Поиск по названию")
async def search_start(message: types.Message, state: FSMContext):
    await state.set_state(InventorySearch.waiting_for_query)
    await message.answer("Введите часть названия товара:", reply_markup=ReplyKeyboardRemove())

@router.message(InventorySearch.waiting_for_query)
async def search_execute(message: types.Message, state: FSMContext):
    query = message.text.strip().lower()
    inv = await load_inventory()
    items = inv.get("items", [])
    matches = [i for i in items if query in i["name"].lower()]
    await state.clear()
    if not matches:
        await message.answer("Ничего не найдено.", reply_markup=inv_menu)
    else:
        await state.update_data(inv_items=matches, current_page=0)
        text, total_pages = build_items_page(matches, 0)
        kb = items_pagination_kb(0, total_pages) if total_pages > 1 else None
        await message.answer(text, parse_mode="HTML", reply_markup=kb or inv_menu)

@router.message(F.text == "💾 Сохранить в GitHub")
async def save_to_github(message: types.Message):
    inv = await load_inventory()
    try:
        await save_file_content("inventory_data.json", inv, "Save from bot")
        await message.answer("✅ Инвентаризация сохранена в GitHub")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.message(F.text == "📎 CSV расхождений")
async def export_mismatches_csv(message: types.Message):
    inv = await load_inventory()
    mismatches = [i for i in inv.get("items", []) if i["factQuantity"] != i["systemQuantity"]]
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
