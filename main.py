import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp_socks import ProxyConnector  # <-- для прокси
from config import BOT_TOKEN
from database import init_db
from handlers import router

# ===== НАСТРОЙКА ПРОКСИ (SOCKS5) =====
# Замени ip и port на свои данные прокси-сервера.
# Например, многие VPN создают локальный прокси на 127.0.0.1:1080 (или 10808).
PROXY_HOST = "127.0.0.1"   # адрес прокси
PROXY_PORT = 10808          # порт прокси (уточни в настройках VPN)
USE_PROXY = True            # измени на False, если не нужен прокси

async def main():
    await init_db()

    # Создаём коннектор с SOCKS5, если прокси включён
    if USE_PROXY:
        connector = ProxyConnector.from_url(f"socks5://{PROXY_HOST}:{PROXY_PORT}")
    else:
        connector = None

    bot = Bot(token=BOT_TOKEN, session=connector)  # передаём коннектор в сессию
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())