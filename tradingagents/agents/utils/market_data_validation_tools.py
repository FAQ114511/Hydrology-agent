from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.local_csv import build_local_observation_snapshot


@tool
def get_verified_observation_snapshot(
    station: Annotated[str, "水文站点编号"],
    curr_date: Annotated[str, "当前研判日期，YYYY-mm-dd"],
    look_back_days: Annotated[
        int, "纳入近期观测的行数，用于校核"
    ] = 30,
) -> str:
    """生成确定性的观测校验快照，用于校核精确的水文数据主张。

    返回截至 curr_date 的最新观测行、关键水文指标与近期水位。
    在做精确水位、涨水幅度或指标数值主张之前先调用本工具，并把它当作真值来源。
    """
    return build_local_observation_snapshot(station, curr_date, look_back_days)
