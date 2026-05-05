from aiogram.fsm.state import State, StatesGroup

# Заполнение техотчёта по шагам
class TechFill(StatesGroup):
    choosing_computer = State()   # ожидание номера компьютера (опционально)
    monitor = State()
    mouse = State()
    keyboard = State()
    disks = State()
    sound = State()
    notes = State()

# Ввод фактического остатка
class InventoryEdit(StatesGroup):
    waiting_for_quantity = State()

# Поиск товара
class InventorySearch(StatesGroup):
    waiting_for_query = State()