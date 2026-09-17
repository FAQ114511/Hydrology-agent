"""生成 ZHUJIANG / DONGJIANG 两个演示站点的模拟数据 CSV。

sample_data 下这两个站点的 8 个 CSV 是本脚本的产物：要调整数值就改这里再重跑，
不要直接手改 CSV，否则下次生成会被覆盖。

    D:\\Anaconda\\envs\\tradingagents\\python.exe scripts\\generate_simulated_stations.py

数据全部为虚拟模拟数据，与任何真实水文站、真实洪水事件无关。
"""

from __future__ import annotations

import csv
import math
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "sample_data"

START = date(2023, 10, 2)
END = date(2024, 5, 10)

STATIONS = {
    "ZHUJIANG": {
        # 洪潮相遇型站点：水位常年受潮位顶托，涨幅平缓，本次过程未达警戒。
        "level": [
            ("2023-10-02", 6.35), ("2023-11-01", 6.28), ("2023-12-01", 6.18),
            ("2024-01-02", 6.14), ("2024-02-01", 6.20), ("2024-03-01", 6.38),
            ("2024-04-01", 6.62), ("2024-04-26", 6.88), ("2024-05-03", 6.98),
            ("2024-05-06", 7.04), ("2024-05-08", 7.09), ("2024-05-10", 7.12),
        ],
        "flow": [
            ("2023-10-02", 3400), ("2023-12-01", 3050), ("2024-02-01", 3300),
            ("2024-04-01", 7100), ("2024-04-26", 8900), ("2024-05-03", 9500),
            ("2024-05-06", 9850), ("2024-05-08", 10180), ("2024-05-10", 10420),
        ],
        "rainfall": {
            "2024-04-29": 8.4, "2024-04-30": 2.0, "2024-05-01": 21.5,
            "2024-05-02": 12.8, "2024-05-03": 0.0, "2024-05-06": 22.0,
            "2024-05-07": 28.5, "2024-05-08": 18.2, "2024-05-09": 14.6,
            "2024-05-10": 26.4,
        },
        "environment": [
            ("2024-05-04", 58, 52, 150, 48, 68, "低", "正常"),
            ("2024-05-05", 60, 54, 142, 50, 68, "低", "正常"),
            ("2024-05-06", 63, 56, 132, 53, 68, "低", "正常"),
            ("2024-05-07", 66, 58, 124, 55, 68, "中", "正常"),
            ("2024-05-08", 69, 60, 116, 57, 68, "中", "重点河段加密巡查"),
            ("2024-05-09", 72, 62, 104, 60, 68, "中", "重点河段加密巡查"),
            ("2024-05-10", 74, 64, 95, 62, 68, "中", "重点河段加密巡查"),
        ],
        "weather": [
            ("2024-05-07 08:00:00", "2024-05-07", 18, 75, "降雨", "蓝色", "预计有中到大雨，注意低洼区积水"),
            ("2024-05-08 08:00:00", "2024-05-08", 26, 80, "降雨", "蓝色", "降雨持续，需关注潮位顶托叠加影响"),
            ("2024-05-09 08:00:00", "2024-05-09", 32, 82, "暴雨", "黄色", "局地暴雨，沿岸低洼区存在积水风险"),
            ("2024-05-10 08:00:00", "2024-05-10", 38, 84, "暴雨", "黄色", "强降雨叠加天文潮位，需防范城市内涝"),
            ("2024-05-10 08:00:00", "2024-05-11", 46, 80, "暴雨", "黄色", "降雨仍将持续，潮位处于较高区间"),
            ("2024-05-10 08:00:00", "2024-05-12", 22, 65, "降雨", "蓝色", "降雨减弱，仍需关注滞后积水"),
            ("2024-05-10 08:00:00", "2024-05-13", 8, 40, "降雨", "蓝色", "降雨明显减弱"),
        ],
        "social": [
            ("2024-05-04", 0, 0, 0, 0, 0, 0, "低", "暂未报告明显社会影响"),
            ("2024-05-05", 0, 0, 0, 0, 0, 0, "低", "暂未报告明显社会影响"),
            ("2024-05-06", 10, 0, 0, 0, 0, 0, "低", "个别低洼路段出现短时积水"),
            ("2024-05-07", 25, 0, 0, 0, 0, 3, "低", "低洼路段积水，交通缓慢"),
            ("2024-05-08", 40, 0, 0, 0, 0, 6, "低", "部分地下空间采取临时封闭措施"),
            ("2024-05-09", 65, 0, 0, 0, 0, 9, "中", "沿江低洼区启动巡查"),
            ("2024-05-10", 90, 0, 0, 0, 0, 12, "中", "低洼区预置排涝设备"),
        ],
    },
    "DONGJIANG": {
        # 台风季快速涨水型站点：本次过程已超警戒水位，接近橙色阈值。
        "level": [
            ("2023-10-02", 10.55), ("2023-11-01", 10.42), ("2023-12-01", 10.30),
            ("2024-01-02", 10.26), ("2024-02-01", 10.34), ("2024-03-01", 10.58),
            ("2024-04-01", 10.90), ("2024-04-26", 11.44), ("2024-05-03", 11.90),
            ("2024-05-06", 12.12), ("2024-05-08", 12.30), ("2024-05-10", 12.44),
        ],
        "flow": [
            ("2023-10-02", 1850), ("2023-12-01", 1620), ("2024-02-01", 1780),
            ("2024-04-01", 3050), ("2024-04-26", 4280), ("2024-05-03", 4930),
            ("2024-05-06", 5120), ("2024-05-08", 5310), ("2024-05-10", 5480),
        ],
        "rainfall": {
            "2024-04-29": 12.5, "2024-04-30": 4.0, "2024-05-01": 33.0,
            "2024-05-02": 18.5, "2024-05-03": 2.0, "2024-05-06": 58.0,
            "2024-05-07": 76.5, "2024-05-08": 88.2, "2024-05-09": 69.4,
            "2024-05-10": 96.0,
        },
        "environment": [
            ("2024-05-04", 82, 88, 40, 74, 74, "中", "正常"),
            ("2024-05-05", 85, 89, 36, 78, 74, "中", "正常"),
            ("2024-05-06", 88, 90, 32, 82, 74, "中高", "正常"),
            ("2024-05-07", 90, 91, 26, 86, 74, "中高", "重点河段加密巡查"),
            ("2024-05-08", 92, 92, 20, 89, 74, "高", "局部堤段发现轻微渗水"),
            ("2024-05-09", 94, 93, 16, 91, 74, "高", "局部加强巡查并预置抢险物资"),
            ("2024-05-10", 95, 94, 12, 93, 74, "高", "局部堤段渗水扩大，已组织处置"),
        ],
        "weather": [
            ("2024-05-07 08:00:00", "2024-05-07", 55, 88, "暴雨", "橙色", "流域强降雨，中小河流涨水迅速"),
            ("2024-05-08 08:00:00", "2024-05-08", 78, 92, "暴雨", "橙色", "降雨持续加强，需防范山洪与内涝"),
            ("2024-05-09 08:00:00", "2024-05-09", 88, 92, "暴雨", "橙色", "多日累积雨量大，土壤接近饱和"),
            ("2024-05-10 08:00:00", "2024-05-10", 96, 94, "特大暴雨", "红色", "预计出现特大暴雨，防汛形势严峻"),
            ("2024-05-10 08:00:00", "2024-05-11", 105, 90, "特大暴雨", "红色", "上游来水与本地降雨叠加，洪峰可能进一步抬升"),
            ("2024-05-10 08:00:00", "2024-05-12", 48, 72, "暴雨", "橙色", "降雨逐步减弱，但退水期仍需警惕堤防险情"),
            ("2024-05-10 08:00:00", "2024-05-13", 15, 50, "降雨", "蓝色", "降雨明显减弱"),
        ],
        "social": [
            ("2024-05-04", 0, 0, 0, 0, 0, 0, "低", "暂未报告明显社会影响"),
            ("2024-05-05", 30, 0, 0, 0, 0, 8, "低", "沿河农田出现积水"),
            ("2024-05-06", 120, 0, 0, 0, 0, 26, "中", "部分沿河村组启动巡查"),
            ("2024-05-07", 320, 40, 1, 0, 0, 58, "中", "一处乡道临时管控"),
            ("2024-05-08", 760, 140, 2, 1, 0, 124, "中", "低洼区人员开始转移"),
            ("2024-05-09", 1500, 420, 4, 2, 0, 218, "高", "多所学校停课，转移范围扩大"),
            ("2024-05-10", 2600, 780, 7, 3, 1, 320, "高", "低洼区大规模转移，部分医院受到影响"),
        ],
    },
}

