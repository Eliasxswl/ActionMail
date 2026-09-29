import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from actionmail.ingestion.eml import load_eml
from actionmail.ingestion.fixtures import load_json_email
from actionmail.content.links import fetch_allowlisted_https
from actionmail.reasoning.api_client import APIClient, ModelCallError
from actionmail.workflow.pipeline import process_email, process_email_with_external
from actionmail.workflow.multi_pipeline import MAX_ACTIONS, process_email_multi, process_email_multi_with_external


OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="actionmail", description="Review one work email for a recipient action.")
    parser.add_argument("input", type=Path, help="A local .eml or normalized .json email file")
    parser.add_argument("--recipient", help="Target recipient address (required for .eml files)")
    parser.add_argument("--api-url", default=os.getenv("ACTIONMAIL_API_URL", OPENROUTER_API_URL), help="Chat-completions API URL")
    parser.add_argument("--model", default=os.getenv("ACTIONMAIL_MODEL"), help="Model identifier")
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY", help="Environment variable containing the API key")
    parser.add_argument("--external-mode", choices=("body-only", "snapshots", "allowed-live"), default="body-only")
    parser.add_argument("--allow-domain", action="append", default=[], help="Explicitly allow a domain for live HTTPS reading")
    parser.add_argument("--schema", choices=("v1", "v2"), default="v1", help="Result contract; v2 supports multiple actions")
    parser.add_argument("--max-actions", type=int, help="V2 action limit, 1-3; defaults to 3")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.input.suffix.lower() == ".json":
            email = load_json_email(args.input)
        elif args.input.suffix.lower() == ".eml":
            if not args.recipient:
                raise ValueError("--recipient is required for .eml files")
            email = load_eml(args.input, args.recipient)
        else:
            raise ValueError("Input must be a .eml or .json file")
        if args.external_mode == "allowed-live" and not args.allow_domain:
            raise ValueError("--external-mode allowed-live requires --allow-domain")
        if args.allow_domain and args.external_mode != "allowed-live":
            raise ValueError("--allow-domain requires --external-mode allowed-live")
        if args.schema == "v2" and args.max_actions is not None and not 1 <= args.max_actions <= MAX_ACTIONS:
            raise ValueError(f"--max-actions must be between 1 and {MAX_ACTIONS}")
        if args.schema == "v1" and args.max_actions is not None:
            raise ValueError("--max-actions requires --schema v2")
        action_limit = args.max_actions if args.max_actions is not None else MAX_ACTIONS

        api_key = os.getenv(args.api_key_env)
        if not args.api_url or not args.model or not api_key:
            raise ValueError(f"Set ACTIONMAIL_MODEL and {args.api_key_env}, or pass --model and --api-key-env")
        model = APIClient(args.api_url, api_key, args.model)
        print(f"Email: {email.subject or email.case_id}")
        print(f"Target recipient: {email.target_recipient}")
        if input("Send this email and selected external text to the configured model API? [y/N] ").strip().lower() != "y":
            print("Cancelled. No content was sent.")
            return 0
        if args.external_mode == "allowed-live" and any(source.kind == "link" and source.snapshot_text is None for source in email.external_sources):
            if input("Fetch live links from the explicitly allowed domain(s)? [y/N] ").strip().lower() != "y":
                print("Cancelled. No live link was fetched.")
                return 0

        fetch_live = (lambda url: fetch_allowlisted_https(url, tuple(args.allow_domain))) if args.external_mode == "allowed-live" else None
        if args.schema == "v2":
            run = process_email_multi(email, model, action_limit) if args.external_mode == "body-only" else process_email_multi_with_external(email, model, action_limit, fetch_live=fetch_live)
            output = {**asdict(run.decision), "action_count": run.decision.action_count}
            replies = run.replies
        else:
            run = process_email(email, model) if args.external_mode == "body-only" else process_email_with_external(email, model, fetch_live=fetch_live)
            output = asdict(run.decision)
            replies = run.replies or (run.reply,)
        print(json.dumps(output, indent=2, ensure_ascii=False))
        print(f"Model: {replies[-1].model}")
        if all(reply.input_tokens is not None and reply.output_tokens is not None for reply in replies):
            print(f"Tokens: {sum(reply.input_tokens for reply in replies)} input, {sum(reply.output_tokens for reply in replies)} output across {len(replies)} call(s)")
        if all(reply.latency_ms is not None for reply in replies):
            print(f"Latency: {sum(reply.latency_ms for reply in replies):.0f} ms")
        if run.read_records:
            print("Read sources: " + ", ".join(record.source_id for record in run.read_records))
        if input("Approve this result for your own review? [y/N] ").strip().lower() == "y":
            print("Approved for review. No calendar or mailbox change was made.")
        else:
            print("Result was not approved. No calendar or mailbox change was made.")
        return 0
    except (OSError, ValueError, ModelCallError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
