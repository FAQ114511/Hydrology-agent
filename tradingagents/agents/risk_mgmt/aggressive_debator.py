from tradingagents.agents.utils.agent_utils import (
    get_area_context_from_state,
    get_language_instruction,
    opponent_argument_or_opening,
)


def create_aggressive_debator(llm):
    def aggressive_node(state) -> dict:
        response_debate_state = state["response_debate_state"]
        history = response_debate_state.get("history", "")
        aggressive_history = response_debate_state.get("aggressive_history", "")

        current_conservative_response = opponent_argument_or_opening(
            response_debate_state.get("current_conservative_response", ""), "保守型研判员"
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

        prompt = f"""你是激进型响应研判员，倾向在灾害后果可能较大时提前提高预警、扩大巡查和做好转移准备。请评估处置方案，并直接回应保守型和中立型研判员，指出其谨慎判断可能遗漏的风险。处置方案如下：

{dispatch_plan}

必须根据以下资料提出有说服力的论点，不得把缺失数据写成事实：

{area_context}
水文报告：{hydrology_report}
社会影响报告：{social_impact_report}
气象报告：{meteorology_report}
环境风险报告：{environment_report}
当前辩论历史：{history}
保守型研判员上一轮观点：{current_conservative_response}
中立型研判员上一轮观点：{current_neutral_response}

重点说明为何更早、更强的响应能降低人员和设施损失。以自然对话方式辩论，不使用特殊格式。""" + get_language_instruction()

        response = llm.invoke(prompt)

        argument = f"Aggressive Analyst: {response.content}"

        new_response_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": aggressive_history + "\n" + argument,
            "conservative_history": response_debate_state.get("conservative_history", ""),
            "neutral_history": response_debate_state.get("neutral_history", ""),
            "latest_speaker": "Aggressive",
            "current_aggressive_response": argument,
            "current_conservative_response": response_debate_state.get("current_conservative_response", ""),
            "current_neutral_response": response_debate_state.get(
                "current_neutral_response", ""
            ),
            "count": response_debate_state["count"] + 1,
        }

        return {"response_debate_state": new_response_debate_state}

    return aggressive_node
