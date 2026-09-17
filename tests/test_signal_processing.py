"""Tests for deterministic hydrology alert parsing."""

import pytest

from tradingagents.alert_levels import ALERT_LEVELS, parse_alert_level
from tradingagents.graph.signal_processing import ALERT_REVIEW, SignalProcessor


@pytest.mark.unit
@pytest.mark.parametrize("level", ALERT_LEVELS)
def test_parse_alert_level_recognises_all_levels(level):
    assert parse_alert_level(f"**预警等级**: {level}") == level


@pytest.mark.unit
def test_parse_alert_level_uses_default_when_absent():
    assert parse_alert_level("当前证据不足") == "蓝色预警"
    assert parse_alert_level("当前证据不足", default="REVIEW") == "REVIEW"


@pytest.mark.unit
class TestSignalProcessor:
    def test_returns_alert_level_from_alert_manager_markdown(self):
        processor = SignalProcessor()
        decision = "**预警等级**: 橙色预警\n\n**行动摘要**: 启动应急响应。"
        assert processor.process_signal(decision) == "橙色预警"

    def test_unparseable_signal_is_review(self):
        assert SignalProcessor().process_signal("无法形成等级结论") == ALERT_REVIEW

    def test_makes_no_llm_calls(self):
        from unittest.mock import MagicMock

        llm = MagicMock()
        SignalProcessor(llm).process_signal("**预警等级**: 蓝色预警")
        llm.invoke.assert_not_called()
        llm.with_structured_output.assert_not_called()
