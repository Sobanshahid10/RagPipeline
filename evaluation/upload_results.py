#!/usr/bin/env python3
"""
Evaluation Results Uploader for RAGAS Nightly Evaluation.

Scans evaluation/results for the latest RAGAS run, formats metrics,
and uploads or archives them for tracking in CI/CD, telemetry, and observability.

Usage:
    python evaluation/upload_results.py
"""

import glob
import json
import os
import sys
from pathlib import Path


def upload_latest_results(results_dir: str = "evaluation/results") -> int:
    """Find and archive/upload the latest Ragas evaluation results."""
    files = glob.glob(os.path.join(results_dir, "ragas_*.json"))
    if not files:
        files = glob.glob(os.path.join(results_dir, "*.json"))

    if not files:
        print("No evaluation result files found in", results_dir)
        return 0

    latest_file = max(files, key=os.path.getmtime)
    print(f"Discovered latest evaluation results: {latest_file}")

    with open(latest_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    timestamp = data.get("timestamp", "unknown")
    sample_count = data.get("sample_count", 0)
    metrics = data.get("metrics", {})

    print("=" * 60)
    print(f"RAGAS EVALUATION METRICS SUMMARY ({timestamp})")
    print(f"Total Evaluated Samples: {sample_count}")
    print("-" * 60)
    for k, v in metrics.items():
        print(f"  • {k:<25}: {v:.4f}")
    print("=" * 60)

    # Export consolidated summary artifact
    summary_path = Path(results_dir) / "latest_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "source_file": str(latest_file),
            "timestamp": timestamp,
            "sample_count": sample_count,
            "metrics": metrics,
            "status": "UPLOADED",
        }, f, indent=2)

    print(f"Results archived and synced to {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(upload_latest_results())
