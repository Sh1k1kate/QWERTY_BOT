from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from keyboards import inv_menu, items_pagination_kb
from github_api import get_file_content, save_file_content
from states import InventorySearch, BarcodeSearch, InventoryAdd
import math
import datetime

router = Router()
ITEMS_PER_PAGE = 10

# Состояние для редактирования остатка
class InventoryEdit(StatesGroup):
    waiting_for_quantity = State()

# Глобальный флаг фильтра
stock_filter_active = False

# ---------- Загрузка данных ----------
async def load_master():
    data = await get_file_content("products_master.json")
    return data.get("products", []) if data else []

async def load_inventory():
    data = await get_file_content("inventory_data.json")
    return data.get("items", []) if data else []

async def save_inventory(items: list):
    await save_file_content("inventory_data.json", {"items": items})

async def load_history():
    data = await get_file_content("history.json")
    return data if data else []

async def save_history(history: list):
    await save_file_content("history.json", history, "Update history")

# ---------- Фильтр ----------
def apply_stock_filter(items: list) -> list:
    if stock_filter_active:
        return [i for i in items if i["systemQuantity"] > 0]
    return items

# ---------- Построитель страниц ----------
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
    return text, total_pages, chunk

# ---------- Меню ----------
@router.message(F.text == "📊 Инвентаризация")
async def show_inv_menu(message: types.Message):
    await message.answer("Управление инвентаризацией:", reply_markup=inv_menu)

# ---------- Все товары ----------
@router.message(F.text == "📋 Все товары")
async def show_all_items(message: types.Message, state: FSMContext):
    items = await load_inventory()
    filtered = apply_stock_filter(items)
    await state.update_data(inv_items=filtered, current_page=0)
    text, total_pages, chunk = build_items_page(filtered, 0)
    kb = items_pagination_kb(0, total_pages, chunk, stock_filter_active)
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("inv_page_"))
async def paginate_items(callback: types.CallbackQuery, state: FSMContext):
    page = int(callback.data.split("_")[2])
    data = await state.get_data()
    items = data.get("inv_items", [])
    text, total_pages, chunk = build_items_page(items, page)
    kb = items_pagination_kb(page, total_pages, chunk, stock_filter_active)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "toggle_stock_filter")
async def toggle_stock_filter(callback: types.CallbackQuery, state: FSMContext):
    global stock_filter_active
    stock_filter_active = not stock_filter_active
    items = await load_inventory()
    filtered = apply_stock_filter(items)
    await state.update_data(inv_items=filtered, current_page=0)
    text, total_pages, chunk = build_items_page(filtered, 0)
    kb = items_pagination_kb(0, total_pages, chunk, stock_filter_active)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

# ---------- Только расхождения ----------
@router.message(F.text == "⚠️ Только расхождения")
async def show_mismatches(message: types.Message, state: FSMContext):
    items = await load_inventory()
    mismatches = [i for i in items if i["factQuantity"] != i["systemQuantity"]]
    filtered = apply_stock_filter(mismatches)
    await state.update_data(inv_items=filtered, current_page=0)
    if not filtered:
        await message.answer("Расхождений нет! 🎉", reply_markup=inv_menu)
    else:
        text, total_pages, chunk = build_items_page(filtered, 0)
        kb = items_pagination_kb(0, total_pages, chunk, stock_filter_active)
        await message.answer(text, parse_mode="HTML", reply_markup=kb)

# ---------- Поиск по названию ----------
@router.message(F.text == "🔍 Поиск по названию")
async def search_start(message: types.Message, state: FSMContext):
    await state.set_state(InventorySearch.waiting_for_query)
    await message.answer("Введите часть названия товара:", reply_markup=ReplyKeyboardRemove())

