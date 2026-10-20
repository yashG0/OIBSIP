
from unittest.mock import patch

import pytest

from assistant.reminders import schedule_reminder


def test_schedule_reminder_starts_timer():
    with patch("assistant.reminders.threading.Timer") as mock_timer:
        timer = schedule_reminder("stretch", 30, print)

    mock_timer.assert_called_once_with(
        30,
        print,
        args=("Reminder: stretch",),
    )
    mock_timer.return_value.start.assert_called_once()
    assert timer is mock_timer.return_value


def test_rejects_empty_message():
    with pytest.raises(ValueError, match="cannot be empty"):
        schedule_reminder("  ", 10, print)


def test_rejects_invalid_delay():
    with pytest.raises(ValueError, match="at least one second"):
        schedule_reminder("stretch", 0, print)
