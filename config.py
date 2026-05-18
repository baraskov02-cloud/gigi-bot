import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if BOT_TOKEN is None:
    BOT_TOKEN = "8429549473:AAECo6LIbuvzLJoJotzdlEughiJkaDykLqQ"

CRYPTO_BOT_TOKEN = os.getenv("CRYPTO_BOT_TOKEN")
if CRYPTO_BOT_TOKEN is None:
    CRYPTO_BOT_TOKEN = "583578:AAET9DoMT6sfgs2x5eMPOc3QSas9gQ5kJIM"

ADMIN_ID = int(os.getenv("ADMIN_ID", "6665494648"))
