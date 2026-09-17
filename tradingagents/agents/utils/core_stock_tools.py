from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_observations(
    station: Annotated[str, "水文站点编号"],
    start_date: Annotated[str, "开始日期，yyyy-mm-dd 格式"],
    end_date: Annotated[str, "结束日期，yyyy-mm-dd 格式"],
) -> str:
    """
    获取给定水文站点的观测数据（水位/流量/雨量）。
    使用已配置的 core_stock_apis 厂商。
    Args:
        station (str): 水文站点编号，例如 XIANGJIANG
        start_date (str): 开始日期，yyyy-mm-dd 格式
        end_date (str): 结束日期，yyyy-mm-dd 格式
    Returns:
        str: 指定日期区间内该站点的观测数据格式化字符串。
    """
    return route_to_vendor("get_observations", station, start_date, end_date)
