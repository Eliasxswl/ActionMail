"""Short command router for ActionMail's analysis, evaluation and review tools.

The established extraction and evaluation CLIs remain the implementation of
those workflows. This module supplies discoverable shortcuts without creating
a second analysis or scoring path.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from actionmail.evaluation.cli import DEFAULT_MAILEX_ROOT, PROJECT_ROOT
from actionmail.evaluation.history import saved_runs


COMMANDS = {"start", "demo", "analyze", "eval", "results", "check", "doctor", "ui", "review"}
EVALUATIONS = PROJECT_ROOT / "results" / "evaluation"
REGISTRY = PROJECT_ROOT / "evaluation" / "active_suite.json"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="actionmail",
        description="Analyze mail, run or inspect experiments, and start optional review tools.",
    )
    parser.add_argument("command", nargs="?", help="start, demo, analyze, eval, results, check, doctor, ui, or review")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Options for the selected command")
    return parser


def _print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def _has_option(arguments: list[str], option: str) -> bool:
    """Recognize both argparse spellings: --option VALUE and --option=VALUE."""
    return any(item == option or item.startswith(option + "=") for item in arguments)


def _active_registry_check() -> dict:
    """Verify the committed active-suite references without requiring corpus data."""
    try:
        suite = json.loads(REGISTRY.read_text(encoding="utf-8"))
        identifiers: set[str] = set()
        manifests = []
        required_sources: set[str] = set()
        for component in suite["components"]:
            relative = Path(component["manifest"])
            path = (REGISTRY.parent / relative).resolve()
            if not path.is_relative_to(REGISTRY.parent.resolve()):
                raise ValueError("Manifest path escapes evaluation directory")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != component["sha256"]:
                raise ValueError(f"Active manifest hash mismatch: {relative}")
            with path.open(encoding="utf-8-sig") as stream:
                rows = [json.loads(line) for line in stream if line.strip()]
            if len(rows) != component["cases"]:
                raise ValueError(f"Active manifest case count mismatch: {relative}")
            component_ids = [row["case_id"] for row in rows]
            if identifiers.intersection(component_ids) or len(component_ids) != len(set(component_ids)):
                raise ValueError(f"Duplicate case ID in active manifest: {relative}")
            identifiers.update(component_ids)
            for row in rows:
                source = row.get("source", {})
                if source.get("kind") == "mailex_raw":
                    required_sources.add(str(Path("raw_threads") / source["file"]))
                elif source.get("kind") == "enron_export":
                    required_sources.add(source["file"])
                    required_sources.update(item["file"] for item in source.get("attachments", []))
            manifests.append({"path": str(relative), "cases": len(rows), "sha256": digest})
        if len(identifiers) != suite["total_cases"]:
            raise ValueError("Active-suite total does not match its components")
        if suite.get("reference_overrides"):
            ref = suite["reference_overrides"]
            path = (REGISTRY.parent / ref["file"]).resolve()
            if not path.is_relative_to(REGISTRY.parent.resolve()):
                raise ValueError("Reference override path escapes evaluation directory")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != ref["sha256"]:
                raise ValueError("Active reference override hash mismatch")
        missing_sources = []
        for relative in sorted(required_sources):
            path = (DEFAULT_MAILEX_ROOT / relative).resolve()
            if not path.is_relative_to(DEFAULT_MAILEX_ROOT.resolve()):
                raise ValueError("Evaluation source path escapes corpus directory")
            if not path.is_file():
                missing_sources.append(relative)
        return {"status": "ok", "active_cases": len(identifiers), "manifests": manifests,
                "required_raw_sources": len(required_sources), "missing_raw_sources": missing_sources,
                "external_corpus_available": not missing_sources}
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return {"status": "error", "error": str(exc)}


def _doctor() -> dict:
    try:
        distribution = importlib.metadata.version("actionmail")
    except importlib.metadata.PackageNotFoundError:
        distribution = "source checkout (not installed)"
    python_ok = sys.version_info >= (3, 10)
    optional = {}
    for name in ("pypdf", "google.auth", "uipath"):
        try:
            optional[name] = importlib.util.find_spec(name) is not None
        except (ModuleNotFoundError, ValueError):
            optional[name] = False
    active = _active_registry_check()
    samples = (PROJECT_ROOT / "results" / "evaluation" / "v2-regression-repair-20261001").is_dir()
    corpus_ready = active.get("external_corpus_available", False)
    return {
        "project": distribution,
        "python": {"version": sys.version.split()[0], "supported": python_ok},
        "optional_packages": optional,
        "model": {"configured": bool(os.getenv("ACTIONMAIL_MODEL") and os.getenv("OPENROUTER_API_KEY")),
                  "model_id": os.getenv("ACTIONMAIL_MODEL") or None},
        "evaluation": {"registry": active, "original_corpus_available": corpus_ready,
                       "saved_v2_run_available": samples,
                       "new_v2_run_ready": bool(os.getenv("ACTIONMAIL_MODEL") and os.getenv("OPENROUTER_API_KEY") and corpus_ready)},
        "uip_cli_available": shutil.which("uip") is not None,
        "status": "ok" if python_ok and active["status"] == "ok" else "attention",
    }


def _check() -> int:
    state = _doctor()
    _print_json(state)
    return 0 if state["status"] == "ok" else 1


def _doctor_command() -> int:
    _print_json(_doctor())
    return 0


def _run_demo(arguments: list[str]) -> int:
    from actionmail.interfaces.workflow_cli import main as workflow_main

    if not _has_option(arguments, "--output-dir"):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        arguments = [*arguments, "--output-dir", str(PROJECT_ROOT / "results" / "private" / f"demo-{stamp}-{uuid4().hex[:6]}")]
    return workflow_main(["demo", *arguments])


def _evaluation(arguments: list[str]) -> int:
    from actionmail.evaluation.cli import main as evaluation_main

    if any(item in arguments for item in ("--help", "-h")) and "--saved" not in arguments:
        print("Shortcuts: --estimate previews cost; --validate checks data offline; --saved inspects saved results.")
        print("Default benchmark: v2-60. Remaining options are forwarded to actionmail-eval.\n")
    if "--saved" in arguments:
        return _results([item for item in arguments if item != "--saved"])
    estimate_only = "--estimate" in arguments
    validate_only = "--validate" in arguments
    arguments = [item for item in arguments if item not in {"--estimate", "--validate"}]
    if estimate_only and validate_only:
        print("Choose either --estimate or --validate.", file=sys.stderr)
        return 2
    options = list(arguments)
    default_benchmark = not _has_option(options, "--benchmark")
    if default_benchmark:
        options = ["--benchmark", "v2-60", *options]
    if estimate_only:
        options.append("--preflight")
    elif validate_only and "--validate" not in options:
        options.append("--validate")
    elif default_benchmark and not any(item in options for item in ("--help", "-h")):
        print("Default evaluation: active v2-60 suite; live inference is estimated and requires confirmation.")
    return evaluation_main(options)


def _results(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="actionmail results", description="Inspect saved evaluation results without inference.")
    parser.add_argument("--all", action="store_true", help="List all saved runs, including incomplete runs; default: latest complete run")
    parser.add_argument("--run", help="Run directory name shown by results")
    parser.add_argument("--case", help="Show one saved case row")
    parser.add_argument("--trace", action="store_true", help="Include prompt replies and source-read details for --case")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output")
    args = parser.parse_args(arguments)
    if args.trace and not args.case:
        parser.error("--trace requires --case")
    runs = saved_runs(EVALUATIONS)
    if not args.all and not args.run:
        runs = [item for item in runs if item["summary"].get("complete") is True]
        runs = runs[:1]
    if args.run:
        runs = [item for item in runs if item["directory"] == args.run]
        if not runs:
            print(f"Saved run {args.run} was not found.", file=sys.stderr)
            return 1
    if not runs and args.case:
        print("No matching saved evaluation is available.", file=sys.stderr)
        return 1
    if args.case and len(runs) != 1:
        print("Select one run with --run before requesting a case.", file=sys.stderr)
        return 2
    if args.case:
        run_dir = EVALUATIONS / runs[0]["directory"]
        try:
            rows = [json.loads(line) for line in (run_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        except (OSError, ValueError) as exc:
            print(f"Cannot read saved case rows: {exc}", file=sys.stderr)
            return 1
        row = next((item for item in rows if item.get("case_id") == args.case), None)
        if row is None:
            print(f"Case {args.case} is absent from {runs[0]['directory']}.", file=sys.stderr)
            return 1
        if not args.trace:
            row = {key: value for key, value in row.items()
                   if key not in {"replies", "raw_model_response", "raw_model_responses", "source_plan", "coverage", "read_failures", "evidence_locations", "repair_attempts"}}
        _print_json({"run": runs[0]["directory"], "case": row})
        return 0
    if args.json:
        _print_json(runs)
        return 0
    if not runs:
        print(f"No matching saved evaluation runs in {EVALUATIONS}")
        return 0
    print(f"Saved runs: {len(runs)}" + (" (including incomplete)" if args.all else ""))
    for item in runs:
        run, summary = item["run"], item["summary"]
        counts = summary.get("counts") or {}
        cost = summary.get("estimated_cost_usd")
        cost_text = f"${cost:.6f}" if isinstance(cost, (float, int)) else "unavailable"
        denominator = counts.get("status_checked", summary.get("completed_cases", 0)) if run.get("schema") == "v2" else summary.get("completed_cases", 0)
        checked = counts.get("status_correct", 0)
        print(f"{item['directory']}  {run.get('engine', '?')}/{run.get('model', '?')}  "
              f"{summary.get('completed_cases', 0)}/{summary.get('planned_cases', '?')} cases  "
              f"status {checked}/{denominator} checked  estimated cost {cost_text}")
    return 0


def _interactive() -> int:
    choices = {"1": ("Offline scripted demo", _run_demo, []),
               "2": ("Run active v2 evaluation", _evaluation, []),
               "3": ("Show completed evaluation results", _results, []),
               "4": ("Launch optional offline product UI", main, ["ui"]),
               "0": ("Exit", None, [])}
    while True:
        print("\nActionMail")
        for key, (label, _, _) in choices.items():
            print(f"  {key}. {label}")
        try:
            choice = input("Choose an option: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if choice == "0":
            return 0
        selected = choices.get(choice)
        if selected is None:
            print("Choose one of the displayed numbers.")
            continue
        _, operation, arguments = selected
        try:
            operation(arguments)
        except KeyboardInterrupt:
            print("\nCancelled.")


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        if sys.stdin.isatty():
            return _interactive()
        _parser().print_help()
        return 0
    command = arguments[0]
    tail = arguments[1:]
    if command in {"-h", "--help"}:
        _parser().print_help()
        return 0
    if command not in COMMANDS:
        # Preserve the established `actionmail INPUT [options]` interface.
        from actionmail.interfaces.cli import main as single_email_main
        return single_email_main(arguments)
    if command == "start":
        argparse.ArgumentParser(prog="actionmail start", description="Open the terminal menu.").parse_args(tail)
        return _interactive() if sys.stdin.isatty() else (_parser().print_help() or 0)
    if command == "demo":
        return _run_demo(tail)
    if command == "analyze":
        from actionmail.interfaces.cli import main as single_email_main
        return single_email_main(tail)
    if command == "eval":
        return _evaluation(tail)
    if command == "results":
        return _results(tail)
    if command == "check":
        argparse.ArgumentParser(prog="actionmail check", description="Check local runtime and active manifest references offline.").parse_args(tail)
        return _check()
    if command == "doctor":
        argparse.ArgumentParser(prog="actionmail doctor", description="Show local runtime, corpus and provider readiness.").parse_args(tail)
        return _doctor_command()
    if command == "ui":
        from actionmail.interfaces.app_server import main as app_main
        return app_main(tail)
    if command == "review":
        from actionmail.interfaces.review_server import main as review_main
        if any(item in tail for item in ("--help", "-h")):
            return review_main(tail)
        # Ignore option values when detecting an explicit positional run path.
        positional = []
        skip_value = False
        for item in tail:
            if skip_value:
                skip_value = False
            elif item in {"--manifest", "--mailex-root", "--port"}:
                skip_value = True
            elif not item.startswith("-"):
                positional.append(item)
        if not positional:
            runs = saved_runs(EVALUATIONS)
            latest = next((item for item in runs if item["summary"].get("complete") is True), None)
            if latest is None:
                print("No complete saved evaluation is available to review.", file=sys.stderr)
                return 1
            tail = [str(EVALUATIONS / latest["directory"]), *tail]
        return review_main(tail)
    _parser().print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
