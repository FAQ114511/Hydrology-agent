from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_utils import (
    get_area_context_from_state,
    get_environment_risk,
    get_language_instruction,
    get_river_flow,
    get_soil_moisture,
    search_flood_knowledge,
    get_water_storage,
)


def create_environment_analyst(llm):
    def environment_analyst_node(state):
        current_date = state["analysis_date"]
        area_context = get_area_context_from_state(state)

        tools = [
            get_environment_risk,
            get_water_storage,
            get_river_flow,
            get_soil_moisture,
            search_flood_knowledge,
        ]

        system_message = (
            "你是一名环境风险分析师，负责评估站点所在区域的产汇流条件与承灾环境。"
            "使用 get_environment_risk 获取综合环境风险，使用 get_water_storage、get_river_flow 和"
            " get_soil_moisture 分别检查蓄水/库容、河道流量和土壤墒情。"
            "涉及站点警戒阈值、处置规程、承灾规则或历史案例时，调用 search_flood_knowledge；"
            "使用后必须标注返回的 doc_id 和 source。该工具只补充规则与历史经验，不能替代实时观测。"
            "报告应覆盖土壤饱和度、蓄水余量、河道行洪能力、地形地质、堤防或低洼区风险、"
            "可用数据的时效性及数据缺口。工具未提供数据时应明确说明无法判断，不得虚构。"
            "报告末尾附 Markdown 表格汇总环境因素、当前状态、证据来源和风险影响。"
            + get_language_instruction(),
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是与其他智能体协作的环境风险分析助手。使用工具推进分析；数据不足时明确报告缺口。"
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
            "environment_report": report,
        }

    return environment_analyst_node
