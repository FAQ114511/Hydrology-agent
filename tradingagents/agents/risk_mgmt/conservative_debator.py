from tradingagents.agents.utils.agent_utils import (
    get_area_context_from_state,
    get_language_instruction,
    opponent_argument_or_opening,
)


def create_conservative_debator(llm):
    def conservative_node(state) -> dict:
        response_debate_state = state["response_debate_state"]
        history = response_debate_state.get("history", "")
        conservative_history = response_debate_state.get("conservative_history", "")

        current_aggressive_response = opponent_argument_or_opening(
            response_debate_state.get("current_aggressive_response", ""), "激进型研判员"
        )
        current_neutral_response = opponent_argument_or_opening(
            response_debate_state.get("current_neutral_response", ""), "中立型研判员"
        )

        hydrology_report = state["hydrology_report"]
        social_impact_report = state["social_impact_report"]
        meteorology_report = state["meteorology_report"]
        environment_report = state["environment_report"]
        area_context = get_area_context_from_state(state)

        dispatch_plan = state["dispatch_plan"]

        prompt = f"""你是保守型响应研判员，负责避免证据不足时过度提高预警，同时确保必要监测和安全措施不被削弱。请评估处置方案，并审查激进型与中立型研判员是否夸大风险。处置方案如下：

{dispatch_plan}

请依据以下资料提出更审慎、资源配置合理的响应建议：

{area_context}
水文报告：{hydrology_report}
社会影响报告：{social_impact_report}
气象报告：{meteorology_report}
环境风险报告：{environment_report}
当前辩论历史：{history}
激进型研判员上一轮观点：{current_aggressive_response}
中立型研判员上一轮观点：{current_neutral_response}

不得把没有数据当作安全证据。直接回应对方观点，以自然对话方式辩论，不使用特殊格式。""" + get_language_instruction()

        response = llm.invoke(prompt)

        argument = f"Conservative Analyst: {response.content}"

        new_response_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": response_debate_state.get("aggressive_history", ""),
            "conservative_history": conservative_history + "\n" + argument,
            "neutral_history": response_debate_state.get("neutral_history", ""),
            "latest_speaker": "Conservative",
            "current_aggressive_response": response_debate_state.get(
                "current_aggressive_response", ""
            ),
            "current_conservative_response": argument,
            "current_neutral_response": response_debate_state.get(
                "current_neutral_response", ""
            ),
            "count": response_debate_state["count"] + 1,
        }

        return {"response_debate_state": new_response_debate_state}

    return conservative_node
