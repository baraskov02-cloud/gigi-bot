import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from config import BOT_TOKEN
from database import init_db
from handlers import router

async def main():
    await init_db()

    # Включаем классическую Markdown‑разметку (поддерживает **жирный** и `код`)
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
