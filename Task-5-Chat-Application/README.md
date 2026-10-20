# OIBSIP Chat Application

A Python real-time chat application built with sockets, threading,
GTK4/libadwaita, and SQLite.

## Features

- User registration and login
- Password hashes stored in SQLite
- Real-time messaging over TCP sockets
- Message timestamps
- Persistent message history by room
- Named room creation and joining
- Emoji shortcode conversion

## Requirements

- Python
- GTK4 and libadwaita with Python GObject bindings
- uv

## Run

Start the server in one terminal:

```bash
PYTHONPATH=src uv run python -c \
"from chat_app.server import ChatServer; ChatServer().start()
```
