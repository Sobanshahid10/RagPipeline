"""Authenticated chat over the existing, public-only knowledge-book index."""

from __future__ import annotations

import asyncio
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

import time
import asyncpg
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.core.dependencies import get_current_user
from app.models.user import User

from huggingface_hub import snapshot_download

try:
    from backend.app.generation.public_book_generate import send_to_gemini
    from backend.app.generation.public_book_prompt import ABSTENTION, build_public_book_prompt
    from backend.app.ingestion.embed_public_book import MODEL_ID, LocalMiniLM
    from backend.app.retrieval.public_book_context import build_context
    from backend.app.retrieval.public_book_rerank import rerank_public_book_pg
    PUBLIC_BOOK_MODULES_AVAILABLE = True
except ModuleNotFoundError:
    # The generic Docker image has backend/ as its build context and lacks the
    # repository-root public book and its step modules. Keep generic chat up.
    PUBLIC_BOOK_MODULES_AVAILABLE = False

ROOT = Path(__file__).resolve().parents[3]
MODELS = Literal[
    "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash",
    "gemini-3.5-flash", "gemini-3.5-flash-lite",
    "openai/gpt-oss-120b", "openai/gpt-oss-20b",
]
router = APIRouter(prefix=f"{settings.API_V1_STR}/public-book", tags=["Public Book"])


class PublicBookQuestion(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    model: MODELS = "gemini-3.8-flash"


def _retrieval_query(question: str) -> tuple[str, str | None]:
    lowered = question.casefold()
    if "portfolio" in lowered and ("best" in lowered or "strongest" in lowered):
        return question + " Umar portfolio skills projects technical patterns evidence provenance experience", "umar"
    if "portfolio" in lowered and ("worst" in lowered or "weakest" in lowered):
        return question + " Umar portfolio scale claims shipped agents self-reported limits verification", "umar"
    if any(phrase in lowered for phrase in (
        "created this", "made this", "built this", "developed this",
        "creator", "creators", "maker", "makers", "author", "authors",
        "who created", "who made", "who built", "who developed",
        "who are the people", "names of the people", "who built you",
        "who made you", "who created you"
    )):
        return question + " Muhammad Umar Farooq Muhammad Soban Shahid creators authors people identity shared context collaboration", None
    return question, None


@lru_cache(maxsize=1)
def _retrieval_model() -> LocalMiniLM:
    return LocalMiniLM(Path(snapshot_download(MODEL_ID, local_files_only=True)))


def _parse_answer(content: str, allowed: list[str]) -> dict:
    result = json.loads(content.strip().removeprefix("```json").removesuffix("```").strip())
    if set(result) != {"answer", "citations", "abstained"}:
        raise ValueError("Model response has unexpected fields")
    if not isinstance(result["answer"], str) or not isinstance(result["citations"], list) or not all(isinstance(item, str) for item in result["citations"]) or type(result["abstained"]) is not bool:
        raise ValueError("Model response has invalid field types")
    result["answer"] = re.sub(r"【(S\d+)】", r"[\1]", result["answer"])
    result["answer"] = re.sub(
        r"\[((?:S\d+\s*,\s*)+S\d+)\]",
        lambda match: "".join(f"[{part.strip()}]" for part in match.group(1).split(",")),
        result["answer"],
    )
    # An abstention is a fixed message, not an evidentiary claim. Some models
    # append a citation even when declining; remove only that exact suffix.
    abstention_with_citations = re.fullmatch(
        re.escape(ABSTENTION[:-1]) + r"\.?\s*(?:\[S\d+\]\s*)+\.?",
        result["answer"],
    )
    if abstention_with_citations and all(
        source_id in allowed for source_id in re.findall(r"\[(S\d+)\]", result["answer"])
    ):
        result["answer"] = ABSTENTION
        result["citations"] = []
    if result["answer"] == ABSTENTION and not result["citations"]:
        result["abstained"] = True
    inline = list(dict.fromkeys(re.findall(r"\[(S\d+)\]", result["answer"])))
    if not result.get("abstained"):
        if any(s not in allowed for s in inline) or any(s not in allowed for s in result.get("citations", [])):
            raise ValueError("Model response contains missing or mismatched citations")

    if result["abstained"]:
        result["answer"] = ABSTENTION
        result["citations"] = []
    else:
        if inline:
            result["citations"] = inline
        elif result["citations"]:
            valid_cits = [s for s in result["citations"] if s in allowed]
            if valid_cits:
                result["citations"] = valid_cits
                result["answer"] = f"{result['answer'].rstrip()} " + "".join(f"[{s}]" for s in valid_cits)
            else:
                result["citations"] = []
        else:
            result["citations"] = []
    return result


def _generate(prompt: dict, model: str) -> str:
    if model.startswith("gemini-"):
        last_error = None
        models_to_try = [model] + [m for m in ("gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite") if m != model]
        for m in models_to_try:
            for attempt in range(2):
                try:
                    data = send_to_gemini(prompt, model=m, api_key=settings.GEMINI_API_KEY or "")
                    return "".join(part.get("text", "") for candidate in data.get("candidates", []) for part in candidate.get("content", {}).get("parts", []))
                except httpx.HTTPStatusError as err:
                    last_error = err
                    if err.response.status_code in (429, 500, 502, 503, 504) and attempt < 1:
                        time.sleep(1.2)
                        continue
                    break
                except Exception as err:
                    last_error = err
                    break
            # If 429 or 5xx, continue to next sibling Gemini model
            if isinstance(last_error, httpx.HTTPStatusError) and last_error.response.status_code in (429, 500, 502, 503, 504):
                continue
            elif last_error:
                break

        # If all Gemini models are exhausted and Groq is available, try Groq as emergency resilience
        if settings.GROQ_API_KEY:
            for groq_m in ("openai/gpt-oss-120b", "openai/gpt-oss-20b"):
                try:
                    response = httpx.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                        json={"model": groq_m, "messages": prompt["messages"], "temperature": 0,
                              "response_format": {"type": "json_object"}},
                        timeout=75,
                    )
                    if response.status_code == 200:
                        return response.json()["choices"][0]["message"]["content"]
                except Exception:
                    continue

        if last_error:
            raise last_error

    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured")

    groq_models = [model] + [m for m in ("openai/gpt-oss-20b", "openai/gpt-oss-120b") if m != model]
    last_groq_error = None
    for gm in groq_models:
        for attempt in range(2):
            try:
                response = httpx.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                    json={"model": gm, "messages": prompt["messages"], "temperature": 0,
                          "response_format": {"type": "json_object"}},
                    timeout=75,
                )
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                response.raise_for_status()
            except httpx.HTTPStatusError as err:
                last_groq_error = err
                if err.response.status_code in (429, 500, 502, 503, 504) and attempt < 1:
                    time.sleep(1.5)
                    continue
                break
            except Exception as err:
                last_groq_error = err
                break

    # If Groq is rate limited or unavailable, fall back to Gemini
    if settings.GEMINI_API_KEY:
        for gem_m in ("gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash"):
            try:
                data = send_to_gemini(prompt, model=gem_m, api_key=settings.GEMINI_API_KEY or "")
                return "".join(part.get("text", "") for candidate in data.get("candidates", []) for part in candidate.get("content", {}).get("parts", []))
            except Exception:
                continue

    if last_groq_error:
        raise last_groq_error
    raise RuntimeError("Failed to generate response across all available providers")


