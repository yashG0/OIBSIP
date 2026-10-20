import json
import webbrowser
from datetime import datetime
from pathlib import Path

from assistant.reminders import schedule_reminder

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "commands.json"


def load_custom_commands() -> dict[str, dict[str, str]]:
    """Load custom commands from the JSON configuration file."""
    try:
        with CONFIG_PATH.open(encoding="utf-8") as config_file:
            config = json.load(config_file)
    except OSError, json.JSONDecodeError:
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

    if normalized.startswith("remind me to "):
        reminder_text = normalized.removeprefix("remind me to ")
        parts = reminder_text.rsplit(" in ", maxsplit=1)

        if len(parts) != 2:
            return "Use: remind me to stretch in 30 seconds.", True

        message, duration = parts
        duration_parts = duration.split()

        if (
            not message.strip()
            or len(duration_parts) != 2
            or not duration_parts[0].isdigit()
        ):
            return "Use a reminder like: remind me to stretch in 30 seconds.", True

        amount = int(duration_parts[0])
        unit = duration_parts[1].rstrip("s")

        multipliers = {"second": 1, "minute": 60, "hour": 3600}

        if amount < 1 or unit not in multipliers:
            return "Use a positive delay in seconds, minutes, or hours.", True

        delay_seconds = amount * multipliers[unit]

        schedule_reminder(
            message,
            delay_seconds,
            lambda text: print(f"\nAssistant: {text}"),
        )
        return f"Reminder set for {message} in {duration}.", True

    custom_commands = load_custom_commands()
    custom_command = custom_commands.get(normalized)

    if custom_command:
        webbrowser.open(custom_command["url"])
        return custom_command["response"], True

    return "Sorry, I don't know that command yet.", True
