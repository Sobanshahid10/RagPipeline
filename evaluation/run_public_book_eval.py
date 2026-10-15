#!/usr/bin/env python3
"""Evaluate real public-book RAG traces with evidence checks and a rubric judge.

Examples:
  python evaluation/run_public_book_eval.py --base-url http://localhost:8000
  python evaluation/run_public_book_eval.py --traces /tmp/public-book-traces.json
  python evaluation/run_public_book_eval.py --traces /tmp/public-book-traces.json --retrieval-only

Live runs require API_TOKEN and, unless --retrieval-only is given, OPENAI_API_KEY.
There is deliberately no mock response, heuristic judge, or success-shaped fallback.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
BOOK_NAME = "PUBLIC_KNOWLEDGE_BOOK.md"
DEFAULT_CASES = ROOT / "evaluation" / "public_book_cases.json"


def normalized(text: str) -> str:
    return " ".join(re.findall(r"[\w]+", text.casefold()))


def load_cases(path: Path, book_path: Path) -> list[dict[str, Any]]:
    cases = json.loads(path.read_text(encoding="utf-8"))
    book = normalized(book_path.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        raise ValueError("The public-book case list is empty or invalid")
    seen: set[str] = set()
    for case in cases:
        if case["id"] in seen:
            raise ValueError(f"Duplicate case ID: {case['id']}")
        seen.add(case["id"])
        if not case.get("question") or not case.get("reference_answer"):
            raise ValueError(f"Case {case['id']} lacks a question or reference answer")
        for phrase in case.get("evidence", []):
            if normalized(phrase) not in book:
                raise ValueError(f"Evidence for {case['id']} is absent from {book_path.name}: {phrase}")
    return cases


def parse_query_events(body: str) -> tuple[str, list[dict[str, Any]]]:
    tokens: list[str] = []
    chunks: list[dict[str, Any]] | None = None
    done_answer: str | None = None
    for line in body.splitlines():
        if not line.startswith("data:"):
            continue
        event = json.loads(line[5:].strip())
        if event.get("type") == "retrieval":
            chunks = event.get("chunks", [])
        elif event.get("type") == "token":
            tokens.append(str(event.get("content", "")))
        elif event.get("type") == "done":
            done_answer = event.get("answer")
    if chunks is None:
        raise ValueError("Query response did not expose its actual retrieved chunks")
    answer = "".join(tokens).strip() or str(done_answer or "").strip()
    if not answer:
        raise ValueError("Query response contained no answer")
    return answer, chunks


def collect_live(cases: list[dict[str, Any]], base_url: str, token: str) -> list[dict[str, Any]]:
    if not token:
        raise ValueError("Set API_TOKEN to run against the authenticated application")
    headers = {"Authorization": f"Bearer {token}"}
    traces: list[dict[str, Any]] = []
    with httpx.Client(timeout=120.0) as client:
        for case in cases:
            response = client.post(
                f"{base_url.rstrip('/')}/api/v1/query",
                headers=headers,
                json={"query": case["question"], "include_context": True, "bypass_cache": True},
            )
            response.raise_for_status()
            answer, chunks = parse_query_events(response.text)
            traces.append({"id": case["id"], "answer": answer, "chunks": chunks})
    return traces


def validate_traces(cases: list[dict[str, Any]], traces: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_id = {item["id"]: item for item in traces}
    if len(by_id) != len(traces):
        raise ValueError("Traces contain duplicate IDs")
    if set(by_id) != {case["id"] for case in cases}:
        raise ValueError("Trace IDs must match the public-book case IDs exactly")
    for item in traces:
        if not isinstance(item.get("answer"), str) or not item["answer"].strip():
            raise ValueError(f"Trace {item['id']} has no real answer")
        if not isinstance(item.get("chunks"), list):
            raise ValueError(f"Trace {item['id']} has no retrieved chunk list")
        for chunk in item["chunks"]:
            if chunk.get("source_filename") != BOOK_NAME:
                raise ValueError(
                    f"Trace {item['id']} includes a chunk without the required public-book source; "
                    "run this suite in a book-only tenant or index"
                )
            if not isinstance(chunk.get("content"), str):
                raise ValueError(f"Trace {item['id']} has a chunk without text")
    if not any(item["chunks"] for item in traces):
        raise ValueError("No public-book chunks were retrieved; index the book before running this benchmark")
    return by_id


def exact_evidence_recall(case: dict[str, Any], chunks: list[dict[str, Any]]) -> float | None:
    """Conservative string-match check; compression can lower this despite semantic relevance."""
    phrases = case.get("evidence", [])
    if not phrases:
        return None
    context = normalized(" ".join(chunk["content"] for chunk in chunks))
    return sum(normalized(phrase) in context for phrase in phrases) / len(phrases)


JUDGE_SYSTEM = """You are a strict, independent evaluator for a public-profile RAG system.
Grade only from the question, reference answer, and retrieved context supplied. Do not use outside knowledge.
The book contains attributed claims and uncertainty. Penalize answers that turn self-reports into verified facts,
erase uncertainty, invent private details, or use a different person's facts.

