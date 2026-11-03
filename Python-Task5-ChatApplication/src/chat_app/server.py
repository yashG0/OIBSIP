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

    def room_directory(self) -> list[dict]:
        rooms = self.database.list_public_rooms()
        with self.lock:
            counts: dict[str, int] = {}
            for info in self.clients.values():
                room_id = info.get("room", "")
                if room_id:
                    room_id = room_id.upper()
                    counts[room_id] = counts.get(room_id, 0) + 1
        return [
            {**room, "member_count": counts.get(room["id"].upper(), 0)}
            for room in rooms
        ]

    def broadcast_room_directory(self) -> None:
        message = {"type": "room_list", "rooms": self.room_directory()}
        with self.lock:
            recipients = list(self.clients)
        for conn in recipients:
            try:
                self.send(conn, message)
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

                                with self.lock:
                                    self.clients[conn] = {
                                        "username": username,
                                        "room": "",
                                    }

                                self.send(
                                    conn,
                                    {
                                        "type": "auth",
                                        "success": True,
                                        "username": username,
                                        "text": "Login successful.",
                                    },
                                )

                                self.broadcast_room_directory()
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

                    if action == "list_rooms":
                        self.send(
                            conn,
                            {"type": "room_list", "rooms": self.room_directory()},
                        )

                    elif action == "create_room":
                        room_name = str(message.get("room", "")).strip()

                        if not room_name or len(room_name) > 64:
                            self.send(
                                conn,
                                {"type": "error", "text": "Room name must be 1–64 characters."},
                            )
                            continue

                        is_public = message.get("is_public", True)
                        if not isinstance(is_public, bool):
                            self.send(
                                conn,
                                {"type": "error", "text": "Choose public or private room access."},
                            )
                            continue

                        try:
                            created = self.database.create_room(
                                room_name, username, is_public=is_public
                            )
                        except ValueError as exc:
                            self.send(conn, {"type": "error", "text": str(exc)})
                            continue

                        self.send(
                            conn,
                            {
                                "type": "room_created",
                                "room": created["id"],
                                "room_name": created["name"],
                                "is_public": created["is_public"],
                                "text": (
                                    f"{created['name']} is now public. Choose it to join."
                                    if created["is_public"]
                                    else f"{created['name']} is private. Share invite code {created['id']} to let others join."
                                ),
                            },
                        )
                        self.broadcast_room_directory()

                    elif action == "delete_room":
                        room_id = str(message.get("room", "")).strip()
                        try:
                            deleted = self.database.delete_public_room(room_id, username)
                        except ValueError as exc:
                            self.send(conn, {"type": "error", "text": str(exc)})
                            continue

                        with self.lock:
                            members = [
                                member
                                for member, info in self.clients.items()
                                if info.get("room", "").upper() == deleted["id"]
                            ]
                            for member in members:
                                self.clients[member]["room"] = ""

                        notice = {
                            "type": "room_deleted",
                            "room": deleted["id"],
                            "room_name": deleted["name"],
                            "text": f"{deleted['name']} was deleted by its creator.",
                        }
                        recipients = set(members)
                        recipients.add(conn)
                        for recipient in recipients:
                            try:
                                self.send(recipient, notice)
                            except OSError:
                                self.remove_client(recipient)
                        self.broadcast_room_directory()

                    elif action == "join_room":
                        requested_room = str(message.get("room", "")).strip()
                        room_record = self.database.find_room(requested_room)
                        if not room_record or (
                            not room_record["is_public"]
                            and requested_room.upper() != room_record["id"]
                        ):
                            self.send(
                                conn,
                                {"type": "error", "text": "Public room or valid private invite code not found."},
                            )
                            continue

                        room = room_record["id"]
                        with self.lock:
                            old_info = self.clients.get(conn)
                            if not old_info:
                                continue
                            old_room = old_info.get("room", "")
                            self.clients[conn]["room"] = room

                        switched_room = old_room.upper() != room.upper() if old_room else True
                        if old_room and switched_room:
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
                                "room_name": room_record["name"],
                                "is_public": bool(room_record["is_public"]),
                                "text": f"Joined {room_record['name']}.",
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
                        if switched_room:
                            self.broadcast(
                                room,
                                {
                                    "type": "system",
                                    "text": f"{username} joined {room_record['name']}.",
                                    "time": self.timestamp(),
                                },
                            )
                        self.broadcast_room_directory()

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
            room = info.get("room", "")
            if room:
                self.broadcast(
                    room,
                    {
                        "type": "system",
                        "text": f"{info['username']} left the chat.",
                        "time": self.timestamp(),
                    },
                )
            self.broadcast_room_directory()

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
