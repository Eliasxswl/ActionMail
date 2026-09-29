import json
from datetime import datetime
from pathlib import Path

from actionmail.domain.email import EmailPackage, ExternalSource, SourceText


def load_json_email(path: Path) -> EmailPackage:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Email JSON must be an object")
    for key in ("case_id", "target_recipient", "body"):
        if not isinstance(payload.get(key), str):
            raise ValueError(f"{key} must be a string")
    if payload.get("received_at") is not None and not isinstance(payload["received_at"], str):
        raise ValueError("received_at must be a string or null")

    thread = payload.get("thread", [])
    if not isinstance(thread, list):
        raise ValueError("thread must be a list")
    normalized_thread = []
    for index, item in enumerate(thread, start=1):
        text = item if isinstance(item, str) else item.get("text") if isinstance(item, dict) else None
        if not isinstance(text, str):
            raise ValueError(f"thread item {index} must contain text")
        headers = item if isinstance(item, dict) else {}
        normalized_thread.append(SourceText(
            f"thread:{index}", text,
            str(headers.get("sender", "")), str(headers.get("recipients", "")),
            str(headers.get("cc", "")), str(headers.get("subject", "")),
        ))

    received_at = datetime.fromisoformat(payload["received_at"].replace("Z", "+00:00")) if payload.get("received_at") else None
    recipients = payload.get("recipients", [])
    if not isinstance(recipients, list) or any(not isinstance(item, str) for item in recipients):
        raise ValueError("recipients must be a list of strings")
    cc_recipients = payload.get("cc_recipients", [])
    if not isinstance(cc_recipients, list) or any(not isinstance(item, str) for item in cc_recipients):
        raise ValueError("cc_recipients must be a list of strings")
    unread = payload.get("unread_sources", [])
    if not isinstance(unread, list) or any(not isinstance(item, str) for item in unread):
        raise ValueError("unread_sources must be a list of strings")
    external = payload.get("external_sources", [])
    if not isinstance(external, list) or any(
        not isinstance(item, dict) or
        not all(isinstance(item.get(key), str) for key in ("source_id", "kind", "name")) or
        ("text" in item and not isinstance(item["text"], str)) or
        (item.get("kind") not in {"attachment", "link"})
        for item in external
    ):
        raise ValueError("external_sources need source_id, kind, name, and optional text strings")
    external_sources = tuple(
        ExternalSource(item["source_id"], item["kind"], item["name"], snapshot_text=item.get("text"))
        for item in external
    )

    return EmailPackage(
        case_id=payload["case_id"],
        target_recipient=payload["target_recipient"],
        received_at=received_at,
        sender=str(payload.get("sender", "")),
        recipients=tuple(dict.fromkeys((*recipients, *cc_recipients))),
        to_recipients=tuple(recipients),
        cc_recipients=tuple(cc_recipients),
        subject=str(payload.get("subject", "")),
        body=payload["body"],
        thread=tuple(normalized_thread),
        unread_sources=tuple(dict.fromkeys((*unread, *(item.name for item in external_sources)))),
        external_sources=external_sources,
    )
