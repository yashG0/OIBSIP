# Relay — Chat Application

Relay is a desktop chat application built with Python, GTK4/libadwaita, TCP sockets, and SQLite. Create an account, browse public rooms, or join an invite-only private room with a code.

## Features

- Separate **Sign In** and **Create Account** pages
- Username and password validation; salted scrypt password hashes
- Public room directory with live online-member counts
- Private rooms hidden from the public directory and joined with an invite code
- Real-time chat with timestamps, stored message history, emoji shortcodes, and desktop notifications when the window is unfocused
- System, light, and dark appearance options
- Public room deletion by its creator; the built-in **General** room is protected. Leaving or disconnecting does not delete a room.

## Requirements

- Linux desktop with GTK4 and libadwaita
- PyGObject bindings for the system Python used to launch the interface
- Python 3.15 or newer and [uv](https://docs.astral.sh/uv/)

On Fedora, install the system GUI dependencies if needed:

```bash
sudo dnf install gtk4 libadwaita python3-gobject
```

## Setup and run

From this project folder, install the Python dependencies:

```bash
uv sync
```

Start the chat server in one terminal:

```bash
PYTHONPATH=src uv run python -c \
'from chat_app.server import ChatServer; ChatServer().start()'
```

Keep the server running. In another terminal, launch the GTK application with the system Python that has PyGObject available:

```bash
PYTHONPATH=src /usr/bin/python3 src/main.py
```

Create an account or sign in, then join a public room or create one. Choose **Private** when creating a room to generate an invite code. Share that code with the people you want to invite.

The server listens on 127.0.0.1:5050 by default. The server and clients can communicate only from the same computer with this default configuration.

## Tests

From this project folder:

```bash
uv run python -m pytest -q
```

## Project structure

```text
src/
├── main.py
└── chat_app/
    ├── auth.py
    ├── client.py
    ├── database.py
    ├── gui.py
    ├── protocol.py
    └── server.py
tests/
├── test_auth.py
├── test_database.py
└── test_server.py
```

## Storage and security

- chat.db stores account records, room data, and message history in the directory from which the server is started.
- Passwords are stored as salted scrypt hashes, not plaintext.
- Chat traffic uses TCP without transport encryption and is not end-to-end encrypted. The default server binds to localhost; do not expose it to an untrusted network or use it for sensitive conversations without adding network security.
- Anyone with a private-room invite code can join that room. Share codes only with intended participants.

Developed as Task 5 of the Oasis Infobyte Python Programming Internship (OIBSIP).
