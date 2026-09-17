from unittest.mock import patch

from requests import ConnectionError

from tradingagents.dataflows.weather_api import get_cached_or_fetch_forecast


config = {
    "weather_api_retries": 0,
    "weather_fallback_to_local": True,
    "weather_cache_dir": "runtime/cache/weather-test",
}

with patch(
    "tradingagents.dataflows.weather_api.fetch_open_meteo_forecast",
    side_effect=ConnectionError("模拟断网"),
):
    text = get_cached_or_fetch_forecast(
        "XIANGJIANG", "2024-05-10", "2024-05-12", config
    )

print(text)
assert "虚拟模拟数据" in text
