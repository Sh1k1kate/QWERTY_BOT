import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from config import BOT_TOKEN, ALLOWED_USERS
from aiogram.types import ReplyKeyboardRemove
from keyboards import main_menu
from techreport import router as tech_router
from inventory import router as inv_router

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Фильтр авторизации (только разрешённые пользователи)
@dp.message()
async def auth_filter(message: types.Message, **kwargs):
    if message.from_user.id not in ALLOWED_USERS:
        await message.answer("⛔ Доступ запрещён. Обратитесь к администратору.")
        return
    # Передаём управление дальше, если пользователь разрешён
    # (этот middleware пропустит сообщение в другие роутеры)
    await dp.propagate_event("message", message, **kwargs)

# Включаем роутеры
dp.include_router(tech_router)
dp.include_router(inv_router)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Добро пожаловать! Выберите раздел:",
        reply_markup=main_menu
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("Это бот для техотчёта и инвентаризации. Используйте меню.")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())