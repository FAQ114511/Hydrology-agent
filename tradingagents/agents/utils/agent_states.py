from typing import Annotated

from langgraph.graph import MessagesState
from typing_extensions import TypedDict


# 风险研判辩论状态（原 InvestDebateState）
class RiskDebateState(TypedDict):
    high_risk_history: Annotated[
        str, "风险研判员（主张升级预警）的对话历史"
    ]
    safety_history: Annotated[
        str, "安全研判员（主张风险可控）的对话历史"
    ]
    history: Annotated[str, "对话历史"]
    current_response: Annotated[str, "最新发言"]
    judge_decision: Annotated[str, "研判经理的最终裁定"]
    count: Annotated[int, "当前对话轮数"]


# 响应处置辩论状态（原 RiskDebateState）
class ResponseDebateState(TypedDict):
    aggressive_history: Annotated[
        str, "激进型研判员的对话历史"
    ]
    conservative_history: Annotated[
        str, "保守型研判员的对话历史"
    ]
    neutral_history: Annotated[
        str, "中立型研判员的对话历史"
    ]
    history: Annotated[str, "对话历史"]
    latest_speaker: Annotated[str, "上一位发言者"]
    current_aggressive_response: Annotated[str, "激进型研判员的最新发言"]
    current_conservative_response: Annotated[str, "保守型研判员的最新发言"]
    current_neutral_response: Annotated[str, "中立型研判员的最新发言"]
    judge_decision: Annotated[str, "预警决策员的裁定"]
    count: Annotated[int, "当前对话轮数"]


class AgentState(MessagesState):
    area_of_interest: Annotated[str, "需要研判的区域/水文站点"]
    asset_type: Annotated[str, "监测场景类型，如 flood（防汛）"]
    area_context: Annotated[str, "运行开始时解析出的站点确定性身份信息"]
    analysis_date: Annotated[str, "研判所依据的日期"]

    sender: Annotated[str, "发送该消息的智能体"]

    # 分析阶段
    hydrology_report: Annotated[str, "水文分析师报告"]
    social_impact_report: Annotated[str, "社会影响分析师报告"]
    meteorology_report: Annotated[
        str, "气象分析师报告（实时气象与降雨预报）"
    ]
    environment_report: Annotated[str, "环境风险分析师报告"]

    # 风险研判辩论阶段
    risk_debate_state: Annotated[
        RiskDebateState, "风险升级与风险可控两侧的辩论状态"
    ]
    assessment_plan: Annotated[str, "研判经理生成的研判方案"]

    dispatch_plan: Annotated[str, "处置员生成的处置方案"]

    # 响应处置辩论阶段
    response_debate_state: Annotated[
        ResponseDebateState, "预警等级激进/保守/中性三方的辩论状态"
    ]
    final_alert_decision: Annotated[str, "预警决策员给出的最终防汛预警等级"]
    past_context: Annotated[str, "运行开始时注入的记忆日志上下文（同站点历史决策 + 跨站点经验教训）"]
