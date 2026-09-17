"""Open-Meteo adapter for hydrological forecast data."""

from __future__ import annotations
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATIONS = PROJECT_ROOT / "runtime" / "knowledge" / "stations.json"
DEFAULT_URL = "https://api.open-meteo.com/v1/forecast"
REALTIME_CURRENT_FIELDS = "precipitation,rain"
REALTIME_HOURLY_FIELDS = "precipitation,precipitation_probability,soil_moisture_0_to_7cm"

# 中国无夏令时，固定 UTC+8 可避免 Windows 缺少 tzdata 的问题。
CN_TZ = timezone(timedelta(hours=8))

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

def _now_cn() -> datetime:
    return datetime.now(CN_TZ)


def fetch_open_meteo_realtime(
    latitude: float,
    longitude: float,
    past_days: int,
    forecast_days: int,
    timeout: int = 10,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """拉取站点实况降雨、逐小时降雨与 0-7cm 土壤墒情。"""
    cfg = config or {}
    response = requests.get(
        cfg.get("weather_api_base_url", DEFAULT_URL),
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": REALTIME_CURRENT_FIELDS,
            "hourly": REALTIME_HOURLY_FIELDS,
            "timezone": "Asia/Shanghai",
            "past_days": int(past_days),
            "forecast_days": int(forecast_days),
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("天气 API 顶层返回值必须是对象")
    return payload


def normalize_realtime_payload(station: str, payload: dict[str, Any], now: datetime) -> dict[str, Any]:
    """把实况返回整理成累积降雨、逐日汇总与墒情摘要。"""
    current, hourly = payload.get("current"), payload.get("hourly")
    if not isinstance(current, dict) or not isinstance(hourly, dict):
        raise ValueError("realtime payload 缺少 current/hourly 对象")
    fields = ("time", "precipitation", "precipitation_probability", "soil_moisture_0_to_7cm")
    missing = [key for key in fields if key not in hourly]
    if missing:
        raise ValueError(f"realtime payload 缺少字段：{', '.join(missing)}")
    lengths = {key: len(hourly[key]) for key in fields}
    if len(set(lengths.values())) != 1:
        raise ValueError(f"realtime payload 数组长度不一致：{lengths}")
    if "time" not in current or "precipitation" not in current:
        raise ValueError("realtime payload 缺少 current 实况字段")

    rows = [
        {
            "time": time_key,
            "precipitation_mm": rainfall,
            "probability_pct": probability,
            "soil_moisture": moisture,
        }
        for time_key, rainfall, probability, moisture in zip(
            hourly["time"],
            hourly["precipitation"],
            hourly["precipitation_probability"],
            hourly["soil_moisture_0_to_7cm"],
        )
    ]

    def window_key(offset_hours: int) -> str:
        return (now + timedelta(hours=offset_hours)).strftime("%Y-%m-%dT%H:%M")

    now_key = window_key(0)

    def window(start_key: str, end_key: str) -> float:
        return round(sum(row["precipitation_mm"] for row in rows if start_key < row["time"] <= end_key), 2)

    past_rows = [row for row in rows if row["time"] <= now_key]
    daily: dict[str, dict[str, Any]] = {}
    for row in past_rows:
        day = row["time"][:10]
        bucket = daily.setdefault(day, {"date": day, "rainfall_mm": 0.0, "max_hourly_mm": 0.0})
        bucket["rainfall_mm"] = round(bucket["rainfall_mm"] + row["precipitation_mm"], 2)
        bucket["max_hourly_mm"] = max(bucket["max_hourly_mm"], row["precipitation_mm"])

    def soil_at(boundary_key: str):
        candidates = [row["soil_moisture"] for row in rows if row["time"] <= boundary_key]
        return candidates[-1] if candidates else None

    soil_now = soil_at(now_key)
    soil_prev = soil_at(window_key(-24))
    change = round(soil_now - soil_prev, 3) if soil_now is not None and soil_prev is not None else None

    return {
        "station": station.strip().upper(),
        "observed_at": current["time"],
        "current_rainfall_mm": current["precipitation"],
        "past_24h_rainfall_mm": window(window_key(-24), now_key),
        "past_72h_rainfall_mm": window(window_key(-72), now_key),
        "past_7d_rainfall_mm": window(window_key(-168), now_key),
        "forecast_24h_rainfall_mm": window(now_key, window_key(24)),
        "forecast_48h_rainfall_mm": window(now_key, window_key(48)),
        "daily": list(daily.values()),
        "hourly": [row for row in rows if row["time"] > now_key][:48],
        "soil_moisture_0_to_7cm": soil_now,
        "soil_moisture_24h_change": change,
        "source": "open_meteo_realtime",
    }


def _render_realtime(snapshot: dict[str, Any], issued_at: str) -> str:
    lines = [
        f"## 实时气象（{snapshot['station']}）",
        "",
        "source: open_meteo_realtime",
        f"issued_at: {issued_at}",
        f"观测时刻：{snapshot['observed_at']}（网格模式实况，非地面气象站观测）",
        "",
        "### 实况与累积降雨",
        f"- 最近一小时降雨：{snapshot['current_rainfall_mm']} mm",
        f"- 过去 24 小时累积降雨：{snapshot['past_24h_rainfall_mm']} mm",
        f"- 过去 72 小时累积降雨：{snapshot['past_72h_rainfall_mm']} mm",
        f"- 过去 7 天累积降雨：{snapshot['past_7d_rainfall_mm']} mm",
        f"- 未来 24 小时预报降雨：{snapshot['forecast_24h_rainfall_mm']} mm",
        f"- 未来 48 小时预报降雨：{snapshot['forecast_48h_rainfall_mm']} mm",
        f"- 0-7cm 土壤体积含水量：{snapshot['soil_moisture_0_to_7cm']}（过去 24 小时变化 {snapshot['soil_moisture_24h_change']}）",
        "",
        "### 过去逐日降雨",
        "| 日期 | 日降雨 mm | 最大小时雨强 mm |",
        "|---|---|---|",
    ]
    lines += [f"| {row['date']} | {row['rainfall_mm']} | {row['max_hourly_mm']} |" for row in snapshot["daily"]]
    lines += [
        "",
        "### 未来 48 小时逐小时",
        "| 时间 | 降雨 mm | 降雨概率 % |",
        "|---|---|---|",
    ]
    lines += [f"| {row['time']} | {row['precipitation_mm']} | {row['probability_pct']} |" for row in snapshot["hourly"]]
    return "\n".join(lines)


def _realtime_cache_path(station: str, config: dict[str, Any]) -> Path:
    cache_dir = _path(config.get("weather_cache_dir", PROJECT_ROOT / "runtime" / "cache" / "weather"))
    safe_station = station.strip().upper().replace("/", "_")
    return cache_dir / f"realtime_{safe_station}.json"


def _read_valid_realtime_cache(station: str, config: dict[str, Any]) -> dict[str, Any] | None:
    path = _realtime_cache_path(station, config)
    if not path.exists():
        return None
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
        fetched_at = datetime.fromisoformat(envelope["fetched_at"])
        age = (datetime.now(timezone.utc) - fetched_at).total_seconds()
        ttl = int(config.get("weather_cache_ttl_seconds", 900))
        if age < 0 or age > ttl:
            return None
        if not isinstance(envelope.get("payload"), dict):
            return None
        return envelope
    except (OSError, KeyError, TypeError, ValueError):
        return None


def _write_realtime_cache(station: str, payload: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    envelope = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "station": station.strip().upper(),
        "source": "open_meteo_realtime",
        "payload": payload,
    }
    path = _realtime_cache_path(station, config)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")
    return envelope


def get_online_realtime_weather(station: str, curr_date: str, config: dict[str, Any] | None = None) -> str:
    """返回站点实时降雨与土壤墒情；仅支持当前与未来日期。"""
    if config is None:
        from .config import get_config

        config = get_config()
    cfg = dict(config or {})
    code = (station or "").strip().upper()
    if not code:
        raise ValueError("station 不能为空")
    requested = _date(curr_date)
    now = _now_cn()
    if requested < now.date().isoformat():
        return (
            f"## 实时气象（{code}）\n\nsource: open_meteo_realtime\n"
            f"实时气象只支持当前与未来日期；{requested} 属历史日期，请改用本地降雨预报。"
        )

    cached = _read_valid_realtime_cache(code, cfg)
    if cached is not None:
        return _render_realtime(normalize_realtime_payload(code, cached["payload"], now), cached["fetched_at"])

    latitude, longitude = load_station_coordinates(code, cfg)
    try:
        payload = _run_with_retry(
            lambda: fetch_open_meteo_realtime(
                latitude,
                longitude,
                int(cfg.get("weather_realtime_past_days", 7)),
                int(cfg.get("weather_realtime_forecast_days", 3)),
                timeout=int(cfg.get("weather_api_timeout", 10)),
                config=cfg,
            ),
            cfg,
        )
    except (requests.RequestException, RuntimeError, ValueError) as exc:
        return (
            f"## 实时气象（{code}）\n\nsource: open_meteo_realtime\n"
            f"实时气象数据暂不可用（{exc}）。请如实报告该数据缺口，不要臆造数值。"
        )

    envelope = _write_realtime_cache(code, payload, cfg)
    return _render_realtime(normalize_realtime_payload(code, payload, now), envelope["fetched_at"])


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


def _run_with_retry(call, config: dict[str, Any]) -> dict[str, Any]:
    """执行一次请求，仅对限流与 5xx 做退避重试，其他错误立即上抛。"""
    retries = max(0, int(config.get("weather_api_retries", 2)))
    delay = max(0.0, float(config.get("weather_retry_backoff_seconds", 0.2)))
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return call()
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


def _fetch_with_retry(latitude: float, longitude: float, start_date: str, end_date: str, config: dict[str, Any]) -> dict[str, Any]:
    return _run_with_retry(
        lambda: fetch_open_meteo_forecast(
            latitude,
            longitude,
            start_date,
            end_date,
            timeout=int(config.get("weather_api_timeout", 10)),
            config=config,
        ),
        config,
    )


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
