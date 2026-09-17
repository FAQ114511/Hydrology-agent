"""用户自备数据的启动前检查。

CLI 里用户指定数据目录后，先确认四个必需文件都在、观测 CSV 列名正确，
把「文件名写错」这类问题拦在 LLM 调用之前。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

OBSERVATION_COLUMNS = ("Date", "WaterLevel", "Flow", "Rainfall")

# 辅助数据文件名后缀：与 local_csv._load_auxiliary() 的读取约定一致。
AUXILIARY_SUFFIXES = ("ENVIRONMENT", "WEATHER", "SOCIAL")


class UserDataError(Exception):
    """用户数据不可用，无法继续运行。"""


def validate_user_dataset(station: str, data_dir: str | Path) -> dict:
    """检查用户目录下的观测 CSV 与三个辅助 CSV。

    通过时返回 dict(rows, start_date, end_date)；缺文件或缺列抛 UserDataError。
    """
    directory = Path(data_dir).expanduser()
    code = station.strip().upper()

    required = [
        directory / f"{code}.csv",
        *(directory / f"{code}_{suffix}.csv" for suffix in AUXILIARY_SUFFIXES),
    ]
    absent = [path for path in required if not path.exists()]
    if absent:
        raise UserDataError("缺少数据文件：" + "、".join(str(path) for path in absent))

    frame = pd.read_csv(directory / f"{code}.csv")
    missing = [column for column in OBSERVATION_COLUMNS if column not in frame.columns]
    if missing:
        raise UserDataError(f"{code}.csv 缺少必需列：{', '.join(missing)}")

    # 日期是 YYYY-MM-DD，字符串首尾就是时间范围，不必解析成时间戳。
    return {
        "rows": int(len(frame)),
        "start_date": str(frame["Date"].min()),
        "end_date": str(frame["Date"].max()),
    }
