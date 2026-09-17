from datetime import date, timedelta

from tradingagents.dataflows.weather_api import get_online_rainfall_forecast

start = date.today()
end = start + timedelta(days=2)

text = get_online_rainfall_forecast(
    "XIANGJIANG",
    start.isoformat(),
    end.isoformat(),
)

print(text)

assert "降雨预报（在线 API）" in text
assert "issued_at" in text
assert "valid_date" in text
assert "forecast_rainfall_mm" in text
assert '"source": "open_meteo"' in text
