from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_regional_indicators(
    indicator: Annotated[
        str,
        "区域环境指标：如 'soil_saturation'、'vegetation_cover'、"
        "'land_use' 等友好别名，或原始序列 ID。",
    ],
    curr_date: Annotated[str, "当前日期，yyyy-mm-dd 格式；作为窗口终点"],
    look_back_days: Annotated[
        int | None, "回溯窗口天数；省略则使用 1 年窗口"
    ] = None,
) -> str:
    """
    获取区域环境指标时间序列。
    返回序列标题、单位、频率、最新值、窗口内变化量及近期观测表。
    使用已配置的 macro_data 厂商。

    Args:
        indicator (str): 友好别名或原始序列 ID
        curr_date (str): 当前日期，yyyy-mm-dd 格式
        look_back_days (int): 回溯窗口天数；省略则使用 1 年窗口

    Returns:
        str: 区域指标的格式化 markdown 报告
    """
    return route_to_vendor("get_regional_indicators", indicator, curr_date, look_back_days)
