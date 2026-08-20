"""Query-aware context compression with an LLMLingua-2 fallback."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

MODEL_NAME = "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank"
_prompt_compressor: Any | None = None
_load_attempted = False


def _get_prompt_compressor() -> Any | None:
    global _prompt_compressor, _load_attempted
    if _load_attempted:
        return _prompt_compressor
    _load_attempted = True
    try:
        from llmlingua import PromptCompressor

        _prompt_compressor = PromptCompressor(
            model_name=MODEL_NAME,
            use_llmlingua2=True,
        )
    except Exception as exc:
        logger.warning("LLMLingua compressor unavailable; using extractive fallback: %s", exc)
        _prompt_compressor = None
    return _prompt_compressor


def _extractive_compress(text: str, query: str, ratio: float) -> str:
    """Keep query-relevant sentences while honoring an approximate word budget."""
    words = text.split()
    if not words:
        return ""
    budget = max(1, round(len(words) * ratio))
    query_terms = set(re.findall(r"\w+", query.casefold()))
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    ranked = sorted(
        enumerate(sentences),
        key=lambda pair: (
            -len(query_terms & set(re.findall(r"\w+", pair[1].casefold()))),
            pair[0],
        ),
    )
    selected: list[tuple[int, str]] = []
    used = 0
    for index, sentence in ranked:
        sentence_words = sentence.split()
        if selected and used + len(sentence_words) > budget:
            continue
        selected.append((index, " ".join(sentence_words[: max(1, budget - used)])))
        used += len(sentence_words)
        if used >= budget:
            break
    return " ".join(sentence for _, sentence in sorted(selected)) or " ".join(words[:budget])


def compress_context(
    chunks: list[dict[str, Any]],
    query: str,
    ratio: float = 0.5,
    prompt_compressor: Any | None = None,
) -> list[dict[str, Any]]:
    """Compress the combined context and preserve each chunk's citation metadata."""
    if not 0 < ratio <= 1:
        raise ValueError("ratio must be greater than 0 and at most 1")
    if not chunks:
        return []

    compressor = prompt_compressor if prompt_compressor is not None else _get_prompt_compressor()
    originals = [str(chunk.get("content", "")) for chunk in chunks]
    combined_context = "\n\n".join(originals)
    compressed_context = ""
    if compressor is not None and combined_context:
        try:
            result = compressor.compress_prompt(combined_context, question=query, ratio=ratio)
            if isinstance(result, dict):
                compressed_context = str(
                    result.get("compressed_prompt")
                    or result.get("compressed_text")
                    or ""
                )
            elif isinstance(result, str):
                compressed_context = result
        except Exception as exc:
            logger.warning("LLMLingua compression failed: %s", exc)

    # Assign each retained sentence to the source with the greatest token overlap.
    # This keeps page and bounding-box citations attached after global compression.
    assigned: list[list[str]] = [[] for _ in chunks]
    source_terms = [set(re.findall(r"\w+", text.casefold())) for text in originals]
    for segment in re.split(r"(?<=[.!?])\s+|\n+", compressed_context.strip()):
        if not segment.strip():
            continue
        terms = set(re.findall(r"\w+", segment.casefold()))
        source_index = max(
            range(len(chunks)),
            key=lambda index: len(terms & source_terms[index]),
        )
        assigned[source_index].append(segment.strip())

    compressed_chunks: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks):
        item = chunk.copy()
        mapped_text = " ".join(assigned[index]).strip()
        item["content"] = mapped_text or _extractive_compress(originals[index], query, ratio)
        compressed_chunks.append(item)
    return compressed_chunks
