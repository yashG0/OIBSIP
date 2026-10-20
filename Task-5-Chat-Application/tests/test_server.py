import json
import socket
import threading
import time

import pytest

from chat_app.protocol import encode_message
from chat_app.server import ChatServer


@pytest.fixture
def running_server(tmp_path):
    server = ChatServer(
        host="127.0.0.1",
        port=0,
        db_path=str(tmp_path / "chat-test.db"),
    )

    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()

    deadline = time.monotonic() + 3
    while server.server_socket is None:
        if time.monotonic() > deadline:
            pytest.fail("Server did not start")
        time.sleep(0.01)

    port = server.server_socket.getsockname()[1]

    yield port

    server.stop()
    thread.join(timeout=2)


class ChatTestClient:
    def __init__(self, port):
        self.sock = socket.create_connection(("127.0.0.1", port))
        self.sock.settimeout(2)
        self.buffer = b""
        self.receive()  # Initial system message

    def send(self, message):
        self.sock.sendall(encode_message(message))

    def receive(self):
        while b"\n" not in self.buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("Server disconnected")
            self.buffer += chunk

        line, self.buffer = self.buffer.split(b"\n", 1)
        return json.loads(line)

    def close(self):
        self.sock.close()



def test_register_login_and_message_history(running_server):
    client = ChatTestClient(running_server)

    try:
        client.send(
            {
                "type": "register",
                "username": "yash",
                "password": "secure-password-123",
            }
        )
        response = client.receive()
        assert response["success"] is True

        client.send(
            {
                "type": "login",
                "username": "yash",
                "password": "secure-password-123",
            }
        )
        response = client.receive()
        assert response["success"] is True

        history = client.receive()
        assert history["type"] == "history"
        assert history["messages"] == []

        # The server sends the join notification after login.
        join_event = client.receive()
        assert join_event["type"] == "system"
        assert "joined the chat" in join_event["text"]

        client.send(
            {
                "type": "chat",
                "text": "Hello integration test!",
            }
        )
        message = client.receive()

        assert message["type"] == "chat"
        assert message["username"] == "yash"
        assert message["text"] == "Hello integration test!"

    finally:
        client.close()

def test_invalid_login_is_rejected(running_server):
    client = ChatTestClient(running_server)

    try:
        client.send(
            {
                "type": "login",
                "username": "unknown",
                "password": "wrong-password",
            }
        )

        response = client.receive()
        assert response["type"] == "auth"
        assert response["success"] is False
    finally:
        client.close()
