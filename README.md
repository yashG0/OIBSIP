# Oasis Infobyte Python Projects

This repository contains completed projects developed for the Oasis Infobyte Python Programming Internship (OIBSIP). Each project is self-contained and has its own dependencies, setup instructions, and tests.

## Projects

| Internship task | Project | Description | Status |
|---|---|---|---|
| Task 1 | [Python Voice Assistant](Python-Task1-VoiceAssistant/README.md) | Voice and text assistant with reminders, weather, web search, email, and optional Gemini answers. | Complete |
| Task 4 | [Atmos Weather](Python-Task4-BasicWeatherApp/README.md) | PyQt5 desktop weather app with current conditions and short-term and five-day forecasts. | Complete |
| Task 5 | [Relay Chat](Python-Task5-ChatApplication/README.md) | GTK4/libadwaita desktop chat with accounts, public rooms, and invite-only private rooms. | Complete |

## Quick start

Choose a project folder and follow its README. Each project manages dependencies independently with [uv](https://docs.astral.sh/uv/).

For example, to start Atmos:

```bash
cd Python-Task4-BasicWeatherApp
uv sync
# Add OPENWEATHERMAP_API_KEY to your environment, then:
uv run python src/main.py
```

The Voice Assistant and Atmos need optional service credentials for some features. Relay requires a Linux desktop with GTK4, libadwaita, and PyGObject. Their READMEs explain the full setup and privacy details.

## Repository layout

```text
OIBSIP/
├── Python-Task1-VoiceAssistant/
├── Python-Task4-BasicWeatherApp/
└── Python-Task5-ChatApplication/
```

## Tests

Run tests from the project folder being checked:

```bash
uv run pytest
```

Relay's README also provides its test command and environment notes.