Return JSON only with these keys:
context_relevance: list of integers 0, 1, or 2, one per chunk (0 irrelevant, 1 partial, 2 directly useful)
context_coverage: integer 0, 1, or 2 (0 missing crucial evidence, 1 partial, 2 enough evidence)
answer_relevance: integer 0, 1, or 2 (0 off-topic, 1 partial, 2 directly answers)
faithfulness: integer 0, 1, or 2 (0 material unsupported/contradictory claims, 1 mixed, 2 fully supported)
reference_accuracy: integer 0, 1, or 2 (0 materially wrong, 1 partly correct, 2 agrees with reference)
unsupported_claims: list of short strings naming any unsupported factual claims; empty if none
reason: one concise sentence explaining the main failure or why the answer passes.

For an unanswerable question, a clear refusal/statement of missing evidence can receive full marks.
Do not give a high faithfulness score merely because a claim appears in the reference answer; the retrieved
chunks must support it. Treat empty retrieved context as insufficient for an affirmative factual answer."""


def judge_case(case: dict[str, Any], trace: dict[str, Any], model: str, api_key: str) -> dict[str, Any]:
    chunks = trace["chunks"]
    payload = {
        "question": case["question"],
        "reference_answer": case["reference_answer"],
        "answerable": case.get("answerable", True),
        "retrieved_chunks": [
            {"rank": i + 1, "text": chunk["content"][:5000]}
            for i, chunk in enumerate(chunks)
        ],
        "answer": trace["answer"],
    }
    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        },
        timeout=120.0,
    )
    response.raise_for_status()
    result = json.loads(response.json()["choices"][0]["message"]["content"])
    scores = ["context_coverage", "answer_relevance", "faithfulness", "reference_accuracy"]
    if any(type(result.get(name)) is not int or result[name] not in (0, 1, 2) for name in scores):
        raise ValueError(f"Judge returned invalid scores for {case['id']}: {result}")
    relevance = result.get("context_relevance")
    if (not isinstance(relevance, list) or len(relevance) != len(chunks)
            or any(type(score) is not int or score not in (0, 1, 2) for score in relevance)):
        raise ValueError(f"Judge returned invalid chunk relevance for {case['id']}")
    if not isinstance(result.get("unsupported_claims"), list):
        raise ValueError(f"Judge returned invalid unsupported claims for {case['id']}")
    return result


def mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def evaluate(
    cases: list[dict[str, Any]],
    traces: dict[str, dict[str, Any]],
    judge_model: str | None,
    api_key: str | None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        trace = traces[case["id"]]
        chunks = trace["chunks"]
        row: dict[str, Any] = {
            "id": case["id"],
            "category": case.get("category"),
            "question": case["question"],
            "reference_answer": case["reference_answer"],
            "answer": trace["answer"],
            "retrieved_chunk_ids": [chunk.get("id") for chunk in chunks],
            "retrieved_chunk_count": len(chunks),
            "exact_evidence_recall": exact_evidence_recall(case, chunks),
        }
        if judge_model:
            row["judge"] = judge_case(case, trace, judge_model, api_key or "")
        rows.append(row)

    judged = [row["judge"] for row in rows if "judge" in row]
    metrics: dict[str, Any] = {
        "exact_evidence_recall": mean([row["exact_evidence_recall"] for row in rows if row["exact_evidence_recall"] is not None]),
        "no_context_rate": mean([float(row["retrieved_chunk_count"] == 0) for row in rows]),
    }
    if judged:
        metrics.update({
            "relevant_chunk_rate_at_5": mean([float(score == 2) for judge in judged for score in judge["context_relevance"][:5]]),
            "context_coverage": mean([judge["context_coverage"] / 2 for judge in judged]),
            "answer_relevance": mean([judge["answer_relevance"] / 2 for judge in judged]),
            "faithfulness": mean([judge["faithfulness"] / 2 for judge in judged]),
            "reference_accuracy": mean([judge["reference_accuracy"] / 2 for judge in judged]),
            "unsupported_answer_rate": mean([float(bool(judge["unsupported_claims"])) for judge in judged]),
        })
    return {
        "evaluated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "corpus": BOOK_NAME,
        "case_count": len(cases),
        "judge_model": judge_model,
        "metrics": metrics,
        "cases": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--traces", type=Path, help="JSON list of real query traces")
    source.add_argument("--base-url", help="Live application URL")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--book", type=Path, default=ROOT / BOOK_NAME)
    parser.add_argument("--retrieval-only", action="store_true", help="Skip LLM judgment; answer scores remain unavailable")
    parser.add_argument("--judge-model", default="gpt-4o-mini")
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation" / "results" / "public_book_latest.json")
    args = parser.parse_args()

    try:
        cases = load_cases(args.cases, args.book)
        raw_traces = (
            json.loads(args.traces.read_text(encoding="utf-8")) if args.traces
            else collect_live(cases, args.base_url, os.environ.get("API_TOKEN", ""))
        )
        traces = validate_traces(cases, raw_traces)
        api_key = os.environ.get("OPENAI_API_KEY")
        if not args.retrieval_only and not api_key:
            raise ValueError("Set OPENAI_API_KEY for G-Eval-style judgment, or use --retrieval-only")
        report = evaluate(cases, traces, None if args.retrieval_only else args.judge_model, api_key)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"report": str(args.output), "metrics": report["metrics"]}, indent=2))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, httpx.HTTPError) as exc:
        print(f"Public-book evaluation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
