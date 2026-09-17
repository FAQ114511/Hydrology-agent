"""预警决策员：综合响应辩论并给出最终防汛预警等级。"""

from __future__ import annotations

from tradingagents.agents.schemas import AlertDecision, render_alert_decision
from tradingagents.agents.utils.agent_utils import (
    get_area_context_from_state,
    get_language_instruction,
)
from tradingagents.agents.utils.structured import (
    NO_EXTERNAL_TOOLS,
    bind_structured,
    invoke_structured_or_freetext,
)


def create_alert_manager(llm):
    structured_llm = bind_structured(llm, AlertDecision, "Alert Manager")

    def alert_manager_node(state) -> dict:
        area_context = get_area_context_from_state(state)

        history = state["response_debate_state"]["history"]
        response_debate_state = state["response_debate_state"]
        assessment_plan = state["assessment_plan"]
        dispatch_plan = state["dispatch_plan"]

        past_context = state.get("past_context", "")
        lessons_line = (
            f"- 同站点历史预警、实际水情与处置经验：\n{past_context}\n"
            if past_context
            else ""
        )

        prompt = f"""你是预警决策员。请综合三方响应辩论，给出最终防汛预警等级和行动结论。

{area_context}

---

**预警等级**（恰好选择一个）：
- **红色预警**：极高风险，立即启动最高级别应急处置
- **橙色预警**：高风险，启动应急响应并严密监测
- **黄色预警**：风险明显，加强监测、巡查和准备
- **蓝色预警**：一般风险或证据不足，维持常规监测并持续关注

**上下文：**
- 研判经理方案：**{assessment_plan}**
- 处置员方案：**{dispatch_plan}**
{lessons_line}
**响应研判历史：**
{history}

---

所有结论必须基于分析师的具体证据。只有证据明确支持时才提高等级；证据平衡、明显冲突、含糊或不足时选择蓝色预警，不能为了显得果断而强行升级。独立评估三方论点，不受发言顺序影响。

{NO_EXTERNAL_TOOLS}{get_language_instruction()}"""

        final_alert_decision = invoke_structured_or_freetext(
            structured_llm,
            llm,
            prompt,
            render_alert_decision,
            "Alert Manager",
        )

        new_response_debate_state = {
            "judge_decision": final_alert_decision,
            "history": response_debate_state["history"],
            "aggressive_history": response_debate_state["aggressive_history"],
            "conservative_history": response_debate_state["conservative_history"],
            "neutral_history": response_debate_state["neutral_history"],
            "latest_speaker": "Judge",
            "current_aggressive_response": response_debate_state["current_aggressive_response"],
            "current_conservative_response": response_debate_state["current_conservative_response"],
            "current_neutral_response": response_debate_state["current_neutral_response"],
            "count": response_debate_state["count"],
        }

        return {
            "response_debate_state": new_response_debate_state,
            "final_alert_decision": final_alert_decision,
        }

    return alert_manager_node
