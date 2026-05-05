import os

# Òîêåí áîòà – ïîëó÷èòü ó @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# GitHub Personal Access Token (íóæíû ïðàâà repo)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# Íàñòðîéêè ðåïîçèòîðèÿ
OWNER = "Sh1k1kate"
REPO = "Technical-Review-QWERTY_GAME_ZONE"

# Ôàéëû äàííûõ â ðåïîçèòîðèè
DATA_FILES = {
    "tech_report": "tech_report_data.json",
    "products_master": "products_master.json",
    "inventory": "inventory_data.json",
    "history": "history.json"
}

# ID ïîëüçîâàòåëåé, êîòîðûì ðàçðåø¸í äîñòóï (ìîæíî ðàñøèðèòü)
ALLOWED_USERS = []  # çàìåíè íà ñâîé Telegram ID
