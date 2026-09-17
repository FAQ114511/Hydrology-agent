"""Hydrology memory is append-only and immediately available to later runs."""

from tradingagents.agents.utils.memory import TradingMemoryLog


def test_store_decision_writes_alert_level_and_is_visible(tmp_path):
    log = TradingMemoryLog({"memory_log_path": str(tmp_path / "hydrology_memory.md")})
    decision = "**预警等级**: 黄色预警\n\n**行动摘要**: 加强监测。"

    log.store_decision("XIANGJIANG", "2024-05-10", decision)

    text = (tmp_path / "hydrology_memory.md").read_text(encoding="utf-8")
    assert "[2024-05-10 | XIANGJIANG | 黄色预警 | logged]" in text
    assert "Hold" not in text
    assert log.load_entries()[0]["alert_level"] == "黄色预警"
    assert "黄色预警" in log.get_past_context("XIANGJIANG", as_of="2024-05-11")


def test_same_station_and_date_is_idempotent(tmp_path):
    log = TradingMemoryLog({"memory_log_path": str(tmp_path / "hydrology_memory.md")})
    log.store_decision("XIANGJIANG", "2024-05-10", "**预警等级**: 蓝色预警")
    log.store_decision("XIANGJIANG", "2024-05-10", "**预警等级**: 红色预警")
    assert len(log.load_entries()) == 1
    assert log.load_entries()[0]["alert_level"] == "蓝色预警"


def test_same_day_decision_is_not_injected_into_the_same_run(tmp_path):
    log = TradingMemoryLog({"memory_log_path": str(tmp_path / "hydrology_memory.md")})
    log.store_decision("XIANGJIANG", "2024-05-10", "**预警等级**: 黄色预警")
    assert log.get_past_context("XIANGJIANG", as_of="2024-05-10") == ""


def test_other_station_decisions_are_available_as_context(tmp_path):
    log = TradingMemoryLog({"memory_log_path": str(tmp_path / "hydrology_memory.md")})
    log.store_decision("OTHER_STATION", "2024-05-09", "**预警等级**: 橙色预警")
    context = log.get_past_context("XIANGJIANG", as_of="2024-05-10")
    assert "OTHER_STATION" in context
    assert "橙色预警" in context
