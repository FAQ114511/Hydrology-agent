from unittest.mock import patch

import requests

from tradingagents.dataflows.config import set_config
from tradingagents.dataflows.interface import route_to_vendor


set_config(
    {
        "tool_vendors": {
            "get_rainfall_forecast": "online_api,local_csv",
        },
        "weather_api_retries": 0,
        "weather_fallback_to_local": True,
        "weather_cache_dir": "runtime/cache/weather-route-test",
    }
)

with patch(
    "tradingagents.dataflows.weather_api.fetch_open_meteo_forecast",
    side_effect=requests.ConnectionError("offline"),
):
    result = route_to_vendor(
        "get_rainfall_forecast",
        "XIANGJIANG",
        "2024-05-10",
        "2024-05-12",
    )

print(result)
assert "虚拟模拟数据" in result
