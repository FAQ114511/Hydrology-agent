import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
import requests

from tradingagents.dataflows import weather_api

NOW = datetime(2026, 9, 15, 11, 30, tzinfo=weather_api.CN_TZ)
SERIES_START = datetime(2026, 9, 8, 0, 0)


def build_payload():
    """构造 10 天逐小时序列（过去 7 天 + 未来 3 天），每小时降雨固定 1.0mm。"""
    times, rainfall, probability, soil = [], [], [], []
    for hour in range(24 * 10):
        times.append((SERIES_START + timedelta(hours=hour)).strftime("%Y-%m-%dT%H:%M"))
        rainfall.append(1.0)
        probability.append(80)
        soil.append(round(0.15 + hour * 0.001, 4))
    return {
        "current": {"time": "2026-09-15T11:30", "precipitation": 1.5, "rain": 1.5},
        "hourly": {
            "time": times,
            "precipitation": rainfall,
            "precipitation_probability": probability,
            "soil_moisture_0_to_7cm": soil,
        },
    }


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_normalize_splits_past_and_future_windows():
    snapshot = weather_api.normalize_realtime_payload("XIANGJIANG", build_payload(), NOW)

    assert snapshot["observed_at"] == "2026-09-15T11:30"
    assert snapshot["current_rainfall_mm"] == 1.5
    assert snapshot["past_24h_rainfall_mm"] == 24.0
    assert snapshot["past_72h_rainfall_mm"] == 72.0
    assert snapshot["past_7d_rainfall_mm"] == 168.0
    assert snapshot["forecast_24h_rainfall_mm"] == 24.0
    assert snapshot["forecast_48h_rainfall_mm"] == 48.0
    assert snapshot["source"] == "open_meteo_realtime"


def test_normalize_builds_daily_and_hourly_sections():
    snapshot = weather_api.normalize_realtime_payload("XIANGJIANG", build_payload(), NOW)

    assert len(snapshot["daily"]) == 8
    assert snapshot["daily"][0]["date"] == "2026-09-08"
    assert snapshot["daily"][0]["rainfall_mm"] == 24.0
    assert snapshot["daily"][-1]["date"] == "2026-09-15"
    assert snapshot["daily"][-1]["rainfall_mm"] == 12.0
    assert snapshot["daily"][-1]["max_hourly_mm"] == 1.0

    assert len(snapshot["hourly"]) == 48
    assert snapshot["hourly"][0]["time"] == "2026-09-15T12:00"
    assert snapshot["hourly"][-1]["time"] == "2026-09-17T11:00"


def test_normalize_reports_soil_moisture_trend():
    snapshot = weather_api.normalize_realtime_payload("XIANGJIANG", build_payload(), NOW)

    assert snapshot["soil_moisture_0_to_7cm"] == 0.329
    assert snapshot["soil_moisture_24h_change"] == 0.024


def _write_cache(tmp_path, fetched_at):
    path = tmp_path / "realtime_XIANGJIANG.json"
    path.write_text(
        json.dumps({
            "fetched_at": fetched_at,
            "station": "XIANGJIANG",
            "source": "open_meteo_realtime",
            "payload": build_payload(),
        }),
        encoding="utf-8",
    )


def test_valid_cache_is_used_without_network(tmp_path):
    cfg = {"weather_cache_dir": str(tmp_path), "weather_cache_ttl_seconds": 900}
    _write_cache(tmp_path, datetime.now(weather_api.timezone.utc).isoformat())

    def boom(*args, **kwargs):
        raise AssertionError("缓存命中时不应发起网络请求")

    with patch.object(weather_api.requests, "get", boom), patch.object(weather_api, "_now_cn", lambda: NOW):
        text = weather_api.get_online_realtime_weather("XIANGJIANG", "2026-09-15", cfg)

    assert "过去 24 小时累积降雨：24.0 mm" in text
    assert "未来 48 小时预报降雨：48.0 mm" in text


def test_expired_cache_triggers_refetch(tmp_path):
    cfg = {"weather_cache_dir": str(tmp_path), "weather_cache_ttl_seconds": 900, "weather_api_retries": 0}
    _write_cache(tmp_path, (datetime.now(weather_api.timezone.utc) - timedelta(seconds=3600)).isoformat())

    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        return FakeResponse(build_payload())

    with patch.object(weather_api.requests, "get", fake_get), patch.object(weather_api, "_now_cn", lambda: NOW):
        text = weather_api.get_online_realtime_weather("XIANGJIANG", "2026-09-15", cfg)

    assert len(calls) == 1
    assert calls[0]["past_days"] == 7
    assert calls[0]["forecast_days"] == 3
    assert "未来 48 小时预报降雨：48.0 mm" in text


def test_online_failure_without_cache_returns_prompt(tmp_path):
    cfg = {"weather_cache_dir": str(tmp_path), "weather_api_retries": 0}

    def boom(*args, **kwargs):
        raise requests.ConnectionError("down")

    with patch.object(weather_api.requests, "get", boom), patch.object(weather_api, "_now_cn", lambda: NOW):
        text = weather_api.get_online_realtime_weather("XIANGJIANG", "2026-09-15", cfg)

    assert "source: open_meteo_realtime" in text
    assert "暂不可用" in text
    assert "24.0 mm" not in text


def test_historical_date_is_rejected(tmp_path):
    cfg = {"weather_cache_dir": str(tmp_path)}

    with patch.object(weather_api, "_now_cn", lambda: NOW):
        text = weather_api.get_online_realtime_weather("XIANGJIANG", "2024-05-10", cfg)

    assert "source: open_meteo_realtime" in text
    assert "历史日期" in text


def test_station_without_coordinates_raises(tmp_path):
    stations = tmp_path / "stations.json"
    stations.write_text(json.dumps({"BAD": {"station_name": "缺经纬度站"}}), encoding="utf-8")
    cfg = {"stations_path": str(stations), "weather_cache_dir": str(tmp_path / "cache")}

    with patch.object(weather_api, "_now_cn", lambda: NOW), pytest.raises(ValueError, match="缺少有效经纬度"):
        weather_api.get_online_realtime_weather("BAD", "2026-09-15", cfg)
