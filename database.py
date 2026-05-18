import aiosqlite

DB_NAME = "bot_database.db"

async def init_db():
    """Создаёт все таблицы, если их ещё нет"""
    async with aiosqlite.connect(DB_NAME) as db:
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

# ---------- НОВЫЕ УДОБНЫЕ ФУНКЦИИ ----------

async def get_user_info(user_id: int):
    """Возвращает кортеж (username, balance, rating, deals_count) или None"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT username, balance, rating, deals_count FROM users WHERE user_id=?",
            (user_id,)
        )
        return await cursor.fetchone()

async def get_active_ads(limit: int = 5):
    """Возвращает список активных объявлений с данными продавца"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT a.id, a.operator, a.gb, a.price, a.region, a.seller_id,
                   u.username, u.rating, u.deals_count
            FROM ads a JOIN users u ON a.seller_id = u.user_id
            WHERE a.status='active'
            ORDER BY a.created_at DESC
            LIMIT ?
        """, (limit,))
        return await cursor.fetchall()

async def get_user_deals(user_id: int, role: str = "buyer", limit: int = 5):
    """
    Возвращает сделки пользователя:
    role = "buyer" — покупки, "seller" — продажи.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        if role == "buyer":
            cursor = await db.execute("""
                SELECT d.id, a.operator, a.gb, d.amount, d.status,
                       a.seller_id, u.username
                FROM deals d
                JOIN ads a ON d.ad_id = a.id
                JOIN users u ON a.seller_id = u.user_id
                WHERE d.buyer_id=? AND d.status IN ('paid','completed','disputed')
                ORDER BY d.created_at DESC
                LIMIT ?
            """, (user_id, limit))
        else:  # seller
            cursor = await db.execute("""
                SELECT d.id, a.operator, a.gb, d.amount, d.status,
                       d.buyer_id, u.username
                FROM deals d
                JOIN ads a ON d.ad_id = a.id
                JOIN users u ON d.buyer_id = u.user_id
                WHERE d.seller_id=? AND d.status IN ('paid','completed','disputed')
                ORDER BY d.created_at DESC
                LIMIT ?
            """, (user_id, limit))
        return await cursor.fetchall()
