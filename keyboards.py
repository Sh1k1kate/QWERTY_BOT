from aiogram.types import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton
)

# Главное меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Инвентаризация")],
        [KeyboardButton(text="🖥️ Техотчёт")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# Меню техотчёта
tech_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🗺️ Карта компьютеров")],
        [KeyboardButton(text="📝 Начать заполнение")],
        [KeyboardButton(text="📥 CSV отчёт")],
        [KeyboardButton(text="🔙 Главное меню")]
    ],
    resize_keyboard=True
)

# Меню инвентаризации
inv_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Все товары")],
        [KeyboardButton(text="⚠️ Только расхождения")],
        [KeyboardButton(text="🔍 Поиск по названию")],
        [KeyboardButton(text="💾 Сохранить в GitHub")],
        [KeyboardButton(text="📎 CSV расхождений")],
        [KeyboardButton(text="🔙 Главное меню")]
    ],
    resize_keyboard=True
)

# Inline-клавиатура для карты компьютеров
def computers_map_keyboard(computers: list, status: dict):
    """Inline‑кнопки с номерами и эмодзи состояния."""
    kb = []
    row = []
    for comp in computers:
        icon = status.get(comp["num"], "✅")
        row.append(
            InlineKeyboardButton(
                text=f"{comp['num']}{icon}",
                callback_data=f"comp_{comp['num']}"
            )
        )
        if len(row) == 6:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    # Кнопка обновления
    kb.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_map")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# Пагинация для списка товаров
def items_pagination_kb(page: int, total_pages: int):
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"inv_page_{page-1}"))
    if page < total_pages - 1:
        buttons.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"inv_page_{page+1}"))
    kb = [buttons] if buttons else []
    return InlineKeyboardMarkup(inline_keyboard=kb)
