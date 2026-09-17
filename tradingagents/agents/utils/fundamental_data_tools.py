from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_environment_risk(
    station: Annotated[str, "水文站点编号"],
    curr_date: Annotated[str, "当前研判日期，yyyy-mm-dd"],
) -> str:
    """
    获取给定站点的环境风险数据。
    使用已配置的 fundamental_data 厂商。
    Args:
        station (str): 水文站点编号
        curr_date (str): 当前研判日期，yyyy-mm-dd
    Returns:
        str: 包含环境风险数据的格式化报告
    """
    return route_to_vendor("get_environment_risk", station, curr_date)


@tool
def get_water_storage(
    station: Annotated[str, "水文站点编号"],
    freq: Annotated[str, "报告频率：annual/quarterly"] = "quarterly",
    curr_date: Annotated[str, "当前研判日期，yyyy-mm-dd"] = None,
) -> str:
    """
    获取给定站点的蓄水/库容数据。
    使用已配置的 fundamental_data 厂商。
    Args:
        station (str): 水文站点编号
        freq (str): 报告频率：annual/quarterly（默认 quarterly）
        curr_date (str): 当前研判日期，yyyy-mm-dd
    Returns:
        str: 包含蓄水/库容数据的格式化报告
    """
    return route_to_vendor("get_water_storage", station, freq, curr_date)


@tool
def get_river_flow(
    station: Annotated[str, "水文站点编号"],
    freq: Annotated[str, "报告频率：annual/quarterly"] = "quarterly",
    curr_date: Annotated[str, "当前研判日期，yyyy-mm-dd"] = None,
) -> str:
    """
    获取给定站点的河道流量明细。
    使用已配置的 fundamental_data 厂商。
    Args:
        station (str): 水文站点编号
        freq (str): 报告频率：annual/quarterly（默认 quarterly）
        curr_date (str): 当前研判日期，yyyy-mm-dd
    Returns:
        str: 包含河道流量明细的格式化报告
    """
    return route_to_vendor("get_river_flow", station, freq, curr_date)


@tool
def get_soil_moisture(
    station: Annotated[str, "水文站点编号"],
    freq: Annotated[str, "报告频率：annual/quarterly"] = "quarterly",
    curr_date: Annotated[str, "当前研判日期，yyyy-mm-dd"] = None,
) -> str:
    """
    获取给定站点的土壤墒情数据。
    使用已配置的 fundamental_data 厂商。
    Args:
        station (str): 水文站点编号
        freq (str): 报告频率：annual/quarterly（默认 quarterly）
        curr_date (str): 当前研判日期，yyyy-mm-dd
    Returns:
        str: 包含土壤墒情数据的格式化报告
    """
    return route_to_vendor("get_soil_moisture", station, freq, curr_date)
