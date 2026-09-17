"""研判经理：把风险/安全双方辩论整理成处置员可用的结构化研判方案。"""

from __future__ import annotations

from tradingagents.agents.schemas import AssessmentPlan, render_assessment_plan
from tradingagents.agents.utils.agent_utils import (
    get_area_context_from_state,
    get_language_instruction,
)
from tradingagents.agents.utils.structured import (
    NO_EXTERNAL_TOOLS,
    bind_structured,
    invoke_structured_or_freetext,
)


def create_assessment_manager(llm):
    structured_llm = bind_structured(llm, AssessmentPlan, "Assessment Manager")

    def assessment_manager_node(state) -> dict:
        area_context = get_area_context_from_state(state)
        history = state["risk_debate_state"].get("history", "")

        risk_debate_state = state["risk_debate_state"]

        prompt = f"""你是研判经理和辩论主持人。请客观评估本轮风险/安全辩论，为处置员形成明确、可执行的防汛研判方案。

{area_context}

---

**预警等级**（恰好选择一个）：
- **红色预警**：极高风险，需要立即启动最高级别防汛应急处置
- **橙色预警**：高风险，需要启动应急响应并密切跟踪
- **黄色预警**：风险明显，需要加强监测、巡查和准备
- **蓝色预警**：存在一般风险或证据不足，维持常规监测并关注变化

仅当最有力证据明确支持时才提高预警等级。证据平衡、相互冲突、含糊或不足时选择蓝色预警；不能为了显得果断而夸大风险。独立评估双方论据，不受发言先后影响。

---

**辩论历史：**
{history}

{NO_EXTERNAL_TOOLS}""" + get_language_instruction()

        assessment_plan = invoke_structured_or_freetext(
            structured_llm,
            llm,
            prompt,
            render_assessment_plan,
            "Assessment Manager",
        )

        new_risk_debate_state = {
            "judge_decision": assessment_plan,
            "history": risk_debate_state.get("history", ""),
            "safety_history": risk_debate_state.get("safety_history", ""),
            "high_risk_history": risk_debate_state.get("high_risk_history", ""),
            "current_response": assessment_plan,
            "count": risk_debate_state["count"],
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "assessment_plan": assessment_plan,
        }

    return assessment_manager_node
