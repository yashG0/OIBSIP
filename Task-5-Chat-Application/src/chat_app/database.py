import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class ChatDatabase:
    def __init__(self, db_path: str | Path = "chat.db") -> None:
        self.db_path = str(db_path)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    room TEXT NOT NULL DEFAULT 'general',
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_messages_room_id
                ON messages(room, id);
            """)

    def create_user(self, username: str, password_hash: str) -> int:
        username = username.strip()
        if not username or len(username) > 32:
            raise ValueError("Username must be 1–32 characters.")

        created_at = datetime.now(timezone.utc).isoformat()

        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO users (username, password_hash, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (username, password_hash, created_at),
                )
                return int(cursor.lastrowid)
        except sqlite3.IntegrityError as exc:
            raise ValueError("Username is already registered.") from exc

    def get_user(self, username: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE username = ?",
                (username.strip(),),
            ).fetchone()
            return dict(row) if row else None

    def save_message(
        self,
        username: str,
        content: str,
        room: str = "general",
    ) -> int:
        content = content.strip()
        room = room.strip()

        if not content or len(content) > 2000:
            raise ValueError("Message must be 1–2000 characters.")
        if not room or len(room) > 64:
            raise ValueError("Room name must be 1–64 characters.")

        created_at = datetime.now(timezone.utc).isoformat()

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO messages (username, room, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (username, room, content, created_at),
            )
            return int(cursor.lastrowid)

    def get_messages(self, room: str = "general", limit: int = 100) -> list[dict]:
        if not 1 <= limit <= 1000:
            raise ValueError("Limit must be between 1 and 1000.")

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, username, room, content, created_at
                FROM messages
                WHERE room = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (room, limit),
            ).fetchall()

        return [dict(row) for row in reversed(rows)]
