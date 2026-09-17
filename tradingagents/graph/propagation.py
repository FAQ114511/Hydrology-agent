# TradingAgents/graph/propagation.py

from typing import Any

from tradingagents.agents.utils.agent_states import (
    ResponseDebateState,
    RiskDebateState,
)


class Propagator:
    """负责图的状态初始化与推进。"""

    def __init__(self, max_recur_limit=100):
        """按配置参数初始化。"""
        self.max_recur_limit = max_recur_limit

    def create_initial_state(
        self,
        area_name: str,
        analysis_date: str,
        asset_type: str = "flood",
        past_context: str = "",
        area_context: str = "",
    ) -> dict[str, Any]:
        """构造智能体图的初始状态。

        ``area_context`` 是运行开始时一次性解析出的站点确定性身份字符串
        （见 ``TradingAgentsGraph.resolve_area_context``）。
        为空时，各智能体退回到只用站点编号的上下文
        （``get_area_context_from_state``，Step 3 改名）。
        """
        return {
            "messages": [("human", area_name)],
            "area_of_interest": area_name,
            "asset_type": asset_type,
            "area_context": area_context,
            "analysis_date": str(analysis_date),
            "past_context": past_context,
            "risk_debate_state": RiskDebateState(
                {
                    "high_risk_history": "",
                    "safety_history": "",
                    "history": "",
                    "current_response": "",
                    "judge_decision": "",
                    "count": 0,
                }
            ),
            "response_debate_state": ResponseDebateState(
                {
                    "aggressive_history": "",
                    "conservative_history": "",
                    "neutral_history": "",
                    "history": "",
                    "latest_speaker": "",
                    "current_aggressive_response": "",
                    "current_conservative_response": "",
                    "current_neutral_response": "",
                    "judge_decision": "",
                    "count": 0,
                }
            ),
            "hydrology_report": "",
            "environment_report": "",
            "social_impact_report": "",
            "meteorology_report": "",
        }

    def get_graph_args(self, callbacks: list | None = None) -> dict[str, Any]:
        """构造调用图时传入的参数。

        Args:
            callbacks: 可选的回调处理器列表，用于跟踪工具执行。
                       注意：LLM 相关的回调由 LLM 构造函数单独处理。
        """
        config = {"recursion_limit": self.max_recur_limit}
        if callbacks:
            config["callbacks"] = callbacks
        return {
            "stream_mode": "values",
            "config": config,
        }
