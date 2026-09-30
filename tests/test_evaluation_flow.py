import io
import json
import os
import tempfile
import unittest
import threading
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen

from actionmail.evaluation.cli import DEFAULT_MAILEX_ROOT, DEFAULT_MANIFEST, main
from actionmail.evaluation.review import ReviewDataset
from actionmail.interfaces.review_server import create_server
from actionmail.workflow.pipeline import _user_prompt


class EvaluationFlowTests(unittest.TestCase):
    def test_frozen_cases_run_through_rule_baseline_and_persist_counts(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            output = Path(directory) / "rules"
            code = main(["--engine", "rules", "--output-dir", str(output)])
            rows = [json.loads(line) for line in (output / "cases.jsonl").read_text(encoding="utf-8").splitlines()]
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertEqual(len(rows), 50)
        self.assertTrue(summary["complete"])
        self.assertEqual(summary["planned_category_counts"], {"no_action": 15, "explicit_action": 15, "context_dependent": 10, "external_content": 10})
        self.assertEqual(summary["gold_status_counts"], {"action": 22, "no_action": 20, "needs_review": 8})
        self.assertEqual(summary["gold_deadline_kind_counts"], {"none": 37, "exact": 8, "relative_resolvable": 2, "relative_unresolvable": 1, "vague": 2})
        self.assertEqual(summary["counts"]["safe_external_abstention"], 10)
        self.assertEqual(sum(sum(values.values()) for values in summary["status_confusion"].values()), 50)

    def test_llm_smoke_run_records_usage_and_resume_avoids_duplicate_calls(self):
        completion = {
            "model": "test-model",
            "choices": [{"message": {"content": json.dumps({
                "status": "action", "action": "Work with Richard on collection procedures.", "deadline": None,
                "evidence": [{"source_id": "body", "quote": "Raetta, would you please work with Richard"}], "review_reason": None,
            })}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20},
        }
        calls = []

        def fake_urlopen(request, timeout):
            calls.append(request.full_url)
            return io.BytesIO(json.dumps(completion).encode("utf-8"))

        def fake_preflight(request, timeout):
            if request.full_url.endswith("/key"):
                data = {"usage": 0.2, "limit_remaining": 1.3}
            elif request.full_url.endswith("/credits"):
                data = {"total_credits": 3.0, "total_usage": 0.4}
            else:
                data = {"id": "test-model", "pricing": {"prompt": "0.0000001", "completion": "0.0000005", "request": "0"}}
            return io.BytesIO(json.dumps({"data": data}).encode("utf-8"))

        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret", "OPENROUTER_MANAGEMENT_KEY": "management-secret"}), patch(
            "actionmail.reasoning.api_client.urlopen", side_effect=fake_urlopen
        ), patch("actionmail.evaluation.preflight.urlopen", side_effect=fake_preflight), redirect_stdout(io.StringIO()) as output_text:
            output = Path(directory) / "smoke"
            arguments = ["--engine", "llm", "--model", "test-model", "--case-id", "A01", "--output-dir", str(output), "--input-price-per-million", "0.1", "--output-price-per-million", "0.5", "--yes"]
            self.assertEqual(main(arguments + ["--preflight"]), 0)
            self.assertFalse(output.exists())
            first = main(arguments)
            second = main(arguments + ["--resume"])
            rows = [json.loads(line) for line in (output / "cases.jsonl").read_text(encoding="utf-8").splitlines()]
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            metadata = (output / "run.json").read_text(encoding="utf-8")
        self.assertEqual((first, second), (0, 0))
        self.assertEqual(len(calls), 1)
        self.assertIn("Key spending limit remaining: $1.3000", output_text.getvalue())
        self.assertIn("Account credit balance: $2.6000", output_text.getvalue())
        self.assertIn("Expected batch cost: about", output_text.getvalue())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["prediction"]["status"], "action")
        self.assertEqual(rows[0]["usage"]["input_tokens"], 100)
        self.assertAlmostEqual(rows[0]["estimated_cost_usd"], 0.00002)
        self.assertFalse(summary["complete"])
        self.assertNotIn("test-secret", metadata)
        self.assertNotIn("management-secret", metadata)

    def test_history_command_lists_saved_runs_without_loading_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir = root / "results" / "evaluation" / "demo"
            run_dir.mkdir(parents=True)
            (run_dir / "run.json").write_text(json.dumps({"started_at_utc": "2026-09-29T00:00:00Z", "engine": "rules", "model": "rules-v1", "manifest_sha256": "12345678", "case_ids": ["A01"]}), encoding="utf-8")
            (run_dir / "summary.json").write_text(json.dumps({"completed_cases": 1, "counts": {"status_correct": 1}, "estimated_cost_usd": None}), encoding="utf-8")
            with patch("actionmail.evaluation.cli.PROJECT_ROOT", root), redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(["--history"]), 0)
            self.assertIn("demo  rules/rules-v1  1/1 cases", output.getvalue())

    def test_snapshot_evaluation_records_two_calls_and_read_source(self):
        decisions = iter([
            {"status": "needs_review", "action": None, "deadline": None, "evidence": [], "review_reason": "Attachment unread"},
            {"status": "action", "action": "Approve invoice INV-104.", "deadline": "2026-10-01", "evidence": [{"source_id": "attachment:1", "quote": "Alex, please approve invoice INV-104 by 2026-10-01."}], "review_reason": None},
        ])

        def fake_urlopen(request, timeout):
            completion = {"model": "test-model", "choices": [{"message": {"content": json.dumps(next(decisions))}}], "usage": {"prompt_tokens": 100, "completion_tokens": 20}}
            return io.BytesIO(json.dumps(completion).encode("utf-8"))

        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret"}), patch(
            "actionmail.reasoning.api_client.urlopen", side_effect=fake_urlopen
        ), patch("actionmail.evaluation.cli._show_preflight", return_value=(0.1, 0.5, 0.0, "test")), redirect_stdout(io.StringIO()):
            output = Path(directory) / "snapshot"
            self.assertEqual(main(["--engine", "llm", "--model", "test-model", "--case-id", "E01", "--external-mode", "snapshots", "--output-dir", str(output), "--yes"]), 0)
            row = json.loads((output / "cases.jsonl").read_text(encoding="utf-8"))
            metadata = json.loads((output / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(row["prediction"]["status"], "action")
        self.assertEqual(row["prediction"]["evidence"][0]["source_id"], "attachment:1")
        self.assertEqual(row["model_calls"], 2)
        self.assertEqual(row["usage"]["input_tokens"], 200)
        self.assertEqual(row["read_sources"][0]["method"], "frozen_snapshot")
        self.assertFalse(row["safe_external_abstention"])
        self.assertEqual(metadata["external_mode"], "snapshots")

    def test_external_cohort_preflight_selects_only_ten_frozen_cases(self):
        selected = []

        def preview(args, cases, key):
            selected.extend(case.case_id for case in cases)
            return (0.1, 0.5, 0.0, "test")

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret"}), patch(
            "actionmail.evaluation.cli._show_preflight", side_effect=preview
        ), redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--engine", "llm", "--model", "test-model", "--case-group", "external", "--external-mode", "snapshots", "--preflight"]), 0)
        self.assertEqual(selected, [f"E{index:02d}" for index in range(1, 11)])

    def test_v2_snapshot_case_checks_one_action_and_read_provenance(self):
        responses = iter([
            {"sources": [{"source_id": "attachment:1", "relevance": "decisive", "reason": "Newest message refers to attached instructions"}]},
            {"status": "action", "review_reason": None, "actions": [
                {"kind": "perform_task", "text": "Approve invoice INV-104.", "deadline": "2026-10-01",
                 "evidence": [{"source_id": "attachment:1", "quote": "Alex, please approve invoice INV-104 by 2026-10-01."}]},
            ]},
        ])

        def fake_urlopen(request, timeout):
            completion = {"model": "test-model", "choices": [{"message": {"content": json.dumps(next(responses))}}], "usage": {"prompt_tokens": 100, "completion_tokens": 30}}
            return io.BytesIO(json.dumps(completion).encode("utf-8"))

        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret"}), patch(
            "actionmail.reasoning.api_client.urlopen", side_effect=fake_urlopen
        ), patch("actionmail.evaluation.cli._show_preflight", return_value=(0.1, 0.5, 0.0, "test")), redirect_stdout(io.StringIO()):
            output = Path(directory) / "external-v2"
            self.assertEqual(main(["--engine", "llm", "--schema", "v2", "--model", "test-model", "--case-id", "E01", "--external-mode", "snapshots", "--output-dir", str(output), "--yes"]), 0)
            row = json.loads((output / "cases.jsonl").read_text(encoding="utf-8"))
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(row["model_calls"], 2)
        self.assertEqual(row["read_sources"][0]["source_id"], "attachment:1")
        self.assertTrue(row["status_correct"])
        self.assertTrue(row["action_count_match"])
        self.assertEqual(summary["counts"]["status_checked"], 1)

    def test_v2_draft_cohort_is_saved_without_scoring_pending_references(self):
        responses = iter([
            {"status": "action", "review_reason": None, "actions": [
                {"kind": "perform_task", "text": "Approve invoice INV-104.", "deadline": None,
                 "evidence": [{"source_id": "body", "quote": "Alex, please approve invoice INV-104."}]},
                {"kind": "perform_task", "text": "Update the website contact page.", "deadline": None,
                 "evidence": [{"source_id": "body", "quote": "Separately, update the public website's contact page."}]},
            ]},
            {"status": "needs_review", "review_reason": "The attachment is missing.", "actions": []},
        ])

        def fake_urlopen(request, timeout):
            completion = {"model": "test-model", "choices": [{"message": {"content": json.dumps(next(responses))}}], "usage": {"prompt_tokens": 100, "completion_tokens": 30}}
            return io.BytesIO(json.dumps(completion).encode("utf-8"))

        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret"}), patch(
            "actionmail.reasoning.api_client.urlopen", side_effect=fake_urlopen
        ), patch("actionmail.evaluation.cli._show_preflight", return_value=(0.1, 0.5, 0.0, "test")), redirect_stdout(io.StringIO()):
            output = Path(directory) / "multi"
            self.assertEqual(main(["--engine", "llm", "--schema", "v2", "--model", "test-model", "--case-group", "multi-draft", "--output-dir", str(output), "--yes"]), 0)
            rows = [json.loads(line) for line in (output / "cases.jsonl").read_text(encoding="utf-8").splitlines()]
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            dataset = ReviewDataset.open(output, DEFAULT_MANIFEST, DEFAULT_MAILEX_ROOT)
            detail = dataset.detail("A16")
            saved = dataset.save_review("A16", {
                "action_meaning": "", "evidence_support": "", "gold_label": "uncertain", "note": "Review each task.",
                "action_checks": [
                    {"action_meaning": "correct", "evidence_support": "correct"},
                    {"action_meaning": "uncertain", "evidence_support": "correct"},
                ],
            })
        self.assertEqual([row["case_id"] for row in rows], ["A16", "C13"])
        self.assertEqual(rows[0]["prediction"]["actions"][1]["kind"], "perform_task")
        self.assertIsNone(rows[0]["status_correct"])
        self.assertEqual(summary["counts"]["pending_owner_reference"], 2)
        self.assertEqual(summary["counts"].get("status_checked", 0), 0)
        self.assertEqual(detail["multi_action_draft"]["review_state"], "pending_owner")
        self.assertEqual(len(detail["multi_action_draft"]["candidate_actions"]), 2)
        self.assertEqual(saved["action_checks"][1]["action_meaning"], "uncertain")

    def test_local_review_page_loads_case_and_saves_separate_assessment(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            output = Path(directory) / "rules"
            self.assertEqual(main(["--engine", "rules", "--output-dir", str(output)]), 0)
            original = (output / "cases.jsonl").read_bytes()
            dataset = ReviewDataset.open(output, DEFAULT_MANIFEST, DEFAULT_MAILEX_ROOT)
            server = create_server(dataset)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                base = f"http://127.0.0.1:{server.server_port}"
                with urlopen(base + "/") as response:
                    self.assertIn(b"Evaluation review", response.read())
                with urlopen(base + "/api/cases/A06") as response:
                    detail = json.load(response)
                self.assertIn("would not apply", detail["email"]["body"])
                self.assertEqual(detail["gold"]["status"], "action")
                with urlopen(base + "/api/cases/C10") as response:
                    context = json.load(response)
                self.assertEqual(context["email"]["thread"][0]["sender"], "Lee, Dennis")
                self.assertEqual(context["email"]["thread"][0]["recipients"], "Lindberg, Lorraine")
                self.assertEqual(context["email"]["thread"][0]["sender_addresses"], [])
                self.assertEqual(context["gold"]["status"], "action")
                self.assertEqual(dataset.cases["C08"].gold["status"], "action")
                self.assertEqual(dataset.cases["C11"].gold["status"], "needs_review")
                self.assertEqual(dataset.cases["C12"].gold["status"], "needs_review")
                self.assertEqual(dataset.cases["A16"].gold["status"], "needs_review")
                self.assertEqual(dataset.cases["C13"].gold["status"], "needs_review")
                self.assertEqual(dataset.cases["A21"].gold["deadline_kind"], "exact")
                self.assertEqual(dataset.cases["A22"].gold["deadline_kind"], "exact")
                self.assertEqual(dataset.cases["A23"].gold["deadline_kind"], "relative_resolvable")
                self.assertEqual(dataset.cases["A23"].gold["deadline"], "2026-09-30")
                self.assertEqual(dataset.cases["A24"].gold["deadline_kind"], "relative_resolvable")
                with urlopen(base + "/api/cases/A23") as response:
                    relative = json.load(response)
                self.assertEqual(relative["email"]["received_at"], "2026-09-29T09:00:00+08:00")
                self.assertEqual(relative["gold"]["deadline"], "2026-09-30")
                self.assertIn("receives this for awareness", dataset.cases["E05"].record["source"]["external_sources"][0]["text"])
                prompt = _user_prompt(dataset.cases["C10"].email)
                self.assertIn("SOURCE thread:1 (older message):\nFrom: Lee, Dennis\nFrom email address(es): not provided in source\nTo: Lindberg, Lorraine", prompt)
                self.assertIn("Target recipient: darrell.schoolcraft@enron.com", prompt)
                self.assertIn("To: dennis.lee@enron.com, darrell.schoolcraft@enron.com, perry.frazier@enron.com", prompt)
                self.assertIn("Cc: none shown", prompt)
                self.assertIn("sscott5@enron.com", _user_prompt(dataset.cases["C09"].email))
                review = {"action_meaning": "uncertain", "evidence_support": "correct", "gold_label": "correct", "note": "Question meaning needs review."}
                request = Request(
                    base + "/api/cases/A06/review",
                    data=json.dumps(review).encode("utf-8"),
                    headers={"Content-Type": "application/json", "Origin": base},
                    method="POST",
                )
                with urlopen(request) as response:
                    saved = json.load(response)
                self.assertEqual(saved["review"]["action_meaning"], "uncertain")
                self.assertEqual(dataset.reviews()["A06"]["note"], review["note"])
                self.assertEqual((output / "cases.jsonl").read_bytes(), original)
                later_output = Path(directory) / "later-rules"
                self.assertEqual(main(["--engine", "rules", "--output-dir", str(later_output)]), 0)
                later_dataset = ReviewDataset.open(later_output, DEFAULT_MANIFEST, DEFAULT_MAILEX_ROOT)
                self.assertEqual(later_dataset.detail("A06")["prior_gold_review"]["gold_label"], "correct")
                self.assertIsNone(later_dataset.detail("A06")["review"])
            finally:
                server.shutdown()
                worker.join(timeout=2)
                server.server_close()


if __name__ == "__main__":
    unittest.main()
