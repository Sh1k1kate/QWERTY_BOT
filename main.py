import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from config import BOT_TOKEN, ALLOWED_USERS
from keyboards import main_menu
from techreport import router as tech_router
from inventory import router as inv_router

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Универсальный middleware проверки доступа
class AccessMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data: dict):
        # Пытаемся найти пользователя в разных типах апдейтов
        user = None
        if hasattr(event, 'from_user'):
            user = event.from_user
        elif hasattr(event, 'message') and event.message:
            user = event.message.from_user
        elif hasattr(event, 'callback_query') and event.callback_query:
            user = event.callback_query.from_user
        elif hasattr(event, 'inline_query') and event.inline_query:
            user = event.inline_query.from_user
        # Добавьте другие типы при необходимости

        if user and user.id not in ALLOWED_USERS:
            # Отвечаем, если есть способ (например, сообщение)
            if hasattr(event, 'message') and event.message:
                await event.message.answer("⛔ Доступ запрещён.")
            return  # не передаём дальше
        return await handler(event, data)

dp.update.outer_middleware(AccessMiddleware())

dp.include_router(tech_router)
dp.include_router(inv_router)

tech_router.bot = bot
inv_router.bot = bot

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Добро пожаловать! Выберите раздел:", reply_markup=main_menu)

@dp.message(Command("cancel"))
@dp.message(F.text.casefold() == "/cancel")
async def cmd_cancel(message: types.Message, state: FSMContext):
    if await state.get_state():
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu)
    else:
        await message.answer("Нет активных действий.", reply_markup=main_menu)

# ---------- HTTP‑сервер (health + Mini App) ----------
async def health_handler(request):
    return web.Response(text="OK", status=200)

async def scanner_handler(request):
    file_path = os.path.join(os.path.dirname(__file__), "scanner.html")
    if not os.path.exists(file_path):
        return web.Response(text="File not found", status=404)
    return web.FileResponse(file_path)

def create_web_app():
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/scanner", scanner_handler)
    return app

async def main():
    # Убиваем старые сессии
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
