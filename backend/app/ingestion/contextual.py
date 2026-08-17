"""
Contextual Summary Generator Module.

Implements Anthropic's Contextual Retrieval paradigm by generating a global document summary
that is injected into individual chunks to preserve document-level semantics during vector search.
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


def _extractive_summary_fallback(text: str) -> str:
    """Generate deterministic extractive summary from text header/first paragraphs."""
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return "General document overview."
    sentences = [s.strip() for s in cleaned.split(".") if s.strip()]
    if len(sentences) >= 2:
        return f"{sentences[0]}. {sentences[1]}."
    elif sentences:
        return f"{sentences[0]}."
    return cleaned[:150]


async def generate_contextual_summary(
    document_text: str,
    llm_client: Optional[Any] = None,
    max_context_chars: int = 2000
) -> str:
    """
    Generate a concise 2-sentence global document summary for contextual retrieval injection.

    Args:
        document_text: The complete or prefix text of the document.
        llm_client: Optional async LLM client (OpenAI / LiteLLM / LangChain / Anthropic).
        max_context_chars: Character limit to pass to the summary prompt (defaults to 2000).

    Returns:
        str: A 2-sentence global context summary string.
    """
    if not document_text or not document_text.strip():
        return "Empty document."

    first_snippet = document_text.strip()[:max_context_chars]

    if llm_client is None:
        return _extractive_summary_fallback(first_snippet)

    prompt = (
        "In 2 concise sentences, summarize what this document is about for retrieval context:\n\n"
        f"{first_snippet}"
    )

    try:
        # Support OpenAI AsyncClient
        if hasattr(llm_client, "chat") and hasattr(llm_client.chat, "completions"):
            response = await llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a precise technical summarizer for RAG systems."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.2
            )
            summary = response.choices[0].message.content.strip()
            return summary

        # Support callable async functions
        elif callable(llm_client):
            res = await llm_client(prompt)
            return str(res).strip()

        # Support client with .generate / .agenerate method
        elif hasattr(llm_client, "agenerate"):
            res = await llm_client.agenerate([prompt])
            return res.generations[0][0].text.strip()

        else:
            return _extractive_summary_fallback(first_snippet)

    except Exception as e:
        logger.warning(f"LLM contextual summary generation failed: {e}. Using extractive fallback.")
        return _extractive_summary_fallback(first_snippet)