OBS_HEADER = ["Date", "WaterLevel", "Flow", "Rainfall"]
ENV_HEADER = [
    "Date", "SoilSaturationPct", "ReservoirStoragePct", "ReservoirAvailableMm",
    "RiverCapacityPct", "VegetationCoverPct", "LowlandRisk", "LeveeStatus",
]
WEATHER_HEADER = [
    "IssuedAt", "ValidDate", "ForecastRainfallMm", "RainProbabilityPct",
    "WarningType", "WarningLevel", "WarningText",
]
SOCIAL_HEADER = [
    "Date", "AffectedPopulation", "TransferredPopulation", "RoadClosures",
    "SchoolsAffected", "HospitalsAffected", "CropAffectedHa", "PublicConcern", "Summary",
]


def _interpolate(anchors: list[tuple[str, float]], day: date) -> float:
    points = [(date.fromisoformat(d), v) for d, v in anchors]
    if day <= points[0][0]:
        return points[0][1]
    for (day_a, value_a), (day_b, value_b) in zip(points, points[1:], strict=False):
        if day <= day_b:
            ratio = (day - day_a).days / (day_b - day_a).days
            return value_a + (value_b - value_a) * ratio
    return points[-1][1]


def _weekdays(start: date, end: date):
    day = start
    while day <= end:
        if day.weekday() < 5:
            yield day
        day += timedelta(days=1)


