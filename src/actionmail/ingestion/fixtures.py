import json
from datetime import datetime
from pathlib import Path

from actionmail.domain.email import EmailPackage, SourceText


def load_json_email(path: Path) -> EmailPackage:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Email JSON must be an object")
    for key in ("case_id", "target_recipient", "received_at", "body"):
        if not isinstance(payload.get(key), str):
            raise ValueError(f"{key} must be a string")

    thread = payload.get("thread", [])
    if not isinstance(thread, list):
        raise ValueError("thread must be a list")
    normalized_thread = []
    for index, item in enumerate(thread, start=1):
        text = item if isinstance(item, str) else item.get("text") if isinstance(item, dict) else None
        if not isinstance(text, str):
            raise ValueError(f"thread item {index} must contain text")
        normalized_thread.append(SourceText(f"thread:{index}", text))

    received_at = datetime.fromisoformat(payload["received_at"].replace("Z", "+00:00"))
    recipients = payload.get("recipients", [])
    if not isinstance(recipients, list) or any(not isinstance(item, str) for item in recipients):
        raise ValueError("recipients must be a list of strings")
    unread = payload.get("unread_sources", [])
    if not isinstance(unread, list) or any(not isinstance(item, str) for item in unread):
        raise ValueError("unread_sources must be a list of strings")

    return EmailPackage(
        case_id=payload["case_id"],
        target_recipient=payload["target_recipient"],
        received_at=received_at,
        sender=str(payload.get("sender", "")),
        recipients=tuple(recipients),
        subject=str(payload.get("subject", "")),
        body=payload["body"],
        thread=tuple(normalized_thread),
        unread_sources=tuple(unread),
    )
