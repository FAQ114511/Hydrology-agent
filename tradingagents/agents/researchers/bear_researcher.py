from tradingagents.agents.utils.agent_utils import (
    get_area_context_from_state,
    get_language_instruction,
    opponent_argument_or_opening,
)


def create_safety_researcher(llm):
    def safety_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        safety_history = risk_debate_state.get("safety_history", "")

        current_response = opponent_argument_or_opening(
            risk_debate_state.get("current_response", ""), "风险研判员"
        )
        hydrology_report = state["hydrology_report"]
        social_impact_report = state["social_impact_report"]
        meteorology_report = state["meteorology_report"]
        environment_report = state["environment_report"]
        area_context = get_area_context_from_state(state)

        prompt = f"""你是安全研判员，负责提出风险可控或暂不升级防汛预警的有力、基于证据的论点。审查风险研判员的主张是否受到数据缺口、预报不确定性或过度推断影响。

重点关注：
- 水位和流量是否稳定，变化是否足以支持升级预警。
- 降雨预报、环境和社会影响资料是否缺失或可信度不足。
- 是否存在蓄水余量、河道行洪能力或趋势趋缓等风险缓冲证据。
- 用具体数据指出风险侧的薄弱环节，避免证据不足时过度预警。
- 直接回应风险研判员，以对话方式辩论，不要只罗列资料。

可用资料：
{area_context}
水文报告：{hydrology_report}
社会影响报告：{social_impact_report}
气象报告：{meteorology_report}
环境风险报告：{environment_report}
辩论历史：{history}
风险研判员上一轮观点：{current_response}
请提出风险可控或暂不升级预警的论点，同时不得把缺失数据当成安全证据。
""" + get_language_instruction()

        response = llm.invoke(prompt)

        argument = f"Safety Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "safety_history": safety_history + "\n" + argument,
            "high_risk_history": risk_debate_state.get("high_risk_history", ""),
            "current_response": argument,
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return safety_node
