import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

OWNER = "Sh1k1kate"
REPO = "Technical-Review-QWERTY_GAME_ZONE"

DATA_FILES = {
    "tech_report": "tech_report_data.json",
    "products_master": "products_master.json",
    "inventory": "inventory_data.json",
    "history": "history.json"
}

ALLOWED_USERS = [398362790]  # ← замени на свой Telegram ID !!!
