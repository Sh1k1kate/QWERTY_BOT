from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    ReplyKeyboardMarkup, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton
)
from keyboards import tech_menu, computers_map_keyboard
from github_api import get_file_content, save_file_content
from states import TechFill
import datetime

router = Router()

# Глобальный фильтр карты
map_filter = "all"

async def load_tech_data():
    data = await get_file_content("tech_report_data.json")
    if data and "computers" in data:
        return data
    return {
        "computers": [
            {"num": i, "monitor": "Нет проблем", "mouse": "Нет проблем",
             "keyboard": "Нет проблем", "disks": "Есть ещё место",
             "sound": "Нет проблем", "notes": ""}
            for i in range(1, 62)
        ],
        "globalInspector": "Риад",
        "globalDate": datetime.date.today().isoformat(),
        "lastUpdated": datetime.datetime.now().isoformat()
    }

def get_computer_status(comp: dict) -> str:
    if comp.get("notes") and comp["notes"].strip():
        return "bad"
    if any(comp[field] != default
           for field, default in [("monitor", "Нет проблем"), ("mouse", "Нет проблем"),
                                   ("keyboard", "Нет проблем"), ("sound", "Нет проблем"),
                                   ("disks", "Есть ещё место")]):
        return "warning"
    return "good"

STATUS_ICONS = {"good": "✅", "warning": "⚠️", "bad": "🔴"}

def _build_keyboard(buttons: list[list[str]], **kwargs):
    keyboard = []
    for row in buttons:
        keyboard.append([KeyboardButton(text=text) for text in row])
    return ReplyKeyboardMarkup(keyboard=keyboard, **kwargs)

# ---------- Меню ----------
@router.message(F.text == "🖥️ Техотчёт")
async def show_tech_menu(message: types.Message):
    await message.answer("Выберите действие:", reply_markup=tech_menu)

@router.message(F.text == "🔙 Главное меню")
async def back_to_main(message: types.Message):
    from keyboards import main_menu
    await message.answer("Главное меню", reply_markup=main_menu)

# ---------- Карта ----------
@router.message(F.text == "🗺️ Карта компьютеров")
async def show_map_message(message: types.Message):
    data = await load_tech_data()
    computers = data["computers"]
    status_dict = {c["num"]: STATUS_ICONS[get_computer_status(c)] for c in computers}
    await message.answer("Компьютеры (нажмите для деталей):",
                         reply_markup=computers_map_keyboard(computers, status_dict, map_filter))

@router.callback_query(F.data == "refresh_map")
async def refresh_map(callback: types.CallbackQuery):
    await callback.message.delete()
    data = await load_tech_data()
    computers = data["computers"]
    status_dict = {c["num"]: STATUS_ICONS[get_computer_status(c)] for c in computers}
    await callback.message.answer("Компьютеры:", reply_markup=computers_map_keyboard(computers, status_dict, map_filter))
    await callback.answer()

@router.callback_query(F.data.startswith("map_filter_"))
async def set_map_filter(callback: types.CallbackQuery):
    global map_filter
    map_filter = callback.data.split("_")[2]
    await callback.message.delete()
    data = await load_tech_data()
    computers = data["computers"]
    status_dict = {c["num"]: STATUS_ICONS[get_computer_status(c)] for c in computers}
    await callback.message.answer("Компьютеры:", reply_markup=computers_map_keyboard(computers, status_dict, map_filter))
    await callback.answer()

