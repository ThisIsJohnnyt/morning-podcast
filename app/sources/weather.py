"""Today's forecast from Open-Meteo (free, no key)."""
import httpx

WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "freezing fog", 51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    56: "freezing drizzle", 57: "heavy freezing drizzle", 61: "light rain", 63: "rain",
    65: "heavy rain", 66: "freezing rain", 67: "heavy freezing rain", 71: "light snow",
    73: "snow", 75: "heavy snow", 77: "snow grains", 80: "light showers", 81: "showers",
    82: "violent showers", 85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorms", 96: "thunderstorms with hail", 99: "severe thunderstorms with hail",
}


def get_weather(cfg: dict) -> dict:
    unit = cfg.get("temperature_unit", "fahrenheit")
    r = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": cfg["latitude"],
            "longitude": cfg["longitude"],
            "current": "temperature_2m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
            "temperature_unit": unit,
            "timezone": "auto",
            "forecast_days": 1,
        },
        timeout=15,
    )
    r.raise_for_status()
    d = r.json()
    daily, cur = d["daily"], d["current"]
    sym = "°F" if unit == "fahrenheit" else "°C"
    return {
        "city": cfg.get("city", ""),
        "now": f"{round(cur['temperature_2m'])}{sym}, {WEATHER_CODES.get(cur['weather_code'], 'unknown')}",
        "high": f"{round(daily['temperature_2m_max'][0])}{sym}",
        "low": f"{round(daily['temperature_2m_min'][0])}{sym}",
        "conditions": WEATHER_CODES.get(daily["weather_code"][0], "unknown"),
        "rain_chance": f"{daily['precipitation_probability_max'][0]}%",
    }


if __name__ == "__main__":
    from app.config import load_config
    print(get_weather(load_config()))
