from aiogram.types import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton,
    WebAppInfo           # ← новый импорт
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
        [KeyboardButton(text="📥 Загрузить CSV отчёт")],
        [KeyboardButton(text="🔙 Главное меню")]
    ],
    resize_keyboard=True
)

# Меню инвентаризации (обновлённая кнопка)
inv_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Все товары")],
        [KeyboardButton(text="⚠️ Только расхождения")],
        [KeyboardButton(text="🔍 Поиск по названию")],
        # Новая кнопка с WebApp
        [KeyboardButton(
            text="📷 Сканировать штрихкод",
            web_app=WebAppInfo(url="https://qwerty-bot-wa72.onrender.com/scanner")  # <-- замени на свой URL
        )],
        [KeyboardButton(text="➕ Добавить товар")],
        [KeyboardButton(text="📁 Загрузить CSV (1С)")],
        [KeyboardButton(text="📄 Экспорт TXT")],
        [KeyboardButton(text="📜 История")],
        [KeyboardButton(text="💾 Сохранить в GitHub")],
        [KeyboardButton(text="📎 CSV расхождений")],
        [KeyboardButton(text="🔙 Главное меню")]
    ],
    resize_keyboard=True
)

def computers_map_keyboard(computers: list, status: dict, filter_status: str = "all"):
    kb = []
    # Строка фильтров
    filter_buttons = []
    for s, label in [("all", "Все"), ("good", "✅"), ("warning", "⚠️"), ("bad", "🔴")]:
        prefix = "✓ " if s == filter_status else ""
        filter_buttons.append(InlineKeyboardButton(text=f"{prefix}{label}", callback_data=f"map_filter_{s}"))
    kb.append(filter_buttons)

    # Компьютеры
    row = []
    for comp in computers:
        icon = status.get(comp["num"], "✅")
        comp_status = "good"  # default
        if icon == "⚠️": comp_status = "warning"
        elif icon == "🔴": comp_status = "bad"
        if filter_status == "all" or comp_status == filter_status:
            row.append(InlineKeyboardButton(text=f"{comp['num']}{icon}", callback_data=f"comp_{comp['num']}"))
            if len(row) == 6:
                kb.append(row)
                row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_map")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def items_pagination_kb(page: int, total_pages: int, items_on_page: list = None, stock_filter: bool = False):
    buttons = []
    if items_on_page:
        for item in items_on_page:
            buttons.append([
                InlineKeyboardButton(text=f"✏️ {item['name'][:30]}", callback_data=f"edit_qty_{item['id']}")
            ])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"inv_page_{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"inv_page_{page+1}"))
    if nav:
        buttons.append(nav)
    # Переключатель фильтра
    stock_text = "📦 Только с остатком: ВЫКЛ" if stock_filter else "📦 Только с остатком: ВКЛ"
    buttons.append([InlineKeyboardButton(text=stock_text, callback_data="toggle_stock_filter")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
