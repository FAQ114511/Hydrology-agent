"""处置员：把研判经理的方案转化为具体处置建议。"""

from __future__ import annotations

import functools

from langchain_core.messages import AIMessage

from tradingagents.agents.schemas import DispatchProposal, render_dispatch_proposal
from tradingagents.agents.utils.agent_utils import (
    get_area_context_from_state,
    get_language_instruction,
)
from tradingagents.agents.utils.structured import (
    NO_EXTERNAL_TOOLS,
    bind_structured,
    invoke_structured_or_freetext,
)


def create_dispatcher(llm):
    structured_llm = bind_structured(llm, DispatchProposal, "Dispatcher")

    def dispatcher_node(state, name):
        area_name = state["area_of_interest"]
        area_context = get_area_context_from_state(state)
        assessment_plan = state["assessment_plan"]
        hydrology_report = (state["hydrology_report"] or "").strip()

        if hydrology_report:
            grounding = (
                "具体处置动作必须以水文报告中的水位、流量、降雨和趋势证据为依据，"
                "并使用研判方案确定响应强度。"
            )
            report_section = f"水文报告：\n{hydrology_report}\n\n"
        else:
            grounding = ""
            report_section = ""

        messages = [
            {
                "role": "system",
                "content": (
                    "你是防汛处置员，负责把研判结果转化为具体行动建议。"
                    "在启动应急响应、加强监测预警、维持常规监测中恰好选择一项。"
                    + grounding
                    + "说明处置理由，并可给出响应等级、监测频次、巡查或转移准备。"
                    "没有数据支持时不得编造精确范围或响应级别。"
                    + NO_EXTERNAL_TOOLS
                    + get_language_instruction()
                ),
            },
            {
                "role": "user",
                "content": (
                    f"以下是 {area_name} 的研判方案。{area_context}\n\n"
                    f"{report_section}"
                    f"研判方案：\n{assessment_plan}\n\n"
                    "请作出有依据、可执行的防汛处置建议。"
                ),
            },
        ]

        dispatch_plan = invoke_structured_or_freetext(
            structured_llm,
            llm,
            messages,
            render_dispatch_proposal,
            "Dispatcher",
        )

        return {
            "messages": [AIMessage(content=dispatch_plan)],
            "dispatch_plan": dispatch_plan,
            "sender": name,
        }

    return functools.partial(dispatcher_node, name="Dispatcher")
