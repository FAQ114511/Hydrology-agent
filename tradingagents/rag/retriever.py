from __future__ import annotations

import math
import re
from pathlib import Path

from .corpus import KnowledgeDocument, build_corpus

_ASCII_RE = re.compile(r"[a-z0-9_]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_KNOWLEDGE_DIR = _PROJECT_ROOT / "runtime" / "knowledge"


def _tokenize(text: str) -> list[str]:
    lowered = (text or "").lower()
    tokens = _ASCII_RE.findall(lowered)
    for chunk in _CJK_RE.findall(lowered):
        if len(chunk) == 1:
            tokens.append(chunk)
        else:
            tokens.extend(chunk[i : i + 2] for i in range(len(chunk) - 1))
    return tokens


class FloodKnowledgeRetriever:
    def __init__(self, documents: list[KnowledgeDocument]):
        self.documents = list(documents)
        self._tokens = [
            _tokenize(f"{doc.title} {doc.content}") for doc in self.documents
        ]
        self._doc_freq: dict[str, int] = {}
        for tokens in self._tokens:
            for token in set(tokens):
                self._doc_freq[token] = self._doc_freq.get(token, 0) + 1

    def _idf(self, token: str) -> float:
        total = max(len(self.documents), 1)
        return math.log((total + 1) / (self._doc_freq.get(token, 0) + 1)) + 1.0

    def _score(self, query_tokens: list[str], index: int, station: str | None) -> float:
        if not query_tokens:
            return 0.0
        counts: dict[str, int] = {}
        for token in self._tokens[index]:
            counts[token] = counts.get(token, 0) + 1
        score = 0.0
        for token in set(query_tokens):
            if token in counts:
                score += self._idf(token) * (1.0 + math.log(counts[token]))
        if station and self.documents[index].station == station.upper():
            score += 2.0
        return score

    def search(
        self,
        query: str,
        station: str | None = None,
        kind: str | None = None,
        k: int = 5,
    ) -> list[KnowledgeDocument]:
        station_upper = station.upper() if station else None
        candidates = [
            index
            for index, doc in enumerate(self.documents)
            if (not station_upper or not doc.station or doc.station == station_upper)
            and (not kind or doc.kind == kind)
        ]
        query_tokens = _tokenize(query)
        if not query_tokens:
            return [self.documents[i] for i in candidates[:k]]
        scored = [
            (self._score(query_tokens, index, station), index)
            for index in candidates
        ]
        scored = [(score, index) for score, index in scored if score > 0]
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [self.documents[index] for _, index in scored[:k]]


def _resolve_knowledge_dir(config: dict) -> Path:
    raw = (config or {}).get("rag_knowledge_dir")
    if not raw:
        return _DEFAULT_KNOWLEDGE_DIR
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    return (_PROJECT_ROOT / path).resolve()


def load_retriever(config: dict | None = None) -> FloodKnowledgeRetriever:
    config = config or {}
    knowledge_dir = _resolve_knowledge_dir(config)
    memory_path = None
    if config.get("rag_memory_enabled", True) and config.get("memory_log_path"):
        memory_path = Path(config["memory_log_path"])
    documents = build_corpus(knowledge_dir=knowledge_dir, memory_path=memory_path)
    return FloodKnowledgeRetriever(documents)