@router.post("/ask")
async def ask_public_book(request: PublicBookQuestion, _user: User = Depends(get_current_user)) -> dict:
    if not PUBLIC_BOOK_MODULES_AVAILABLE:
        raise HTTPException(503, "Public-book pipeline is unavailable in this deployment")
    source = ROOT / "PUBLIC_KNOWLEDGE_BOOK.md"
    records_path = ROOT / "storage/knowledge/public_book_records.json"
    if not source.exists() or not records_path.exists():
        raise HTTPException(503, "Public-book source or index metadata is unavailable")
    source_bytes = source.read_bytes()
    records = json.loads(records_path.read_text(encoding="utf-8"))
    database_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
    try:
        connection = await asyncpg.connect(database_url)
        try:
            search_question, owner = _retrieval_query(request.question)
            retrieval_model = await asyncio.to_thread(_retrieval_model)
            ranked = await rerank_public_book_pg(
                search_question, model=retrieval_model, source_bytes=source_bytes,
                connection=connection, top_k=10, owner=owner,
            )
            ranked["question"] = request.question
        finally:
            await connection.close()
        context = build_context(ranked)
        prompt = build_public_book_prompt(context, records, source_bytes)
        raw_answer = await asyncio.to_thread(_generate, prompt, request.model)
        answer = _parse_answer(raw_answer, prompt["allowed_citation_ids"])
    except httpx.HTTPStatusError as error:
        status = error.response.status_code
        if status == 429:
            raise HTTPException(429, f"{request.model} reached its rate limit; choose another model or try later") from error
        if status in (500, 502, 503, 504):
            raise HTTPException(503, f"{request.model} is temporarily unavailable") from error
        raise HTTPException(502, f"{request.model} request failed with provider status {status}") from error
    except httpx.RequestError as error:
        raise HTTPException(503, f"{request.model} could not be reached; try again shortly") from error
    except RuntimeError as error:
        if "quota or rate limit" in str(error):
            raise HTTPException(429, f"{request.model} reached its rate limit; choose another model or try later") from error
        if "unavailable for this API" in str(error):
            raise HTTPException(502, f"{request.model} is unavailable for this API key") from error
        raise HTTPException(502, "Answer generation failed") from error
    except (ValueError, json.JSONDecodeError) as error:
        raise HTTPException(502, f"Answer validation failed: {error}") from error
    except (OSError, asyncpg.PostgresError) as error:
        raise HTTPException(503, "Public-book index is unavailable or stale") from error
    return {
        "question": request.question,
        "model": request.model,
        **answer,
        "sources": json.loads(context["context"])["sources"],
    }
