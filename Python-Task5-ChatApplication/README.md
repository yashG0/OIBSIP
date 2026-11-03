# Relay — OIBSIP Task 5 Chat Application

Relay is a desktop chat application built with Python, GTK4/libadwaita, TCP sockets, and SQLite. It supports account registration, public community rooms, and invite-only private rooms.

## Features

- **Sign in and account creation** with username and password validation.
- **Hashed passwords** stored in SQLite using `scrypt`.
- **Public room directory** with live online-member counts.
- **Private rooms** that stay out of the public directory and can be joined with an invite code.
- **Creator-controlled public room deletion.** Only a room's creator can delete it. The built-in General room is protected. Deleting a room also deletes its message history and returns its members to the room directory; disconnecting does not delete a room.
- **Real-time chat** with timestamps, message history, emoji shortcodes, and desktop notifications when the window is unfocused.
- **System, light, and dark appearance choices.**

## Requirements

- Linux desktop with GTK4 and libadwaita
- Python 3.15 or newer for the project environment
- PyGObject bindings for the system Python used to launch the GTK interface
- [`uv`](https://docs.astral.sh/uv/)

On Fedora, install the GTK dependencies if needed:

```bash
sudo dnf install gtk4 libadwaita python3-gobject
```

## Setup

From the cloned repository, enter the Task 5 project folder:

```bash
cd OIBSIP/Python-Task5-ChatApplication
uv sync
```

Start the server in one terminal, from the project folder:

```bash
PYTHONPATH=src uv run python -c \
'from chat_app.server import ChatServer; ChatServer().start()'
```

Leave the server running. In a second terminal, launch Relay:

```bash
cd OIBSIP/Python-Task5-ChatApplication
PYTHONPATH=src /usr/bin/python3 src/main.py
```

Register or sign in, then choose a public room or create one. To make an invite-only room, select **Private** when creating it and share the displayed invite code with the people you want to join. Anyone with that code can join the private room.

The default server listens on `127.0.0.1:5050`, so the server and clients run on the same computer by default.

## Storage and security

- `chat.db` stores account records, rooms, and message history in the project directory where the server starts.
- Passwords are stored as salted `scrypt` hashes, not plaintext.
- Chat traffic uses TCP without transport encryption and is not end-to-end encrypted. The default server binds to localhost. Do not expose it to an untrusted network or use it for sensitive conversations without adding suitable network security.
- A private-room invite code grants access to that room. Share it only with intended participants.

## Tests

Run the test suite from the project folder:

```bash
uv run python -m pytest -q
```

## Project structure

```text
Python-Task5-ChatApplication/
├── src/
│   ├── chat_app/
│   │   ├── auth.py
│   │   ├── client.py
│   │   ├── database.py
│   │   ├── gui.py
│   │   ├── protocol.py
│   │   └── server.py
│   └── main.py
├── tests/
├── README.md
└── pyproject.toml
```

## Internship

Developed as **Task 5** of the Oasis Infobyte Python Programming Internship (OIBSIP).
