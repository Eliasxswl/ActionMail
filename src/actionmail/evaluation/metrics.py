from collections import Counter, defaultdict

from actionmail.evaluation.cases import EXPECTED_COUNTS, EXPECTED_EXTERNAL_COUNTS


STATUSES = ("action", "no_action", "needs_review", "error")


def summarize(rows: list[dict], total_cases: int) -> dict:
    categories = defaultdict(lambda: {"total": 0, "status_correct": 0})
    matrix = {gold: {predicted: 0 for predicted in STATUSES} for gold in ("action", "no_action", "needs_review")}
    totals = Counter()
    gold_status_counts = Counter()
    gold_deadline_kind_counts = Counter()
    input_tokens = output_tokens = 0
    estimated_cost = 0.0
    cost_count = 0
    for row in rows:
        gold = row["gold"]["status"]
        gold_status_counts[gold] += 1
        gold_deadline_kind_counts[row["gold"]["deadline_kind"]] += 1
        predicted = row["prediction"]["status"] if row["prediction"] else "error"
        matrix[gold][predicted] += 1
        category = categories[row["category"]]
        category["total"] += 1
        if predicted == gold:
            category["status_correct"] += 1
            totals["status_correct"] += 1
        if gold == "action" and predicted == "action":
            totals["tp"] += 1
        elif gold != "action" and predicted == "action":
            totals["fp"] += 1
        elif gold == "action":
            totals["fn"] += 1
        elif gold == "no_action" and predicted == "no_action":
            totals["tn"] += 1
        if gold == "no_action" and predicted == "no_action":
            totals["correct_no_action"] += 1
        if gold == "needs_review" and predicted == "needs_review":
            totals["correct_review"] += 1
        if row["category"] == "external_content" and predicted == "needs_review":
            totals["safe_external_abstention"] += 1
        if predicted == "needs_review":
            totals["abstentions"] += 1
        if row["error"]:
            totals["api_or_run_errors"] += 1
        if row["validation_errors"]:
            totals["validation_failures"] += 1
        if gold == "action" and predicted == "action" and row["gold"]["deadline_kind"] in {"none", "exact", "relative_resolvable"}:
            totals["deadline_field_checked"] += 1
            if row["gold"]["deadline"] == row["prediction"]["deadline"]:
                totals["deadline_field_match"] += 1
        usage = row.get("usage") or {}
        input_tokens += usage.get("input_tokens") or 0
        output_tokens += usage.get("output_tokens") or 0
        if row.get("estimated_cost_usd") is not None:
            estimated_cost += row["estimated_cost_usd"]
            cost_count += 1
    precision_denominator = totals["tp"] + totals["fp"]
    recall_denominator = sum(matrix["action"].values())
    return {
        "completed_cases": len(rows),
        "planned_cases": total_cases,
        "complete": len(rows) == total_cases,
        "category_counts": dict(categories),
        "planned_category_counts": EXPECTED_COUNTS,
        "planned_external_counts": EXPECTED_EXTERNAL_COUNTS,
        "status_confusion": matrix,
        "gold_status_counts": dict(gold_status_counts),
        "gold_deadline_kind_counts": dict(gold_deadline_kind_counts),
        "counts": dict(totals),
        "precision": totals["tp"] / precision_denominator if precision_denominator else None,
        "recall": totals["tp"] / recall_denominator if recall_denominator else None,
        "precision_denominator": precision_denominator,
        "recall_denominator": recall_denominator,
        "token_totals": {"input": input_tokens, "output": output_tokens},
        "estimated_cost_usd": round(estimated_cost, 8) if cost_count else None,
        "costed_cases": cost_count,
        "manual_action_and_evidence_review_complete": False,
        "metric_scope": "Status classification only; action wording and evidence support are not automatically scored.",
        "counting_rule": "FN includes action cases predicted no_action, needs_review, or error. Safe external abstentions are separate from full-content status correctness.",
    }


def summarize_v2(rows: list[dict], planned_cases: int) -> dict:
    """Count only established references; pending draft labels stay unscored."""
    counts = Counter()
    by_category = defaultdict(lambda: {"total": 0, "status_checked": 0, "status_correct": 0})
    input_tokens = output_tokens = 0
    estimated_cost = 0.0
    costed_cases = 0
    for row in rows:
        category = by_category[row["category"]]
        category["total"] += 1
        if row.get("status_correct") is not None:
            category["status_checked"] += 1
            counts["status_checked"] += 1
            if row["status_correct"]:
                category["status_correct"] += 1
                counts["status_correct"] += 1
        if row.get("action_count_match") is not None:
            counts["action_count_checked"] += 1
            if row["action_count_match"]:
                counts["action_count_match"] += 1
        if row.get("multi_action_draft"):
            counts["pending_owner_reference"] += 1
        if row.get("error"):
            counts["api_or_run_errors"] += 1
        if row.get("validation_errors"):
            counts["validation_failures"] += 1
        usage = row.get("usage") or {}
        input_tokens += usage.get("input_tokens") or 0
        output_tokens += usage.get("output_tokens") or 0
        if row.get("estimated_cost_usd") is not None:
            estimated_cost += row["estimated_cost_usd"]
            costed_cases += 1
    return {
        "schema": "v2", "completed_cases": len(rows), "planned_cases": planned_cases,
        "complete": len(rows) == planned_cases, "category_counts": dict(by_category),
        "counts": dict(counts), "token_totals": {"input": input_tokens, "output": output_tokens},
        "estimated_cost_usd": round(estimated_cost, 8) if costed_cases else None,
        "costed_cases": costed_cases,
        "metric_scope": "Established single-action references support status and action-count checks. A16/C13 draft labels are pending owner review and are not scored. Action wording and evidence meaning require human review.",
    }
