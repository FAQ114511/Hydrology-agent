from pathlib import Path

from tradingagents.agents.utils.memory import TradingMemoryLog
from tradingagents.rag.corpus import load_memory_documents
from tradingagents.rag.retriever import _expansion_tokens, _tokenize, load_retriever

ROOT = Path(__file__).resolve().parents[1]


def _retriever():
    return load_retriever({
        "rag_knowledge_dir": str(ROOT / "runtime" / "knowledge"),
        "rag_memory_enabled": False,
    })


def test_decimal_token_is_canonicalized():
    tokens = _tokenize("36.0 米")

    assert "36" in tokens
    assert "0" not in tokens


def test_colloquial_alert_name_reaches_rule_document():
    documents = _retriever().search("红警的触发条件", station="XIANGJIANG", k=3)

    assert documents[0].doc_id == "alert_rules:XIANGJIANG"


def test_synonym_expansion_adds_standard_wording():
    query = "红警的触发条件"
    extra = _expansion_tokens(query, _tokenize(query))

    assert "红色" in extra
    assert "阈值" in extra


def test_station_filter_keeps_each_station_threshold_separate():
    retriever = _retriever()
    zhujiang = retriever.search("警戒水位是多少", station="ZHUJIANG", kind="station", k=3)
    dongjiang = retriever.search("警戒水位是多少", station="DONGJIANG", kind="station", k=3)

    assert zhujiang[0].doc_id == "station:ZHUJIANG"
    assert "7.5" in zhujiang[0].content
    assert dongjiang[0].doc_id == "station:DONGJIANG"
    assert "12.0" in dongjiang[0].content

def test_station_warning_level_is_retrievable():
    docs = _retriever().search(
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
