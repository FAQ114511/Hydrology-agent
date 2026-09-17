"""本地 CSV 数据厂商 —— 完全离线地从静态 CSV 文件读取水文观测数据。

该厂商对外暴露与路由层（``tradingagents.dataflows.interface``）一致的方法，
但不调用任何网络 API，而是从本地 CSV 文件读取水文站点观测。它的存在是为了
让多智能体流水线能端到端离线运行，使用简单、自包含的数据 —— 既便于学习
智能体工作流，也便于针对固定数据集做防汛风险评估。

数据布局（默认目录 ``<project>/sample_data``）：
    ``{STATION}.csv`` —— 逐日观测，列为
    ``Date,WaterLevel,Flow,Rainfall``（水位 m / 流量 m³/s / 日雨量 mm）

通过在 ``data_vendors`` 里把厂商类别设为 ``"local_csv"`` 来启用，
并可用 ``local_data_dir`` 指向其他目录。
"""

from __future__ import annotations

import os

import pandas as pd

from .config import get_config
from .errors import NoMarketDataError

from .weather_api import (
    get_online_rainfall_forecast,
)

# 可由本地观测 CSV 计算的水文趋势指标。
# 每个键即水文分析师可以请求的指标名。
_INDICATORS = {
    "water_level_ma3",
    "water_level_ma7",
    "water_level_ma30",
    "water_level_change_1d",
    "water_level_change_7d",
    "rainfall_1d",
    "rainfall_sum_7d",
    "flow_ma7",
}


def _data_dir() -> str:
    """返回本地观测数据目录。"""
    cfg = get_config()
    return cfg.get("local_data_dir") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "sample_data",
    )

def _data_source_label() -> str:
    """观测数据的来源标签：用户目录 vs 内置演示数据。"""
    return "用户提供数据" if get_config().get("local_data_dir") else "内置模拟数据"


def _load_auxiliary(station: str, suffix: str) -> pd.DataFrame:
    """加载站点配套的模拟环境/气象/社会影响 CSV。"""
    path = os.path.join(_data_dir(), f"{station.upper()}_{suffix}.csv")
    if not os.path.exists(path):
        raise NoMarketDataError(station, station.upper(), f"本地不存在辅助 CSV：{path}")
    return pd.read_csv(path)


def _latest_auxiliary(station: str, suffix: str, curr_date: str) -> pd.Series:
    df = _load_auxiliary(station, suffix)
    date_col = "Date" if "Date" in df.columns else "ValidDate"
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df[df[date_col] <= pd.to_datetime(curr_date)].dropna(subset=[date_col])
    if df.empty:
        raise NoMarketDataError(station, station.upper(), f"{curr_date} 之前无 {suffix} 辅助数据")
    return df.sort_values(date_col).iloc[-1]


def _format_row(title: str, row: pd.Series) -> str:
    lines = [f"## {title}（虚拟模拟数据）", ""]
    for key, value in row.items():
        if pd.isna(value):
            continue
        if isinstance(value, pd.Timestamp):
            value = value.strftime("%Y-%m-%d")
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def is_local_mode() -> bool:
    """核心观测类别是否路由到本地 CSV 厂商。"""
    vendors = get_config().get("data_vendors", {})
    return "local_csv" in str(vendors.get("core_stock_apis", ""))


