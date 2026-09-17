"""Open-Meteo adapter for hydrological forecast data."""

from __future__ import annotations
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATIONS = PROJECT_ROOT / "runtime" / "knowledge" / "stations.json"
DEFAULT_URL = "https://api.open-meteo.com/v1/forecast"

def _date(value: str) -> str:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"日期必须是 yyyy-mm-dd：{value!r}") from exc

def _path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()

def load_station_coordinates(station: str, config: dict[str, Any] | None = None) -> tuple[float, float]:
    """Read and validate latitude/longitude from stations.json."""
    code = (station or "").strip().upper()
    if not code:
        raise ValueError("station 不能为空")
    cfg = config or {}
    filename = _path(cfg.get("stations_path", DEFAULT_STATIONS))
    if not filename.exists():
        raise FileNotFoundError(f"站点文件不存在：{filename}")
    data = json.loads(filename.read_text(encoding="utf-8"))
    meta = data.get(code)
    if not isinstance(meta, dict):
        raise KeyError(f"stations.json 中没有站点：{code}")
    try:
        latitude = float(meta["latitude"])
        longitude = float(meta["longitude"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"站点 {code} 缺少有效经纬度") from exc
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError(f"站点 {code} 的经纬度超出范围")
    return latitude, longitude

def fetch_open_meteo_forecast(latitude: float, longitude: float, start_date: str, end_date: str, timeout: int = 10, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fetch raw daily rainfall forecast JSON. Retries/cache are next step."""
    start, end = _date(start_date), _date(end_date)
    if start > end:
        raise ValueError("start_date 不能晚于 end_date")
    cfg = config or {}
    response = requests.get(cfg.get("weather_api_base_url", DEFAULT_URL), params={"latitude": latitude, "longitude": longitude, "daily": "precipitation_sum,precipitation_probability_max", "timezone": "Asia/Shanghai", "start_date": start, "end_date": end}, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("天气 API 顶层返回值必须是对象")
    return payload

def validate_forecast_payload(payload: dict[str, Any]) -> None:
    """Check required daily arrays and matching lengths."""
    daily = payload.get("daily") if isinstance(payload, dict) else None
    required = ("time", "precipitation_sum", "precipitation_probability_max")
    if not isinstance(daily, dict):
        raise ValueError("forecast payload 缺少 daily 对象")
    missing = [key for key in required if key not in daily]
    if missing:
        raise ValueError(f"forecast payload 缺少字段：{', '.join(missing)}")
    if any(not isinstance(daily[key], list) for key in required):
        raise ValueError("forecast payload 的 daily 字段必须是数组")
    lengths = [len(daily[key]) for key in required]
    if len(set(lengths)) != 1:
        raise ValueError(f"forecast payload 数组长度不一致：{lengths}")


def normalize_forecast_payload(station: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert provider fields to stable project fields."""
    validate_forecast_payload(payload)
    daily = payload["daily"]
    issued_at = datetime.now(timezone.utc).isoformat()
    return [{"station": station.strip().upper(), 
    "valid_date": _date(valid_date),
     "forecast_rainfall_mm": rainfall, 
     "rain_probability_pct": probability,
      "issued_at": issued_at, 
      "source": "open_meteo", "is_forecast": True} for
       valid_date, rainfall, probability in zip(daily["time"], 
       daily["precipitation_sum"], daily["precipitation_probability_max"])]

def get_online_rainfall_forecast(
    station: str, start_date: str, end_date: str
) -> str:
    """Use global project config and run online/cache/local fallback."""
    from .config import get_config

    return get_cached_or_fetch_forecast(
        station, start_date, end_date, get_config()
    )

def get_online_weather_warning(station: str, curr_date: str, config: dict[str, Any] | None = None) -> str:
    """State that Open-Meteo does not provide official warning levels."""
    _date(curr_date)
    code = (station or "").strip().upper()
    if not code:
        raise ValueError("station 不能为空")
    return (f"## 气象预警（{code}）\n\n" + "source: open_meteo\n" + "官方预警等级：未提供。Open-Meteo 不等同于主管部门发布的红、橙、黄、蓝预警。\n" + "模型规则结果：未在本函数计算，请由项目规则模块单独标注。")


def _cache_path(station: str, start_date: str, end_date: str, config: dict[str, Any]) -> Path:
    cache_dir = _path(config.get("weather_cache_dir", PROJECT_ROOT / "runtime" / "cache" / "weather"))
    safe_station = station.strip().upper().replace("/", "_")
    return cache_dir / f"{safe_station}_{_date(start_date)}_{_date(end_date)}.json"


def _read_valid_cache(station: str, start_date: str, end_date: str, config: dict[str, Any]) -> dict[str, Any] | None:
    path = _cache_path(station, start_date, end_date, config)
    if not path.exists():
        return None
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
        fetched_at = datetime.fromisoformat(envelope["fetched_at"])
        age = (datetime.now(timezone.utc) - fetched_at).total_seconds()
        ttl = int(config.get("weather_cache_ttl_seconds", 900))
        if age < 0 or age > ttl:
            return None
        payload = envelope["payload"]
        validate_forecast_payload(payload)
        return envelope
    except (OSError, KeyError, TypeError, ValueError):
        return None


def _write_cache(station: str, start_date: str, end_date: str, payload: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    fetched_at = datetime.now(timezone.utc).isoformat()
    envelope = {
        "fetched_at": fetched_at,
        "station": station.strip().upper(),
        "start_date": _date(start_date),
        "end_date": _date(end_date),
        "source": "open_meteo",
        "payload": payload,
    }
    path = _cache_path(station, start_date, end_date, config)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")
    return envelope


def _fetch_with_retry(latitude: float, longitude: float, start_date: str, end_date: str, config: dict[str, Any]) -> dict[str, Any]:
    retries = max(0, int(config.get("weather_api_retries", 2)))
    delay = max(0.0, float(config.get("weather_retry_backoff_seconds", 0.2)))
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return fetch_open_meteo_forecast(
                latitude,
                longitude,
                start_date,
                end_date,
                timeout=int(config.get("weather_api_timeout", 10)),
                config=config,
            )
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status != 429 and not (status is not None and 500 <= status <= 599):
                raise
            last_error = exc
        except requests.RequestException as exc:
            last_error = exc
        if attempt < retries:
            time.sleep(delay * (2**attempt))
    raise RuntimeError(f"天气 API 在 {retries + 1} 次尝试后仍失败") from last_error


def get_cached_or_fetch_forecast(
    station: str,
    start_date: str,
    end_date: str,
    config: dict[str, Any] | None = None,
) -> str:
    """Return online forecast, valid cache, or local CSV fallback in that order."""
    cfg = dict(config or {})
    latitude, longitude = load_station_coordinates(station, cfg)

    try:
        payload = _fetch_with_retry(latitude, longitude, start_date, end_date, cfg)
    except (requests.RequestException, RuntimeError) as online_error:
        cached = _read_valid_cache(station, start_date, end_date, cfg)
        if cached is not None:
            rows = normalize_forecast_payload(station, cached["payload"])
            for row in rows:
                row["issued_at"] = cached["fetched_at"]
                row["source"] = "open_meteo_cache"
            return "## 降雨预报（有效缓存）\n\n" + "\n".join(
                json.dumps(row, ensure_ascii=False) for row in rows
            )
        if cfg.get("weather_fallback_to_local", True):
            from .local_csv import get_rainfall_forecast as get_local_rainfall_forecast

            try:
                return get_local_rainfall_forecast(station, start_date, end_date)
            except Exception as local_error:
                raise RuntimeError(
                    f"在线 API、有效缓存和 local_csv 均不可用；在线错误：{online_error}；本地错误：{local_error}"
                ) from local_error
        raise RuntimeError(f"在线 API 失败且未启用 local_csv 回退：{online_error}") from online_error

    envelope = _write_cache(station, start_date, end_date, payload, cfg)
    rows = normalize_forecast_payload(station, payload)
    for row in rows:
        row["issued_at"] = envelope["fetched_at"]
    return "## 降雨预报（在线 API）\n\n" + "\n".join(
        json.dumps(row, ensure_ascii=False) for row in rows
    )
