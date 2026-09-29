import json
from pathlib import Path

from actionmail.evaluation.cases import EvaluationCase


def load_multi_drafts(path: Path, cases: list[EvaluationCase]) -> dict[str, dict]:
    by_id = {case.case_id: case for case in cases}
    drafts = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        case_id = row.get("case_id")
        if case_id not in by_id or case_id in drafts:
            raise ValueError(f"Unknown or duplicate multi-action draft case: {case_id}")
        if row.get("review_state") != "pending_owner":
            raise ValueError(f"Multi-action draft must remain pending owner review: {case_id}")
        if row.get("proposed_status") not in {"action", "needs_review"}:
            raise ValueError(f"Invalid proposed multi-action status: {case_id}")
        actions = row.get("candidate_actions")
        if not isinstance(actions, list) or not 1 < len(actions) <= 3:
            raise ValueError(f"Multi-action draft needs two or three candidate actions: {case_id}")
        sources = by_id[case_id].email.sources()
        for action in actions:
            if action.get("kind") not in {"answer_question", "perform_task", "follow_up"} or not action.get("text"):
                raise ValueError(f"Invalid candidate action: {case_id}")
            if action.get("deadline") is not None:
                raise ValueError(f"Draft deadlines need separate validation: {case_id}")
            evidence = action.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                raise ValueError(f"Candidate action needs evidence: {case_id}")
            if any(not item.get("quote") or item["quote"] not in sources.get(item.get("source_id"), "") for item in evidence):
                raise ValueError(f"Candidate evidence is absent from the source: {case_id}")
        drafts[case_id] = row
    if set(drafts) != {"A16", "C13"}:
        raise ValueError("Multi-action draft must contain A16 and C13")
    return drafts
