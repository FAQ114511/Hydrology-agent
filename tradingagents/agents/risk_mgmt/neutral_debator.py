from tradingagents.agents.utils.agent_utils import (
    get_area_context_from_state,
    get_language_instruction,
    opponent_argument_or_opening,
)


def create_neutral_debator(llm):
    def neutral_node(state) -> dict:
        response_debate_state = state["response_debate_state"]
        history = response_debate_state.get("history", "")
        neutral_history = response_debate_state.get("neutral_history", "")

        current_aggressive_response = opponent_argument_or_opening(
            response_debate_state.get("current_aggressive_response", ""), "激进型研判员"
        )
        current_conservative_response = opponent_argument_or_opening(
            response_debate_state.get("current_conservative_response", ""), "保守型研判员"
        )

        hydrology_report = state["hydrology_report"]
        social_impact_report = state["social_impact_report"]
        meteorology_report = state["meteorology_report"]
        environment_report = state["environment_report"]
        area_context = get_area_context_from_state(state)

        dispatch_plan = state["dispatch_plan"]

        prompt = f"""你是中立型响应研判员，负责平衡灾害后果、预报不确定性、监测证据和响应成本。请评估处置方案，并同时审查激进型与保守型研判员可能存在的偏差。处置方案如下：

{dispatch_plan}

依据以下资料提出适度、可持续且可随新观测调整的响应策略：

{area_context}
水文报告：{hydrology_report}
社会影响报告：{social_impact_report}
气象报告：{meteorology_report}
环境风险报告：{environment_report}
当前辩论历史：{history}
激进型研判员上一轮观点：{current_aggressive_response}
保守型研判员上一轮观点：{current_conservative_response}

直接回应双方论点，指出哪些结论有数据支撑、哪些仍属不确定。以自然对话方式辩论，不使用特殊格式。""" + get_language_instruction()

        response = llm.invoke(prompt)

        argument = f"Neutral Analyst: {response.content}"

        new_response_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": response_debate_state.get("aggressive_history", ""),
            "conservative_history": response_debate_state.get("conservative_history", ""),
            "neutral_history": neutral_history + "\n" + argument,
            "latest_speaker": "Neutral",
            "current_aggressive_response": response_debate_state.get(
                "current_aggressive_response", ""
            ),
            "current_conservative_response": response_debate_state.get("current_conservative_response", ""),
            "current_neutral_response": argument,
            "count": response_debate_state["count"] + 1,
        }

        return {"response_debate_state": new_response_debate_state}

    return neutral_node
