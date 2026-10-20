
from unittest.mock import MagicMock, patch

from assistant.email_sender import send_email


def test_email_requires_configuration():
    with patch.dict("os.environ", {}, clear=True):
        result = send_email("yashgaurkar0@gmail.com", "Test", "Hello")

    assert "not configured" in result


def test_email_rejects_empty_fields():
    result = send_email("", "Test", "Hello")

    assert "must not be empty" in result


@patch("assistant.email_sender.smtplib.SMTP")
def test_email_sends_message(mock_smtp):
    server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = server

    settings = {
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "sender@example.com",
        "SMTP_PASSWORD": "test-password",
        "SMTP_FROM": "sender@example.com",
    }

    with patch.dict("os.environ", settings, clear=True):
        result = send_email("recipient@example.com", "Test", "Hello")

    assert result == "Email sent to recipient@example.com."
    server.starttls.assert_called_once()
    server.login.assert_called_once_with(
        "sender@example.com",
        "test-password",
    )
    server.send_message.assert_called_once()
