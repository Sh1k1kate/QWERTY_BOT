from aiogram.fsm.state import State, StatesGroup

class TechFill(StatesGroup):
    choosing_computer = State()
    monitor = State()
    mouse = State()
    keyboard = State()
    disks = State()
    sound = State()
    notes = State()

class InventoryEdit(StatesGroup):
    waiting_for_quantity = State()

class InventorySearch(StatesGroup):
    waiting_for_query = State()

class BarcodeScan(StatesGroup):
    waiting_for_barcode = State()
