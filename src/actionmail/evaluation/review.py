import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from actionmail.domain.email import addresses_in_header
from actionmail.evaluation.cases import EvaluationCase, load_cases


REVIEW_VALUES = {"correct", "incorrect", "uncertain", ""}
REVIEW_FIELDS = ("action_meaning", "evidence_support", "gold_label")


@dataclass
class ReviewDataset:
    run_dir: Path
    run: dict
    rows: dict[str, dict]
    cases: dict[str, EvaluationCase]
    manifest_name: str
    revised_gold: dict[str, dict]
    prior_gold_reviews: dict[str, dict]

    @classmethod
    def open(cls, run_dir: Path, manifest: Path, mailex_root: Path) -> "ReviewDataset":
        run_dir = run_dir.resolve()
        run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        manifest_hash = hashlib.sha256(manifest.read_bytes()).hexdigest()
        if manifest_hash != run["manifest_sha256"] and manifest.name == "cases.jsonl":
            snapshots = [
                path for path in manifest.parent.glob("cases_v*.jsonl")
                if hashlib.sha256(path.read_bytes()).hexdigest() == run["manifest_sha256"]
            ]
            if len(snapshots) == 1:
                manifest = snapshots[0]
                manifest_hash = run["manifest_sha256"]
        if manifest_hash != run["manifest_sha256"]:
            raise ValueError("The manifest does not match this evaluation run")
        cases = {case.case_id: case for case in load_cases(manifest, mailex_root)}
        rows_list = [json.loads(line) for line in (run_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        rows = {row["case_id"]: row for row in rows_list}
        if len(rows) != len(rows_list) or set(rows) - set(run["case_ids"]) or set(rows) - set(cases):
            raise ValueError("Evaluation rows do not match the run and manifest")
        revised_gold = {}
        current_manifest = manifest.parent / "cases.jsonl"
        if manifest != current_manifest and current_manifest.exists():
            for case in load_cases(current_manifest, mailex_root):
                if case.case_id in rows and case.gold != rows[case.case_id]["gold"]:
                    revised_gold[case.case_id] = case.gold
        prior_gold_reviews = {}
        for prior_run_path in run_dir.parent.glob("*/run.json"):
            if prior_run_path.parent == run_dir:
                continue
            try:
                prior_run = json.loads(prior_run_path.read_text(encoding="utf-8"))
                if prior_run.get("engine") != "rules" or prior_run.get("manifest_sha256") != run["manifest_sha256"]:
                    continue
                prior_review = json.loads((prior_run_path.parent / "adjudication.json").read_text(encoding="utf-8"))
                if prior_review.get("run_id") != prior_run["run_id"] or prior_review.get("manifest_sha256") != run["manifest_sha256"]:
                    continue
                prior_gold_reviews.update({
                    case_id: {"gold_label": value["gold_label"], "note": value.get("note", "")}
                    for case_id, value in prior_review["reviews"].items()
                    if case_id in rows and value.get("gold_label")
                })
            except (OSError, ValueError, KeyError):
                continue
        return cls(run_dir, run, rows, cases, manifest.name, revised_gold, prior_gold_reviews)

    @property
    def review_path(self) -> Path:
        return self.run_dir / "adjudication.json"

    def reviews(self) -> dict:
        if not self.review_path.exists():
            return {}
        payload = json.loads(self.review_path.read_text(encoding="utf-8"))
        if payload.get("run_id") != self.run["run_id"] or payload.get("manifest_sha256") != self.run["manifest_sha256"]:
            raise ValueError("Adjudication file belongs to a different evaluation run")
        return payload["reviews"]

    def overview(self) -> dict:
        reviews = self.reviews()
        items = []
        for case_id in self.run["case_ids"]:
            row = self.rows.get(case_id)
            if row is None:
                continue
            case = self.cases[case_id]
            items.append({
                "case_id": case_id,
                "subject": case.email.subject,
                "category": row["category"],
                "gold_status": row["gold"]["status"],
                "predicted_status": row["prediction"]["status"] if row["prediction"] else "error",
                "status_correct": row["status_correct"],
                "reviewed": case_id in reviews,
            })
        return {"run_id": self.run["run_id"], "model": self.run["model"], "manifest": self.manifest_name, "cases": items}

    def detail(self, case_id: str) -> dict:
        row = self.rows[case_id]
        case = self.cases[case_id]
        email = case.email
        external = case.record["source"].get("external_sources", [])
        return {
            "case_id": case_id,
            "category": row["category"],
            "email": {
                "target_recipient": email.target_recipient,
                "received_at": email.received_at.isoformat() if email.received_at else None,
                "sender": email.sender,
                "recipients": email.recipients,
                "to_recipients": email.to_recipients or email.recipients,
                "cc_recipients": email.cc_recipients,
                "subject": email.subject,
                "body": email.body,
                "thread": [
                    {
                        "source_id": part.source_id, "text": part.text,
                        "sender": part.sender, "sender_addresses": addresses_in_header(part.sender),
                        "recipients": part.recipients, "recipient_addresses": addresses_in_header(part.recipients),
                        "cc": part.cc, "cc_addresses": addresses_in_header(part.cc),
                        "subject": part.subject,
                    }
                    for part in email.thread
                ],
            },
            "external_sources": [
                {"source_id": item["source_id"], "name": item["name"], "text": item["text"],
                 "read_by_model": any(record["source_id"] == item["source_id"] for record in row.get("read_sources", []))}
                for item in external
            ],
            "gold": row["gold"],
            "annotation_note": case.record.get("annotation_note"),
            "revised_gold": self.revised_gold.get(case_id),
            "manifest_name": self.manifest_name,
            "prediction": row["prediction"],
            "multi_action_draft": row.get("multi_action_draft"),
            "action_count_match": row.get("action_count_match"),
            "raw_model_response": row["raw_model_response"],
            "validation_errors": row["validation_errors"],
            "error": row["error"],
            "status_correct": row["status_correct"],
            "review": self.reviews().get(case_id),
            "prior_gold_review": self.prior_gold_reviews.get(case_id),
        }

    def save_review(self, case_id: str, review: dict) -> dict:
        if case_id not in self.rows:
            raise KeyError(case_id)
        if not {*REVIEW_FIELDS, "note"} <= set(review) or set(review) - {*REVIEW_FIELDS, "note", "action_checks"}:
            raise ValueError("Review must contain action_meaning, evidence_support, gold_label, and note")
        if any(not isinstance(review[field], str) or review[field] not in REVIEW_VALUES for field in REVIEW_FIELDS):
            raise ValueError("Review choice is invalid")
        note = review["note"]
        if not isinstance(note, str) or len(note) > 2000:
            raise ValueError("Review note must be text of at most 2000 characters")
        checks = review.get("action_checks", [])
        if not isinstance(checks, list) or len(checks) > 3:
            raise ValueError("Action checks must contain at most three items")
        predicted_actions = (self.rows[case_id].get("prediction") or {}).get("actions") or []
        if checks and len(checks) != len(predicted_actions):
            raise ValueError("Action checks must match the predicted action count")
        if any(not isinstance(item, dict) or set(item) != {"action_meaning", "evidence_support"} or
               any(not isinstance(item[field], str) or item[field] not in REVIEW_VALUES for field in ("action_meaning", "evidence_support")) for item in checks):
            raise ValueError("Action check choice is invalid")
        if not note.strip() and not any(review[field] for field in REVIEW_FIELDS) and not any(any(item.values()) for item in checks):
            raise ValueError("Choose at least one assessment or write a note")
        updated = {field: review[field] for field in REVIEW_FIELDS}
        updated["note"] = note.strip()
        if checks:
            updated["action_checks"] = checks
        updated["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        reviews = self.reviews()
        reviews[case_id] = updated
        payload = {
            "run_id": self.run["run_id"],
            "manifest_sha256": self.run["manifest_sha256"],
            "reviews": reviews,
        }
        temporary = self.review_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary.replace(self.review_path)
        return updated
