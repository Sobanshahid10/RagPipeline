"""ONNX cross-encoder reranking with a deterministic offline fallback."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

class CrossEncoderReranker:
    """Rerank fused candidates with an ONNX sequence-classification model."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self.model_name = model_name
        self.model: Any | None = None
        self.tokenizer: Any | None = None
        self._load_attempted = False
        self._fallback_warning_logged = False

    def _load_model(self) -> None:
        """Load and export the model on first use instead of slowing API startup."""
        if self._load_attempted:
            return
        self._load_attempted = True
        try:
            from optimum.onnxruntime import ORTModelForSequenceClassification
            from transformers import AutoTokenizer

            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = ORTModelForSequenceClassification.from_pretrained(
                self.model_name,
                export=True,
            )
        except Exception as exc:
            self.model = None
            self.tokenizer = None
            logger.warning("ONNX reranker unavailable; using lexical fallback: %s", exc)
            self._fallback_warning_logged = True

    @staticmethod
    def _fallback_score(query: str, candidate: dict[str, Any]) -> float:
        query_terms = set(re.findall(r"\w+", query.casefold()))
        content_terms = set(re.findall(r"\w+", str(candidate.get("content", "")).casefold()))
        lexical_overlap = len(query_terms & content_terms) / max(len(query_terms), 1)
        return float(candidate.get("rrf_score", 0.0)) + lexical_overlap

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int = 5
    ) -> list[dict[str, Any]]:
        if not candidates or top_k <= 0:
            return []

        limited = candidates[:40]
        self._load_model()
        scores: list[float]
        if self.model is not None and self.tokenizer is not None:
            try:
                import numpy as np

                pairs = [(query, str(chunk.get("content", ""))) for chunk in limited]
                encoded = self.tokenizer(
                    pairs,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="np",
                )
                outputs = self.model(**encoded)
                logits = np.asarray(outputs.logits)
                scores = logits[:, -1].reshape(-1).astype(float).tolist()
            except Exception as exc:
                logger.warning("ONNX reranking failed; using lexical fallback: %s", exc)
                scores = [self._fallback_score(query, chunk) for chunk in limited]
        else:
            if not self._fallback_warning_logged:
                logger.warning("ONNX reranker unavailable; using lexical fallback")
                self._fallback_warning_logged = True
            scores = [self._fallback_score(query, chunk) for chunk in limited]

        ranked: list[dict[str, Any]] = []
        for candidate, score in zip(limited, scores):
            item = candidate.copy()
            item["rerank_score"] = float(score)
            ranked.append(item)
        ranked.sort(key=lambda item: (-item["rerank_score"], str(item.get("id", ""))))
        return ranked[:top_k]
