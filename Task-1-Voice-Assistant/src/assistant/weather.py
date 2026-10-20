import os

import requests
from dotenv import load_dotenv

API_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_weather(city: str) -> str:
    """Fetch current weather for a city using OpenWeatherMap."""
    load_dotenv()

    api_key = os.getenv("OPENWEATHERMAP_API_KEY")

    if not api_key:
        return (
            "Weather is not configured yet. Set the "
            "OPENWEATHERMAP_API_KEY environment variable."
        )

    if not city.strip():
        return "Please provide a city name."

    try:
        response = requests.get(
            API_URL,
            params={
                "q": city.strip(),
                "appid": api_key,
                "units": "metric",
            },
            timeout=10,
        )

        if response.status_code == 404:
            return f"I couldn't find the city {city.strip()}."

        response.raise_for_status()
        data = response.json()

        description = data["weather"][0]["description"].capitalize()
        temperature = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]

        return (
            f"Weather in {data['name']}: {description}. "
            f"Temperature: {temperature:.1f}°C, "
            f"feels like {feels_like:.1f}°C, "
            f"humidity {humidity}%."
        )

    except requests.RequestException:
        return "I couldn't retrieve weather information. Please try again."
    except KeyError, IndexError, TypeError, ValueError:
        return "The weather service returned an unexpected response."
