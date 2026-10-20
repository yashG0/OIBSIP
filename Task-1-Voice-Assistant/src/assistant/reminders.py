import threading
from collections.abc import Callable


def schedule_reminder(
    message: str,
    delay_seconds: int,
    notify: Callable[[str], None],
) -> threading.Timer:
    """Schedule a reminder to notify the user after a delay."""
    message = message.strip()

    if not message:
        raise ValueError("Reminder message cannot be empty.")

    if delay_seconds < 1:
        raise ValueError("Reminder delay must be at least one second.")

    timer = threading.Timer(
        delay_seconds,
        notify,
        args=(f"Reminder: {message}",),
    )
    timer.daemon = True
    timer.start()
    return timer
