from unittest.mock import Mock, patch

import pytest
import requests
from weather_app.api import (
    WeatherAPIError,
    get_current_weather,
    get_forecast,
)


@pytest.fixture
def current_response():
    return {
        "name": "Nagpur",
        "sys": {"country": "IN"},
        "main": {"temp": 30.0, "feels_like": 32.0, "humidity": 45},
        "weather": [{"description": "clear sky", "icon": "01d"}],
        "wind": {"speed": 3.5},
    }


def test_empty_city_is_rejected():
    with pytest.raises(WeatherAPIError, match="Enter a city"):
        get_current_weather("  ")


def test_missing_api_key():
    with patch.dict("os.environ", {}, clear=True):
        with patch("weather_app.api.requests.get") as mock_get:
            with pytest.raises(WeatherAPIError, match="Missing"):
                get_current_weather("Nagpur")
    mock_get.assert_not_called()


@patch("weather_app.api.requests.get")
def test_current_weather_parsing(mock_get, current_response):
    response = Mock()
    response.status_code = 200
    response.json.return_value = current_response
    response.raise_for_status.return_value = None
    mock_get.return_value = response

    with patch.dict("os.environ", {"OPENWEATHERMAP_API_KEY": "test-key"}):
        result = get_current_weather("Nagpur")

    assert result["city"] == "Nagpur"
    assert result["temperature_c"] == 30.0
    assert result["temperature_f"] == pytest.approx(86.0)
    assert result["humidity"] == 45
    assert result["description"] == "Clear sky"


@patch("weather_app.api.requests.get", side_effect=requests.Timeout)
def test_timeout_is_handled(mock_get):
    with patch.dict("os.environ", {"OPENWEATHERMAP_API_KEY": "test-key"}):
        with pytest.raises(WeatherAPIError, match="timed out"):
            get_current_weather("Nagpur")


@patch("weather_app.api.requests.get")
def test_unknown_city(mock_get):
    response = Mock()
    response.status_code = 404
    mock_get.return_value = response

    with patch.dict("os.environ", {"OPENWEATHERMAP_API_KEY": "test-key"}):
        with pytest.raises(WeatherAPIError, match="Location not found"):
            get_current_weather("DefinitelyNotARealCity")


@patch("weather_app.api.requests.get")
def test_forecast_parsing(mock_get):
    response = Mock()
    response.status_code = 200
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "list": [
            {
                "dt_txt": f"2026-10-{day:02d} {hour:02d}:00:00",
                "main": {"temp": 25.0, "temp_min": 20.0, "temp_max": 28.0},
                "weather": [{"description": "few clouds", "icon": "02d"}],
            }
            for day in range(21, 27)
            for hour in (9, 12, 15)
        ]
    }
    mock_get.return_value = response

    with patch.dict("os.environ", {"OPENWEATHERMAP_API_KEY": "test-key"}):
        result = get_forecast("Nagpur")

    assert len(result["hourly"]) == 2
    assert len(result["daily"]) == 5
    assert result["daily"][0]["temperature_min_c"] == 20.0
