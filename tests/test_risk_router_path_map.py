"""Conditional-router contracts for the hydrology debate graph."""

import pytest

from tradingagents.graph.conditional_logic import ConditionalLogic
from tradingagents.graph.setup import DEBATE_PATH_MAP, RISK_ANALYSIS_PATH_MAP


def _risk_state(current_response, count=0):
    return {
        "risk_debate_state": {
            "current_response": current_response,
            "count": count,
        }
    }


def _response_state(latest_speaker, count=0):
    return {
        "response_debate_state": {
            "latest_speaker": latest_speaker,
            "count": count,
        }
    }


@pytest.mark.unit
@pytest.mark.parametrize(
    "current_response, expected",
    [
        ("Risk Analyst: 水位接近警戒", "Safety Researcher"),
        ("Safety Analyst: 数据不足", "Risk Researcher"),
        ("", "Risk Researcher"),
        ("unexpected speaker", "Risk Researcher"),
    ],
)
def test_risk_debate_router_return_always_routable(current_response, expected):
    logic = ConditionalLogic(max_debate_rounds=1)
    target = logic.should_continue_debate(_risk_state(current_response))
    assert target == expected
    assert target in DEBATE_PATH_MAP


@pytest.mark.unit
def test_risk_debate_terminates_at_round_limit():
    logic = ConditionalLogic(max_debate_rounds=1)
    assert logic.should_continue_debate(_risk_state("Risk Analyst", count=2)) == "Assessment Manager"


@pytest.mark.unit
@pytest.mark.parametrize(
    "latest_speaker, expected",
    [
        ("Aggressive", "Conservative Analyst"),
        ("Conservative", "Neutral Analyst"),
        ("Neutral", "Aggressive Analyst"),
        ("", "Aggressive Analyst"),
        ("unexpected speaker", "Aggressive Analyst"),
    ],
)
def test_response_debate_router_return_always_routable(latest_speaker, expected):
    logic = ConditionalLogic(max_risk_discuss_rounds=1)
    target = logic.should_continue_risk_analysis(_response_state(latest_speaker))
    assert target == expected
    assert target in RISK_ANALYSIS_PATH_MAP


@pytest.mark.unit
def test_response_debate_terminates_at_round_limit():
    logic = ConditionalLogic(max_risk_discuss_rounds=1)
    assert logic.should_continue_risk_analysis(_response_state("Neutral", count=3)) == "Alert Manager"
