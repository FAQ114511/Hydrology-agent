from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_hydrology_indicators(
    station: Annotated[str, "水文站点编号"],
    indicator: Annotated[str, "要查询的水文趋势指标名"],
    curr_date: Annotated[str, "当前分析日期，yyyy-mm-dd 格式"],
    look_back_days: Annotated[int, "向前回溯多少天"] = 30,
) -> str:
    """
    获取给定水文站点在回溯窗口内的单个趋势指标序列。
    使用已配置的 technical_indicators 厂商。
    Args:
        station (str): 水文站点编号，例如 XIANGJIANG
        indicator (str): 单个水文指标名，例如 water_level_ma7、rainfall_sum_7d。每个指标调用一次本工具。
        curr_date (str): 当前分析日期，yyyy-mm-dd 格式
        look_back_days (int): 向前回溯多少天，默认 30
    Returns:
        str: 指定指标在回溯窗口内的格式化序列。
    """
    # LLM 有时会把多个指标用逗号拼接传入；逐个拆分处理。
    indicators = [i.strip().lower() for i in indicator.split(",") if i.strip()]
    results = []
    for ind in indicators:
        try:
            results.append(
                route_to_vendor("get_hydrology_indicators", station, ind, curr_date, look_back_days)
            )
        except ValueError as e:
            results.append(str(e))
    return "\n\n".join(results)
