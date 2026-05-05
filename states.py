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

class BarcodeSearch(StatesGroup):
    waiting_for_barcode = State()

class InventoryAdd(StatesGroup):
    category = State()
    name = State()
    barcode = State()
    system_qty = State()
    fact_qty = State()
