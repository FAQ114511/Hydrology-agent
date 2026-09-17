"""Hydrology-specific contracts for the interactive CLI."""

from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

import cli.main as m
import cli.utils as u
from cli.models import AnalystType


class _Prompt:
    def __init__(self, answer):
        self.answer = answer

    def ask(self):
        return self.answer


def test_get_station_normalizes_and_uses_default(monkeypatch):
    captured = {}

    def fake_text(prompt, **kwargs):
        captured["prompt"] = prompt
        captured.update(kwargs)
        return _Prompt(" xiangjiang ")

    monkeypatch.setattr(u.questionary, "text", fake_text)

    assert u.get_station() == "XIANGJIANG"
    assert captured["default"] == "XIANGJIANG"


def test_get_station_rejects_unknown_station(monkeypatch):
    captured = {}

    def fake_text(prompt, **kwargs):
        captured.update(kwargs)
        return _Prompt("NOT_A_STATION")

    monkeypatch.setattr(u.questionary, "text", fake_text)
    with pytest.raises(SystemExit):
        u.get_station()
    message = captured["validate"]("NOT_A_STATION")
    assert "XIANGJIANG" in message


def test_message_buffer_initializes_hydrology_agents_and_sections():
    buffer = m.MessageBuffer()
    buffer.init_for_analysis([
        AnalystType.MARKET,
        AnalystType.SOCIAL,
        AnalystType.NEWS,
        AnalystType.FUNDAMENTALS,
    ])

    assert set(buffer.agent_status) == {
        "水文分析师",
        "社会影响分析师",
        "气象分析师",
        "环境风险分析师",
        "风险研判员",
        "安全研判员",
        "研判经理",
        "处置员",
        "激进型研判员",
        "保守型研判员",
        "中立型研判员",
        "预警决策员",
    }
    assert list(buffer.report_sections) == [
        "hydrology_report",
        "social_impact_report",
        "meteorology_report",
        "environment_report",
        "assessment_plan",
        "dispatch_plan",
        "final_alert_decision",
    ]


def test_message_buffer_builds_five_hydrology_report_parts():
    buffer = m.MessageBuffer()
    buffer.init_for_analysis(list(AnalystType))
    buffer.update_report_section("hydrology_report", "水文报告")
    buffer.update_report_section("assessment_plan", "风险结论")
    buffer.update_report_section("dispatch_plan", "处置方案")
    buffer.update_response_debate("### 激进型研判员\n激进意见")
    buffer.update_report_section("final_alert_decision", "黄色预警")

    assert "## 一、专业分析" in buffer.final_report
    assert "## 二、风险研判结论" in buffer.final_report
    assert "## 三、处置方案" in buffer.final_report
    assert "## 四、响应处置辩论" in buffer.final_report
    assert "## 五、最终预警决策" in buffer.final_report


def _selections():
    return {
        "station": "XIANGJIANG",
        "asset_type": "flood",
        "analysis_date": "2024-05-10",
        "analysts": list(AnalystType),
        "research_depth": 1,
        "llm_provider": "deepseek",
        "backend_url": None,
        "shallow_thinker": "deepseek-v4-flash",
        "deep_thinker": "deepseek-v4-flash",
        "google_thinking_level": None,
        "openai_reasoning_effort": None,
        "anthropic_effort": None,
        "output_language": "Chinese",
    }


class _Live:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _FakePropagator:
    def __init__(self, graph):
        self.graph = graph

    def create_initial_state(self, *args, **kwargs):
        self.graph.init_calls.append((args, kwargs))
        return {"messages": []}

    def get_graph_args(self, callbacks=None):
        return {"config": {}, "stream_mode": "values"}


class _FakeGraph:
    def __init__(self, *args, **kwargs):
        self.config = kwargs["config"]
        self.resolve_calls = []
        self.init_calls = []
        self.clear_calls = []
        self.propagator = _FakePropagator(self)
        self.graph = SimpleNamespace(stream=self._stream, invoke=lambda *a, **k: {})

    def resolve_area_context(self, station, asset_type):
        self.resolve_calls.append((station, asset_type))
        return "XIANGJIANG: 湘江示范站"

    def checkpoint_input(self, state):
        return state

    def begin_checkpoint(self, *args):
        return None

    def end_checkpoint(self):
        pass

    def clear_checkpoint_on_success(self, *args):
        self.clear_calls.append(args)

    def _stream(self, state, **kwargs):
        yield {
            "messages": [],
            "hydrology_report": "水文报告",
            "social_impact_report": "社会影响报告",
            "meteorology_report": "气象报告",
            "environment_report": "环境报告",
        }
        yield {
            "risk_debate_state": {
                "high_risk_history": "风险意见",
                "safety_history": "安全意见",
                "judge_decision": "风险研判结论",
            }
        }
        yield {"dispatch_plan": "处置方案"}
        yield {
            "response_debate_state": {
                "aggressive_history": "激进意见",
                "conservative_history": "保守意见",
                "neutral_history": "中立意见",
                "judge_decision": "黄色预警",
            }
        }
        yield {"final_alert_decision": "黄色预警"}


def test_run_analysis_uses_hydrology_graph_context_and_new_stream_fields(monkeypatch, tmp_path):
    config = copy.deepcopy(m.build_hydrology_config())
    config["results_dir"] = str(tmp_path / "results")
    monkeypatch.setattr(m, "build_hydrology_config", lambda: copy.deepcopy(config))
    fake_graph = _FakeGraph(config=config)
    monkeypatch.setattr(m, "TradingAgentsGraph", lambda *args, **kwargs: fake_graph)
    monkeypatch.setattr(m, "get_user_selections", _selections)
    monkeypatch.setattr(m, "create_layout", lambda: object())
    monkeypatch.setattr(m, "update_display", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "Live", _Live)
    monkeypatch.setattr(m.typer, "prompt", lambda *args, **kwargs: "N")

    m.run_analysis()

    assert fake_graph.resolve_calls == [("XIANGJIANG", "flood")]
    assert fake_graph.init_calls[0][1]["area_context"] == "XIANGJIANG: 湘江示范站"
    assert "hydrology_report" in m.message_buffer.report_sections
    assert "风险研判员" in m.message_buffer.agent_status
    assert "assessment_plan" in m.message_buffer.report_sections
    assert "dispatch_plan" in m.message_buffer.report_sections
    assert "final_alert_decision" in m.message_buffer.report_sections
