# Python Voice Assistant

A Python desktop assistant with voice and text modes. Ask common questions, search the web, check the weather, set reminders, send confirmed emails, or open configured website shortcuts.

## Features

- Voice input through SpeechRecognition with ambient-noise calibration
- Spoken responses through pyttsx3, using a feminine English voice variant when the local speech engine supports it
- Text mode if no microphone is available or speech recognition cannot connect
- Natural-language commands for greetings, date, and time
- Flexible phrase matching with NLTK stemming
- Web searches opened in the default browser
- Current weather by city using OpenWeatherMap
- Timed reminders, including spoken notifications
- Email through SMTP after the assistant reads back the recipient and subject and receives explicit confirmation
- Local question answers from config/knowledge.json, with optional Gemini answers for unmatched questions
- Website shortcuts maintained in config/commands.json

## Requirements

- Python 3.15 or newer, as configured in pyproject.toml
- [uv](https://docs.astral.sh/uv/) for dependency management
- Microphone and speakers or headphones for voice mode
- Internet for speech transcription, web search, and enabled API integrations
- Optional OpenWeatherMap and Gemini API keys; SMTP settings are needed only for email

On Linux, PyAudio may require PortAudio development libraries.

## Setup

From this project folder, install dependencies:

```bash
uv sync
```

Copy .env.example to .env and add credentials for the features you want:

```env
OPENWEATHERMAP_API_KEY=your_openweathermap_key
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash-lite
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your_email@example.com
SMTP_PASSWORD=your_smtp_or_app_password
SMTP_FROM=your_email@example.com
```

All keys and mail settings are optional until you use the corresponding feature. .env is ignored by Git; never commit real credentials.

## Run

```bash
uv run python src/main.py
```

Choose voice or text mode at startup. Voice mode needs a working microphone and an internet connection for Google speech transcription. If either is unavailable, the assistant falls back to text mode.

## Example commands

- Hello
- What time is it?
- What's today's date?
- Search the web for beginner Python projects
- What's the weather like in Nagpur?
- Remind me to stretch in 10 minutes
- What is the largest planet?
- Send email to name@example.com subject Project update body The demo is ready
- Open GitHub

The assistant asks for explicit confirmation before sending an email. You can add website shortcuts in config/commands.json and local facts in config/knowledge.json. Gemini is used for general questions only when no local answer matches and GEMINI_API_KEY is configured.

## Tests

```bash
uv run pytest
```

## Privacy

- Voice transcription sends recorded audio to Google's speech recognition service. Text mode does not send audio.
- Weather lookups send the requested city and API key to OpenWeatherMap.
- Unmatched general questions are sent to the configured Gemini model. The app requests stateless interactions, but avoid sending sensitive or confidential information.
- Email is sent through the SMTP server in .env only after explicit confirmation.
- Spoken output uses the local speech engine. Reminders exist only while the assistant is running; the app does not save command history.
