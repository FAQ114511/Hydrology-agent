from copy import deepcopy
from pathlib import Path

import pytest

from tradingagents.agents.utils.rag_tools import search_flood_knowledge
from tradingagents.dataflows import config as config_module
from tradingagents.dataflows.config import set_config
from tradingagents.graph.trading_graph import TradingAgentsGraph


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def restore_config():
    original = deepcopy(config_module._config)
    yield
    config_module._config = original


def test_search_flood_knowledge_returns_source_metadata(restore_config):
    set_config({
        "rag_enabled": True,
        "rag_knowledge_dir": str(ROOT / "runtime" / "knowledge"),
        "rag_memory_enabled": False,
        "rag_top_k": 3,
    })

    result = search_flood_knowledge.func(
        "警戒水位", station="XIANGJIANG", kind="station"
    )

    assert "36.0" in result
    assert '"doc_id":' in result
    assert '"source":' in result
    assert '"kind": "station"' in result


def test_search_flood_knowledge_respects_disabled_flag(restore_config):
    set_config({"rag_enabled": False})

    result = search_flood_knowledge.func("警戒水位", station="XIANGJIANG")

    assert result.startswith("NO_DATA_AVAILABLE")


def test_search_flood_knowledge_rejects_unknown_kind(restore_config):
    set_config({"rag_enabled": True})

    with pytest.raises(ValueError, match="不支持的 kind"):
        search_flood_knowledge.func("警戒水位", kind="unknown")


def test_search_flood_knowledge_is_registered_on_analysis_nodes():
    tool_nodes = TradingAgentsGraph._create_tool_nodes(None)

    assert "search_flood_knowledge" in tool_nodes["news"].tools_by_name
    assert "search_flood_knowledge" in tool_nodes["fundamentals"].tools_by_name
