from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_utils import (
    get_area_context_from_state,
    get_forward_forecast,
    get_language_instruction,
    get_rainfall_forecast,
    get_regional_indicators,
    get_realtime_weather,
    search_flood_knowledge,
)


def create_meteorology_analyst(llm):
    def meteorology_analyst_node(state):
        current_date = state["analysis_date"]
        area_context = get_area_context_from_state(state)

        tools = [
            get_rainfall_forecast,
            get_realtime_weather,
            get_regional_indicators,
            get_forward_forecast,
            search_flood_knowledge,
        ]

        system_message = (
            "你是一名气象分析师，负责评估研判区域近期和未来的降雨过程及气象风险。"
            "使用 get_realtime_weather 获取站点实时降雨、累积降雨与土壤墒情，使用 get_rainfall_forecast 获取日尺度降雨预报；"
            "仅在确有必要时用 get_regional_indicators 和 get_forward_forecast 补充区域背景与前瞻信息；"
            "调用这两个工具时必须传入当前站点编号，不要使用其他站点的数据。"
            "涉及站点警戒阈值、气象研判规则、处置规程或历史案例时，调用 search_flood_knowledge；"
            "使用后必须标注返回的 doc_id 和 source。该工具只补充规则与历史经验，不能替代实时观测或天气预报。"
            "get_realtime_weather 返回的是网格模式实况而非地面气象站观测，引用时必须注明这一点。"
            "报告应覆盖降雨量级、持续时间、空间影响、未来趋势、数据缺口及其对水位上涨的可能影响。"
            "当 get_realtime_weather 提示历史日期不可用或数据缺口时，必须如实写明，不能用历史模拟数据冒充实时气象。"
            "本地工具返回 NO_DATA_AVAILABLE 时必须如实写明，不能把历史观测当作未来预报，也不能编造天气过程。"
            "报告末尾附 Markdown 表格汇总时间窗、气象信号、证据来源、可信度与风险含义。"
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是与其他智能体协作的气象分析助手。使用工具推进分析；数据不足时明确报告缺口。"
                    "若上下文已包含 FINAL ALERT DECISION: **红色预警/橙色预警/黄色预警/蓝色预警**，则停止继续研判。"
                    "你可使用以下工具：{tool_names}。"
                    "当前研判日期为 {current_date}，所有分析与工具日期范围以此为准。{area_context}\n"
                    "{system_message}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(area_context=area_context)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "meteorology_report": report,
        }

    return meteorology_analyst_node
