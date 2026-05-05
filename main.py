import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from config import BOT_TOKEN, ALLOWED_USERS
from keyboards import main_menu
from techreport import router as tech_router
from inventory import router as inv_router

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(tech_router)
dp.include_router(inv_router)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Добро пожаловать! Выберите раздел:", reply_markup=main_menu)

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("Бот для техотчёта и инвентаризации.")

async def health_handler(request):
    return web.Response(text="OK", status=200)

def create_web_app():
    app = web.Application()
    app.router.add_get("/health", health_handler)
    return app

async def main():
    # Вот эта строка сбрасывает все старые подключения
    await bot.delete_webhook(drop_pending_updates=True)

    polling_task = asyncio.create_task(dp.start_polling(bot))

    port = int(os.environ.get("PORT", 8000))
    runner = web.AppRunner(create_web_app())
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print(f"Server started on port {port}")
    await polling_task

if __name__ == "__main__":
    asyncio.run(main())
