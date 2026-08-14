import re
from typing import List, Dict, Any
import tiktoken

def get_tokenizer():
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None

tokenizer = get_tokenizer()

def count_tokens(text: str) -> int:
    if tokenizer:
        return len(tokenizer.encode(text))
    # Fallback heuristic: 1 token ~= 4 characters
    return max(1, len(text) // 4)

def split_into_sentences(text: str) -> List[str]:
    """
    Split text into grammatical sentences preserving punctuation boundaries.
    """
    sentence_endings = re.compile(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s+')
    sentences = sentence_endings.split(text.strip())
    return [s.strip() for s in sentences if s.strip()]

def sentence_aware_chunking(
    text: str,
    chunk_size: int = 512,
    overlap: int = 64,
    contextual_summary: str = ""
) -> List[Dict[str, Any]]:
    """
    Chunk document text without breaking mid-sentence, appending global context summaries.
    Returns list of dicts with text, token_count, and index.
    """
    sentences = split_into_sentences(text)
    chunks = []
    current_sentences: List[str] = []
    current_tokens = 0
    chunk_idx = 0

    prefix_summary = f"[Context: {contextual_summary.strip()}]\n" if contextual_summary else ""
    prefix_tokens = count_tokens(prefix_summary)

    for sentence in sentences:
        sentence_tokens = count_tokens(sentence)

        if current_tokens + sentence_tokens > chunk_size and current_sentences:
            # Build completed chunk text
            chunk_content = " ".join(current_sentences)
            full_chunk_text = f"{prefix_summary}{chunk_content}"
            
            chunks.append({
                "chunk_index": chunk_idx,
                "content": full_chunk_text,
                "token_count": prefix_tokens + current_tokens,
                "contextual_summary": contextual_summary
            })
            chunk_idx += 1

            # Keep overlapping sentences for continuous context window
            overlap_sentences: List[str] = []
            overlap_count = 0
            for s in reversed(current_sentences):
                s_tok = count_tokens(s)
                if overlap_count + s_tok <= overlap:
                    overlap_sentences.insert(0, s)
                    overlap_count += s_tok
                else:
                    break

            current_sentences = overlap_sentences
            current_tokens = overlap_count

        current_sentences.append(sentence)
        current_tokens += sentence_tokens

    # Append final remaining chunk
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
