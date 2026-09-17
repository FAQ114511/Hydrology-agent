"""RAG 检索评测脚本：跑一组带标注的查询，输出 Hit@1 / Hit@3 / Recall@3 / MRR。

用法：
    python scripts/rag_eval.py --cases tests/rag_eval_cases.json --label r0-baseline

每轮调优后重跑一次并用不同的 --label 区分结果，JSON 结果落在 runtime/rag_eval/
。脚本固定关闭 memory 检索，保证不同轮次之间可复现。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tradingagents.rag.retriever import load_retriever  # noqa: E402

DEFAULT_CASES = ROOT / "tests" / "rag_eval_cases.json"
DEFAULT_RESULTS_DIR = ROOT / "runtime" / "rag_eval"


def _hit_rank(ranked: list[str], gold: list[str]) -> int | None:
    for index, doc_id in enumerate(ranked, start=1):
        if doc_id in gold:
            return index
    return None


def evaluate(cases: list[dict], top_k: int) -> dict:
    retriever = load_retriever(
        {
            "rag_knowledge_dir": str(ROOT / "runtime" / "knowledge"),
            "rag_memory_enabled": False,
        }
    )

    per_query = []
    hits_at_1 = hits_at_3 = 0
    recall_sum = 0.0
    mrr_sum = 0.0
    empty = 0

    for case in cases:
        gold = case["relevant_doc_ids"]
        documents = retriever.search(
            case["query"],
            station=case.get("station"),
            kind=case.get("kind"),
            k=top_k,
        )
        ranked = [document.doc_id for document in documents]
        rank = _hit_rank(ranked, gold)

        if not ranked:
            empty += 1
        if rank == 1:
            hits_at_1 += 1
        if rank is not None and rank <= top_k:
            hits_at_3 += 1
            recall_sum += sum(1 for doc_id in gold if doc_id in ranked) / len(gold)
            mrr_sum += 1.0 / rank

        per_query.append(
            {
                "id": case["id"],
                "category": case["category"],
                "query": case["query"],
                "gold": gold,
                "ranked": ranked,
                "first_hit_rank": rank,
            }
        )

    total = len(cases)
    return {
        "top_k": top_k,
        "total_queries": total,
        "hit@1": round(hits_at_1 / total, 4),
        "hit@3": round(hits_at_3 / total, 4),
        "recall@3": round(recall_sum / total, 4),
        "mrr": round(mrr_sum / total, 4),
        "empty_rate": round(empty / total, 4),
        "per_query": per_query,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG 检索评测")
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--label", default="run")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    result = evaluate(cases, args.top_k)

    DEFAULT_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DEFAULT_RESULTS_DIR / f"{args.label}.json"
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"label={args.label} queries={result['total_queries']} top_k={result['top_k']}")
    print(
        "Hit@1={hit@1}  Hit@3={hit@3}  Recall@3={recall@3}  MRR={mrr}  empty={empty_rate}".format(**result)
    )
    misses = [row for row in result["per_query"] if row["first_hit_rank"] is None]
    print(f"misses={len(misses)} ids={[row['id'] for row in misses]}")
    print(f"written: {out_path}")


if __name__ == "__main__":
    main()
