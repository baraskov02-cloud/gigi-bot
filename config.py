import os
from dotenv import load_dotenv

# Загружаем переменные из файла .env
load_dotenv()

# Достаём токены и ID администратора
BOT_TOKEN = os.getenv("BOT_TOKEN")
CRYPTO_BOT_TOKEN = os.getenv("CRYPTO_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))