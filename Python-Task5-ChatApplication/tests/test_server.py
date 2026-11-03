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

        directory = client.receive()
        assert directory["type"] == "room_list"
        general = next(room for room in directory["rooms"] if room["name"] == "General")
        assert general["member_count"] == 0

        client.send({"type": "join_room", "room": general["id"]})
        joined = client.receive()
        assert joined["type"] == "room_joined"
        assert joined["room_name"] == "General"

        history = client.receive()
        assert history["type"] == "history"
        assert history["messages"] == []

        join_event = client.receive()
        assert join_event["type"] == "system"
        assert "joined General" in join_event["text"]

        directory = client.receive()
        general = next(room for room in directory["rooms"] if room["name"] == "General")
        assert general["member_count"] == 1

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

        client.send(
            {
                "type": "create_room",
                "room": "private-project",
                "is_public": False,
            }
        )
        private_room = client.receive()
        assert private_room["type"] == "room_created"
        assert private_room["is_public"] is False
        private_directory = client.receive()
        assert private_directory["type"] == "room_list"
        assert all(
            room["id"] != private_room["room"]
            for room in private_directory["rooms"]
        )

        client.send({"type": "join_room", "room": "private-project"})
        rejected = client.receive()
        assert rejected["type"] == "error"

        client.send({"type": "join_room", "room": private_room["room"]})
        joined_private = client.receive()
        assert joined_private["type"] == "room_joined"
        assert joined_private["is_public"] is False
        assert joined_private["room_name"] == "private-project"

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


def receive_type(client, expected_type):
    for _ in range(12):
        message = client.receive()
        if message.get("type") == expected_type:
            return message
    pytest.fail(f"Did not receive a {expected_type!r} message")


def register_and_login(client, username):
    password = "secure-password-123"
    client.send({"type": "register", "username": username, "password": password})
    assert client.receive()["success"] is True
    client.send({"type": "login", "username": username, "password": password})
    assert client.receive()["success"] is True
    assert receive_type(client, "room_list")["rooms"]


def test_only_public_room_creator_can_delete_it(running_server):
    host = ChatTestClient(running_server)
    guest = ChatTestClient(running_server)

    try:
        register_and_login(host, "room-host")
        host.send({"type": "create_room", "room": "host-room", "is_public": True})
        created = host.receive()
        assert created["type"] == "room_created"
        receive_type(host, "room_list")

        register_and_login(guest, "room-guest")
        guest.send({"type": "delete_room", "room": created["room"]})
        denied = guest.receive()
        assert denied["type"] == "error"
        assert "creator" in denied["text"]

        host.send({"type": "delete_room", "room": created["room"]})
        deleted = receive_type(host, "room_deleted")
        assert deleted["room"] == created["room"]
        directory = receive_type(host, "room_list")
        assert all(room["id"] != created["room"] for room in directory["rooms"])
    finally:
        host.close()
        guest.close()
