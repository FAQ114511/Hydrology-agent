"""Prompt anchors for hydrology decision agents."""

from unittest.mock import MagicMock

from tradingagents.agents.managers.portfolio_manager import create_alert_manager
from tradingagents.agents.managers.research_manager import create_assessment_manager
from tradingagents.agents.trader.trader import create_dispatcher
from tradingagents.agents.utils.structured import NO_EXTERNAL_TOOLS


def _plain_llm():
    llm = MagicMock()
    llm.with_structured_output.side_effect = AttributeError("unsupported")
    llm.invoke.return_value = MagicMock(content="fallback result")
    return llm


def test_assessment_manager_prompt_is_station_anchored():
    llm = _plain_llm()
    state = {
        "area_of_interest": "XIANGJIANG",
        "area_context": "XIANGJIANG 湘江示范站",
        "risk_debate_state": {"history": "风险与安全辩论", "count": 2},
    }
    create_assessment_manager(llm)(state)
    prompt = llm.invoke.call_args.args[0]
    assert "XIANGJIANG" in prompt
    assert NO_EXTERNAL_TOOLS in prompt


def test_alert_manager_prompt_contains_dispatch_and_history():
    llm = _plain_llm()
    state = {
        "area_of_interest": "XIANGJIANG",
        "area_context": "XIANGJIANG 湘江示范站",
        "assessment_plan": "研判方案",
        "dispatch_plan": "处置方案",
        "past_context": "历史黄色预警",
        "response_debate_state": {
            "history": "三方辩论",
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "count": 3,
        },
    }
    create_alert_manager(llm)(state)
    prompt = llm.invoke.call_args.args[0]
    assert "处置方案" in prompt
    assert "历史黄色预警" in prompt
    assert NO_EXTERNAL_TOOLS in prompt


def test_dispatcher_prompt_requires_hydrology_grounding():
    llm = _plain_llm()
    state = {
        "area_of_interest": "XIANGJIANG",
        "area_context": "XIANGJIANG 湘江示范站",
        "assessment_plan": "黄色预警研判方案",
        "hydrology_report": "水位 35.5 m，流量 3300 m3/s",
    }
    create_dispatcher(llm)(state)
    messages = llm.invoke.call_args.args[0]
    prompt = "\n".join(message["content"] for message in messages)
    assert "水位 35.5 m" in prompt
    assert NO_EXTERNAL_TOOLS in prompt
