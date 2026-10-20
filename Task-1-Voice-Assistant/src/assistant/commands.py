import webbrowser
from datetime import datetime


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

    if normalized == "open youtube":
        webbrowser.open("https://www.youtube.com")
        return "Opening YouTube.", True

    if normalized == "open github":
        webbrowser.open("https://github.com")
        return "Opening GitHub.", True

    return "Sorry, I don't know that command yet.", True
