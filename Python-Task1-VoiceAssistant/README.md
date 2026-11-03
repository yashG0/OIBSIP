# Python Voice Assistant

A command assistant with voice and text modes. It can answer everyday questions, search the web, check live weather, set spoken reminders, send confirmed emails, and open user-configured shortcuts.

## Features

- Microphone input using SpeechRecognition, with ambient-noise calibration
- Spoken responses using pyttsx3; reminder notifications are spoken as well
- Text mode when microphone access or online speech recognition is unavailable
- Greeting, time, and date intents
- Flexible phrase parsing with NLTK stemming for common word variations
- Web searches opened in the default browser
- Weather lookup by city using OpenWeatherMap
- Timed reminders for seconds, minutes, or hours
- Email sending through SMTP with a read-back and explicit yes/no confirmation
- Offline question answers from the editable `config/knowledge.json`, with optional Gemini answers for questions not covered locally
- Website shortcuts configured in `config/commands.json`

## Requirements

- Python 3.15 or newer, as configured in `pyproject.toml`
- `uv` to install the project dependencies
- A microphone and speakers/headphones for voice mode
- Internet access for voice transcription, web searches, and enabled API integrations
- Optional OpenWeatherMap and Gemini API keys, plus SMTP settings for email

On Linux, PyAudio may require the system PortAudio development libraries before it can be installed.

## Setup

From this project folder, install dependencies:

```bash
uv sync
```

Copy `.env.example` to `.env` and fill in the services you plan to use:

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

Weather, Gemini, and email credentials are optional unless you use those features. `.env` is ignored by Git; never commit real credentials.

## Start the assistant

```bash
uv run python src/main.py
```

Choose **voice** or **text** mode at startup. If the microphone is unavailable or speech recognition cannot connect, the assistant switches to text mode.

## Example commands

- `Hello`
- `Could you tell me the current time?`
- `What's today's date?`
- `Search the web for beginner Python projects`
- `What's the weather like in Nagpur?`
- `Remind me to stretch in 10 minutes`
- `What is the largest planet?`
- `What is the capital of India?`
- `Send email to name@example.com subject Project update body The demo is ready`
- `Open GitHub`

For email, the assistant repeats the recipient and subject first. Say **yes** to send or **no** to cancel. You can also say an address as “name at example dot com.”

Add website shortcuts to `config/commands.json`. Add local fact aliases and answers to `config/knowledge.json`; those are answered locally first. If no local fact matches, the assistant uses Gemini when `GEMINI_API_KEY` is configured.

## Run the existing checks

```bash
uv run pytest
```

## Privacy and data handling

- In voice mode, recorded audio is sent to Google's speech recognition service through SpeechRecognition for transcription. Text mode does not send audio.
- Web search terms are placed in a Google Search URL and opened in your default browser.
- Weather queries send the requested city and API key to OpenWeatherMap.
- General questions not answered by the local knowledge file are sent to the configured Gemini model. The app requests stateless interactions (`store=False`), but Google’s unpaid API terms may still allow submitted content to be used to improve its services. Do not ask Gemini questions containing sensitive or confidential information.
- An email is sent only after explicit confirmation, through the SMTP server configured in `.env`.
- NLTK stemming and local knowledge matching run on the device; no language corpus is downloaded. Local answers do not require a Gemini request.
- Reminder timers exist only while the assistant is running. The application does not save a command history.
