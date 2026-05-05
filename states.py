from aiogram.fsm.state import State, StatesGroup

class TechFill(StatesGroup):
    monitor = State()
    mouse = State()
    keyboard = State()
    disks = State()
    sound = State()
    notes = State()

class InventorySearch(StatesGroup):
    waiting_for_query = State()
