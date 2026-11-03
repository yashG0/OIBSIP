import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.openweathermap.org/data/2.5"
ICON_URL = "https://openweathermap.org/img/wn/{icon}@2x.png"


class WeatherAPIError(Exception):
    """Raised when weather data cannot be retrieved."""


def _get_json(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("OPENWEATHERMAP_API_KEY", "").strip()
    if not api_key:
        raise WeatherAPIError("Missing OpenWeatherMap API key.")

    try:
        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            params={**params, "appid": api_key},
            timeout=10,
        )

        if response.status_code == 401:
            raise WeatherAPIError("Invalid API key.")
        if response.status_code == 404:
            raise WeatherAPIError("Location not found.")

        response.raise_for_status()
        return response.json()
    except requests.Timeout as exc:
        raise WeatherAPIError("Weather request timed out.") from exc
    except requests.HTTPError as exc:
        raise WeatherAPIError("Weather service returned an error.") from exc
    except requests.RequestException as exc:
        raise WeatherAPIError("Could not connect to the weather service.") from exc
    except ValueError as exc:
        raise WeatherAPIError("Weather service returned invalid JSON.") from exc


def get_current_weather(city: str) -> dict[str, Any]:
    city = city.strip()
    if not city:
        raise WeatherAPIError("Enter a city name or ZIP code.")

    data = _get_json("weather", {"q": city, "units": "metric"})
    condition = data["weather"][0]
    temp_c = data["main"]["temp"]

    return {
        "city": data.get("name", city),
        "country": data.get("sys", {}).get("country", ""),
        "temperature_c": temp_c,
        "temperature_f": temp_c * 9 / 5 + 32,
        "feels_like_c": data["main"]["feels_like"],
        "humidity": data["main"]["humidity"],
        "description": condition["description"].capitalize(),
        "icon_url": ICON_URL.format(icon=condition["icon"]),
        "wind_speed": data.get("wind", {}).get("speed", 0),
    }


def get_forecast(city: str) -> dict[str, list[dict[str, Any]]]:
    city = city.strip()
    if not city:
        raise WeatherAPIError("Enter a city name or ZIP code.")

    data = _get_json("forecast", {"q": city, "units": "metric"})
    entries = data.get("list", [])

    hourly = [
        {
            "time": item["dt_txt"],
            "temperature_c": item["main"]["temp"],
            "description": item["weather"][0]["description"].capitalize(),
            "icon_url": ICON_URL.format(icon=item["weather"][0]["icon"]),
        }
        for item in entries[:2]
    ]

    # The free forecast endpoint provides 3-hour intervals.
    by_day: dict[str, list[dict[str, Any]]] = {}
    for item in entries:
        by_day.setdefault(item["dt_txt"][:10], []).append(item)

    daily = []
    for day, items in by_day.items():
        representative = min(
            items,
            key=lambda item: abs(int(item["dt_txt"][11:13]) - 12),
        )
        daily.append(
            {
                "date": day,
                "temperature_min_c": min(x["main"]["temp_min"] for x in items),
                "temperature_max_c": max(x["main"]["temp_max"] for x in items),
                "description": representative["weather"][0]["description"].capitalize(),
                "icon_url": ICON_URL.format(icon=representative["weather"][0]["icon"]),
            }
        )
        if len(daily) == 5:
            break

    return {"hourly": hourly, "daily": daily}
