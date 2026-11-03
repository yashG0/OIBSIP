"""Intent routing and command actions for the voice assistant."""

from __future__ import annotations

import json
import re
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

from assistant.email_sender import send_email
from assistant.gemini import answer_with_gemini
from assistant.knowledge import answer_question
from assistant.nlu import intent_tokens
from assistant.reminders import schedule_reminder
from assistant.weather import get_weather

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "commands.json"
EMAIL_PATTERN = re.compile(
    r"\bsend(?:\s+an?)?\s+email\s+to\s+"
    r"(?P<recipient>[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})"
    r"(?:\s+(?:with\s+)?subject\s+(?P<subject>.*?))?"
    r"(?:\s+(?:body|message|saying)\s+(?P<body>.+))?\s*$",
    re.IGNORECASE,
)
EMAIL_ABOUT_PATTERN = re.compile(
    r"\bemail\s+(?P<recipient>[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})"
    r"\s+about\s+(?P<subject>[^:]+):\s*(?P<body>.+)$",
    re.IGNORECASE,
)
REMINDER_PATTERN = re.compile(
    r"\bremind\s+me\s+to\s+(?P<message>.+?)\s+in\s+"
    r"(?P<amount>\d+)\s*(?P<unit>seconds?|minutes?|hours?)\b",
    re.IGNORECASE,
)
REMINDER_ALT_PATTERN = re.compile(
    r"\bset\s+(?:a\s+)?reminder\s+to\s+(?P<message>.+?)\s+in\s+"
    r"(?P<amount>\d+)\s*(?P<unit>seconds?|minutes?|hours?)\b",
    re.IGNORECASE,
)
SEARCH_PATTERNS = (
    re.compile(
        r"^(?:(?:can|could|would)\s+you\s+)?(?:please\s+)?"
        r"search(?:\s+the)?(?:\s+web)?(?:\s+(?:for|about))?\s+(.+)$",
        re.I,
    ),
    re.compile(r"^(?:(?:can|could|would)\s+you\s+)?(?:please\s+)?google\s+(.+)$", re.I),
    re.compile(r"^(?:(?:can|could|would)\s+you\s+)?(?:please\s+)?look\s+up\s+(.+)$", re.I),
    re.compile(r"^(?:(?:can|could|would)\s+you\s+)?(?:please\s+)?find(?:\s+me)?\s+(.+)$", re.I),
)
STOP_WORDS = {
    "a", "an", "and", "are", "can", "could", "do", "does", "for", "from",
    "give", "hey", "hi", "hello", "i", "is", "it", "me", "of", "please",
    "tell", "that", "the", "to", "what", "whats", "when", "where", "who",
    "why", "would", "you", "your",
}


def normalize_text(text: str) -> str:
    """Normalize speech-recognition output without losing searchable slot text."""
    text = text.casefold().replace("’", "'")
    return " ".join(re.findall(r"[\w@.+'-]+", text, flags=re.UNICODE)).strip()