@router.message(InventorySearch.waiting_for_query)
async def search_execute(message: types.Message, state: FSMContext):
    query = message.text.strip().lower()
    items = await load_inventory()
    matches = [i for i in items if query in i["name"].lower()]
    filtered = apply_stock_filter(matches)
    await state.clear()
    if not filtered:
        await message.answer("Ничего не найдено.", reply_markup=inv_menu)
    else:
        await state.update_data(inv_items=filtered, current_page=0)
        text, total_pages, chunk = build_items_page(filtered, 0)
        kb = items_pagination_kb(0, total_pages, chunk, stock_filter_active)
        await message.answer(text, parse_mode="HTML", reply_markup=kb)

# ---------- Поиск по штрихкоду ----------
@router.message(F.text == "🔍 По штрихкоду")
async def barcode_search_start(message: types.Message, state: FSMContext):
    await state.set_state(BarcodeSearch.waiting_for_barcode)
    await message.answer("Введите штрихкод:", reply_markup=ReplyKeyboardRemove())

@router.message(BarcodeSearch.waiting_for_barcode)
async def barcode_search_execute(message: types.Message, state: FSMContext):
    barcode = message.text.strip()
    master = await load_master()
    inventory = await load_inventory()
    product = next((p for p in master if p.get("barcode") == barcode), None)
    if product:
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
            await message.answer("Товар есть в мастер-файле, но отсутствует в инвентаризации.")
    else:
        await message.answer(f"Товар со штрихкодом {barcode} не найден.\nИспользуйте «➕ Добавить товар».")
    await state.clear()
    await message.answer("Меню инвентаризации:", reply_markup=inv_menu)

# ---------- Редактирование остатка ----------
@router.callback_query(F.data.startswith("edit_qty_"))
async def edit_quantity_prompt(callback: types.CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split("_")[2])
    items = await load_inventory()
    item = next((i for i in items if i["id"] == item_id), None)
    if not item:
        await callback.answer("Товар не найден", show_alert=True)
        return
    await state.update_data(edit_item_id=item_id)
    await state.set_state(InventoryEdit.waiting_for_quantity)
    await callback.message.answer(
        f"Введите фактический остаток для товара:\n<b>{item['name']}</b>\n"
        f"Текущее значение: {item['factQuantity']}\nДля отмены /cancel",
        parse_mode="HTML", reply_markup=ReplyKeyboardRemove()
    )
    await callback.answer()

@router.message(InventoryEdit.waiting_for_quantity)
async def process_new_quantity(message: types.Message, state: FSMContext):
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
        # Запись в историю
        history = await load_history()
        history.append({
            "timestamp": int(datetime.datetime.now().timestamp() * 1000),
            "items": [{
                "id": item["id"],
                "factQuantity": new_qty,
                "systemQuantity": item["systemQuantity"],
                "name": item["name"],
                "category": item["category"]
            }]
        })
        await save_history(history)
        await message.answer(f"✅ Фактический остаток обновлён: {item['name']} = {new_qty}")
    else:
        await message.answer("Ошибка: товар не найден.")
    await state.clear()
    await message.answer("Меню инвентаризации:", reply_markup=inv_menu)

