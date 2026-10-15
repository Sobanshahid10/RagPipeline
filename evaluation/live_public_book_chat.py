"""Ask the already-indexed public book and save inspectable live RAG traces.

This exercises the dedicated public-book index. It never uploads or re-embeds
the book, and it never reads storage/private.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import asyncpg
import httpx
from huggingface_hub import snapshot_download

from backend.app.config import settings
from backend.app.generation.public_book_generate import send_to_gemini
from backend.app.generation.public_book_prompt import ABSTENTION, build_public_book_prompt
from backend.app.ingestion.embed_public_book import MODEL_ID, LocalMiniLM
from backend.app.ingestion.index_public_book_pg import DEFAULT_URL
from backend.app.retrieval.public_book_context import build_context
from backend.app.retrieval.public_book_rerank import rerank_public_book_pg

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("basic", "Which hackathon did Umar report winning, and what did its README measure?"),
    ("chronology", "When did Umar start doing projects? Distinguish earliest evidence from the true start of coding."),
    ("paraphrase", "What is the oldest dated footprint of Omer building software that these records can actually prove?"),
    ("conflict", "Why do the book's commit totals differ, and what can we safely conclude from each?"),
    ("best", "What is the best part of Omer's portfolio? Give a reasoned opinion grounded in the evidence."),
    ("worst", "What is the worst part of Omer's portfolio? Give a constructive evidence-based critique without inventing flaws."),
    ("cross_person", "Did Soban contribute to Umar's Docinsight project? What evidence establishes this?"),
    ("unanswerable", "What is Umar's GitHub password?"),
]


def parse_answer(content: str, allowed: list[str]) -> dict:
    result = json.loads(content.strip().removeprefix("```json").removesuffix("```").strip())
    if set(result) != {"answer", "citations", "abstained"}:
        raise ValueError("Response did not match the requested JSON keys")
    if not isinstance(result["answer"], str) or not isinstance(result["citations"], list) or not all(isinstance(item, str) for item in result["citations"]) or type(result["abstained"]) is not bool:
        raise ValueError("Response used incorrect JSON value types")
    result["answer"] = re.sub(r"【(S\d+)】", r"[\1]", result["answer"])
    result["answer"] = re.sub(
        r"\[((?:S\d+\s*,\s*)+S\d+)\]",
        lambda match: "".join(f"[{part.strip()}]" for part in match.group(1).split(",")),
        result["answer"],
    )
    if re.fullmatch(re.escape(ABSTENTION) + r"(?:\s*\[S\d+\])+", result["answer"]):
        result["answer"] = ABSTENTION
        result["citations"] = []
    if result["answer"] == ABSTENTION and not result["citations"]:
        result["abstained"] = True
    inline = list(dict.fromkeys(re.findall(r"\[(S\d+)\]", result["answer"])))
    if set(inline) != set(result["citations"]) or any(cid not in allowed for cid in inline):
        raise ValueError("Response citations do not match inline citations or retrieved evidence")
    result["citations"] = inline
    return result


def generate(prompt: dict, provider: str, model: str) -> str:
    if provider == "gemini":
        data = send_to_gemini(prompt, model=model, api_key=settings.GEMINI_API_KEY or "")
        return "".join(part.get("text", "") for candidate in data.get("candidates", []) for part in candidate.get("content", {}).get("parts", []))
    if provider == "groq":
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is missing")
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            json={"model": model, "messages": prompt["messages"], "temperature": 0, "response_format": {"type": "json_object"}},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    raise ValueError("provider must be gemini or groq")


async def collect(selected: list[tuple[str, str]], provider: str, model_id: str, database_url: str) -> list[dict]:
    source_bytes = (ROOT / "PUBLIC_KNOWLEDGE_BOOK.md").read_bytes()
    records = json.loads((ROOT / "storage/knowledge/public_book_records.json").read_text())
    embedding_model = LocalMiniLM(Path(snapshot_download(MODEL_ID, local_files_only=True)))
    connection = await asyncpg.connect(database_url)
    rows = []
    try:
        for category, question in selected:
            context = None
            try:
                ranked = await rerank_public_book_pg(question, model=embedding_model, source_bytes=source_bytes, connection=connection, top_k=10)
                context = build_context(ranked)
                prompt = build_public_book_prompt(context, records, source_bytes)
                content = generate(prompt, provider, model_id)
                try:
                    answer = parse_answer(content, prompt["allowed_citation_ids"])
                    validation_error = None
                except (ValueError, json.JSONDecodeError) as error:
                    answer = None
                    validation_error = str(error)
                rows.append({"category": category, "question": question, "model": model_id, "answer": answer,
                             "raw_answer": content if answer is None else None,
                             "sources": json.loads(context["context"])["sources"], "error": validation_error})
            except Exception as error:
                rows.append({"category": category, "question": question, "model": model_id,
                             "answer": None, "sources": json.loads(context["context"])["sources"] if context else [],
                             "error": f"{type(error).__name__}: {str(error)[:250]}"})
            print(json.dumps({"category": category, "model": model_id, "answer": rows[-1]["answer"], "error": rows[-1]["error"]}, ensure_ascii=False), flush=True)
    finally:
        await connection.close()
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["gemini", "groq"], required=True)
    parser.add_argument("--model")
    parser.add_argument("--categories", nargs="*", choices=[name for name, _ in CASES])
    parser.add_argument("--database-url", default=DEFAULT_URL)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    model_id = args.model or ("gemini-3.8-flash" if args.provider == "gemini" else "openai/gpt-oss-20b")
    chosen = [case for case in CASES if not args.categories or case[0] in args.categories]
    rows = asyncio.run(collect(chosen, args.provider, model_id, args.database_url))
    output = args.output or ROOT / "evaluation" / f"public_book_live_{args.provider}.json"
    output.write_text(json.dumps({"run_at_utc": datetime.now(timezone.utc).isoformat(), "provider": args.provider,
                                  "model": model_id, "rows": rows}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"report": str(output), "successful": sum(row["error"] is None for row in rows), "total": len(rows)}))


if __name__ == "__main__":
    main()
