import json
import io
import os
import tempfile
import unittest
from scripted_responses import explained
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from actionmail.ingestion.eml import load_eml
from actionmail.ingestion.fixtures import load_json_email
from actionmail.content.links import fetch_allowlisted_https
from actionmail.content.reader import read_external_sources
from actionmail.interfaces.cli import main
from actionmail.domain.email import EmailPackage, ExternalSource, SourceText
from actionmail.reasoning.model_client import ModelReply
from actionmail.workflow.pipeline import process_email, process_email_with_external
from actionmail.workflow.multi_pipeline import process_email_multi


class FakeModel:
    def __init__(self, result: dict):
        self.result = result

    def complete(self, system_prompt: str, user_prompt: str) -> ModelReply:
        self.last_prompt = user_prompt
        return ModelReply(json.dumps(explained(self.result, user_prompt)), "fake-model")


class SequenceModel:
    def __init__(self, results: list[dict]):
        self.results = iter(results)
        self.prompts = []

    def complete(self, system_prompt: str, user_prompt: str) -> ModelReply:
        self.prompts.append(user_prompt)
        return ModelReply(json.dumps(explained(next(self.results), user_prompt)), "fake-model", 100, 20, 10.0)


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

    def test_common_model_shape_variants_keep_evidence_gate(self):
        email = load_json_email(Path(__file__).resolve().parents[1] / "examples" / "sample_email.json")
        base = {"action": None, "deadline": None, "evidence": None, "review_reason": None}
        no_action = process_email(email, FakeModel({"status": "no_action", **base}))
        self.assertEqual(no_action.decision.status, "no_action")
        self.assertFalse(no_action.validation_errors)

        request = {
            "status": "action", "action": "Send the revised proposal", "deadline": "2026-10-01",
            "evidence": {"source_id": "body", "quote": "Alex, please send me the revised proposal by 1 October 2026."},
            "review_reason": None,
        }
        action = process_email(email, FakeModel(request))
        self.assertEqual(action.decision.status, "action")
        self.assertFalse(action.validation_errors)

        request["review_reason"] = "The sender asks for a proposal."
        explained = process_email(email, FakeModel(request))
        self.assertIsNone(explained.decision.review_reason)
        request["review_reason"] = None

        request["evidence"]["quote"] = "Alex, please  send me the revised proposal by 1 October 2026."
        spacing = process_email(email, FakeModel(request))
        self.assertEqual(spacing.decision.status, "action")
        self.assertEqual(spacing.decision.evidence[0].quote, "Alex, please send me the revised proposal by 1 October 2026.")

        request["evidence"]["quote"] = "Please send the fabricated proposal."
        unsupported = process_email(email, FakeModel(request))
        self.assertEqual(unsupported.decision.status, "needs_review")
        self.assertIn("Evidence quote is absent", unsupported.decision.review_reason)

    def test_old_thread_request_alone_cannot_become_current_action(self):
        email = EmailPackage(
            case_id="thread-example", target_recipient="alex@example.com", received_at=None,
            sender="sender@example.com", recipients=("alex@example.com",), subject="Update",
            body="I have sent the update to you.",
            thread=(SourceText("thread:1", "Please send me the report."),),
        )
        model = FakeModel({
            "status": "action", "action": "Send the report", "deadline": None,
            "evidence": [{"source_id": "thread:1", "quote": "Please send me the report."}],
            "review_reason": None,
        })
        result = process_email(email, model)
        self.assertEqual(result.decision.status, "needs_review")
        self.assertIn("prior-thread request", result.decision.review_reason)

    def test_abbreviation_period_is_recovered_without_changing_the_request(self):
        email = EmailPackage(
            case_id="abbreviation", target_recipient="alex@example.com", received_at=None,
            sender="manager@example.com", recipients=("alex@example.com",), subject="Agreement",
            body="Can you confirm that this would not apply to Enron Power Marketing, Inc.?",
        )
        response = {
            "status": "action", "action": "Confirm whether the agreement applies.", "deadline": None,
            "evidence": [{"source_id": "body", "quote": "Can you confirm that this would not apply to Enron Power Marketing, Inc?"}],
            "review_reason": None,
        }
        recovered = process_email(email, FakeModel(response))
        self.assertEqual(recovered.decision.status, "action")
        self.assertEqual(recovered.decision.evidence[0].quote, email.body)
        response["evidence"][0]["quote"] = "Can you confirm that this would apply to Enron Power Marketing, Inc?"
        changed_meaning = process_email(email, FakeModel(response))
        self.assertEqual(changed_meaning.decision.status, "needs_review")

    def test_empty_newest_body_requires_review_even_with_a_subject_and_thread(self):
        email = EmailPackage(
            case_id="empty-body", target_recipient="alex@example.com", received_at=None,
            sender="manager@example.com", recipients=("alex@example.com",), subject="Ready to execute ASAP",
            body="", thread=(SourceText("thread:1", "Please sign the attached amendment."),),
        )
        response = {"status": "no_action", "action": None, "deadline": None, "evidence": [], "review_reason": None}
        result = process_email(email, FakeModel(response))
        self.assertEqual(result.decision.status, "needs_review")
        self.assertIn("empty newest-message body", result.decision.review_reason)

    def test_eml_no_action_reaches_reviewable_result(self):
        raw = (
            "From: manager@example.com\n"
            "To: alex@example.com\n"
            "Cc: reviewer@example.com\n"
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
        self.assertIn("To: alex@example.com", model.last_prompt)
        self.assertIn("Cc: reviewer@example.com", model.last_prompt)

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

    def test_frozen_attachment_snapshot_uses_second_model_pass_and_source_evidence(self):
        payload = {
            "case_id": "snapshot", "target_recipient": "alex@example.com", "received_at": "2026-09-29T09:00:00+08:00",
            "body": "The next step is in the attachment.",
            "external_sources": [{"source_id": "attachment:1", "kind": "attachment", "name": "instructions.txt", "text": "Alex, approve invoice INV-104 by 2026-10-01."}],
        }
        model = SequenceModel([
            {"status": "needs_review", "action": None, "deadline": None, "evidence": [], "review_reason": "Attachment unread"},
            {"status": "action", "action": "Approve invoice INV-104.", "deadline": "2026-10-01", "evidence": [{"source_id": "attachment:1", "quote": "Alex, approve invoice INV-104 by 2026-10-01."}], "review_reason": None},
        ])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            run = process_email_with_external(load_json_email(path), model)
        self.assertEqual(run.decision.status, "action")
        self.assertEqual(run.decision.deadline, "2026-10-01")
        self.assertEqual(len(run.replies), 2)
        self.assertEqual(run.read_records[0].source_id, "attachment:1")
        self.assertIn("SOURCE attachment:1", model.prompts[1])
        self.assertFalse(run.validation_errors)

    def test_local_text_attachment_reads_and_unapproved_link_is_denied(self):
        raw = (
            "From: manager@example.com\nTo: alex@example.com\nDate: Tue, 29 Sep 2026 09:00:00 +0800\n"
            "Subject: Instructions\nMIME-Version: 1.0\nContent-Type: multipart/mixed; boundary=part\n\n"
            "--part\nContent-Type: text/plain; charset=utf-8\n\nPlease read the attachment.\n"
            "--part\nContent-Type: text/plain; name=instructions.txt\nContent-Disposition: attachment; filename=instructions.txt\n\n"
            "Alex, approve invoice INV-104.\n--part--\n"
        ).encode("utf-8")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "message.eml"
            path.write_bytes(raw)
            email = load_eml(path, "alex@example.com")
            outcome = read_external_sources(email)
        self.assertEqual(outcome.email.sources()["attachment:1"].strip(), "Alex, approve invoice INV-104.")
        self.assertEqual(outcome.email.unread_sources, ())
        with self.assertRaisesRegex(ValueError, "explicitly allowed"):
            fetch_allowlisted_https("https://example.org/instructions", ())
        with self.assertRaisesRegex(ValueError, "allowlist"):
            fetch_allowlisted_https("https://example.org/instructions", ("other.example",))
        with patch("actionmail.content.links.socket.getaddrinfo", return_value=[(None, None, None, None, ("127.0.0.1", 443))]):
            with self.assertRaisesRegex(ValueError, "non-public address"):
                fetch_allowlisted_https("https://example.org/instructions", ("example.org",))

    def test_link_snapshot_and_explicit_live_reader_keep_distinct_provenance(self):
        snapshot = ExternalSource("link:1", "link", "https://example.org/task", snapshot_text="Alex, send the plan.")
        email = EmailPackage(
            case_id="link-example", target_recipient="alex@example.com", received_at=None,
            sender="manager@example.com", recipients=("alex@example.com",), subject="Task page",
            body="Your task is at https://example.org/task", unread_sources=(snapshot.name,), external_sources=(snapshot,),
        )
        frozen = read_external_sources(email)
        self.assertEqual(frozen.email.sources()["link:1"], "Alex, send the plan.")
        self.assertEqual(frozen.records[0].method, "frozen_snapshot")
        live_email = EmailPackage(
            case_id="live-link", target_recipient="alex@example.com", received_at=None,
            sender="manager@example.com", recipients=("alex@example.com",), subject="Task page",
            body="Your task is at https://example.org/task", unread_sources=(snapshot.name,),
            external_sources=(ExternalSource("link:1", "link", snapshot.name),),
        )
        live = read_external_sources(live_email, fetch_live=lambda url: (b"Alex, send the plan.", "text/plain", "utf-8"))
        self.assertEqual(live.records[0].method, "allowlisted_https")
        self.assertEqual(live.email.sources()["link:1"], "Alex, send the plan.")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "live.json"
            path.write_text(json.dumps({
                "case_id": "live-link", "target_recipient": "alex@example.com", "body": live_email.body,
                "external_sources": [{"source_id": "link:1", "kind": "link", "name": snapshot.name}],
            }), encoding="utf-8")
            loaded = load_json_email(path)
        self.assertIsNone(loaded.external_sources[0].snapshot_text)
        self.assertEqual(loaded.unread_sources, (snapshot.name,))

    def test_missing_pdf_dependency_requests_review_without_blocking_startup(self):
        source = ExternalSource("attachment:1", "attachment", "report.pdf", content=b"%PDF-1.7", media_type="application/pdf")
        email = EmailPackage(
            case_id="missing-pdf-reader", target_recipient="alex@example.com", received_at=None,
            sender="maya@example.com", recipients=("alex@example.com",), subject="Report",
            body="Please review the attachment.", unread_sources=(source.name,), external_sources=(source,),
        )
        with patch.dict("sys.modules", {"pypdf": None}):
            outcome = read_external_sources(email)
        self.assertEqual(outcome.records, ())
        self.assertIn("PDF support requires pypdf", outcome.failures[0])

    def test_two_independent_tasks_have_two_evidenced_actions(self):
        body = "Alex, please approve invoice INV-104. Separately, update the public website's contact page."
        email = EmailPackage(
            case_id="two-tasks", target_recipient="alex@example.com", received_at=None,
            sender="maya@example.com", recipients=("alex@example.com",), subject="Invoice and website", body=body,
        )
        response = {
            "status": "action", "review_reason": None,
            "actions": [
                {"kind": "perform_task", "text": "Approve invoice INV-104.", "deadline": None, "evidence": [{"source_id": "body", "quote": "Alex, please approve invoice INV-104."}]},
                {"kind": "perform_task", "text": "Update the public website contact page.", "deadline": None, "evidence": [{"source_id": "body", "quote": "Separately, update the public website's contact page."}]},
            ],
        }
        two_actions = process_email_multi(email, FakeModel(response), max_actions=2)
        self.assertEqual(two_actions.decision.status, "action")
        self.assertEqual(two_actions.decision.action_count, 2)
        self.assertFalse(two_actions.validation_errors)
        default_limit = process_email_multi(email, FakeModel(response))
        self.assertEqual(default_limit.decision.action_count, 2)
        one_action_limit = process_email_multi(email, FakeModel(response), max_actions=1)
        self.assertEqual(one_action_limit.decision.status, "needs_review")
        self.assertIn("More than 1 actions", one_action_limit.decision.review_reason)
        with self.assertRaisesRegex(ValueError, "between 1 and 3"):
            process_email_multi(email, FakeModel(response), max_actions=4)

        four_tasks = dict(response)
        four_tasks["actions"] = response["actions"] + [
            {"kind": "perform_task", "text": f"Complete task {index}.", "deadline": None,
             "evidence": [{"source_id": "body", "quote": "Alex, please approve invoice INV-104."}]}
            for index in (3, 4)
        ]
        overflow = process_email_multi(email, FakeModel(four_tasks))
        self.assertEqual(overflow.decision.status, "needs_review")
        self.assertEqual(overflow.decision.action_count, 0)
        self.assertIn("More than 3 actions", overflow.decision.review_reason)

    def test_v2_recovers_unique_quote_source_and_single_evidence_object(self):
        quote = "Alex, approve invoice INV-104 by 2026-10-01."
        email = EmailPackage(
            case_id="source-alias", target_recipient="alex@example.com", received_at=None,
            sender="maya@example.com", recipients=("alex@example.com",), subject="Invoice",
            body="Please check the attached invoice instructions for your next step.",
            read_sources=(SourceText("attachment:1", quote),),
        )
        response = {"status": "action", "review_reason": None, "actions": [{
            "kind": "perform_task", "text": "Approve invoice INV-104.", "deadline": "2026-10-01",
            "evidence": [
                {"source_id": "newest message body", "quote": email.body},
                {"source_id": "attachment:1", "quote": quote},
            ],
        }]}
        recovered = process_email_multi(email, FakeModel(response))
        self.assertEqual(recovered.decision.status, "action")
        self.assertEqual(recovered.decision.actions[0].evidence[0].source_id, "body")
        response["actions"][0]["evidence"] = {"source_id": "attachment:1", "quote": quote}
        singleton = process_email_multi(email, FakeModel(response))
        self.assertEqual(singleton.decision.status, "action")

        ambiguous = EmailPackage(
            case_id="ambiguous-source", target_recipient="alex@example.com", received_at=None,
            sender="maya@example.com", recipients=("alex@example.com",), subject=quote,
            body=quote,
        )
        response["actions"][0]["evidence"] = {"source_id": "newest message", "quote": quote}
        unresolved = process_email_multi(ambiguous, FakeModel(response))
        self.assertEqual(unresolved.decision.status, "needs_review")
        self.assertIn("Unknown evidence source", unresolved.decision.review_reason)

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

    def test_v2_cli_uses_three_action_default(self):
        body = "Alex, please approve the invoice."
        model = FakeModel({
            "status": "action", "review_reason": None,
            "actions": [{"kind": "perform_task", "text": "Approve the invoice.", "deadline": None,
                         "evidence": [{"source_id": "body", "quote": body}]}],
        })
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "message.json"
            path.write_text(json.dumps({"case_id": "cli-v2", "target_recipient": "alex@example.com", "body": body}), encoding="utf-8")
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret"}), patch(
                "actionmail.interfaces.cli.APIClient", return_value=model
            ), patch("builtins.input", side_effect=["y", "n"]), redirect_stdout(output):
                code = main([str(path), "--model", "fake-model", "--schema", "v2"])
        self.assertEqual(code, 0)
        self.assertIn('"action_count": 1', output.getvalue())


if __name__ == "__main__":
    unittest.main()
