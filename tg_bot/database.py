import asyncio
import time
import aiosqlite
from pathlib import Path


class Database:
    def __init__(self, path: str = "storage/bot.db"):
        self.path = path
        self._lock = asyncio.Lock()
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    language TEXT DEFAULT 'ru',
                    authorized INTEGER DEFAULT 0,
                    failed_attempts INTEGER DEFAULT 0,
                    blocked_until INTEGER DEFAULT 0,
                    notify_orders INTEGER DEFAULT 1,
                    notify_chats INTEGER DEFAULT 1
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    created_at INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chat_read (
                    chat_id TEXT PRIMARY KEY,
                    last_msg_id TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS orders_notified (
                    order_id TEXT PRIMARY KEY,
                    created_at INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS orders_status (
                    order_id TEXT PRIMARY KEY,
                    status TEXT,
                    updated_at INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS autodelivery (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at INTEGER DEFAULT 0
                )
            """)
            await db.commit()

    async def get_user(self, user_id: int) -> dict:
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                db.row_factory = aiosqlite.Row
                cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
                row = await cur.fetchone()
                await cur.close()
                if row is None:
                    await db.execute("INSERT INTO users(user_id) VALUES(?)", (user_id,))
                    await db.commit()
                    cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
                    row = await cur.fetchone()
                    await cur.close()
                return dict(row)

    async def set_language(self, user_id: int, lang: str):
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                await db.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))
                await db.commit()

    async def set_authorized(self, user_id: int, val: bool):
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                await db.execute("UPDATE users SET authorized=? WHERE user_id=?", (1 if val else 0, user_id))
                await db.commit()

    async def increment_failed(self, user_id: int) -> int:
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                await db.execute("UPDATE users SET failed_attempts=COALESCE(failed_attempts,0)+1 WHERE user_id=?", (user_id,))
                await db.commit()
                cur = await db.execute("SELECT failed_attempts FROM users WHERE user_id=?", (user_id,))
                row = await cur.fetchone()
                await cur.close()
                return int(row[0]) if row else 0

    async def reset_failed(self, user_id: int):
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                await db.execute("UPDATE users SET failed_attempts=0 WHERE user_id=?", (user_id,))
                await db.commit()

    async def set_blocked_until(self, user_id: int, ts: int):
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                await db.execute("UPDATE users SET blocked_until=? WHERE user_id=?", (ts, user_id))
                await db.commit()

    async def toggle_notify_orders(self, user_id: int) -> bool:
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                cur = await db.execute("SELECT notify_orders FROM users WHERE user_id=?", (user_id,))
                row = await cur.fetchone()
                await cur.close()
                val = 0 if (row and row[0]) else 1
                await db.execute("UPDATE users SET notify_orders=? WHERE user_id=?", (val, user_id))
                await db.commit()
                return bool(val)

    async def toggle_notify_chats(self, user_id: int) -> bool:
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                cur = await db.execute("SELECT notify_chats FROM users WHERE user_id=?", (user_id,))
                row = await cur.fetchone()
                await cur.close()
                val = 0 if (row and row[0]) else 1
                await db.execute("UPDATE users SET notify_chats=? WHERE user_id=?", (val, user_id))
                await db.commit()
                return bool(val)

    async def add_template(self, content: str) -> int:
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                cur = await db.execute(
                    "INSERT INTO templates(content, created_at) VALUES(?, ?)",
                    (content, int(time.time()))
                )
                await db.commit()
                return cur.lastrowid

    async def delete_template(self, tpl_id: int) -> bool:
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                cur = await db.execute("DELETE FROM templates WHERE id=?", (tpl_id,))
                await db.commit()
                return cur.rowcount > 0

    async def get_template(self, tpl_id: int) -> dict | None:
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                db.row_factory = aiosqlite.Row
                cur = await db.execute("SELECT * FROM templates WHERE id=?", (tpl_id,))
                row = await cur.fetchone()
                await cur.close()
                return dict(row) if row else None

    async def list_templates(self, offset: int = 0, limit: int = 5) -> list:
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                db.row_factory = aiosqlite.Row
                cur = await db.execute(
                    "SELECT * FROM templates ORDER BY id DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
                rows = await cur.fetchall()
                await cur.close()
                return [dict(r) for r in rows]

    async def count_templates(self) -> int:
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                cur = await db.execute("SELECT COUNT(*) FROM templates")
                row = await cur.fetchone()
                await cur.close()
                return int(row[0]) if row else 0

    async def get_last_chat_msg(self, chat_id: str) -> str | None:
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                cur = await db.execute("SELECT last_msg_id FROM chat_read WHERE chat_id=?", (chat_id,))
                row = await cur.fetchone()
                await cur.close()
                return row[0] if row else None

    async def set_last_chat_msg(self, chat_id: str, msg_id: str):
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                await db.execute(
                    "INSERT INTO chat_read(chat_id, last_msg_id) VALUES(?, ?) "
                    "ON CONFLICT(chat_id) DO UPDATE SET last_msg_id=excluded.last_msg_id",
                    (chat_id, msg_id)
                )
                await db.commit()

    async def is_order_notified(self, order_id: str) -> bool:
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                cur = await db.execute("SELECT 1 FROM orders_notified WHERE order_id=?", (order_id,))
                row = await cur.fetchone()
                await cur.close()
                return row is not None

    async def mark_order_notified(self, order_id: str):
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                await db.execute(
                    "INSERT INTO orders_notified(order_id, created_at) VALUES(?, ?) ON CONFLICT DO NOTHING",
                    (order_id, int(time.time()))
                )
                await db.commit()

    async def get_order_status(self, order_id: str) -> str | None:
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                cur = await db.execute("SELECT status FROM orders_status WHERE order_id=?", (order_id,))
                row = await cur.fetchone()
                await cur.close()
                return row[0] if row else None

    async def set_order_status(self, order_id: str, status: str):
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                await db.execute(
                    "INSERT INTO orders_status(order_id, status, updated_at) VALUES(?, ?, ?) "
                    "ON CONFLICT(order_id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at",
                    (order_id, status, int(time.time()))
                )
                await db.commit()

    async def add_autodelivery(self, product: str, values: list) -> int:
        if not values:
            return 0
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                ts = int(time.time())
                await db.executemany(
                    "INSERT INTO autodelivery(product, value, created_at) VALUES(?, ?, ?)",
                    [(product, v, ts) for v in values]
                )
                await db.commit()
                return len(values)

    async def pop_autodelivery(self, product: str) -> str | None:
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                db.row_factory = aiosqlite.Row
                cur = await db.execute(
                    "SELECT id, value FROM autodelivery WHERE product=? ORDER BY id ASC LIMIT 1",
                    (product,)
                )
                row = await cur.fetchone()
                await cur.close()
                if not row:
                    return None
                item_id = row["id"]
                value = row["value"]
                await db.execute("DELETE FROM autodelivery WHERE id=?", (item_id,))
                await db.commit()
                return value

    async def count_autodelivery(self, product: str) -> int:
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                cur = await db.execute("SELECT COUNT(*) FROM autodelivery WHERE product=?", (product,))
                row = await cur.fetchone()
                await cur.close()
                return int(row[0]) if row else 0

    async def list_autodelivery(self) -> list:
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                cur = await db.execute(
                    "SELECT product, COUNT(*) as cnt FROM autodelivery GROUP BY product ORDER BY product"
                )
                rows = await cur.fetchall()
                await cur.close()
                return [(r[0], r[1]) for r in rows]

    async def delete_autodelivery(self, product: str) -> int:
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                cur = await db.execute("SELECT COUNT(*) FROM autodelivery WHERE product=?", (product,))
                row = await cur.fetchone()
                count = int(row[0]) if row else 0
                await cur.close()
                await db.execute("DELETE FROM autodelivery WHERE product=?", (product,))
                await db.commit()
                return count

    async def get_authorized_users(self) -> list:
        async with self._lock:
            async with aiosqlite.connect(self.path) as db:
                db.row_factory = aiosqlite.Row
                cur = await db.execute("SELECT user_id, language, notify_orders, notify_chats FROM users WHERE authorized=1")
                rows = await cur.fetchall()
                await cur.close()
                return [dict(r) for r in rows]

