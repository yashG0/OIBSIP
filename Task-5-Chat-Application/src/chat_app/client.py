import socket
import threading

from chat_app.protocol import encode_message, receive_messages


class ChatClient:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5050,
        on_message=None,
    ):
        self.host = host
        self.port = port
        self.on_message = on_message or print
        self.sock = None
        self.running = False
        self.thread = None

    def connect(self):
        self.sock = socket.create_connection((self.host, self.port), timeout=5)
        self.sock.settimeout(None)
        self.running = True

        self.thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.thread.start()

    def send_message(self, text: str):
        if not self.sock or not self.running:
            raise ConnectionError("Not connected to the chat server")

        text = text.strip()
        if not text:
            return
        if len(text) > 2000:
            raise ValueError("Message must be at most 2000 characters")

        self.sock.sendall(
            encode_message(
                {
                    "type": "chat",
                    "text": text,
                }
            )
        )

    def _receive_loop(self):
        buffer = b""
        try:
            while self.running and self.sock:
                messages, buffer = receive_messages(self.sock, buffer)
                for message in messages:
                    self.on_message(message)
        except (ConnectionError, OSError, ValueError) as exc:
            if self.running:
                self.on_message(
                    {
                        "type": "system",
                        "text": f"Disconnected: {exc}",
                    }
                )
        finally:
            self.running = False
            if self.sock:
                try:
                    self.sock.close()
                except OSError:
                    pass
                self.sock = None

    def disconnect(self):
        self.running = False
        sock = self.sock
        self.sock = None
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
