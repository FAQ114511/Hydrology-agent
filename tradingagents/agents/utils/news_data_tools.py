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
def get_weather_warning(
    curr_date: Annotated[str, "当前日期，yyyy-mm-dd 格式"],
    look_back_days: Annotated[int | None, "回溯天数；省略则使用配置默认值"] = None,
    limit: Annotated[int | None, "最多返回条数；省略则使用配置默认值"] = None,
) -> str:
    """
    获取气象预警数据。
    使用已配置的 news_data 厂商。look_back_days 与 limit 的默认值来自
    DEFAULT_CONFIG（global_news_lookback_days、global_news_article_limit）；
    传入显式值可覆盖。

    Args:
        curr_date (str): 当前日期，yyyy-mm-dd 格式
        look_back_days (int): 回溯天数；省略则继承配置
        limit (int): 最大返回条数；省略则继承配置

    Returns:
        str: 包含气象预警数据的格式化字符串
    """
    return route_to_vendor("get_weather_warning", curr_date, look_back_days, limit)

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
