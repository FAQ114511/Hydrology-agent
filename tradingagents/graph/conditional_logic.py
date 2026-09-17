# TradingAgents/graph/conditional_logic.py

from tradingagents.agents.utils.agent_states import AgentState


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""

    def __init__(self, max_debate_rounds=1, max_risk_discuss_rounds=1):
        """Initialize with configuration parameters."""
        self.max_debate_rounds = max_debate_rounds
        self.max_risk_discuss_rounds = max_risk_discuss_rounds

    def should_continue_market(self, state: AgentState):
        """Determine if the hydrology analyst's tool round should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_market"
        return "Msg Clear Hydrology"

    def should_continue_social(self, state: AgentState):
        """Determine if the social-impact analyst's tool round should continue.

        Method name keeps the legacy ``social`` wire value to match the
        ``selected_analysts`` keys and ``tool_nodes`` map; the returned
        ``clear_node`` label matches the node registered by the execution plan.
        """
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_social"
        return "Msg Clear Social Impact"

    def should_continue_news(self, state: AgentState):
        """Determine if the meteorology analyst's tool round should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_news"
        return "Msg Clear Meteorology"

    def should_continue_fundamentals(self, state: AgentState):
        """Determine if the environment analyst's tool round should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_fundamentals"
        return "Msg Clear Environment"

    def should_continue_debate(self, state: AgentState) -> str:
        """Determine if the risk/safety debate should continue."""

        if (
            state["risk_debate_state"]["count"] >= 2 * self.max_debate_rounds
        ):  # 3 rounds of back-and-forth between 2 agents
            return "Assessment Manager"
        if state["risk_debate_state"]["current_response"].startswith("Risk Analyst"):
            return "Safety Researcher"
        return "Risk Researcher"

    def should_continue_risk_analysis(self, state: AgentState) -> str:
        """Determine if the response debate should continue."""
        if (
            state["response_debate_state"]["count"] >= 3 * self.max_risk_discuss_rounds
        ):  # 3 rounds of back-and-forth between 3 agents
            return "Alert Manager"
        if state["response_debate_state"]["latest_speaker"].startswith("Aggressive"):
            return "Conservative Analyst"
        if state["response_debate_state"]["latest_speaker"].startswith("Conservative"):
            return "Neutral Analyst"
        return "Aggressive Analyst"