def load_custom_commands() -> dict[str, dict[str, str]]:
    """Load safe, user-configured website shortcuts."""
    try:
        with CONFIG_PATH.open(encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (OSError, json.JSONDecodeError):
        return {}

    entries = config.get("commands", {}) if isinstance(config, dict) else {}
    if not isinstance(entries, dict):
        return {}
    return {
        " ".join(name.casefold().split()): details
        for name, details in entries.items()
        if isinstance(name, str)
        and isinstance(details, dict)
        and isinstance(details.get("response"), str)
        and isinstance(details.get("url"), str)
        and details["url"].startswith(("https://", "http://"))
    }


def _email_fields(command: str) -> dict[str, str] | None:
    spoken_email = re.sub(
        r"\b([a-z0-9._%+-]+)\s+at\s+([a-z0-9.-]+)\s+dot\s+([a-z]{2,})\b",
        r"\1@\2.\3",
        command,
        flags=re.IGNORECASE,
    )
    match = EMAIL_PATTERN.search(spoken_email)
    if not match:
        match = EMAIL_ABOUT_PATTERN.search(spoken_email)
    if not match:
        return None
    fields = {key: (value or "").strip(" .,:;") for key, value in match.groupdict().items()}
    if fields.get("recipient") and fields.get("subject") and fields.get("body"):
        return fields
    return None


class CommandProcessor:
    """Route flexible natural-language commands and retain confirmation state."""

    def __init__(self, on_reminder=None) -> None:
        self.on_reminder = on_reminder or (lambda text: print(f"\nAssistant: {text}"))
        self.pending_email: dict[str, str] | None = None

    def handle(self, command: str) -> tuple[str, bool]:
        normalized = normalize_text(command)
        if not normalized:
            return "I didn't catch that. Please try again.", True

        if self.pending_email is not None:
            if normalized in {"yes", "yes please", "yes send it", "confirm", "confirm send"}:
                email = self.pending_email
                self.pending_email = None
                return send_email(**email), True
            if normalized in {"no", "cancel", "don't send", "do not send"}:
                self.pending_email = None
                return "Email cancelled.", True
            return "Please say yes to send the email, or no to cancel it.", True

        words = normalized.split()
        intent_words = intent_tokens(command)
        first_word = words[0]

        if first_word in {"hello", "hi", "hey", "greetings"} and len(words) <= 2:
            return "Hello! How can I help you?", True
        if normalized in {"good morning", "good afternoon", "good evening"}:
            return f"{normalized.title()}! How can I help you?", True
        if normalized in {"exit", "quit", "stop", "goodbye", "bye", "close assistant"}:
            return "Goodbye!", False
        if normalized in {"help", "what can you do", "show commands"}:
            return (
                "I can greet you, tell the time or date, search the web, check weather, "
                "set reminders, send confirmed emails, open saved shortcuts, and answer "
                "facts from my local knowledge base.",
                True,
            )

        custom = load_custom_commands().get(normalized)
        if custom:
            try:
                webbrowser.open(custom["url"])
                return custom["response"], True
            except webbrowser.Error:
                return "I couldn't open that website.", True

        asks_for_time = bool({"what", "tell", "current", "know", "show", "give", "check", "now"}.intersection(intent_words))
        if {"time", "clock"}.intersection(intent_words) and (asks_for_time or len(words) <= 2):
            current_time = datetime.now().strftime("%I:%M %p").lstrip("0")
            return f"The current time is {current_time}.", True
        asks_for_date = bool({"what", "tell", "current", "today", "date", "know", "show", "give", "check"}.intersection(intent_words))
        if {"date", "today", "day"}.intersection(intent_words) and asks_for_date:
            current_date = datetime.now().strftime("%A, %d %B %Y")
            return f"Today is {current_date}.", True

        email = _email_fields(command)
        if email:
            self.pending_email = email
            return (
                f"I’m ready to email {email['recipient']} with subject "
                f"'{email['subject']}'. Say yes to send or no to cancel.",
                True,
            )
        if "email" in intent_words:
            return (
                "Say: send email to name@example.com subject Hello body Your message. "
                "I’ll read back the details and ask before sending.",
                True,
            )

        reminder_match = REMINDER_PATTERN.search(command) or REMINDER_ALT_PATTERN.search(command)
        if reminder_match:
            message = reminder_match.group("message").strip(" .,!?")
            amount = int(reminder_match.group("amount"))
            unit = reminder_match.group("unit").casefold().rstrip("s")
            multipliers = {"second": 1, "minute": 60, "hour": 3600}
            if not message or amount < 1:
                return "Please give me a reminder message and a positive delay.", True
            schedule_reminder(
                message,
                amount * multipliers[unit],
                self.on_reminder,
            )
            return f"Reminder set: {message}, in {amount} {unit}{'s' if amount != 1 else ''}.", True
        if {"remind", "reminder"}.intersection(intent_words):
            return "Try: remind me to stretch in 30 seconds.", True

        search_query = self._search_query(command)
        if search_query:
            search_url = "https://www.google.com/search?q=" + quote_plus(search_query)
            try:
                webbrowser.open(search_url)
                return f"Searching the web for {search_query}.", True
            except webbrowser.Error:
                return "I couldn't open the web browser.", True

        if "weather" in intent_words:
            city = self._weather_city(command)
            if not city:
                return "Tell me a city, for example: what's the weather in Nagpur?", True
            return get_weather(city), True

        if self._looks_like_question(normalized):
            answer = answer_question(command)
            if answer:
                return answer, True
            try:
                return answer_with_gemini(command), True
            except RuntimeError as error:
                return str(error), True

        return "Sorry, I don't know that command yet. Try asking me a question or say help.", True

    @staticmethod
    def _search_query(command: str) -> str:
        cleaned = command.strip().rstrip("?.!")
        for pattern in SEARCH_PATTERNS:
            match = pattern.match(cleaned)
            if match and match.group(1).strip():
                return re.sub(r"^(?:for|about)\s+", "", match.group(1).strip(), flags=re.I)
        return ""

    @staticmethod
    def _weather_city(command: str) -> str:
        match = re.search(r"\bweather\s+(?:like\s+)?(?:in|for|at)\s+(.+)$", command, re.I)
        if match:
            city = match.group(1).strip(" .,!?")
            return re.sub(r"\s+(?:today|tonight|tomorrow)$", "", city, flags=re.I)
        match = re.search(r"\b(?:in|for|at)\s+(.+?)\s+(?:weather|today)", command, re.I)
        return match.group(1).strip(" .,!?") if match else ""

    @staticmethod
    def _looks_like_question(normalized: str) -> bool:
        question_stems = {"what", "who", "where", "why", "how", "which", "tell"}
        return bool(question_stems.intersection(intent_tokens(normalized)))


def handle_command(command: str) -> tuple[str, bool]:
    """Convenience wrapper retained for callers and simple command tests."""
    return CommandProcessor().handle(command)
