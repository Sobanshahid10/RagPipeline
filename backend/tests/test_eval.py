"""Unit tests for Day 11 RAGAS Evaluation Infrastructure and Hard-Negative Miner."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure repository root is on sys.path for evaluation imports
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from evaluation.assert_thresholds import (
    calculate_citation_parse_success_rate,
    compute_metric_value,
    load_golden_dataset,
)
from evaluation.hard_negative_miner import (
    analyze_with_llm,
    append_to_golden_dataset,
    deduce_category_from_query,
    process_negative_interactions,
)
from evaluation.run_ragas import (
    compute_eval_metrics,
    generate_mock_rag_response,
    load_dataset,
    parse_sse_events,
)


def test_golden_dataset_structure_and_distribution():
    """Test 1: Validate golden_dataset.json schema, count >= 200, and difficulty distribution."""
    dataset_path = ROOT_DIR / "evaluation" / "golden_dataset.json"
    assert dataset_path.exists(), "golden_dataset.json does not exist"

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    # 1. Total count check
    assert len(dataset) >= 200, f"Dataset has {len(dataset)} items, expected >= 200"

    expected_categories = {
        "HR_Policy",
        "Technical_Docs",
        "Financial_Reports",
        "Legal_Contracts",
        "Onboarding",
    }
    expected_difficulties = {"easy", "medium", "hard"}

    difficulty_counts = {"easy": 0, "medium": 0, "hard": 0}
    category_counts = {cat: 0 for cat in expected_categories}

    # 2. Schema check on each sample
    for item in dataset:
        assert "id" in item and item["id"].startswith("eval_")
        assert "query" in item and len(item["query"].strip()) > 10
        assert "ground_truth" in item and len(item["ground_truth"].strip()) > 10
        assert "relevant_chunk_ids" in item and isinstance(
            item["relevant_chunk_ids"], list
        )
        assert item["category"] in expected_categories, (
            f"Invalid category: {item['category']}"
        )
        assert item["difficulty"] in expected_difficulties, (
            f"Invalid difficulty: {item['difficulty']}"
        )

        difficulty_counts[item["difficulty"]] += 1
        category_counts[item["category"]] += 1

    # 3. Category coverage
    for cat, count in category_counts.items():
        assert count >= 30, f"Category {cat} has only {count} entries, expected >= 30"

    # 4. Difficulty distribution check (40% easy, 40% medium, 20% hard with +/-5% tolerance)
    total = len(dataset)
    easy_pct = difficulty_counts["easy"] / total
    med_pct = difficulty_counts["medium"] / total
    hard_pct = difficulty_counts["hard"] / total

    assert 0.35 <= easy_pct <= 0.45, (
        f"Easy percentage {easy_pct:.2f} out of target ~0.40"
    )
    assert 0.35 <= med_pct <= 0.45, (
        f"Medium percentage {med_pct:.2f} out of target ~0.40"
    )
    assert 0.15 <= hard_pct <= 0.25, (
        f"Hard percentage {hard_pct:.2f} out of target ~0.20"
    )


def test_assert_thresholds_logic_and_metrics():
    """Test 2: Validate threshold assertion computation and bounds checking."""
    dataset_path = str(ROOT_DIR / "evaluation" / "golden_dataset.json")

    # Check recall_at_5
    recall = compute_metric_value("recall_at_5", dataset_path=dataset_path)
    assert recall >= 0.75, f"Expected recall_at_5 >= 0.75, got {recall}"

    # Check max_ttft_ms
    ttft = compute_metric_value("max_ttft_ms", dataset_path=dataset_path)
    assert ttft <= 500.0, f"Expected max_ttft_ms <= 500, got {ttft}"

    # Check citation_parse_success_rate
    rate = compute_metric_value(
        "citation_parse_success_rate", dataset_path=dataset_path
    )
    assert rate >= 0.95, f"Expected citation rate >= 0.95, got {rate}"

    # Check custom results file reading
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump({"metrics": {"faithfulness": 0.96, "context_precision": 0.89}}, tf)
        temp_file = Path(tf.name)

    try:
        val = compute_metric_value("faithfulness", results_file=temp_file)
        assert val == 0.96
        val_prec = compute_metric_value("context_precision", results_file=temp_file)
        assert val_prec == 0.89
    finally:
        if temp_file.exists():
            temp_file.unlink()


def test_hard_negative_miner_processing_and_llm_diagnosis():
    """Test 3: Validate negative interaction mining, classification, and dataset appending."""
    # Test category deduction
    assert deduce_category_from_query("What is the PTO carryover?") == "HR_Policy"
    assert (
        deduce_category_from_query("What was Q3 EBITDA margin?") == "Financial_Reports"
    )
    assert (
        deduce_category_from_query("What is the indemnification liability cap?")
        == "Legal_Contracts"
    )
    assert (
        deduce_category_from_query("How do new hires configure YubiKey SSO?")
        == "Onboarding"
    )

    # Test LLM diagnosis heuristic fallback
    diagnosis = analyze_with_llm(
        raw_query="What is the bereavement policy?",
        chunk_excerpts="No relevant chunks found.",
        answer="I do not have access to that information.",
    )
    assert diagnosis["failure_mode"] in {
        "retrieval_fail",
        "hallucination",
        "context_loss",
        "wrong_route",
    }
    assert len(diagnosis["correct_answer"]) > 0

    # Test dataset appending with a temporary test file
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump(
            [{"id": "eval_001", "query": "Existing query", "ground_truth": "GT"}], tf
        )
        temp_dataset_path = tf.name

    try:
        mock_interactions = [
            {
                "id": "mock_int_1",
                "raw_query": "New question from negative thumbs down?",
                "retrieved_chunk_ids": ["chunk_abc"],
                "answer": "Incorrect answer.",
                "route_used": "SEMANTIC_SEARCH",
            },
            {
                # Duplicate query should be deduplicated
                "id": "mock_int_2",
                "raw_query": "Existing query",
                "retrieved_chunk_ids": [],
                "answer": "Dup answer.",
                "route_used": "DIRECT_LLM",
            },
        ]

        added = process_negative_interactions(
            mock_interactions, dataset_path=temp_dataset_path
        )
        assert added == 1, f"Expected 1 new entry added, got {added}"

        with open(temp_dataset_path, "r", encoding="utf-8") as f:
            updated = json.load(f)

        assert len(updated) == 2
        mined_entry = updated[1]
        assert mined_entry["source"] == "hard_negative_mining"
        assert "failure_mode" in mined_entry
        assert mined_entry["query"] == "New question from negative thumbs down?"
    finally:
        if os.path.exists(temp_dataset_path):
            os.remove(temp_dataset_path)


def test_ragas_runner_sse_parsing_and_mock_eval():
    """Test 4: Validate SSE stream parsing and mock evaluation runner logic."""
    sse_sample = (
        "event: token\n"
        'data: {"token": "Senior employees receive "}\n\n'
        "event: token\n"
        'data: {"token": "30 days PTO."}\n\n'
        "event: citation\n"
        'data: {"chunks": [{"content": "Senior employee PTO policy is 30 days."}]}\n\n'
        "event: done\n"
        'data: {"status": "complete"}\n\n'
    )

    answer, contexts = parse_sse_events(sse_sample)
    assert "Senior employees receive 30 days PTO." in answer
    assert len(contexts) >= 1
    assert "Senior employee PTO policy" in contexts[0]

    # Test mock evaluation metrics
    sample = {
        "id": "eval_test_01",
        "query": "What is annual leave for seniors?",
        "ground_truth": "Senior employees get 30 days PTO.",
    }
    mock_ans, mock_ctx = generate_mock_rag_response(sample)
    assert len(mock_ans) > 0
    assert len(mock_ctx) > 0

    eval_items = [
        {
            "id": sample["id"],
            "question": sample["query"],
            "ground_truth": sample["ground_truth"],
            "answer": mock_ans,
            "contexts": mock_ctx,
        }
    ]

    metrics = compute_eval_metrics(eval_items)
    assert "faithfulness" in metrics
    assert "context_precision" in metrics
    assert "context_recall" in metrics
    assert "answer_relevancy" in metrics
    assert metrics["faithfulness"] >= 0.90
    assert metrics["context_precision"] >= 0.80


def test_celery_does_not_schedule_private_interaction_mining():
    from app.celery_app import celery_app

    assert not celery_app.conf.beat_schedule
    assert "evaluation.hard_negative_miner" not in celery_app.conf.include
