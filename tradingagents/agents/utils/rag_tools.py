from __future__ import annotations

import json
from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.config import get_config
from tradingagents.rag.retriever import load_retriever


_VALID_KINDS = {"station", "rule", "guideline", "case", "memory"}


@tool
def search_flood_knowledge(
    query: Annotated[str, "需要检索的防汛知识问题"],
    station: Annotated[str | None, "可选的水文站点编号"] = None,
    kind: Annotated[
        str | None,
        "可选类型：station、rule、guideline、case 或 memory",
    ] = None,
    k: Annotated[int | None, "可选返回条数；省略时使用 rag_top_k"] = None,
) -> str:
    """检索站点信息、预警规则、防汛规程、历史案例和已确认记忆。"""
    config = get_config()
    if not config.get("rag_enabled", False):
        return "NO_DATA_AVAILABLE：RAG 未启用。"

    normalized_kind = kind.strip().lower() if kind else None
    if normalized_kind and normalized_kind not in _VALID_KINDS:
        raise ValueError(f"不支持的 kind：{kind!r}")

    top_k = int(k if k is not None else config.get("rag_top_k", 5))
    documents = load_retriever(config).search(
        query,
        station=station,
        kind=normalized_kind,
        k=top_k,
    )
    if not documents:
        return "NO_DATA_AVAILABLE：没有检索到匹配的防汛知识。"

    rows = [
        {
            "doc_id": document.doc_id,
            "source": document.source,
            "station": document.station,
            "date": document.date,
            "kind": document.kind,
            "title": document.title,
            "content": document.content,
        }
        for document in documents
    ]
    return "## 防汛知识检索结果\n\n" + "\n".join(
        json.dumps(row, ensure_ascii=False) for row in rows
    )
