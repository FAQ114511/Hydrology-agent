from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_utils import (
    get_area_context_from_state,
    get_hydrology_indicators,
    get_language_instruction,
    get_observations,
    get_verified_observation_snapshot,
)


def create_hydrology_analyst(llm):

    def hydrology_analyst_node(state):
        current_date = state["analysis_date"]
        area_context = get_area_context_from_state(state)

        tools = [
            get_observations,
            get_hydrology_indicators,
            get_verified_observation_snapshot,
        ]

        system_message = (
            """你是一名水文分析师，负责根据站点观测判断当前水情及其变化趋势。

必须先调用 get_observations 获取水位、流量和降雨观测，再按需调用 get_hydrology_indicators。可用指标为：
- water_level_ma3、water_level_ma7、water_level_ma30：短、中期平均水位；
- water_level_change_1d、water_level_change_7d：1 日和 7 日水位变化；
- rainfall_1d、rainfall_sum_7d：当日及 7 日累计雨量；
- flow_ma7：7 日平均流量。

写报告前必须调用 get_verified_observation_snapshot，并把它作为所有精确水位、流量、雨量和指标数值的真值来源。若其他工具与快照冲突，明确指出差异，不得自行折中或编造数值。

报告应包括：当前水位与近期变化、涨落水趋势、流量响应、前期累计降雨、异常突变、数据质量及对防汛预警的含义。只能依据工具返回的数据作判断；没有警戒水位数据时不得声称已经超警。报告末尾附 Markdown 表格汇总关键指标、趋势、证据日期和风险含义。"""
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是与其他智能体协作的水文分析助手。使用提供的工具推进分析；"
                    "如数据不足，请明确报告缺口，不得编造。若上下文已包含"
                    " FINAL ALERT DECISION: **红色预警/橙色预警/黄色预警/蓝色预警**，则停止继续研判。"
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
            "hydrology_report": report,
        }

    return hydrology_analyst_node
