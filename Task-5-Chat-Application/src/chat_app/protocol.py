import json
import socket
from typing import Any

MAX_MESSAGE_BYTES = 64 * 1024


def encode_message(message: dict[str, Any]) -> bytes:
    payload = json.dumps(message, separators=(",", ":")).encode("utf-8")
    if len(payload) > MAX_MESSAGE_BYTES:
        raise ValueError("Message is too large")
    return payload + b"\n"


def receive_messages(
    sock: socket.socket,
    buffer: bytes = b"",
) -> tuple[list[dict[str, Any]], bytes]:
    chunk = sock.recv(4096)
    if not chunk:
        raise ConnectionError("Peer disconnected")

    buffer += chunk
    if len(buffer) > MAX_MESSAGE_BYTES and b"\n" not in buffer:
        raise ValueError("Message is too large")

    messages = []
    while b"\n" in buffer:
        line, buffer = buffer.split(b"\n", 1)
        if not line:
            continue
        if len(line) > MAX_MESSAGE_BYTES:
            raise ValueError("Message is too large")

        decoded = json.loads(line.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise ValueError("Message must be a JSON object")
        messages.append(decoded)

    return messages, buffer
