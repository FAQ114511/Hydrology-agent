"""Rendering and fallback contracts for hydrology structured output."""

from unittest.mock import MagicMock

import pytest

from tradingagents.agents.schemas import (
    AlertDecision,
    AlertLevel,
    AssessmentPlan,
    DispatchAction,
    DispatchProposal,
    SocialImpactBand,
    SocialImpactReport,
    render_alert_decision,
    render_assessment_plan,
    render_dispatch_proposal,
    render_social_impact_report,
)
from tradingagents.agents.utils.structured import invoke_structured_or_freetext


@pytest.mark.unit
def test_render_assessment_plan():
    rendered = render_assessment_plan(
        AssessmentPlan(
            recommendation=AlertLevel.YELLOW,
            rationale="风险明显但升级证据不足。",
            strategic_actions="加密监测并预置抢险物资。",
        )
    )
    assert "**研判建议**: 黄色预警" in rendered
    assert "加密监测" in rendered


@pytest.mark.unit
def test_render_dispatch_proposal():
    rendered = render_dispatch_proposal(
        DispatchProposal(
            action=DispatchAction.STRENGTHEN_MONITORING,
            reasoning="水位接近警戒且仍有降雨预报。",
            response_level="三小时一报",
        )
    )
    assert "**处置动作**: 加强监测预警" in rendered
    assert "FINAL DISPATCH PLAN: **加强监测预警**" in rendered


@pytest.mark.unit
def test_render_alert_decision():
    rendered = render_alert_decision(
        AlertDecision(
            rating=AlertLevel.ORANGE,
            executive_summary="启动应急响应。",
            assessment_thesis="水位持续上涨并接近保证水位。",
            affected_area="湘江沿岸低洼区",
            valid_period="2024-05-10 至 2024-05-11",
        )
    )
    assert "**预警等级**: 橙色预警" in rendered
    assert "湘江沿岸低洼区" in rendered


@pytest.mark.unit
def test_render_social_impact_report():
    rendered = render_social_impact_report(
        SocialImpactReport(
            overall_band=SocialImpactBand.MODERATE,
            overall_score=5.5,
            confidence="medium",
            narrative="已转移 420 人，5 处道路封闭。",
        )
    )
    assert "一般影响" in rendered
    assert "5.5/10" in rendered
    assert "420 人" in rendered


@pytest.mark.unit
def test_structured_failure_falls_back_to_plain_text():
    structured = MagicMock()
    structured.invoke.side_effect = ValueError("bad structured output")
    plain = MagicMock()
    plain.invoke.return_value = MagicMock(content="free text fallback")

    result = invoke_structured_or_freetext(
        structured,
        plain,
        "prompt",
        render_alert_decision,
        "Alert Manager",
    )

    assert result == "free text fallback"
    plain.invoke.assert_called_once_with("prompt")
