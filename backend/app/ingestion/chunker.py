"""
Sentence-Aware Semantic Chunking Module.

Splits document text into clean, semantically coherent chunks by respecting
sentence boundaries, applying contextual prefixes, and maintaining overlap windows.
"""

import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

_tokenizer = None
_spacy_nlp = None


def get_tokenizer():
    """Lazily load tiktoken cl100k_base tokenizer."""
    global _tokenizer
    if _tokenizer is None:
        try:
            import tiktoken
            _tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            _tokenizer = None
    return _tokenizer


def get_spacy_nlp():
    """Lazily load lightweight spaCy sentencizer pipeline."""
    global _spacy_nlp
    if _spacy_nlp is None:
        try:
            import spacy
            _spacy_nlp = spacy.blank("en")
            _spacy_nlp.add_pipe("sentencizer")
        except Exception:
            _spacy_nlp = None
    return _spacy_nlp


def count_tokens(text: str) -> int:
    """
    Count tokens using tiktoken (cl100k_base) with fallback to character heuristic.
    """
    tok = get_tokenizer()
    if tok:
        try:
            return len(tok.encode(text))
        except Exception:
            pass
    # Fallback heuristic: approx 4 characters per token
    return max(1, len(text) // 4)


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into grammatical sentences preserving punctuation boundaries.
    Uses spaCy sentencizer if available, falling back to regex.
    """
    if not text or not text.strip():
        return []

    nlp = get_spacy_nlp()
    if nlp is not None:
        try:
            doc = nlp(text)
            sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
            if sentences:
                return sentences
        except Exception as e:
            logger.debug(f"spaCy sentencizer error: {e}. Using regex fallback.")

    # Regex sentence boundary splitter
    sentence_endings = re.compile(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s+')
    sentences = sentence_endings.split(text.strip())
    return [s.strip() for s in sentences if s.strip()]


def semantic_chunk(
    text: str,
    contextual_summary: str = "",
    chunk_size: int = 512,
    overlap: int = 64
) -> List[Dict[str, Any]]:
    """
    Chunk document text without breaking mid-sentence, prepending global context summaries.

    Args:
        text: Raw or PII-masked text to chunk.
        contextual_summary: Global document summary to inject as prefix context.
        chunk_size: Target token capacity per chunk (default 512).
        overlap: Desired token overlap budget for sliding context window (default 64).

    Returns:
        List[Dict[str, Any]]: List of chunk dicts containing:
            - chunk_index (int): 0-indexed position
            - content (str): Text content with contextual summary prefix
            - token_count (int): Total token length
            - contextual_summary (str): The injected context summary
    """
    if not text or not text.strip():
        return []

    sentences = split_into_sentences(text)
    if not sentences:
        return []

    chunks: List[Dict[str, Any]] = []
    current_sentences: List[str] = []
    current_tokens = 0
    chunk_idx = 0

    prefix_summary = f"[Context: {contextual_summary.strip()}]\n" if contextual_summary.strip() else ""
    prefix_tokens = count_tokens(prefix_summary) if prefix_summary else 0

    for sentence in sentences:
        sentence_tokens = count_tokens(sentence)

        # If adding this sentence exceeds chunk_size and we already have accumulated sentences
        if current_tokens + sentence_tokens > chunk_size and current_sentences:
            chunk_content = " ".join(current_sentences)
            full_chunk_text = f"{prefix_summary}{chunk_content}"

            chunks.append({
                "chunk_index": chunk_idx,
                "content": full_chunk_text,
                "token_count": prefix_tokens + current_tokens,
                "contextual_summary": contextual_summary
            })
            chunk_idx += 1

            # Build overlapping sentence window
            overlap_sentences: List[str] = []
            overlap_count = 0
            for s in reversed(current_sentences):
                s_tok = count_tokens(s)
                if overlap_count + s_tok <= overlap:
                    overlap_sentences.insert(0, s)
                    overlap_count += s_tok
                else:
                    break

            # If overlap_sentences was empty (single sentence was large), retain the last 2 sentences if possible
            if not overlap_sentences and len(current_sentences) > 1:
                overlap_sentences = current_sentences[-2:]
                overlap_count = sum(count_tokens(s) for s in overlap_sentences)

            current_sentences = overlap_sentences
            current_tokens = overlap_count

        current_sentences.append(sentence)
        current_tokens += sentence_tokens

    # Flush final remaining sentences
    if current_sentences:
        chunk_content = " ".join(current_sentences)
        full_chunk_text = f"{prefix_summary}{chunk_content}"
        chunks.append({
            "chunk_index": chunk_idx,
            "content": full_chunk_text,
            "token_count": prefix_tokens + current_tokens,
            "contextual_summary": contextual_summary
        })

    return chunks


# Alias for backward compatibility
sentence_aware_chunking = semantic_chunk
