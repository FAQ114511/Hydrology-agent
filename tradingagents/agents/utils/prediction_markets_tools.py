from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_forward_forecast(
    topic: Annotated[
        str,
        "事件主题/关键词，例如 '湘江流域强降雨'、'上游水库泄洪'、"
        "'台风路径'，或某个区域/站点事件。",
    ],
    limit: Annotated[int | None, "最多返回条数；省略则默认 6"] = None,
) -> str:
    """
    获取前瞻性事件的最新预报信息。
    返回与主题匹配的最受关注预报，每条包含其发生概率/强度、相关度、
    预报时间与近期变化。使用已配置的 prediction_markets 厂商。

    Args:
        topic (str): 事件关键词
        limit (int): 最多返回条数；省略则默认 6

    Returns:
        str: 匹配预报的格式化 markdown 报告
    """
    return route_to_vendor("get_forward_forecast", topic, limit)