# ---------- Добавление товара ----------
@router.message(F.text == "➕ Добавить товар")
async def add_item_start(message: types.Message, state: FSMContext):
    await state.set_state(InventoryAdd.category)
    cats = ["Готовая Еда", "Напитки", "Снэки", "Шоколад", "Энергетические напитки"]
    kb = [[KeyboardButton(text=c)] for c in cats]
    await message.answer("Выберите категорию:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@router.message(InventoryAdd.category)
async def add_item_category(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text.strip())
    await state.set_state(InventoryAdd.name)
    await message.answer("Введите наименование товара:", reply_markup=ReplyKeyboardRemove())

@router.message(InventoryAdd.name)
async def add_item_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(InventoryAdd.barcode)
    await message.answer("Введите штрихкод (или поставьте прочерк '-'):")

@router.message(InventoryAdd.barcode)
async def add_item_barcode(message: types.Message, state: FSMContext):
    barcode = message.text.strip()
    if barcode == "-":
        barcode = ""
    await state.update_data(barcode=barcode)
    await state.set_state(InventoryAdd.system_qty)
    await message.answer("Введите учётный остаток (целое число):")

@router.message(InventoryAdd.system_qty)
async def add_item_system_qty(message: types.Message, state: FSMContext):
    try:
        qty = int(message.text)
    except ValueError:
        await message.answer("Введите целое число.")
        return
    await state.update_data(system_qty=qty)
    await state.set_state(InventoryAdd.fact_qty)
    await message.answer("Введите фактический остаток (или 0):")

@router.message(InventoryAdd.fact_qty)
async def add_item_fact_qty(message: types.Message, state: FSMContext):
    try:
        fact = int(message.text)
    except ValueError:
        await message.answer("Введите целое число.")
        return
    data = await state.get_data()
    # Добавляем в мастер
    master = await load_master()
    new_id = max([p["id"] for p in master], default=0) + 1
    new_product = {
        "id": new_id,
        "category": data["category"],
        "name": data["name"],
        "barcode": data["barcode"],
        "systemQuantity": data["system_qty"],
        "lastFactQuantity": fact
    }
    master.append(new_product)
    await save_file_content("products_master.json", {"products": master}, "Add product from bot")
    # Добавляем в инвентаризацию
    inventory = await load_inventory()
    inventory.append({
        "id": new_id,
        "category": data["category"],
        "name": data["name"],
        "systemQuantity": data["system_qty"],
        "factQuantity": fact
    })
    await save_inventory(inventory)
    await state.clear()
    await message.answer(f"✅ Товар добавлен: {data['name']}", reply_markup=inv_menu)

# ---------- Загрузка CSV (1С) ----------
@router.message(F.text == "📁 Загрузить CSV (1С)")
async def csv_prompt(message: types.Message, state: FSMContext):
    await message.answer("Отправьте CSV-файл (разделитель ';'), полученный из 1С.", reply_markup=ReplyKeyboardRemove())

@router.message(F.document)
async def handle_csv_file(message: types.Message, state: FSMContext):
    if not message.document.file_name.endswith('.csv'):
        await message.answer("Пожалуйста, отправьте файл с расширением .csv")
        return
    file = await bot.get_file(message.document.file_id)
    content = await bot.download_file(file.file_path)
    csv_text = content.decode('utf-8-sig')

    lines = csv_text.splitlines()
    if len(lines) < 2:
        await message.answer("Файл пуст или не содержит данных.")
        return
    headers = lines[0].split(';')
    name_idx = next((i for i, h in enumerate(headers) if 'Наименование' in h), None)
    category_idx = next((i for i, h in enumerate(headers) if 'Категория' in h), None)
    qty_idx = next((i for i, h in enumerate(headers) if 'Количество' in h), None)
    status_idx = next((i for i, h in enumerate(headers) if 'Статус' in h), None)
    barcode_idx = next((i for i, h in enumerate(headers) if h in ('Штрихкод', 'Barcode')), None)

    if name_idx is None or category_idx is None or qty_idx is None:
        await message.answer("CSV должен содержать столбцы 'Наименование', 'Категория', 'Количество'.")
        return

    master = await load_master()
    added, updated = 0, 0
    for line in lines[1:]:
        if not line.strip():
            continue
        cols = line.split(';')
        if len(cols) <= max(name_idx, category_idx, qty_idx):
            continue
        status = cols[status_idx].strip() if status_idx is not None and status_idx < len(cols) else ''
        if status and status != 'Активен':
            continue
        name = cols[name_idx].strip()
        category = cols[category_idx].strip()
        try:
            qty = int(float(cols[qty_idx].strip()))
        except ValueError:
            qty = 0
        barcode = cols[barcode_idx].strip() if barcode_idx is not None and barcode_idx < len(cols) else ''

        existing = next((p for p in master if p['category'].lower() == category.lower() and p['name'].lower() == name.lower()), None)
        if existing:
            existing['systemQuantity'] = qty
            if barcode and not existing.get('barcode'):
                existing['barcode'] = barcode
            updated += 1
        else:
            new_id = max([p['id'] for p in master], default=0) + 1
            master.append({
                "id": new_id,
                "category": category,
                "name": name,
                "barcode": barcode,
                "systemQuantity": qty,
                "lastFactQuantity": qty
            })
            added += 1

    await save_file_content("products_master.json", {"products": master}, "Update master from CSV")
    await message.answer(f"✅ Мастер обновлён: добавлено {added}, обновлено {updated} товаров.")

    # Синхронизация инвентаризации
    inventory = await load_inventory()
    for p in master:
        inv_item = next((i for i in inventory if i['id'] == p['id']), None)
        if inv_item:
            inv_item['systemQuantity'] = p['systemQuantity']
            inv_item['category'] = p['category']
            inv_item['name'] = p['name']
        else:
            inventory.append({
                "id": p['id'],
                "category": p['category'],
                "name": p['name'],
                "systemQuantity": p['systemQuantity'],
                "factQuantity": p.get('lastFactQuantity', p['systemQuantity'])
            })
    await save_inventory(inventory)
    await message.answer("Инвентаризация синхронизирована.", reply_markup=inv_menu)

# ---------- История ----------
@router.message(F.text == "📜 История")
async def history_menu(message: types.Message, state: FSMContext):
    history = await load_history()
    if not history:
        await message.answer("История пуста.")
        return
    text = "📜 <b>История инвентаризаций</b>\n\n"
    for i, rec in enumerate(history):
        dt = datetime.datetime.fromtimestamp(rec['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M')
        count = len(rec['items'])
        text += f"{i+1}. {dt} — {count} товаров\n"
    text += "\nВведите номер для просмотра, или /cancel"
    await state.set_state("history_choose")
    await message.answer(text, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())

@router.message(F.text.regexp(r'^\d+$'))
async def history_choose(message: types.Message, state: FSMContext):
    if await state.get_state() != "history_choose":
        return
    idx = int(message.text) - 1
    history = await load_history()
    if idx < 0 or idx >= len(history):
        await message.answer("Неверный номер.")
        return
    rec = history[idx]
    items = rec['items']
    text = f"📜 Инвентаризация от {datetime.datetime.fromtimestamp(rec['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M')}\n\n"
    for item in items:
        diff = item['factQuantity'] - item['systemQuantity']
        status = "⚠️" if diff != 0 else "✅"
        text += f"{status} {item['name']} — учёт: {item['systemQuantity']}, факт: {item['factQuantity']} ({diff:+.0f})\n"
    text += "\nВосстановить это состояние? Напишите 'да' или 'нет'"
    await state.update_data(history_idx=idx)
    await state.set_state("history_restore_confirm")
    await message.answer(text, parse_mode="HTML")

@router.message(F.text.lower().in_(['да', 'нет']))
async def history_restore_confirm(message: types.Message, state: FSMContext):
    if await state.get_state() != "history_restore_confirm":
        return
    if message.text.lower() == 'да':
        data = await state.get_data()
        idx = data['history_idx']
        history = await load_history()
        rec = history[idx]
        inventory = await load_inventory()
        for hist_item in rec['items']:
            inv_item = next((i for i in inventory if i['id'] == hist_item['id']), None)
            if inv_item:
                inv_item['factQuantity'] = hist_item['factQuantity']
        await save_inventory(inventory)
        await message.answer("✅ Состояние инвентаризации восстановлено.")
    else:
        await message.answer("Восстановление отменено.")
    await state.clear()
    await message.answer("Меню инвентаризации:", reply_markup=inv_menu)

# ---------- Сохранение / Экспорт ----------
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