@router.callback_query(F.data.startswith("comp_"))
async def show_computer_detail(callback: types.CallbackQuery):
    num = int(callback.data.split("_")[1])
    data = await load_tech_data()
    comp = next((c for c in data["computers"] if c["num"] == num), None)
    if not comp:
        await callback.answer("Нет данных", show_alert=True)
        return
    status = get_computer_status(comp)
    text = (
        f"<b>Компьютер {comp['num']}</b> {STATUS_ICONS[status]}\n\n"
        f"🖥️ Монитор: {comp['monitor']}\n"
        f"🖱️ Мышь: {comp['mouse']}\n"
        f"⌨️ Клавиатура: {comp['keyboard']}\n"
        f"💿 Диски: {comp['disks']}\n"
        f"🔊 Звук: {comp['sound']}\n"
        f"📝 Заметки: {comp.get('notes', '—')}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{num}")],
        [InlineKeyboardButton(text="🗺️ На карту", callback_data="refresh_map")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

# ---------- Заполнение ----------
@router.message(F.text == "📝 Начать заполнение")
async def start_fill_sequence(message: types.Message, state: FSMContext):
    data = await load_tech_data()
    await state.update_data(tech_data=data, current_index=0)
    await state.set_state(TechFill.monitor)
    comp = data["computers"][0]
    await message.answer(
        f"Компьютер {comp['num']}\nСостояние монитора:",
        reply_markup=_build_keyboard([
            ["Нет проблем", "Кабель питания", "Дисплей Порт"],
            ["Другое (указать в заметках)"]
        ], resize_keyboard=True)
    )

# Шаг 1: монитор -> мышь
@router.message(TechFill.monitor)
async def process_monitor(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tech_data = data["tech_data"]
    idx = data["current_index"]
    comp = tech_data["computers"][idx]
    comp["monitor"] = message.text.strip()
    await state.update_data(tech_data=tech_data)
    await state.set_state(TechFill.mouse)
    await message.answer(
        f"Компьютер {comp['num']}\nСостояние мыши:",
        reply_markup=_build_keyboard([["Нет проблем", "Не работает", "Другое (указать в заметках)"]], resize_keyboard=True)
    )

# Шаг 2: мышь -> клавиатура
@router.message(TechFill.mouse)
async def process_mouse(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tech_data = data["tech_data"]
    idx = data["current_index"]
    comp = tech_data["computers"][idx]
    comp["mouse"] = message.text.strip()
    await state.update_data(tech_data=tech_data)
    await state.set_state(TechFill.keyboard)
    await message.answer(
        f"Компьютер {comp['num']}\nСостояние клавиатуры:",
        reply_markup=_build_keyboard([
            ["Нет проблем", "Нет резиновых ножек", "Залипает клавиша"],
            ["Другое (указать в заметках)"]
        ], resize_keyboard=True)
    )

# Шаг 3: клавиатура -> диски
@router.message(TechFill.keyboard)
async def process_keyboard(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tech_data = data["tech_data"]
    idx = data["current_index"]
    comp = tech_data["computers"][idx]
    comp["keyboard"] = message.text.strip()
    await state.update_data(tech_data=tech_data)
    await state.set_state(TechFill.disks)
    await message.answer(
        f"Компьютер {comp['num']}\nСостояние дисков:",
        reply_markup=_build_keyboard([["Есть ещё место", "Отсутствует диск", "Другое (указать в заметках)"]], resize_keyboard=True)
    )

# Шаг 4: диски -> звук
@router.message(TechFill.disks)
async def process_disks(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tech_data = data["tech_data"]
    idx = data["current_index"]
    comp = tech_data["computers"][idx]
    comp["disks"] = message.text.strip()
    await state.update_data(tech_data=tech_data)
    await state.set_state(TechFill.sound)
    await message.answer(
        f"Компьютер {comp['num']}\nСостояние звука:",
        reply_markup=_build_keyboard([["Нет проблем", "Нет Аудиокарты", "Другое (указать в заметках)"]], resize_keyboard=True)
    )

# Шаг 5: звук -> заметки
@router.message(TechFill.sound)
async def process_sound(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tech_data = data["tech_data"]
    idx = data["current_index"]
    comp = tech_data["computers"][idx]
    comp["sound"] = message.text.strip()
    await state.update_data(tech_data=tech_data)
    await state.set_state(TechFill.notes)
    await message.answer("Введите заметки (или «-», если нет):", reply_markup=ReplyKeyboardRemove())

# Шаг 6: заметки -> сохранение и переход
@router.message(TechFill.notes)
async def process_notes(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tech_data = data["tech_data"]
    idx = data["current_index"]
    comp = tech_data["computers"][idx]
    comp["notes"] = message.text.strip()
    if comp["notes"] == "-":
        comp["notes"] = ""
    try:
        await save_file_content("tech_report_data.json", tech_data)
        await message.answer("✅ Данные сохранены.")
    except Exception as e:
        await message.answer(f"❌ Ошибка сохранения: {e}")
    idx += 1
    if idx < len(tech_data["computers"]):
        await state.update_data(current_index=idx)
        next_comp = tech_data["computers"][idx]
        await state.set_state(TechFill.monitor)
        await message.answer(
            f"Следующий компьютер: {next_comp['num']}\nСостояние монитора:",
            reply_markup=_build_keyboard([
                ["Нет проблем", "Кабель питания", "Дисплей Порт"],
                ["Другое (указать в заметках)"]
            ], resize_keyboard=True)
        )
    else:
        await state.clear()
        await message.answer("🎉 Все компьютеры заполнены!", reply_markup=tech_menu)

# ---------- CSV экспорт ----------
@router.message(F.text == "📥 CSV отчёт")
async def export_csv(message: types.Message):
    data = await load_tech_data()
    lines = ["num;monitor;mouse;keyboard;disks;sound;notes"]
    for c in data["computers"]:
        lines.append(f"{c['num']};{c['monitor']};{c['mouse']};{c['keyboard']};{c['disks']};{c['sound']};{c.get('notes','')}")
    csv = "\n".join(lines)
    await message.answer_document(types.BufferedInputFile(csv.encode("utf-8"), "tech_report.csv"), caption="CSV отчёт")

# ---------- Редактирование конкретного компьютера ----------
@router.callback_query(F.data.regexp(r"^edit_\d+$"))
async def edit_computer_callback(callback: types.CallbackQuery, state: FSMContext):
    num = int(callback.data.split("_")[1])
    data = await load_tech_data()
    idx = next((i for i, c in enumerate(data["computers"]) if c["num"] == num), None)
    if idx is None:
        await callback.answer("Ошибка", show_alert=True)
        return
    await state.update_data(tech_data=data, current_index=idx)
    await state.set_state(TechFill.monitor)
    await callback.message.edit_text(f"Редактирование компьютера {num}.\nВыберите состояние монитора:")
    await callback.message.answer("Используйте кнопки ниже:", reply_markup=_build_keyboard([
        ["Нет проблем", "Кабель питания", "Дисплей Порт"],
        ["Другое (указать в заметках)"]
    ], resize_keyboard=True))
    await callback.answer()
