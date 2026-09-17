"""Opening speakers must not invent an opponent argument."""

from unittest.mock import MagicMock

import pytest

from tradingagents.agents.researchers.bear_researcher import create_safety_researcher
from tradingagents.agents.researchers.bull_researcher import create_risk_researcher
from tradingagents.agents.risk_mgmt.aggressive_debator import create_aggressive_debator
from tradingagents.agents.risk_mgmt.conservative_debator import create_conservative_debator
from tradingagents.agents.risk_mgmt.neutral_debator import create_neutral_debator
from tradingagents.agents.utils.agent_utils import opponent_argument_or_opening

_REPORTS = {
    "area_of_interest": "XIANGJIANG",
    "asset_type": "flood",
    "hydrology_report": "水文报告",
    "social_impact_report": "社会报告",
    "meteorology_report": "气象报告",
    "environment_report": "环境报告",
}


def _capturing_llm(captured: dict):
    llm = MagicMock()
    llm.invoke.side_effect = lambda prompt: (
        captured.__setitem__("prompt", prompt) or MagicMock(content="argument")
    )
    return llm


def _risk_state(current_response=""):
    return {
        **_REPORTS,
        "risk_debate_state": {
            "history": "",
            "high_risk_history": "",
            "safety_history": "",
            "current_response": current_response,
            "count": 0,
        },
    }


def _response_state(**responses):
    state = {
        "current_aggressive_response": "",
        "current_conservative_response": "",
        "current_neutral_response": "",
        "history": "",
        "aggressive_history": "",
        "conservative_history": "",
        "neutral_history": "",
        "latest_speaker": "",
        "count": 0,
    }
    state.update(responses)
    return {**_REPORTS, "dispatch_plan": "处置方案", "response_debate_state": state}


@pytest.mark.unit
def test_helper_marks_empty_and_passes_through():
    assert "尚未发言" in opponent_argument_or_opening("", "风险研判员")
    assert opponent_argument_or_opening("  real point ", "风险研判员") == "real point"


@pytest.mark.unit
@pytest.mark.parametrize(
    "factory", [create_risk_researcher, create_safety_researcher]
)
def test_risk_debater_opening_has_no_phantom_opponent(factory):
    captured = {}
    factory(_capturing_llm(captured))(_risk_state())
    assert "尚未发言" in captured["prompt"]


@pytest.mark.unit
def test_risk_debater_passes_real_opponent_argument():
    captured = {}
    state = _risk_state("Safety Analyst: 当前数据不足")
    create_risk_researcher(_capturing_llm(captured))(state)
    assert "当前数据不足" in captured["prompt"]
    assert "尚未发言" not in captured["prompt"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "factory", [create_aggressive_debator, create_conservative_debator, create_neutral_debator]
)
def test_response_debater_opening_has_no_phantom_opponent(factory):
    captured = {}
    factory(_capturing_llm(captured))(_response_state())
    assert captured["prompt"].count("尚未发言") == 2


@pytest.mark.unit
def test_response_debater_passes_real_opponent_arguments():
    captured = {}
    state = _response_state(
        current_conservative_response="Conservative Analyst: 控制响应成本",
        current_neutral_response="Neutral Analyst: 维持监测",
    )
    create_aggressive_debator(_capturing_llm(captured))(state)
    assert "控制响应成本" in captured["prompt"]
    assert "维持监测" in captured["prompt"]
