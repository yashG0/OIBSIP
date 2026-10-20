import socket
import threading
from datetime import datetime

from chat_app.protocol import encode_message, receive_messages


class ChatServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 5050):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients: dict[socket.socket, str] = {}
        self.lock = threading.Lock()
        self.running = False

    def start(self):
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

                thread = threading.Thread(
                    target=self._handle_client,
                    args=(conn, address),
                    daemon=True,
                )
                thread.start()
        finally:
            self.stop()

    def _send(self, conn: socket.socket, message: dict):
        conn.sendall(encode_message(message))

    def _broadcast(self, message: dict, exclude=None):
        with self.lock:
            recipients = [conn for conn in self.clients if conn is not exclude]

        payload = encode_message(message)
        for conn in recipients:
            try:
                conn.sendall(payload)
            except OSError:
                self._remove_client(conn)

    def _handle_client(self, conn: socket.socket, address):
        name = f"Guest-{address[1]}"
        buffer = b""

        try:
            self._send(conn, {"type": "welcome", "name": name})

            with self.lock:
                self.clients[conn] = name

            self._broadcast(
                {
                    "type": "system",
                    "text": f"{name} joined the chat.",
                    "time": self._timestamp(),
                },
                exclude=conn,
            )

            while self.running:
                messages, buffer = receive_messages(conn, buffer)
                for message in messages:
                    if message.get("type") != "chat":
                        continue

                    text = str(message.get("text", "")).strip()
                    if not text:
                        continue
                    if len(text) > 2000:
                        self._send(
                            conn,
                            {
                                "type": "error",
                                "text": "Message exceeds 2000 characters.",
                            },
                        )
                        continue

                    self._broadcast(
                        {
                            "type": "chat",
                            "name": name,
                            "text": text,
                            "time": self._timestamp(),
                        }
                    )
        except ConnectionError, OSError, ValueError:
            pass
        finally:
            self._remove_client(conn)

    @staticmethod
    def _timestamp():
        return datetime.now().astimezone().strftime("%H:%M")

    def _remove_client(self, conn: socket.socket):
        with self.lock:
            name = self.clients.pop(conn, None)

        try:
            conn.close()
        except OSError:
            pass

        if name:
            self._broadcast(
                {
                    "type": "system",
                    "text": f"{name} left the chat.",
                    "time": self._timestamp(),
                }
            )

    def stop(self):
        if not self.running and self.server_socket is None:
            return

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
            self._remove_client(conn)


if __name__ == "__main__":
    ChatServer().start()
