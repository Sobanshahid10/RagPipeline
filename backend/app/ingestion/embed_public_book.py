"""Embed the public book locally with the cached all-MiniLM-L6-v2 model.

This stage writes a validated file, never a vector database. No corpus text
leaves the computer and no synthetic vectors are accepted.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import struct
from pathlib import Path
from typing import Any

import numpy as np
from huggingface_hub import snapshot_download
from tokenizers import Tokenizer

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
DIMENSIONS = 384
MAX_TOKENS = 256
INPUT_TEMPLATE_VERSION = 2


def validate_records(artifact: dict[str, Any], source_bytes: bytes) -> list[dict[str, Any]]:
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    if artifact.get("source_name") != "PUBLIC_KNOWLEDGE_BOOK.md":
        raise ValueError("Expected public-book metadata records")
    if artifact.get("source_sha256") != source_hash:
        raise ValueError("Metadata records are stale; rerun earlier steps")
    records = artifact.get("records")
    if not isinstance(records, list) or not records or len(records) != artifact.get("record_count"):
        raise ValueError("Record count does not match the metadata manifest")
    if len({record.get("id") for record in records}) != len(records):
        raise ValueError("Missing or duplicate record IDs")
    for record in records:
        if record["metadata"]["source_sha256"] != source_hash:
            raise ValueError(f"Source hash mismatch in record {record['id']}")
        actual = hashlib.sha256(record["content"].encode("utf-8")).hexdigest()
        if record["metadata"]["content_sha256"] != actual:
            raise ValueError(f"Content hash mismatch in record {record['id']}")
    return records


def validate_vector(values: Any, *, record_id: str) -> list[float]:
    if not isinstance(values, list) or len(values) != DIMENSIONS:
        raise ValueError(f"Record {record_id}: expected {DIMENSIONS} vector values")
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
        raise ValueError(f"Record {record_id}: non-finite or non-numeric vector value")
    norm = math.sqrt(sum(value * value for value in values))
    if not 0.98 <= norm <= 1.02:
        raise ValueError(f"Record {record_id}: unexpected vector norm {norm:.4f}")
    return [float(value) for value in values]


def _load_safetensors(path: Path) -> dict[str, np.ndarray]:
    """Read the cached F32 weights without importing PyTorch."""
    with path.open("rb") as file:
        header_length = struct.unpack("<Q", file.read(8))[0]
        header = json.loads(file.read(header_length))
    weights = {}
    for name, spec in header.items():
        if name == "__metadata__":
            continue
        if name == "embeddings.position_ids":
            continue  # BERT buffer; positions are generated from sequence length.
        if spec["dtype"] != "F32":
            raise ValueError(f"Unexpected weight dtype in {name}")
        start, end = spec["data_offsets"]
        shape = tuple(spec["shape"])
        if int(np.prod(shape)) * 4 != end - start:
            raise ValueError(f"Invalid weight shape in {name}")
        weights[name] = np.memmap(path, dtype="<f4", mode="r", offset=8 + header_length + start, shape=shape)
    return weights


class LocalMiniLM:
    def __init__(self, model_path: Path):
        config = json.loads((model_path / "config.json").read_text())
        sentence_config = json.loads((model_path / "sentence_bert_config.json").read_text())
        pooling_config = json.loads((model_path / "1_Pooling" / "config.json").read_text())
        if (config["hidden_size"], config["num_hidden_layers"], config["num_attention_heads"]) != (384, 6, 12):
            raise ValueError("Unexpected MiniLM architecture")
        if sentence_config["max_seq_length"] != MAX_TOKENS or not pooling_config["pooling_mode_mean_tokens"]:
            raise ValueError("Unexpected sentence pooling configuration")
        self.path = model_path
        self.model_hash = hashlib.sha256((model_path / "model.safetensors").read_bytes()).hexdigest()
        self.weights = _load_safetensors(model_path / "model.safetensors")
        self.tokenizer = Tokenizer.from_file(str(model_path / "tokenizer.json"))
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()

    def _linear(self, x: np.ndarray, prefix: str) -> np.ndarray:
        return x @ self.weights[prefix + ".weight"].T + self.weights[prefix + ".bias"]

    def _norm(self, x: np.ndarray, prefix: str) -> np.ndarray:
        # BERT LayerNorm, epsilon from the model's config.
        return (x - x.mean(axis=-1, keepdims=True)) / np.sqrt(
            x.var(axis=-1, keepdims=True) + 1e-12
        ) * self.weights[prefix + ".weight"] + self.weights[prefix + ".bias"]

    def _window_embedding(self, ids: list[int]) -> np.ndarray:
        count = len(ids)
        w = self.weights
        x = (
            w["embeddings.word_embeddings.weight"][ids]
            + w["embeddings.position_embeddings.weight"][:count]
            + w["embeddings.token_type_embeddings.weight"][0]
        )
        x = self._norm(x, "embeddings.LayerNorm")
        for layer in range(6):
            p = f"encoder.layer.{layer}"
            q, k, v = (
                self._linear(x, f"{p}.attention.self.{part}").reshape(count, 12, 32).transpose(1, 0, 2)
                for part in ("query", "key", "value")
            )
            scores = (q @ k.transpose(0, 2, 1)) / math.sqrt(32)
            scores -= scores.max(axis=-1, keepdims=True)
            attention = np.exp(scores)
            attention /= attention.sum(axis=-1, keepdims=True)
            context = (attention @ v).transpose(1, 0, 2).reshape(count, DIMENSIONS)
            x = self._norm(x + self._linear(context, f"{p}.attention.output.dense"), f"{p}.attention.output.LayerNorm")
            intermediate = self._linear(x, f"{p}.intermediate.dense")
            # GELU tanh approximation; max difference from exact GELU is small.
            activated = 0.5 * intermediate * (
                1 + np.tanh(math.sqrt(2 / math.pi) * (intermediate + 0.044715 * intermediate**3))
            )
            x = self._norm(x + self._linear(activated, f"{p}.output.dense"), f"{p}.output.LayerNorm")
        return x.mean(axis=0)

    def embed(self, content: str) -> tuple[list[float], int, int]:
        encoding = self.tokenizer.encode(content)
        ids = encoding.ids
        # Preserve all tokens. Long records get multiple 256-token model windows.
        # Each window has its own [CLS]/[SEP], then token-weighted pooling.
        cls_id, sep_id = ids[0], ids[-1]
        body = ids[1:-1]
        pieces = [body[i : i + MAX_TOKENS - 2] for i in range(0, len(body), MAX_TOKENS - 2)] or [[]]
        combined = np.zeros(DIMENSIONS, dtype=np.float64)
        total_weight = 0
        for piece in pieces:
            window = [cls_id, *piece, sep_id]
            weight = len(piece) or 1
            combined += self._window_embedding(window).astype(np.float64) * weight
            total_weight += weight
        combined /= total_weight
        norm = np.linalg.norm(combined)
        if not math.isfinite(float(norm)) or norm == 0:
            raise ValueError("Model returned an invalid embedding")
        return (combined / norm).astype(np.float32).tolist(), len(ids), len(pieces)


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def generate_embeddings(
    artifact: dict[str, Any], source_bytes: bytes, *, model: LocalMiniLM, output: Path
) -> dict[str, Any]:
    records = validate_records(artifact, source_bytes)
    source_hash = artifact["source_sha256"]
    checkpoint_path = output.with_name(output.stem + ".partial.json")
    if checkpoint_path.exists():
        saved = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        expected = (MODEL_ID, model.model_hash, source_hash, INPUT_TEMPLATE_VERSION)
        actual = (saved.get("model"), saved.get("model_sha256"), saved.get("source_sha256"), saved.get("input_template_version"))
        if actual != expected or not isinstance(saved.get("vectors"), dict):
            raise ValueError("Existing embedding checkpoint belongs to another source/model/input format")
    else:
        saved = {
            "model": MODEL_ID, "model_sha256": model.model_hash, "source_sha256": source_hash,
            "input_template_version": INPUT_TEMPLATE_VERSION, "vectors": {},
        }
    ids = {record["id"] for record in records}
    if set(saved["vectors"]) - ids:
        raise ValueError("Embedding checkpoint contains unknown record IDs")
    for record in records:
        item = saved["vectors"].get(record["id"])
        if item is not None:
            if item["content_sha256"] != record["metadata"]["content_sha256"]:
                raise ValueError(f"Stale checkpoint content for {record['id']}")
            validate_vector(item["vector"], record_id=record["id"])
            continue
        vector, tokens, windows = model.embed(record["content"])
        saved["vectors"][record["id"]] = {
            "content_sha256": record["metadata"]["content_sha256"],
            "vector": validate_vector(vector, record_id=record["id"]),
            "token_count": tokens,
            "window_count": windows,
        }
        _write_json_atomic(checkpoint_path, saved)
        print(f"Embedded {len(saved['vectors'])}/{len(records)} records", flush=True)
    result = {
        "status": "complete",
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_name": artifact["source_name"],
        "source_sha256": source_hash,
        "model_provider": "local Hugging Face cache",
        "model": MODEL_ID,
        "model_sha256": model.model_hash,
        "dimensions": DIMENSIONS,
        "max_model_tokens": MAX_TOKENS,
        "input_template_version": INPUT_TEMPLATE_VERSION,
        "document_input": "record.content",
        "matching_query_input": "raw question text",
        "record_count": len(records),
        "total_model_tokens": sum(item["token_count"] for item in saved["vectors"].values()),
        "multi_window_records": sum(item["window_count"] > 1 for item in saved["vectors"].values()),
        "records": [
            {"id": record["id"], **saved["vectors"][record["id"]]}
            for record in records
        ],
    }
    _write_json_atomic(output, result)
    checkpoint_path.unlink(missing_ok=True)
    return result


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Generate local embeddings for the public book")
    parser.add_argument("--input", type=Path, default=root / "storage/knowledge/public_book_records.json")
    parser.add_argument("--source", type=Path, default=root / "PUBLIC_KNOWLEDGE_BOOK.md")
    parser.add_argument("--output", type=Path, default=root / "storage/knowledge/public_book_embeddings.json")
    args = parser.parse_args()
    model_path = Path(snapshot_download(MODEL_ID, local_files_only=True))
    artifact = json.loads(args.input.read_text(encoding="utf-8"))
    result = generate_embeddings(artifact, args.source.read_bytes(), model=LocalMiniLM(model_path), output=args.output)
    print(json.dumps({key: value for key, value in result.items() if key != "records"}, indent=2))
    print(f"Saved embeddings to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
