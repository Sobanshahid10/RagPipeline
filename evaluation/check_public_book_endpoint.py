"""Live, authenticated-route public-book check without creating a test account.

The current-user dependency is overridden only inside this in-process test
client. Retrieval, context, prompt, provider call, and answer validation are real.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user
from app.main import app

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = json.loads((ROOT / "evaluation/public_book_cases.json").read_text()) + [
    {"id": "opinion_best", "category": "opinion", "question": "What is the best part of Omer's portfolio, and what evidence supports that judgment?"},
    {"id": "opinion_worst", "category": "opinion", "question": "What is the worst part of Omer's portfolio, and how would you improve it?"},
    {"id": "paraphrase_start", "category": "paraphrase", "question": "What's the oldest trace of Omer actually building software? Is it his real starting date?"},
    {"id": "cross_person", "category": "attribution", "question": "Did Soban implement the Docinsight radar scheduler?"},
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--pause", type=float, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selected = [case for case in QUESTIONS if not args.ids or case["id"] in args.ids]
    if args.ids and len(selected) != len(set(args.ids)):
        raise ValueError("Unknown or repeated case IDs")
    app.dependency_overrides[get_current_user] = lambda: object()
    rows = []
    with TestClient(app) as client:
        for index, case in enumerate(selected):
            if index and args.pause:
                time.sleep(args.pause)
            started = time.monotonic()
            try:
                response = client.post("/api/v1/public-book/ask", json={"question": case["question"], "model": args.model})
                payload = response.json()
                row = {"id": case["id"], "category": case["category"], "question": case["question"],
                       "reference_answer": case.get("reference_answer"), "status": response.status_code,
                       "latency_seconds": round(time.monotonic() - started, 2), "response": payload}
            except Exception as error:
                row = {"id": case["id"], "category": case["category"], "question": case["question"],
                       "status": None, "latency_seconds": round(time.monotonic() - started, 2),
                       "error": f"{type(error).__name__}: {str(error)[:300]}"}
            rows.append(row)
            print(json.dumps({"id": row["id"], "status": row["status"], "seconds": row["latency_seconds"],
                              "answer": row.get("response", {}).get("answer"),
                              "detail": row.get("response", {}).get("detail"), "error": row.get("error")}, ensure_ascii=False), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"run_at_utc": datetime.now(timezone.utc).isoformat(), "model": args.model,
                                       "rows": rows}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"saved": str(args.output), "success": sum(row["status"] == 200 for row in rows), "total": len(rows)}))


if __name__ == "__main__":
    main()
