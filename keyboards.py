from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        ["📊 Инвентаризация"],
        ["🖥️ Техотчёт"]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

tech_menu = ReplyKeyboardMarkup(
    keyboard=[
        ["🗺️ Карта компьютеров"],
        ["📝 Начать заполнение"],
        ["📥 CSV отчёт"],          # вместо Excel (CSV проще)
        ["🔙 Главное меню"]
    ],
    resize_keyboard=True
)

inv_menu = ReplyKeyboardMarkup(
    keyboard=[
        ["📋 Все товары"],
        ["⚠️ Только расхождения"],
        ["🔍 Поиск по названию"],
        ["💾 Сохранить в GitHub"],
        ["📎 CSV расхождений"],
        ["🔙 Главное меню"]
    ],
    resize_keyboard=True
)

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
    # Добавим кнопку "Обновить"
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