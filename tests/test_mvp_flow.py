import json
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from actionmail.ingestion.eml import load_eml
from actionmail.ingestion.fixtures import load_json_email
from actionmail.interfaces.cli import main
from actionmail.reasoning.model_client import ModelReply
from actionmail.workflow.pipeline import process_email


class FakeModel:
    def __init__(self, result: dict):
        self.result = result

    def complete(self, system_prompt: str, user_prompt: str) -> ModelReply:
        self.last_prompt = user_prompt
        return ModelReply(json.dumps(self.result), "fake-model")


class MVPFlowTests(unittest.TestCase):
    def test_json_email_action_reaches_reviewable_result(self):
        payload = {
            "case_id": "sample-1",
            "target_recipient": "alex@example.com",
            "received_at": "2026-09-28T09:00:00+08:00",
            "sender": "manager@example.com",
            "recipients": ["alex@example.com"],
            "subject": "Alex, please send the revised proposal by 2026-10-01",
            "body": "Thank you.",
        }
        model = FakeModel({
            "status": "action",
            "action": "Send the revised proposal",
            "deadline": "2026-10-01",
            "evidence": [{"source_id": "subject", "quote": "please send the revised proposal by 2026-10-01"}],
            "review_reason": None,
        })
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = process_email(load_json_email(path), model)
        self.assertEqual(result.decision.status, "action")
        self.assertEqual(result.decision.deadline, "2026-10-01")
        self.assertFalse(result.validation_errors)
        self.assertIn("Target recipient: alex@example.com", model.last_prompt)

    def test_model_source_label_is_normalized_before_evidence_check(self):
        model = FakeModel({
            "status": "action",
            "action": "Send the revised proposal",
            "deadline": "2026-10-01",
            "evidence": [{"source_id": "SOURCE body", "quote": "send me the revised proposal by 1 October 2026"}],
            "review_reason": None,
        })
        result = process_email(load_json_email(Path(__file__).resolve().parents[1] / "examples" / "sample_email.json"), model)
        self.assertEqual(result.decision.status, "action")
        self.assertEqual(result.decision.evidence[0].source_id, "body")
        self.assertFalse(result.validation_errors)

    def test_eml_no_action_reaches_reviewable_result(self):
        raw = (
            "From: manager@example.com\n"
            "To: alex@example.com\n"
            "Date: Mon, 28 Sep 2026 09:00:00 +0800\n"
            "Subject: Update\n"
            "MIME-Version: 1.0\n"
            "Content-Type: text/plain; charset=utf-8\n\n"
            "I sent the proposal to the client yesterday.\n"
        ).encode("utf-8")
        model = FakeModel({"status": "no_action", "action": None, "deadline": None, "evidence": [], "review_reason": None})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "message.eml"
            path.write_bytes(raw)
            result = process_email(load_eml(path, "alex@example.com"), model)
        self.assertEqual(result.decision.status, "no_action")
        self.assertFalse(result.validation_errors)

    def test_html_email_link_requires_review_before_no_action(self):
        raw = (
            "From: manager@example.com\n"
            "To: alex@example.com\n"
            "Date: Mon, 28 Sep 2026 09:00:00 +0800\n"
            "Subject: Instructions\n"
            "MIME-Version: 1.0\n"
            "Content-Type: text/html; charset=utf-8\n\n"
            '<p>Please see <a href="https://example.com/instructions">the instructions</a>.</p>'
        ).encode("utf-8")
        model = FakeModel({"status": "no_action", "action": None, "deadline": None, "evidence": [], "review_reason": None})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "message.eml"
            path.write_bytes(raw)
            email = load_eml(path, "alex@example.com")
            result = process_email(email, model)
        self.assertEqual(email.unread_sources, ("https://example.com/instructions",))
        self.assertEqual(result.decision.status, "needs_review")

    def test_multipart_email_detects_html_only_link(self):
        raw = (
            "From: manager@example.com\n"
            "To: alex@example.com\n"
            "Date: Mon, 28 Sep 2026 09:00:00 +0800\n"
            "Subject: Instructions\n"
            "MIME-Version: 1.0\n"
            'Content-Type: multipart/alternative; boundary="part"\n\n'
            "--part\nContent-Type: text/plain; charset=utf-8\n\n"
            "Please see the instructions.\n"
            "--part\nContent-Type: text/html; charset=utf-8\n\n"
            '<p>Please see <a href="https://example.com/instructions">the instructions</a>.</p>\n'
            "--part--\n"
        ).encode("utf-8")
        model = FakeModel({"status": "no_action", "action": None, "deadline": None, "evidence": [], "review_reason": None})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "message.eml"
            path.write_bytes(raw)
            email = load_eml(path, "alex@example.com")
            result = process_email(email, model)
        self.assertEqual(email.unread_sources, ("https://example.com/instructions",))
        self.assertEqual(result.decision.status, "needs_review")

    def test_unsupported_evidence_cannot_become_an_action(self):
        payload = {
            "case_id": "sample-2",
            "target_recipient": "alex@example.com",
            "received_at": "2026-09-28T09:00:00+08:00",
            "body": "Please see the attached instructions.",
            "unread_sources": ["instructions.pdf"],
        }
        model = FakeModel({
            "status": "action",
            "action": "Pay the invoice",
            "deadline": None,
            "evidence": [{"source_id": "attachment:1", "quote": "Pay the invoice"}],
            "review_reason": None,
        })
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = process_email(load_json_email(path), model)
        self.assertEqual(result.decision.status, "needs_review")
        self.assertIn("Unknown evidence source", result.decision.review_reason)

    def test_unread_attachment_prevents_definitive_no_action(self):
        payload = {
            "case_id": "sample-3",
            "target_recipient": "alex@example.com",
            "received_at": "2026-09-28T09:00:00+08:00",
            "body": "Please see the attachment.",
            "unread_sources": ["instructions.pdf"],
        }
        model = FakeModel({"status": "no_action", "action": None, "deadline": None, "evidence": [], "review_reason": None})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = process_email(load_json_email(path), model)
        self.assertEqual(result.decision.status, "needs_review")
        self.assertIn("Unread external content", result.decision.review_reason)

    def test_cli_runs_json_through_api_boundary_and_review(self):
        payload = {
            "case_id": "sample-4",
            "target_recipient": "alex@example.com",
            "received_at": "2026-09-28T09:00:00+08:00",
            "body": "Alex, please confirm the meeting by 2026-10-01.",
        }
        completion = {
            "model": "test-model",
            "choices": [{"message": {"content": json.dumps({
                "status": "action",
                "action": "Confirm the meeting",
                "deadline": "2026-10-01",
                "evidence": [{"source_id": "body", "quote": "please confirm the meeting by 2026-10-01"}],
                "review_reason": None,
            })}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 40},
        }
        output = io.StringIO()

        def fake_urlopen(request, timeout):
            self.assertEqual(request.get_header("Authorization"), "Bearer test-secret")
            request_body = json.loads(request.data)
            self.assertEqual(request_body["model"], "test-model")
            self.assertIn("please confirm the meeting", request_body["messages"][1]["content"])
            return io.BytesIO(json.dumps(completion).encode("utf-8"))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret"}), patch(
                "actionmail.reasoning.api_client.urlopen", side_effect=fake_urlopen
            ), patch("builtins.input", side_effect=["y", "y"]), redirect_stdout(output):
                code = main([str(path), "--model", "test-model"])
        self.assertEqual(code, 0)
        self.assertIn('"status": "action"', output.getvalue())
        self.assertIn("Approved for review. No calendar or mailbox change was made.", output.getvalue())


if __name__ == "__main__":
    unittest.main()
