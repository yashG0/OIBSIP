import socket
import threading
from datetime import datetime, timezone

from chat_app.auth import AuthService
from chat_app.database import ChatDatabase
from chat_app.protocol import encode_message, receive_messages


class ChatServer:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5050,
        db_path: str = "chat.db",
    ) -> None:
        self.host = host
        self.port = port
        self.database = ChatDatabase(db_path)
        self.auth = AuthService(self.database)

        self.server_socket: socket.socket | None = None
        self.clients: dict[socket.socket, dict[str, str]] = {}
        self.lock = threading.RLock()
        self.running = False

    @staticmethod
    def timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    def send(self, conn: socket.socket, message: dict) -> None:
        conn.sendall(encode_message(message))

    def broadcast(self, room: str, message: dict) -> None:
        payload = encode_message(message)

        with self.lock:
            recipients = [
                conn for conn, info in self.clients.items() if info["room"] == room
            ]

        for conn in recipients:
            try:
                conn.sendall(payload)
            except OSError:
                self.remove_client(conn)

    def start(self) -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen()
        server.settimeout(1)

        self.server_socket = server
        self.running = True
        print(f"Chat server listening on {self.host}:{self.port}")

        try:
            while self.running:
                try:
                    conn, address = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break

                threading.Thread(
                    target=self.handle_client,
                    args=(conn, address),
                    daemon=True,
                ).start()
        finally:
            self.stop()

    def handle_client(self, conn: socket.socket, address) -> None:
        buffer = b""
        authenticated = False
        username = ""

        try:
            self.send(
                conn,
                {
                    "type": "system",
                    "text": "Register or login to continue.",
                },
            )

            while self.running and not authenticated:
                messages, buffer = receive_messages(conn, buffer)

                for message in messages:
                    action = message.get("type")
                    name = str(message.get("username", "")).strip()
                    password = message.get("password", "")

                    if not isinstance(password, str):
                        self.send(
                            conn,
                            {
                                "type": "error",
                                "text": "Invalid credentials.",
                            },
                        )
                        continue

                    try:
                        if action == "register":
                            self.auth.register(name, password)
                            self.send(
                                conn,
                                {
                                    "type": "auth",
                                    "success": True,
                                    "text": "Registration successful. You can now log in.",
                                },
                            )

                        elif action == "login":
                            if self.auth.login(name, password):
                                username = name
                                authenticated = True
                                room = "general"

                                with self.lock:
                                    self.clients[conn] = {
                                        "username": username,
                                        "room": room,
                                    }

                                self.send(
                                    conn,
                                    {
                                        "type": "auth",
                                        "success": True,
                                        "username": username,
                                        "room": room,
                                        "text": "Login successful.",
                                    },
                                )

                                self.send(
                                    conn,
                                    {
                                        "type": "history",
                                        "messages": self.database.get_messages(room),
                                    },
                                )

                                self.broadcast(
                                    room,
                                    {
                                        "type": "system",
                                        "text": f"{username} joined the chat.",
                                        "time": self.timestamp(),
                                    },
                                )
                                break
                            else:
                                self.send(
                                    conn,
                                    {
                                        "type": "auth",
                                        "success": False,
                                        "text": "Invalid username or password.",
                                    },
                                )

                        else:
                            self.send(
                                conn,
                                {
                                    "type": "error",
                                    "text": "Please register or login first.",
                                },
                            )

                    except ValueError as exc:
                        self.send(
                            conn,
                            {
                                "type": "auth",
                                "success": False,
                                "text": str(exc),
                            },
                        )

            while self.running and authenticated:
                messages, buffer = receive_messages(conn, buffer)

                for message in messages:
                    action = message.get("type")

                    if action == "create_room":
                        room = str(message.get("room", "")).strip().lower()

                        if not room or len(room) > 64:
                            self.send(
                                conn,
                                {
                                    "type": "error",
                                    "text": "Room name must be 1–64 characters.",
                                },
                            )
                            continue

                        if not all(c.isalnum() or c in "-_" for c in room):
                            self.send(
                                conn,
                                {
                                    "type": "error",
                                    "text": "Use letters, numbers, hyphens or underscores.",
                                },
                            )
                            continue

                        self.send(
                            conn,
                            {
                                "type": "room_created",
                                "room": room,
                                "text": f"Room #{room} is ready to join.",
                            },
                        )

                    elif action == "join_room":
                        room = str(message.get("room", "")).strip().lower()

                        if (
                            not room
                            or len(room) > 64
                            or not all(c.isalnum() or c in "-_" for c in room)
                        ):
                            self.send(
                                conn,
                                {
                                    "type": "error",
                                    "text": "Invalid room name.",
                                },
                            )
                            continue

                        with self.lock:
                            old_info = self.clients.get(conn)
                            if not old_info:
                                continue
                            old_room = old_info["room"]
                            self.clients[conn]["room"] = room

                        if old_room != room:
                            self.broadcast(
                                old_room,
                                {
                                    "type": "system",
                                    "text": f"{username} left the room.",
                                    "time": self.timestamp(),
                                },
                            )

                        self.send(
                            conn,
                            {
                                "type": "room_joined",
                                "room": room,
                                "text": f"Joined #{room}.",
                            },
                        )
                        self.send(
                            conn,
                            {
                                "type": "history",
                                "room": room,
                                "messages": self.database.get_messages(room),
                            },
                        )
                        self.broadcast(
                            room,
                            {
                                "type": "system",
                                "text": f"{username} joined the room.",
                                "time": self.timestamp(),
                            },
                        )

                    elif action == "chat":
                        content = str(message.get("text", "")).strip()

                        if not content:
                            continue

                        if len(content) > 2000:
                            self.send(
                                conn,
                                {
                                    "type": "error",
                                    "text": "Message exceeds 2000 characters.",
                                },
                            )
                            continue

                        room = self.clients[conn]["room"]
                        self.database.save_message(
                            username,
                            content,
                            room,
                        )

                        self.broadcast(
                            room,
                            {
                                "type": "chat",
                                "username": username,
                                "text": content,
                                "room": room,
                                "time": self.timestamp(),
                            },
                        )

        except ConnectionError, OSError, ValueError:
            pass
        finally:
            self.remove_client(conn)

    def remove_client(self, conn: socket.socket) -> None:
        with self.lock:
            info = self.clients.pop(conn, None)

        try:
            conn.close()
        except OSError:
            pass

        if info:
            self.broadcast(
                info["room"],
                {
                    "type": "system",
                    "text": f"{info['username']} left the chat.",
                    "time": self.timestamp(),
                },
            )

    def stop(self) -> None:
        self.running = False

        server = self.server_socket
        self.server_socket = None

        if server:
            try:
                server.close()
            except OSError:
                pass

        with self.lock:
            connections = list(self.clients)

        for conn in connections:
            self.remove_client(conn)


if __name__ == "__main__":
    ChatServer().start()
