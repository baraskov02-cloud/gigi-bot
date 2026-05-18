import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database import init_db
from handlers import router

async def main():
    # 1. Создаём таблицы в базе данных
    await init_db()

    # 2. Инициализируем бота
    bot = Bot(token=BOT_TOKEN)

    # 3. Хранилище состояний
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # 4. Подключаем обработчики
    dp.include_router(router)

    # 5. Удаляем вебхуки и запускаем поллинг
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
