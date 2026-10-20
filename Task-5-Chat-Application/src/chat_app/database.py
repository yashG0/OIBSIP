
import secrets
import sqlite3
import string
from datetime import datetime, timezone
from pathlib import Path


ROOM_ID_ALPHABET = string.ascii_uppercase + string.digits


class ChatDatabase:
    def __init__(self, db_path: str | Path = "chat.db") -> None:
        self.db_path = str(db_path)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS rooms (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_by TEXT NOT NULL,
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

            # Preserve compatibility with the previous general room.
            connection.execute(
                """
                INSERT OR IGNORE INTO rooms (id, name, created_by, created_at)
                VALUES ('GENERAL', 'General', 'system', ?)
                """,
                (self._now(),),
            )

    def create_user(self, username: str, password_hash: str) -> int:
        username = username.strip()
        if not username or len(username) > 32:
            raise ValueError("Username must be 1–32 characters.")

        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO users (username, password_hash, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (username, password_hash, self._now()),
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

    def create_room(self, name: str, created_by: str) -> dict:
        name = name.strip()
        if not name or len(name) > 64:
            raise ValueError("Room name must be 1–64 characters.")

        with self._connect() as connection:
            for _ in range(10):
                room_id = "".join(
                    secrets.choice(ROOM_ID_ALPHABET) for _ in range(8)
                )
                try:
                    connection.execute(
                        """
                        INSERT INTO rooms (id, name, created_by, created_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (room_id, name, created_by, self._now()),
                    )
                    return self.get_room(room_id)
                except sqlite3.IntegrityError:
                    continue

        raise RuntimeError("Could not generate a unique room ID.")

    def get_room(self, room_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, name, created_by, created_at FROM rooms WHERE id = ?",
                (room_id.strip().upper(),),
            ).fetchone()
            return dict(row) if row else None

    def list_rooms_for_user(self, username: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT r.id, r.name, r.created_by, r.created_at
                FROM rooms r
                LEFT JOIN messages m ON m.room = r.id
                WHERE r.created_by = ? OR m.username = ?
                ORDER BY r.created_at DESC
                """,
                (username, username),
            ).fetchall()
        return [dict(row) for row in rows]

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
            raise ValueError("Room must be 1–64 characters.")

        # Preserve legacy room names; room IDs are normalized to uppercase.
        room_record = self.get_room(room)
        if room_record:
            room = room_record["id"]
            if room == "GENERAL":
                room = "general"

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO messages (username, room, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (username, room, content, self._now()),
            )
            return int(cursor.lastrowid)

    def get_messages(self, room: str = "general", limit: int = 100) -> list[dict]:
        if not 1 <= limit <= 1000:
            raise ValueError("Limit must be between 1 and 1000.")

        room = room.strip()
        room_record = self.get_room(room)
        if room_record:
            room = room_record["id"]
            if room == "GENERAL":
                room = "general"

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
