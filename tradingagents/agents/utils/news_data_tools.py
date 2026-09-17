from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_rainfall_forecast(
    station: Annotated[str, "水文站点编号"],
    start_date: Annotated[str, "开始日期，yyyy-mm-dd 格式"],
    end_date: Annotated[str, "结束日期，yyyy-mm-dd 格式"],
) -> str:
    """
    获取给定站点的降雨预报数据。
    使用已配置的 news_data 厂商。
    Args:
        station (str): 水文站点编号
        start_date (str): 开始日期，yyyy-mm-dd 格式
        end_date (str): 结束日期，yyyy-mm-dd 格式
    Returns:
        str: 包含降雨预报数据的格式化字符串
    """
    return route_to_vendor("get_rainfall_forecast", station, start_date, end_date)

@tool
def get_realtime_weather(
    station: Annotated[str, "水文站点编号"],
    curr_date: Annotated[str, "当前日期，yyyy-mm-dd 格式"],
) -> str:
    """
    获取站点实时气象信息：最近一小时降雨、过去 24/72 小时与 7 天累积降雨、
    未来 24/48 小时预报降雨、0-7cm 土壤墒情。
    数据来自 Open-Meteo 网格模式实况，不是地面气象站观测，报告中必须注明。
    仅支持当前与未来日期；历史日期返回不可用提示，请改用 get_rainfall_forecast。

    Args:
        station (str): 水文站点编号
        curr_date (str): 当前研判日期，yyyy-mm-dd 格式

    Returns:
        str: 包含实时降雨与土壤墒情的格式化字符串
    """
    return route_to_vendor("get_realtime_weather", station, curr_date)

@tool
def get_social_impact(
    station: Annotated[str, "水文站点编号"],
) -> str:
    """
    获取给定区域/站点的社会影响数据。
    使用已配置的 news_data 厂商。
    Args:
        station (str): 水文站点编号
    Returns:
        str: 社会影响数据报告
    """
    return route_to_vendor("get_social_impact", station)
