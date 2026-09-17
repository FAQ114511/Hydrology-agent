"""社会影响分析师：根据本地可用资料评估防汛事件的社会影响。"""

from datetime import datetime, timedelta

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.schemas import SocialImpactReport, render_social_impact_report
from tradingagents.agents.utils.agent_utils import (
    get_area_context_from_state,
    get_language_instruction,
    get_rainfall_forecast,
    get_social_impact,
)
from tradingagents.agents.utils.structured import (
    NO_EXTERNAL_TOOLS,
    bind_structured,
    invoke_structured_or_freetext,
)
def _seven_days_back(analysis_date: str) -> str:
    return (datetime.strptime(analysis_date, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")


def create_social_impact_analyst(llm):
    """创建社会影响分析节点。"""
    structured_llm = bind_structured(llm, SocialImpactReport, "社会影响分析师")

    def social_impact_analyst_node(state):
        station = state["area_of_interest"]
        end_date = state["analysis_date"]
        start_date = _seven_days_back(end_date)
        area_context = get_area_context_from_state(state)
        impact_block = get_social_impact.func(station)
        rainfall_block = get_rainfall_forecast.func(station, start_date, end_date)

        system_message = _build_system_message(
            station=station,
            start_date=start_date,
            end_date=end_date,
            impact_block=impact_block,
            rainfall_block=rainfall_block,
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是与其他智能体协作的社会影响分析助手。"
                    "若上下文已包含 FINAL ALERT DECISION: **红色预警/橙色预警/黄色预警/蓝色预警**，则停止继续研判。"
                    "当前研判日期为 {current_date}，所有分析以此为准。{area_context}"
                    " " + NO_EXTERNAL_TOOLS +
                    "\n{system_message}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(current_date=end_date)
        prompt = prompt.partial(area_context=area_context)

        # Format the template into a concrete message list so the structured
        # and free-text paths receive the same input. No bind_tools — the
        # data is already in the prompt.
        formatted_messages = prompt.format_messages(messages=state["messages"])

        report_text = invoke_structured_or_freetext(
            structured_llm,
            llm,
            formatted_messages,
            render_social_impact_report,
            "社会影响分析师",
        )

        return {
            "messages": [AIMessage(content=report_text)],
            "social_impact_report": report_text,
        }

    return social_impact_analyst_node


def _build_system_message(
    *,
    station: str,
    start_date: str,
    end_date: str,
    impact_block: str,
    rainfall_block: str,
) -> str:
    """组装包含预取数据块的社会影响分析提示词。"""
    return f"""你是一名社会影响分析师。请评估 {station} 站相关区域在 {start_date} 至 {end_date} 的防汛社会影响。

## 已预取数据

### 社会影响资料
<start_of_social_impact>
{impact_block}
<end_of_social_impact>

### 同期降雨资料
<start_of_rainfall>
{rainfall_block}
<end_of_rainfall>

## 分析要求

1. 关注受影响人口、低洼区与沿河居民、道路交通、农业生产、学校医院等重要设施、转移安置需求和公众关注度。
2. 明确区分观测事实、预报信息与推断，不得把缺失信息写成已发生事实。
3. 任一数据块含 NO_DATA_AVAILABLE 时，必须在报告中说明缺口，并相应降低 confidence。
4. 数据不足时采用轻微影响或一般影响的审慎判断，除非已有明确证据支持严重影响。
5. narrative 必须包含逐项证据、主要不确定性、潜在影响链条及 Markdown 汇总表。

## 输出字段

- overall_band：严重影响 / 一般影响 / 轻微影响，恰好选择一个。
- overall_score：0–10 的影响强度，与 overall_band 一致。
- confidence：low / medium / high，依据资料质量与完整性。
- narrative：完整社会影响报告及 Markdown 汇总表。

{get_language_instruction()}"""
