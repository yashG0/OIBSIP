# OIBSIP Chat Application

A real-time chat application built with Python, TCP sockets, threading, GTK4/libadwaita, and SQLite.

## Features

- **User authentication** — Register and log in with a username and password.
- **Password security** — Passwords are stored as hashes rather than plaintext.
- **Real-time messaging** — Exchange messages over TCP sockets.
- **Timestamps** — Display timestamps with chat messages.
- **Chat rooms** — Create and join named rooms.
- **Message history** — Store messages in SQLite and load room history when joining.
- **Emoji shortcodes** — Convert shortcodes such as `:smile:` and `:heart:` into emojis.
- **Desktop notifications** — Notify users about incoming messages when the application window is unfocused.

## Tech Stack

| Technology        | Purpose                                      |
| ----------------- | -------------------------------------------- |
| Python            | Application logic                            |
| TCP sockets       | Client-server communication                  |
| Threading         | Handle multiple clients                      |
| GTK4 / libadwaita | Desktop GUI                                  |
| SQLite            | User accounts and message history            |
| uv                | Python environment and dependency management |

## Requirements

- Linux desktop with GTK4 and libadwaita
- Python with PyGObject bindings
- `uv`

On Fedora, install the system GUI dependencies if needed:

```bash
sudo dnf install gtk4 libadwaita python3-gobject
```

## Getting Started

Clone the repository and enter the project directory:

```bash
git clone https://github.com/yashG0/OIBSIP.git
cd OIBSIP/Task-5-Chat-Application
```

### 1. Start the server

Open a terminal and run:

```bash
PYTHONPATH=src uv run python -c \
'from chat_app.server import ChatServer; ChatServer().start()'
```

Keep the server running.

### 2. Launch the desktop client

Open another terminal:

```bash
PYTHONPATH=src /usr/bin/python3 src/main.py
```

Register an account or log in, then create or join a room to start chatting.

The server and clients can run on the same computer for local testing.

## Storage and Security

- SQLite stores user account information and chat messages.
- Passwords are stored as hashes.
- Messages are persisted with room information and timestamps.
- Chat traffic uses TCP without transport encryption. Messages are **not end-to-end encrypted**, so this application should not be used to exchange sensitive information.

## Running Tests

From the project directory:

```bash
uv run pytest -q
```

## Project Structure

```text
Task-5-Chat-Application/
├── src/
│   ├── chat_app/
│   │   ├── client.py
│   │   ├── server.py
│   │   ├── gui.py
│   │   └── database.py
│   └── main.py
├── tests/
├── README.md
└── pyproject.toml
```

## Internship

Developed as **Task 5** of the Oasis Infobyte Python Programming Internship (OIBSIP).
