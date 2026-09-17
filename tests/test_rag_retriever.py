from pathlib import Path

from tradingagents.agents.utils.memory import TradingMemoryLog
from tradingagents.rag.corpus import load_memory_documents
from tradingagents.rag.retriever import load_retriever

ROOT = Path(__file__).resolve().parents[1]

def test_station_warning_level_is_retrievable():
    retriever = load_retriever({
        "rag_knowledge_dir": str(ROOT / "runtime" / "knowledge"),
        "rag_memory_enabled": False,
    })
    docs = retriever.search(
        "警戒水位", station="XIANGJIANG", kind="station", k=3
    )
    assert docs
    assert "36.0" in docs[0].content

def test_missing_knowledge_directory_returns_empty(tmp_path):
    retriever = load_retriever({
        "rag_knowledge_dir": str(tmp_path / "missing"),
        "rag_memory_enabled": False,
    })
    assert retriever.documents == []

def test_logged_memory_is_loaded(tmp_path):
    memory = tmp_path / "memory.md"
    log = TradingMemoryLog({"memory_log_path": str(memory)})
    log.store_decision(
        "XIANGJIANG",
        "2024-05-10",
        "**预警等级**: 黄色预警\n\n**行动摘要**: 加强监测。",
    )

    documents = load_memory_documents(memory)
    assert len(documents) == 1
    assert documents[0].station == "XIANGJIANG"
    assert documents[0].date == "2024-05-10"
    assert documents[0].kind == "memory"
    assert "黄色预警" in documents[0].content
