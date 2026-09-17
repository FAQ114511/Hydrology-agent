from tradingagents.agents.utils.agent_utils import (
    get_area_context_from_state,
    get_language_instruction,
    opponent_argument_or_opening,
)


def create_risk_researcher(llm):
    def risk_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        high_risk_history = risk_debate_state.get("high_risk_history", "")

        current_response = opponent_argument_or_opening(
            risk_debate_state.get("current_response", ""), "安全研判员"
        )
        hydrology_report = state["hydrology_report"]
        social_impact_report = state["social_impact_report"]
        meteorology_report = state["meteorology_report"]
        environment_report = state["environment_report"]
        area_context = get_area_context_from_state(state)

        prompt = f"""你是风险研判员，负责提出支持升级防汛预警的有力、基于证据的论点。利用已有报告识别水位快速上涨、累计降雨、流量增大、环境承载不足和社会影响等风险，并直接回应安全研判员的质疑。

重点关注：
- 水文危险性：水位、流量、涨水速率和累计降雨是否表明风险正在增强。
- 气象与环境条件：未来降雨、土壤墒情、蓄水与河道行洪能力是否可能放大风险。
- 社会影响：低洼区、交通、人口和重要设施是否面临潜在影响。
- 反驳：用具体数据审查安全侧是否低估风险或过度依赖缺失数据。
- 表达：直接回应对方观点，以对话方式辩论，不要只罗列资料。

可用资料：
{area_context}
水文报告：{hydrology_report}
社会影响报告：{social_impact_report}
气象报告：{meteorology_report}
环境风险报告：{environment_report}
辩论历史：{history}
安全研判员上一轮观点：{current_response}
请提出支持升级预警的论点，同时明确区分实测证据、推断和数据缺口。
""" + get_language_instruction()

        response = llm.invoke(prompt)

        argument = f"Risk Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "high_risk_history": high_risk_history + "\n" + argument,
            "safety_history": risk_debate_state.get("safety_history", ""),
            "current_response": argument,
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return risk_node