def _load_frame(station: str) -> pd.DataFrame:
    """加载并轻度规范化 ``station`` 的本地水文 CSV。"""
    path = os.path.join(_data_dir(), f"{station.upper()}.csv")
    if not os.path.exists(path):
        raise NoMarketDataError(station, station.upper(), f"本地不存在 CSV：{path}")
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date")
    for col in ("WaterLevel", "Flow", "Rainfall"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if df.empty or "WaterLevel" not in df.columns:
        raise NoMarketDataError(station, station.upper(), f"CSV 为空或格式错误：{path}")
    return df


def load_local_observations(station: str, curr_date: str) -> pd.DataFrame:
    """过滤到 ``curr_date`` 的观测帧（无前瞻）。"""
    df = _load_frame(station)
    return df[df["Date"] <= pd.to_datetime(curr_date)]


def get_observations(station: str, start_date: str, end_date: str) -> str:
    """过滤到 ``[start_date, end_date]`` 的水文观测 CSV 字符串。"""
    df = _load_frame(station)
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    df = df[(df["Date"] >= start) & (df["Date"] <= end)]
    if df.empty:
        raise NoMarketDataError(
            station, station.upper(), f"{start_date} 至 {end_date} 之间无观测记录"
        )
    csv_string = df.to_csv(index=False)
    header = (
        f"# {station.upper()} 站水文观测（{start_date} 至 {end_date}，{_data_source_label()}）\n"
        f"# 列：Date, WaterLevel(m), Flow(m3/s), Rainfall(mm)\n"
        f"# 记录总数：{len(df)}\n\n"
    )
    return header + csv_string


def _compute_series(df: pd.DataFrame, indicator: str) -> pd.Series:
    """计算请求的水文指标（返回 pandas Series）。"""
    wl = df["WaterLevel"]
    if indicator == "water_level_ma3":
        return wl.rolling(3).mean()
    if indicator == "water_level_ma7":
        return wl.rolling(7).mean()
    if indicator == "water_level_ma30":
        return wl.rolling(30).mean()
    if indicator == "water_level_change_1d":
        return wl.diff()
    if indicator == "water_level_change_7d":
        return wl.diff(7)
    if indicator == "rainfall_1d":
        return df["Rainfall"]
    if indicator == "rainfall_sum_7d":
        return df["Rainfall"].rolling(7).sum()
    if indicator == "flow_ma7":
        return df["Flow"].rolling(7).mean()
    raise ValueError(f"指标 {indicator} 不受支持。请从 {sorted(_INDICATORS)} 中选择。")


def get_hydrology_indicators(
    station: str, indicator: str, curr_date: str, look_back_days: int = 30
) -> str:
    """在回溯窗口内本地计算水文指标序列。"""
    if indicator not in _INDICATORS:
        raise ValueError(
            f"指标 {indicator} 不受支持。请从 {sorted(_INDICATORS)} 中选择。"
        )

    df = _load_frame(station)
    df = df[df["Date"] <= pd.to_datetime(curr_date)]
    if df.empty:
        raise NoMarketDataError(station, station.upper(), f"{curr_date} 当日或之前无观测记录")

    series = _compute_series(df, indicator)

    end = pd.to_datetime(curr_date)
    start = end - pd.Timedelta(days=look_back_days)
    mask = (df["Date"] >= start) & (df["Date"] <= end)

    lines = [
        f"## {indicator} 指标值（{start.strftime('%Y-%m-%d')} 至 "
        f"{end.strftime('%Y-%m-%d')}，本地 CSV）：\n"
    ]
    for _, row in df[mask].iterrows():
        val = series.loc[row.name]
        val_str = "N/A" if pd.isna(val) else f"{val:.3f}"
        lines.append(f"{row['Date'].strftime('%Y-%m-%d')}: {val_str}")

    return "\n".join(lines)


def build_local_observation_snapshot(
    station: str, curr_date: str, look_back_days: int = 30
) -> str:
    """生成确定性的本地观测校验快照（供 ``get_verified_observation_snapshot`` 使用）。

    返回截至 ``curr_date`` 的最新观测行、关键水文指标与近期水位序列，
    作为分析师精确数值主张的真值来源。不依赖任何网络。
    """
    df = load_local_observations(station, curr_date)
    if df.empty:
        raise NoMarketDataError(station, station.upper(), f"{curr_date} 当日或之前无观测记录")

    latest = df.iloc[-1]
    latest_date = latest["Date"].strftime("%Y-%m-%d")
    window = max(1, min(int(look_back_days), 30))
    recent = df.tail(window)

    lines = [
        f"## {station.upper()} 站校验观测快照（{_data_source_label()}）",
        "",
        f"- 请求研判日期：{curr_date}",
        f"- 最新观测行：{latest_date}",
        "- 请求日期之后的观测行在校验前已剔除（无前瞻）。",
        "",
        "### 最新观测行",
        "",
        "| 字段 | 数值 |",
        "|---|---:|",
    ]
    for field in ("WaterLevel", "Flow", "Rainfall"):
        val = latest.get(field)
        val_str = "N/A" if pd.isna(val) else f"{val:.3f}"
        lines.append(f"| {field} | {val_str} |")

    lines += ["", "### 关键水文指标（最新一行）", "", "| 指标 | 数值 |", "|---|---:|"]
    for name in ("water_level_ma7", "water_level_change_1d", "water_level_change_7d",
                 "rainfall_sum_7d", "flow_ma7"):
        try:
            series = _compute_series(df, name)
            val = series.iloc[-1]
            val_str = "N/A" if pd.isna(val) else f"{val:.3f}"
        except Exception as exc:  # noqa: BLE001 —— 单个指标失败不应拖垮整个快照
            val_str = f"N/A ({type(exc).__name__})"
        lines.append(f"| {name} | {val_str} |")

    lines += ["", f"### 近期水位观测（最近 {len(recent)} 行）", "",
              "| 日期 | 水位(m) |", "|---|---:|"]
    for _, row in recent.iterrows():
        wl = row.get("WaterLevel")
        wl_str = "N/A" if pd.isna(wl) else f"{wl:.3f}"
        lines.append(f"| {row['Date'].strftime('%Y-%m-%d')} | {wl_str} |")

    lines += [
        "",
        "把本快照当作精确水位、指标值主张的真值来源。若其他工具输出与之冲突，"
        "标注差异，而不是臆造一个折中的数字。不要声称历史验证或精确涨水幅度，"
        "除非有带具体日期和数值的工具输出直接支撑。",
    ]
    return "\n".join(lines)


# 气象 / 环境 / 社会影响类方法：本地 CSV 模式只随附站点观测，
# 这些方法返回明确的「未提供」信号而不是臆造数值 —— 让分析师如实报告缺口。
def get_environment_risk(station: str, curr_date: str) -> str:
    return _format_row(f"{station.upper()} 环境风险（截至 {curr_date}）", _latest_auxiliary(station, "ENVIRONMENT", curr_date))


def get_water_storage(station: str, freq: str = "quarterly", curr_date: str = None) -> str:
    row = _latest_auxiliary(station, "ENVIRONMENT", curr_date or "9999-12-31")
    return _format_row(f"{station.upper()} 蓄水/库容（虚拟模拟数据）", row[["Date", "ReservoirStoragePct", "ReservoirAvailableMm"]])


def get_river_flow(station: str, freq: str = "quarterly", curr_date: str = None) -> str:
    row = _latest_auxiliary(station, "ENVIRONMENT", curr_date or "9999-12-31")
    return _format_row(f"{station.upper()} 河道行洪能力（虚拟模拟数据）", row[["Date", "RiverCapacityPct", "LeveeStatus"]])


def get_soil_moisture(station: str, freq: str = "quarterly", curr_date: str = None) -> str:
    row = _latest_auxiliary(station, "ENVIRONMENT", curr_date or "9999-12-31")
    return _format_row(f"{station.upper()} 土壤墒情（虚拟模拟数据）", row[["Date", "SoilSaturationPct", "LowlandRisk"]])


def get_rainfall_forecast(station: str, start_date: str, end_date: str) -> str:
    df = _load_auxiliary(station, "WEATHER")
    df["ValidDate"] = pd.to_datetime(df["ValidDate"], errors="coerce")
    df = df[(df["ValidDate"] >= pd.to_datetime(start_date)) & (df["ValidDate"] <= pd.to_datetime(end_date))]
    if df.empty:
        raise NoMarketDataError(station, station.upper(), f"{start_date} 至 {end_date} 无降雨预报")
    return "## 降雨预报（虚拟模拟数据）\n\n" + df.to_string(index=False)


def get_social_impact(station: str) -> str:
    return _format_row(f"{station.upper()} 社会影响（虚拟模拟数据）", _latest_auxiliary(station, "SOCIAL", "9999-12-31"))


def get_regional_indicators(
    station: str, indicator: str, curr_date: str, look_back_days: int = None
) -> str:
    row = _latest_auxiliary(station, "ENVIRONMENT", curr_date)
    aliases = {"soil_saturation": "SoilSaturationPct", "vegetation_cover": "VegetationCoverPct", "river_capacity": "RiverCapacityPct"}
    column = aliases.get(indicator, indicator)
    if column not in row.index:
        return f"NO_DATA_AVAILABLE：未提供区域指标 '{indicator}'。"
    return f"## {station.upper()} 区域指标（虚拟模拟数据）\n\n- {column}: {row[column]}\n- Date: {row['Date']}"


def get_forward_forecast(station: str, topic: str, limit: int = None) -> str:
    df = _load_auxiliary(station, "WEATHER").tail(limit or 6)
    return f"## {station.upper()} 前瞻预报：{topic}（虚拟模拟数据）\n\n" + df.to_string(index=False)
