# Atmos — Weather

Atmos is a desktop weather application built with Python and PyQt5. Search by city or ZIP code to see current conditions, upcoming forecast periods, and a five-day outlook in a clean dark interface.

## Features

- Current temperature, feels-like temperature, humidity, wind speed, condition, and weather icon
- Upcoming forecast periods from the three-hour forecast feed
- Five-day daily high and low temperatures
- Celsius and Fahrenheit display
- City or ZIP code search
- Clear in-app messages for missing or invalid API keys, unknown locations, and network errors
- Weather requests run in a background thread so the interface remains responsive

## Requirements

- Python 3.15 or newer, as configured in pyproject.toml
- An OpenWeatherMap API key
- [uv](https://docs.astral.sh/uv/) or pip

## Setup

From this project folder, install dependencies:

```bash
uv sync
```

Create a .env file in the project folder and add your API key:

```env
OPENWEATHERMAP_API_KEY=your_api_key_here
```

Keep .env private and do not commit or share the key. The app reads it locally when making requests.

## Run

```bash
uv run python src/main.py
```

Enter a city or ZIP code and select **Get weather** or press Enter. Use the temperature control to switch between Celsius and Fahrenheit.

## Tests

```bash
uv run pytest
```

## Project structure

```text
src/
├── main.py
└── weather_app/
    ├── api.py       # OpenWeatherMap requests and response parsing
    └── gui.py       # PyQt5 interface
tests/
└── test_api.py
```

## Privacy

Atmos sends the city or ZIP code and API key to OpenWeatherMap to retrieve weather data. Searches are not saved, and the app does not create an account.
