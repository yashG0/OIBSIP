
import os
import smtplib
from email.message import EmailMessage


def send_email(recipient: str, subject: str, body: str) -> str:
    """Send an email using SMTP credentials from environment variables."""

    # Validate inputs first.
    if not recipient.strip() or not subject.strip() or not body.strip():
        return "Recipient, subject, and message must not be empty."

    # Read SMTP configuration.
    host = os.getenv("SMTP_HOST", "")
    port = os.getenv("SMTP_PORT", "587")
    username = os.getenv("SMTP_USERNAME", "")
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM") or username

    if not all((host, username, password, sender, port)):
        return "Email is not configured. Set the SMTP environment variables."

    try:
        message = EmailMessage()
        message["From"] = sender
        message["To"] = recipient.strip()
        message["Subject"] = subject.strip()
        message.set_content(body.strip())

        with smtplib.SMTP(host, int(port), timeout=15) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(message)

        return f"Email sent to {recipient.strip()}."

    except (OSError, ValueError, smtplib.SMTPException):
        return "Email could not be sent. Check the SMTP settings and try again."
