"""Station identity and prompt-anchor contracts."""

from langchain_core.messages import HumanMessage

from tradingagents.agents.utils.agent_utils import (
    build_area_context,
    create_msg_delete,
    get_area_context_from_state,
    resolve_station_identity,
)


def test_resolves_station_metadata_from_runtime_knowledge():
    identity = resolve_station_identity("xiangjiang")
    assert identity["station_name"] == "湘江示范站"
    assert identity["river"] == "湘江"
    assert identity["warning_level_m"] == 36.0


def test_area_context_includes_station_identity():
    identity = resolve_station_identity("XIANGJIANG")
    context = build_area_context("XIANGJIANG", "flood", identity)
    assert "XIANGJIANG" in context
    assert "湘江示范站" in context
    assert "36.0 m" in context


def test_state_context_prefers_precomputed_value():
    state = {
        "area_of_interest": "XIANGJIANG",
        "asset_type": "flood",
        "area_context": "precomputed context",
    }
    assert get_area_context_from_state(state) == "precomputed context"


def test_message_clear_keeps_station_anchor():
    state = {
        "messages": [HumanMessage(content="old")],
        "area_of_interest": "XIANGJIANG",
        "analysis_date": "2024-05-10",
        "area_context": "XIANGJIANG 湘江示范站",
    }
    result = create_msg_delete()(state)
    placeholder = result["messages"][-1].content
    assert "XIANGJIANG" in placeholder
    assert "2024-05-10" in placeholder
