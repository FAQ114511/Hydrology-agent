from unittest.mock import Mock, patch

import pytest
import requests

from tradingagents.dataflows.weather_api import (
    _fetch_with_retry,
    get_cached_or_fetch_forecast,
    normalize_forecast_payload,
    validate_forecast_payload,
)

PAYLOAD = {
    "daily": {
        "time": ["2026-09-12", "2026-09-13"],
        "precipitation_sum": [12.5, 30.0],
        "precipitation_probability_max": [60, 85],
    }
}

def test_normalize_fields():
    rows = normalize_forecast_payload("XIANGJIANG", PAYLOAD)
    assert rows[0]["station"] == "XIANGJIANG"
    assert rows[0]["source"] == "open_meteo"
    assert rows[0]["is_forecast"] is True

def test_rejects_missing_field():
    with pytest.raises(ValueError):
        validate_forecast_payload({"daily": {"time": []}})

def test_rejects_array_length_mismatch():
    bad = {"daily": {"time": ["2026-09-12"],
           "precipitation_sum": [],
           "precipitation_probability_max": [80]}}
    with pytest.raises(ValueError):
        validate_forecast_payload(bad)

def test_retries_connection_error():
    config = {"weather_api_retries": 2,
              "weather_retry_backoff_seconds": 0}
    with patch(
        "tradingagents.dataflows.weather_api.fetch_open_meteo_forecast",
        side_effect=requests.ConnectionError("down"),
    ) as fetch:
        with pytest.raises(RuntimeError):
            _fetch_with_retry(
                28.21, 112.98, "2026-09-12", "2026-09-13", config
            )
    assert fetch.call_count == 3

def test_writes_then_reads_cache(tmp_path):
    config = {
        "weather_api_retries": 0,
        "weather_cache_dir": str(tmp_path),
        "weather_cache_ttl_seconds": 900,
        "weather_fallback_to_local": False,
    }
    target = "tradingagents.dataflows.weather_api.fetch_open_meteo_forecast"
    with patch(target, return_value=PAYLOAD):
        online = get_cached_or_fetch_forecast(
            "XIANGJIANG", "2026-09-12", "2026-09-13", config
        )
    assert "在线 API" in online
    assert '"source": "open_meteo"' in online
    assert list(tmp_path.glob("*.json"))
    with patch(target, side_effect=requests.ConnectionError("down")):
        cached = get_cached_or_fetch_forecast(
            "XIANGJIANG", "2026-09-12", "2026-09-13", config
        )
    assert "有效缓存" in cached
    assert "open_meteo_cache" in cached
