"""Contract checks for the public-book benchmark; these are not quality scores."""

import json
import unittest

from evaluation.run_public_book_eval import (
    BOOK_NAME,
    DEFAULT_CASES,
    ROOT,
    evaluate,
    exact_evidence_recall,
    load_cases,
    parse_query_events,
    validate_traces,
)


class PublicBookEvaluationTests(unittest.TestCase):
    def test_reference_evidence_exists_in_book(self):
        cases = load_cases(DEFAULT_CASES, ROOT / BOOK_NAME)
        self.assertEqual(len(cases), 12)
        self.assertEqual(len({case["id"] for case in cases}), 12)

    def test_reads_actual_context_and_answer_from_query_stream(self):
        chunks = [{"id": "chunk-1", "source_filename": BOOK_NAME, "content": "BS Artificial Intelligence"}]
        stream = "\n\n".join([
            "data: " + json.dumps({"type": "retrieval", "chunks": chunks}),
            "data: " + json.dumps({"type": "token", "content": "Umar studies AI."}),
            "data: " + json.dumps({"type": "done", "metadata": {}}),
        ])
        answer, found = parse_query_events(stream)
        self.assertEqual(answer, "Umar studies AI.")
        self.assertEqual(found, chunks)
        with self.assertRaisesRegex(ValueError, "retrieved chunks"):
            parse_query_events('data: {"type":"token","content":"No provenance"}')

    def test_rejects_non_book_context(self):
        case = load_cases(DEFAULT_CASES, ROOT / BOOK_NAME)[0]
        trace = [{
            "id": case["id"], "answer": "A response",
            "chunks": [{"source_filename": "private_chat.txt", "content": "Something private"}],
        }]
        with self.assertRaisesRegex(ValueError, "public-book source"):
            validate_traces([case], trace)

    def test_rejects_unindexed_book(self):
        case = load_cases(DEFAULT_CASES, ROOT / BOOK_NAME)[0]
        with self.assertRaisesRegex(ValueError, "index the book"):
            validate_traces([case], [{"id": case["id"], "answer": "No information", "chunks": []}])

    def test_retrieval_only_does_not_claim_answer_quality(self):
        case = load_cases(DEFAULT_CASES, ROOT / BOOK_NAME)[1]
        context = " ".join(case["evidence"])
        trace = {"id": case["id"], "answer": "Observed answer", "chunks": [
            {"id": "chunk-1", "source_filename": BOOK_NAME, "content": context}
        ]}
        checked = validate_traces([case], [trace])
        self.assertEqual(exact_evidence_recall(case, trace["chunks"]), 1.0)
        report = evaluate([case], checked, None, None)
        self.assertEqual(report["metrics"]["exact_evidence_recall"], 1.0)
        self.assertNotIn("faithfulness", report["metrics"])


if __name__ == "__main__":
    unittest.main()
