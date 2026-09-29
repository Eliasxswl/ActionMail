"""Compact, read-only index of saved evaluation runs."""

import json
from pathlib import Path


def saved_runs(root: Path) -> list[dict]:
    runs = []
    for path in root.glob("*/run.json"):
        summary_path = path.parent / "summary.json"
        if not summary_path.exists():
            continue
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        runs.append({"directory": path.parent.name, "run": run, "summary": summary})
    return sorted(runs, key=lambda item: item["run"].get("started_at_utc", ""), reverse=True)


def print_history(root: Path) -> None:
    runs = saved_runs(root)
    if not runs:
        print(f"No saved evaluation runs in {root}")
        return
    print(f"Saved evaluation runs: {len(runs)} (repeated cases across runs are not combined)")
    for item in runs:
        run, summary = item["run"], item["summary"]
        counts = summary.get("counts") or {}
        done = summary.get("completed_cases", 0)
        planned = len(run.get("case_ids") or [])
        cost = summary.get("estimated_cost_usd")
        cost_text = f"${cost:.6f}" if isinstance(cost, (float, int)) else "unavailable"
        manifest = str(run.get("manifest_sha256") or "unknown")[:8]
        print(f"{item['directory']}  {run.get('engine', '?')}/{run.get('model', '?')}  {done}/{planned} cases  gold {manifest}")
        status_denominator = counts.get("status_checked", done) if run.get("schema") == "v2" else done
        print(
            f"  status correct {counts.get('status_correct', 0)}/{status_denominator} checked; "
            f"safe external reviews {counts.get('safe_external_abstention', 0)}; "
            f"errors {counts.get('api_or_run_errors', 0)}; estimated cost {cost_text}"
        )
        print(f"  {item['directory']}/summary.json")
