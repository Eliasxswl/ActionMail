import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from actionmail.domain.email import EmailPackage, ExternalSource, SourceText


EXPECTED_COUNTS = {"no_action": 15, "explicit_action": 15, "context_dependent": 10, "external_content": 10}
EXPECTED_EXTERNAL_COUNTS = {"attachment": 5, "link": 5}


@dataclass(frozen=True)
class EvaluationCase:
    record: dict
    email: EmailPackage
    source_hash: str | None

    @property
    def case_id(self) -> str:
        return self.record["case_id"]

    @property
    def gold(self) -> dict:
        return self.record["gold"]


def _raw_block(block: str) -> tuple[str, str, str, str, str]:
    lines = block.strip().splitlines()
    headers = {}
    body_start = 0
    for index, line in enumerate(lines):
        match = re.match(r"^(FROM|TO|CC|SUBJECT):\s*(.*)$", line, re.IGNORECASE)
        if match:
            headers[match.group(1).upper()] = match.group(2).strip()
            body_start = index + 1
        elif headers.get("SUBJECT") is not None:
            break
    return headers.get("FROM", ""), headers.get("TO", ""), headers.get("CC", ""), headers.get("SUBJECT", ""), "\n".join(lines[body_start:]).strip()


def _load_mailex(record: dict, root: Path) -> tuple[EmailPackage, str]:
    source = record["source"]
    filename = source["file"]
    if Path(filename).name != filename:
        raise ValueError(f"Unsafe source filename: {filename}")
    path = root / "raw_threads" / filename
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if source.get("sha256") != digest:
        raise ValueError(f"Source hash mismatch for {record['case_id']}: {filename}")
    blocks = [part.strip() for part in re.split(r"(?m)^-{20,}\s*$", raw.decode("utf-8", errors="replace")) if part.strip()]
    if not blocks:
        raise ValueError(f"Empty raw thread: {filename}")
    sender, to, cc, subject, body = _raw_block(blocks[0])
    target = source["target_recipient"]
    if target.lower() not in (to + "," + cc).lower():
        raise ValueError(f"Target recipient absent from newest message: {record['case_id']}")
    thread = ()
    if source["include_thread"]:
        thread = tuple(
            SourceText(f"thread:{index}", body, sender, to, cc, subject)
            for index, block in enumerate(blocks[1:], start=1)
            for sender, to, cc, subject, body in [_raw_block(block)]
        )
    to_recipients = tuple(value.strip() for value in to.split(",") if value.strip())
    cc_recipients = tuple(value.strip() for value in cc.split(",") if value.strip())
    email = EmailPackage(
        case_id=record["case_id"],
        target_recipient=target,
        received_at=None,
        sender=sender,
        recipients=tuple(dict.fromkeys((*to_recipients, *cc_recipients))),
        to_recipients=to_recipients,
        cc_recipients=cc_recipients,
        subject=subject,
        body=body,
        thread=thread,
        legacy_soft_wraps=True,
    )
    return email, digest


def _load_authored(record: dict) -> EmailPackage:
    source = record["source"]
    payload = source["email"]
    received_at = datetime.fromisoformat(payload["received_at"].replace("Z", "+00:00"))
    return EmailPackage(
        case_id=record["case_id"],
        target_recipient=payload["target_recipient"],
        received_at=received_at,
        sender=payload["sender"],
        recipients=tuple(payload["recipients"]),
        to_recipients=tuple(payload["recipients"]),
        subject=payload["subject"],
        body=payload["body"],
        unread_sources=tuple(item["name"] for item in source["external_sources"]),
        external_sources=tuple(
            ExternalSource(item["source_id"], item["kind"], item["name"], snapshot_text=item["text"])
            for item in source["external_sources"]
        ),
    )


def load_cases(manifest: Path, mailex_root: Path) -> list[EvaluationCase]:
    records = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    counts = Counter(record["category"] for record in records)
    if counts != EXPECTED_COUNTS:
        raise ValueError(f"Expected category counts {EXPECTED_COUNTS}; got {dict(counts)}")
    external_counts = Counter(record.get("external_kind") for record in records if record["category"] == "external_content")
    if external_counts != EXPECTED_EXTERNAL_COUNTS:
        raise ValueError(f"Expected external counts {EXPECTED_EXTERNAL_COUNTS}; got {dict(external_counts)}")
    ids = [record["case_id"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate case_id in manifest")

    cases = []
    for record in records:
        source = record["source"]
        if source["kind"] == "mailex_raw":
            email, digest = _load_mailex(record, mailex_root)
        elif source["kind"] == "authored":
            email, digest = _load_authored(record), None
        else:
            raise ValueError(f"Unknown case source: {record['case_id']}")
        _validate_gold(record, email)
        cases.append(EvaluationCase(record, email, digest))
    return cases


def _validate_gold(record: dict, email: EmailPackage) -> None:
    gold = record["gold"]
    if gold["status"] not in {"action", "no_action", "needs_review"}:
        raise ValueError(f"Invalid gold status: {record['case_id']}")
    if gold["deadline_kind"] not in {"none", "exact", "relative_resolvable", "relative_unresolvable", "vague"}:
        raise ValueError(f"Invalid deadline kind: {record['case_id']}")
    if (gold["deadline"] is not None) != (gold["deadline_kind"] in {"exact", "relative_resolvable"}):
        raise ValueError(f"Deadline and deadline_kind disagree: {record['case_id']}")
    if gold["status"] == "action" and (not gold["action"] or not gold["evidence"]):
        raise ValueError(f"Action needs action text and evidence: {record['case_id']}")
    if gold["status"] != "action" and (gold["action"] is not None or gold["deadline"] is not None):
        raise ValueError(f"Non-action case has action or deadline: {record['case_id']}")
    sources = email.sources()
    for item in record["source"].get("external_sources", []):
        if item["source_id"] in sources:
            raise ValueError(f"Duplicate source ID: {record['case_id']}")
        sources[item["source_id"]] = item["text"]
    for item in gold["evidence"]:
        if not item["quote"].strip() or item["quote"] not in sources.get(item["source_id"], ""):
            raise ValueError(f"Gold evidence quote missing from source: {record['case_id']} {item['source_id']}")
