
import json
import webbrowser
from datetime import datetime
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "commands.json"


def load_custom_commands() -> dict[str, dict[str, str]]:
    """Load custom commands from the JSON configuration file."""
    try:
        with CONFIG_PATH.open(encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (OSError, json.JSONDecodeError):
        return {}

    commands = config.get("commands", {})
    if not isinstance(commands, dict):
        return {}

    return {
        " ".join(name.casefold().split()): details
        for name, details in commands.items()
        if isinstance(name, str)
        and isinstance(details, dict)
        and isinstance(details.get("response"), str)
        and isinstance(details.get("url"), str)
        and details["url"].startswith(("https://", "http://"))
    }


def handle_command(command: str) -> tuple[str, bool]:
    normalized = " ".join(command.casefold().split())

    if not normalized:
        return "I didn't catch that. Please try again.", True

    if normalized in {"exit", "quit", "stop", "goodbye"}:
        return "Goodbye!", False

    if "time" in normalized:
        current_time = datetime.now().strftime("%I:%M %p")
        return f"The current time is {current_time}.", True

    if "date" in normalized or "today" in normalized:
        current_date = datetime.now().strftime("%A, %d %B %Y")
        return f"Today is {current_date}.", True

    custom_commands = load_custom_commands()
    custom_command = custom_commands.get(normalized)

    if custom_command:
        webbrowser.open(custom_command["url"])
        return custom_command["response"], True

    return "Sorry, I don't know that command yet.", True
