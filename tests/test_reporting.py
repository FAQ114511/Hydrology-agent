"""Report parity: the shared writer produces the report tree for the CLI and the
programmatic API alike (#1037)."""

from types import SimpleNamespace

import pytest

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.reporting import write_report_tree


def _state():
    return {
        "hydrology_report": "水文观测",
        "meteorology_report": "降雨预报",
        "risk_debate_state": {
            "high_risk_history": "高风险意见",
            "safety_history": "安全意见",
            "judge_decision": "研判结论",
        },
        "dispatch_plan": "处置方案",
        "response_debate_state": {
            "aggressive_history": "激进意见",
            "conservative_history": "保守意见",
            "neutral_history": "中立意见",
            "judge_decision": "黄色预警",
        },
    }


@pytest.mark.unit
def test_write_report_tree_creates_files(tmp_path):
    out = write_report_tree(_state(), "XIANGJIANG", tmp_path)
    assert out.name == "complete_report.md"
    assert (tmp_path / "1_analysts" / "hydrology.md").read_text(encoding="utf-8") == "水文观测"
    assert (tmp_path / "1_analysts" / "meteorology.md").read_text(encoding="utf-8") == "降雨预报"
    assert (tmp_path / "2_risk_assessment" / "manager.md").read_text(encoding="utf-8") == "研判结论"
    assert (tmp_path / "3_dispatch" / "dispatcher.md").read_text(encoding="utf-8") == "处置方案"
    assert (tmp_path / "5_alert" / "decision.md").read_text(encoding="utf-8") == "黄色预警"
    complete = out.read_text(encoding="utf-8")
    assert "水文防汛研判报告：XIANGJIANG" in complete
    assert "水文观测" in complete and "黄色预警" in complete


@pytest.mark.unit
def test_save_reports_explicit_path(tmp_path):
    # Unbound: with an explicit save_path, the method doesn't touch self/config.
    out = TradingAgentsGraph.save_reports(None, _state(), "XIANGJIANG", save_path=tmp_path)
    assert (tmp_path / "complete_report.md").exists()
    assert out == tmp_path / "complete_report.md"


@pytest.mark.unit
def test_save_reports_defaults_under_results_dir(tmp_path):
    mock_self = SimpleNamespace(config={"results_dir": str(tmp_path)})
    out = TradingAgentsGraph.save_reports(mock_self, _state(), "XIANGJIANG")
    assert out.exists()
    assert out.parent.parent.name == "reports"  # results_dir/reports/XIANGJIANG_<stamp>/...
    assert out.parent.name.startswith("XIANGJIANG_")