def _background_rainfall(index: int) -> float:
    # 固定公式而非随机数：保证每次生成完全一致。
    value = 6.5 * math.sin(index / 6.3) + 3.2 * math.sin(index / 2.9) + 4.0
    return round(max(0.0, value), 1)


def _write(path: Path, header: list[str], rows: list[tuple], encoding: str = "utf-8-sig") -> None:
    # 观测 CSV 与既有 XIANGJIANG.csv 一致用无 BOM 的 UTF-8；
    # 含中文的辅助 CSV 用 BOM，避免 Excel 直接打开时乱码。
    with path.open("w", encoding=encoding, newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def build_observations(spec: dict) -> list[tuple]:
    rows = []
    for index, day in enumerate(_weekdays(START, END)):
        level = _interpolate(spec["level"], day) + 0.02 * math.sin(index / 2.7)
        flow = _interpolate(spec["flow"], day) + 12.0 * math.sin(index / 1.9)
        rainfall = spec["rainfall"].get(day.isoformat(), _background_rainfall(index))
        rows.append((day.isoformat(), round(level, 3), round(flow, 1), rainfall))
    return rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for station, spec in STATIONS.items():
        observations = build_observations(spec)
        _write(OUT_DIR / f"{station}.csv", OBS_HEADER, observations, encoding="utf-8")
        _write(OUT_DIR / f"{station}_ENVIRONMENT.csv", ENV_HEADER, spec["environment"])
        _write(OUT_DIR / f"{station}_WEATHER.csv", WEATHER_HEADER, spec["weather"])
        _write(OUT_DIR / f"{station}_SOCIAL.csv", SOCIAL_HEADER, spec["social"])
        print(f"{station}: {len(observations)} 行观测 + 环境/气象/社会影响各 {len(spec['environment'])} 行")


if __name__ == "__main__":
    main()
