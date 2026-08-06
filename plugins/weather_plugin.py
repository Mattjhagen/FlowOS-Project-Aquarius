import urllib.request
import json
from .base import Plugin


def _get_weather(location: str = "") -> str:
    try:
        loc = location.replace(" ", "+") if location else ""
        url = f"https://wttr.in/{loc}?format=j1"
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        current = data["current_condition"][0]
        area = data["nearest_area"][0]
        city = area["areaName"][0]["value"]
        country = area["country"][0]["value"]
        desc = current["weatherDesc"][0]["value"]
        temp_c = current["temp_C"]
        temp_f = current["temp_F"]
        humidity = current["humidity"]
        feels_c = current["FeelsLikeC"]
        wind_kmph = current["windspeedKmph"]
        return (
            f"{city}, {country}\n"
            f"{desc} — {temp_c}°C / {temp_f}°F (feels like {feels_c}°C)\n"
            f"Humidity: {humidity}%  Wind: {wind_kmph} km/h"
        )
    except Exception as e:
        return f"Could not fetch weather: {e}"


def _get_forecast(location: str = "") -> str:
    try:
        loc = location.replace(" ", "+") if location else ""
        url = f"https://wttr.in/{loc}?format=j1"
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        lines = []
        for day in data.get("weather", [])[:3]:
            date = day["date"]
            max_c = day["maxtempC"]
            min_c = day["mintempC"]
            desc = day["hourly"][4]["weatherDesc"][0]["value"]
            lines.append(f"{date}: {desc}, {min_c}–{max_c}°C")
        return "\n".join(lines)
    except Exception as e:
        return f"Could not fetch forecast: {e}"


class WeatherPlugin(Plugin):
    name = "weather"
    description = "Current weather and 3-day forecast for any location"

    @classmethod
    def tool_definitions(cls):
        return [
            {
                "name": "weather_now",
                "description": "Get current weather for a location",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City name or leave empty for auto-detect"}
                    }
                }
            },
            {
                "name": "weather_forecast",
                "description": "Get 3-day weather forecast for a location",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City name or leave empty for auto-detect"}
                    }
                }
            }
        ]

    @classmethod
    def tool_handlers(cls):
        return {
            "weather_now": lambda location="": _get_weather(location),
            "weather_forecast": lambda location="": _get_forecast(location),
        }
