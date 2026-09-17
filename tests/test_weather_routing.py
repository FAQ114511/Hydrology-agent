from unittest.mock import Mock, patch

from tradingagents.dataflows import interface
from tradingagents.dataflows.config import set_config


def test_online_success_is_used_before_local():
    online = Mock(return_value="ONLINE_WEATHER")
    local = Mock(return_value="LOCAL_WEATHER")
    set_config({"tool_vendors": {
        "get_rainfall_forecast": "online_api,local_csv"
    }})
    with patch.dict(interface.VENDOR_METHODS, {
        "get_rainfall_forecast": {
            "online_api": online, "local_csv": local
        }
    }):
        result = interface.route_to_vendor(
            "get_rainfall_forecast",
            "XIANGJIANG", "2026-09-14", "2026-09-16"
        )
    assert result == "ONLINE_WEATHER"
    online.assert_called_once()
    local.assert_not_called()


def test_online_failure_falls_back_to_local():
    online = Mock(side_effect=ConnectionError("down"))
    local = Mock(return_value="LOCAL_WEATHER")
    set_config({"tool_vendors": {
        "get_rainfall_forecast": "online_api,local_csv"
    }})
    with patch.dict(interface.VENDOR_METHODS, {
        "get_rainfall_forecast": {
            "online_api": online, "local_csv": local
        }
    }):
        result = interface.route_to_vendor(
            "get_rainfall_forecast",
            "XIANGJIANG", "2024-05-10", "2024-05-12"
        )
    assert result == "LOCAL_WEATHER"
    online.assert_called_once()
    local.assert_called_once()


def test_realtime_weather_has_no_local_fallback():
    assert list(interface.VENDOR_METHODS["get_realtime_weather"]) == ["online_api"]


def test_realtime_weather_online_failure_returns_prompt(tmp_path):
    import requests

    from tradingagents.dataflows import weather_api

    set_config({
        "tool_vendors": {"get_realtime_weather": "online_api"},
        "weather_api_retries": 0,
        "weather_cache_dir": str(tmp_path),
    })

    def boom(*args, **kwargs):
        raise requests.ConnectionError("down")

    with patch.object(weather_api.requests, "get", boom):
        result = interface.route_to_vendor(
            "get_realtime_weather",
            "XIANGJIANG",
            weather_api._now_cn().date().isoformat(),
        )

    assert "source: open_meteo_realtime" in result
    assert "暂不可用" in result
