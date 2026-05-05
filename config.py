import os

# Токен бота – получить у @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# GitHub Personal Access Token (нужны права repo)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# Настройки репозитория
OWNER = "Sh1k1kate"
REPO = "Technical-Review-QWERTY_GAME_ZONE"

# Файлы данных в репозитории
DATA_FILES = {
    "tech_report": "tech_report_data.json",
    "products_master": "products_master.json",
    "inventory": "inventory_data.json",
    "history": "history.json"
}

# ID пользователей, которым разрешён доступ (можно расширить)
ALLOWED_USERS = [123456789]  # замени на свой Telegram ID