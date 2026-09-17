import functools
import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, RemoveMessage

# 从各独立工具文件导入
from tradingagents.agents.utils.core_stock_tools import get_observations
from tradingagents.agents.utils.fundamental_data_tools import (
    get_environment_risk,
    get_river_flow,
    get_soil_moisture,
    get_water_storage,
)
from tradingagents.agents.utils.macro_data_tools import get_regional_indicators
from tradingagents.agents.utils.market_data_validation_tools import get_verified_observation_snapshot
from tradingagents.agents.utils.news_data_tools import (
    get_rainfall_forecast,
    get_social_impact,
    get_weather_warning,
)
from tradingagents.agents.utils.prediction_markets_tools import get_forward_forecast
from tradingagents.agents.utils.rag_tools import search_flood_knowledge
from tradingagents.agents.utils.technical_indicators_tools import get_hydrology_indicators

# 对外接口：数据工具在此统一导入，供智能体与图从同一处引用，
# 外加下方定义的站点/语言辅助函数。
__all__ = [
    "get_observations",
    "get_hydrology_indicators",
    "get_environment_risk",
    "get_water_storage",
    "get_river_flow",
    "get_soil_moisture",
    "get_rainfall_forecast",
    "get_weather_warning",
    "get_social_impact",
    "get_regional_indicators",
    "get_forward_forecast",
    "get_verified_observation_snapshot",
    "search_flood_knowledge",
    "build_area_context",
    "resolve_station_identity",
    "get_area_context_from_state",
    "get_language_instruction",
    "create_msg_delete",
]

logger = logging.getLogger(__name__)

_STATIONS_PATH = (
    Path(__file__).resolve().parents[3] / "runtime" / "knowledge" / "stations.json"
)


def get_language_instruction() -> str:
    """返回配置输出语言的提示词指令。

    英语（默认）时返回空字符串，以免消耗多余 token。
    应用于所有输出会进入保存报告的智能体 —— 分析师、研判员、辩论方、
    研判经理、处置员、预警决策员 —— 使非英语运行产生完全本地化的报告，
    而不是多语言混杂。
    """
    from tradingagents.dataflows.config import get_config
    lang = get_config().get("output_language", "English")
    if lang.strip().lower() == "english":
        return ""
    return f" Write your entire response in {lang}."


def opponent_argument_or_opening(text: str, opponent: str) -> str:
    """对方最新论据，为空时返回一个明确的开场标记。

    每轮辩论的第一位发言者拿到的对方回复是空的；把它插进「反驳对方」的提示词
    会让模型臆造另一方的立场。返回明确的「尚未发言」标记，让它可以先陈述
    自己的论据（#1176）。
    """
    text = (text or "").strip()
    if text:
        return text
    return f"(（{opponent} 尚未发言 —— 请先陈述你自己的论据开启辩论。）)"


@functools.lru_cache(maxsize=256)
def resolve_station_identity(station: str) -> dict:
    """解析站点的确定性身份元数据（站点名、所在河流、流域等）。

    它的存在是为了阻止流水线在图表形态提示出「另一个区域」时臆造出不同的
    站点：没有真值名称，分析师会把水位走势套进一个叙事并编造身份，进而
    级联影响所有下游智能体。

    站点身份只来自 ``runtime/knowledge/stations.json``，不发起网络请求。
    """
    data = json.loads(_STATIONS_PATH.read_text(encoding="utf-8"))
    return data.get(str(station).upper(), {})


def build_area_context(
    station: str,
    asset_type: str = "flood",
    identity: Mapping[str, str] | None = None,
) -> str:
    """描述确切的监测站点/区域，使智能体保持站点身份与编号一致。

    当 ``identity`` 提供（通过 :func:`resolve_station_identity` 确定性解析）时，
    站点名称等信息被注入，使智能体锚定真实站点而不是把水位走势套到错误区域上。
    """
    context = (
        f"需要研判的区域/站点是 `{station}`。"
        "在每一次工具调用、报告与建议中都使用这一确切编号。"
    )

    details = []
    if identity:
        name = identity.get("station_name") or identity.get("name")
        if name:
            details.append(f"站点名称：{name}")
        if identity.get("river"):
            details.append(f"所在河流：{identity['river']}")
        if identity.get("basin"):
            details.append(f"所属流域：{identity['basin']}")
        if identity.get("province") or identity.get("city"):
            location = "，".join(x for x in (identity.get("province"), identity.get("city")) if x)
            details.append(f"行政区：{location}")
        if identity.get("warning_level_m") is not None:
            details.append(f"模拟警戒水位：{identity['warning_level_m']} m")
        sector, industry = identity.get("sector"), identity.get("industry")
        if sector and industry:
            details.append(f"所属分类：{sector} / {industry}")
        elif sector:
            details.append(f"所属领域：{sector}")
        elif industry:
            details.append(f"所属领域：{industry}")
        if identity.get("exchange"):
            details.append(f"站点标识：{identity['exchange']}")

    if details:
        context += (
            f" 已解析身份：{'；'.join(details)}。"
            "除非某个工具结果明确推翻这一解析身份，否则不要替换成其他站点。"
        )
    return context


def get_area_context_from_state(state: Mapping[str, Any]) -> str:
    """返回当前运行的站点上下文。

    优先使用运行开始时一次性解析并存入状态的上下文
    （见 ``TradingAgentsGraph.resolve_area_context``）。
    当状态未携带该上下文时（裸状态、测试），退回到仅用站点编号的上下文
    —— 不发起网络查询，从而避免在图执行中途被迫调用外部数据源。
    """
    context = state.get("area_context")
    if isinstance(context, str) and context.strip():
        return context
    return build_area_context(
        str(state["area_of_interest"]),
        state.get("asset_type", "flood"),
    )


def create_msg_delete():
    def delete_messages(state):
        """清空消息并添加一个锚定上下文的占位消息。

        占位消息不能是裸的 ``"Continue"``：有些 OpenAI 兼容供应商会把它
        当作用户任务字面理解，从而输出关于 "continue" 一词的内容而不是分析
        站点（#888）。把它锚定到已解析的站点上下文与日期，能让下一个分析师
        即使供应商把占位消息当作独立请求，也保持聚焦任务。
        """
        messages = state["messages"]
        removal_operations = [RemoveMessage(id=m.id) for m in messages]

        area_context = get_area_context_from_state(state)
        analysis_date = state.get("analysis_date", "请求的日期")
        placeholder = HumanMessage(
            content=(
                f"继续完成你被分配的分析任务。"
                f"{area_context} 研判日期为 {analysis_date}。"
            )
        )
        return {"messages": removal_operations + [placeholder]}

    return delete_messages
