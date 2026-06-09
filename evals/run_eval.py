#!/usr/bin/env python3
"""Run the evaluation over a labeled query set.

Retrieval metrics compare hybrid vs vector-only vs keyword-only (this is the
experiment that justifies the hybrid design). Answer quality (LLM-as-judge)
runs only with --judge since it spends tokens.

    python -m evals.run_eval            # retrieval metrics only
    python -m evals.run_eval --judge    # + answer-quality judging
    python -m evals.run_eval --k 10 --limit 5
"""

import argparse
import json
from pathlib import Path

from app.generate import generate_answer
from app.retrieval import retrieve
from evals.retrieval_metrics import dedup_preserve, hit_at_k, mrr, ndcg_at_k, recall_at_k

DATASET = Path(__file__).parent / "dataset.jsonl"
STRATEGIES = ["hybrid", "vector", "keyword"]


def load_dataset() -> list[dict]:
    return [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def eval_retrieval(items: list[dict], k: int) -> dict:
    agg = {st: {"recall": [], "hit": [], "mrr": [], "ndcg": []} for st in STRATEGIES}
    for it in items:
        relevant = set(it["relevant_sources"])
        for st in STRATEGIES:
            hits = retrieve(it["question"], top_k=k, strategy=st)
            ranked = dedup_preserve([h.source for h in hits])
            agg[st]["recall"].append(recall_at_k(ranked, relevant, k))
            agg[st]["hit"].append(hit_at_k(ranked, relevant, k))
            agg[st]["mrr"].append(mrr(ranked, relevant))
            agg[st]["ndcg"].append(ndcg_at_k(ranked, relevant, k))
    return {st: {m: _mean(v) for m, v in agg[st].items()} for st in STRATEGIES}


def eval_answers(items: list[dict]) -> dict:
    faith, relevance = [], []
    for it in items:
        hits = retrieve(it["question"], strategy="hybrid")
        answer = generate_answer(it["question"], hits)
        verdict = judge(it["question"], answer, [h.content for h in hits])
        if verdict.get("faithfulness"):
            faith.append(verdict["faithfulness"])
        if verdict.get("answer_relevance"):
            relevance.append(verdict["answer_relevance"])
    return {"faithfulness": _mean(faith), "answer_relevance": _mean(relevance)}


def judge(question, answer, contexts):
    from evals.judge import judge_answer

    return judge_answer(question, answer, contexts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--judge", action="store_true", help="also run LLM-as-judge (costs tokens)")
    ap.add_argument("--limit", type=int, help="evaluate only the first N queries")
    args = ap.parse_args()

    items = load_dataset()
    if args.limit:
        items = items[: args.limit]

    retrieval = eval_retrieval(items, args.k)
    print(f"\nRetrieval metrics over {len(items)} queries (k={args.k}):\n")
    print(f"{'strategy':<10}{'recall@k':>10}{'hit@k':>8}{'MRR':>7}{'nDCG@k':>9}")
    print("-" * 44)
    for st in STRATEGIES:
        r = retrieval[st]
        print(f"{st:<10}{r['recall']:>10.3f}{r['hit']:>8.3f}{r['mrr']:>7.3f}{r['ndcg']:>9.3f}")

    results = {"k": args.k, "n": len(items), "retrieval": retrieval}

    if args.judge:
        print("\nLLM-as-judge on hybrid answers (1-5)...")
        answers = eval_answers(items)
        print(f"  faithfulness: {answers['faithfulness']:.2f}   answer_relevance: {answers['answer_relevance']:.2f}")
        results["answers"] = answers

    out = Path(__file__).parent / ".last_results.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
