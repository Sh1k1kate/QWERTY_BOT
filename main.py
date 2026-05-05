import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from config import BOT_TOKEN, ALLOWED_USERS
from keyboards import main_menu
from techreport import router as tech_router
from inventory import router as inv_router

# ------------------ Инициализация бота ------------------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(tech_router)
dp.include_router(inv_router)

# Простой фильтр по ID (опционально)
@dp.message()
async def auth_filter(message: types.Message, **kwargs):
    if message.from_user.id not in ALLOWED_USERS:
        await message.answer("⛔ Доступ запрещён.")
        return
    # Пропускаем сообщение дальше
    await dp.propagate_event("message", message, **kwargs)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Добро пожаловать! Выберите раздел:", reply_markup=main_menu)

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("Это бот для техотчёта и инвентаризации.")

# ------------------ HTTP‑сервер для Health‑check ------------------
async def health_handler(request):
    return web.Response(text="OK", status=200)

def create_web_app():
    app = web.Application()
    app.router.add_get("/health", health_handler)
    # Можно добавить дополнительные маршруты, если нужно
    return app

# ------------------ Запуск ------------------
async def main():
    # Запускаем long polling в фоновой задаче
    polling_task = asyncio.create_task(dp.start_polling(bot))

    # Запускаем HTTP‑сервер на порту, который укажет Render
    port = int(os.environ.get("PORT", 8000))
    runner = web.AppRunner(create_web_app())
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print(f"Server started on port {port}")
    await polling_task  # Держим приложение живым

if __name__ == "__main__":
    import os
    asyncio.run(main())
