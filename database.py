import aiosqlite

DB_NAME = "bot_database.db"

async def init_db():
    """Создаёт все таблицы, если их ещё нет"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance REAL DEFAULT 0.0,
                rating REAL DEFAULT 0.0,
                deals_count INTEGER DEFAULT 0,
                referral_id INTEGER,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица объявлений о продаже гигабайтов
        await db.execute('''
            CREATE TABLE IF NOT EXISTS ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER,
                operator TEXT,
                gb INTEGER,
                price REAL,
                region TEXT,
                transfer_method TEXT,
                comment TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (seller_id) REFERENCES users(user_id)
            )
        ''')

        # Таблица сделок
        await db.execute('''
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad_id INTEGER,
                buyer_id INTEGER,
                seller_id INTEGER,
                amount REAL,
                status TEXT DEFAULT 'pending_payment',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confirmed_at TIMESTAMP,
                FOREIGN KEY (ad_id) REFERENCES ads(id),
                FOREIGN KEY (buyer_id) REFERENCES users(user_id),
                FOREIGN KEY (seller_id) REFERENCES users(user_id)
            )
        ''')

        # Таблица транзакций (пополнения, выплаты, комиссии)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                amount REAL,
                status TEXT,
                external_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица споров
        await db.execute('''
            CREATE TABLE IF NOT EXISTS disputes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id INTEGER,
                initiator_id INTEGER,
                reason TEXT,
                resolved INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица рефералов (кто кого пригласил)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                user_id INTEGER,
                invited_user_id INTEGER,
                bonus_paid REAL DEFAULT 0.0
            )
        ''')

        await db.commit()

async def ensure_user(user_id: int, username: str = None):
    """Добавляет пользователя в базу, если его ещё нет"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        await db.commit()