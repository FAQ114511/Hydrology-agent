from tradingagents.dataflows.weather_api import PROJECT_ROOT, _now_cn, get_online_realtime_weather

text = get_online_realtime_weather("XIANGJIANG", _now_cn().date().isoformat())

print(text)

assert "source: open_meteo_realtime" in text
assert "观测时刻" in text
assert "过去 24 小时累积降雨" in text
assert "过去 72 小时累积降雨" in text
assert "过去 7 天累积降雨" in text
assert "未来 24 小时预报降雨" in text
assert "未来 48 小时预报降雨" in text
assert "土壤体积含水量" in text

cache = PROJECT_ROOT / "runtime" / "cache" / "weather" / "realtime_XIANGJIANG.json"
print(f"\ncache file: {cache} exists={cache.exists()}")
assert cache.exists()
