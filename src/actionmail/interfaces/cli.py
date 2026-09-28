import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from actionmail.ingestion.eml import load_eml
from actionmail.ingestion.fixtures import load_json_email
from actionmail.reasoning.api_client import APIClient, ModelCallError
from actionmail.workflow.pipeline import process_email


OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="actionmail", description="Review one work email for a recipient action.")
    parser.add_argument("input", type=Path, help="A local .eml or normalized .json email file")
    parser.add_argument("--recipient", help="Target recipient address (required for .eml files)")
    parser.add_argument("--api-url", default=os.getenv("ACTIONMAIL_API_URL", OPENROUTER_API_URL), help="Chat-completions API URL")
    parser.add_argument("--model", default=os.getenv("ACTIONMAIL_MODEL"), help="Model identifier")
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY", help="Environment variable containing the API key")
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

        api_key = os.getenv(args.api_key_env)
        if not args.api_url or not args.model or not api_key:
            raise ValueError(f"Set ACTIONMAIL_MODEL and {args.api_key_env}, or pass --model and --api-key-env")
        model = APIClient(args.api_url, api_key, args.model)
        print(f"Email: {email.subject or email.case_id}")
        print(f"Target recipient: {email.target_recipient}")
        if input("Send this email's content to the configured model API? [y/N] ").strip().lower() != "y":
            print("Cancelled. No content was sent.")
            return 0

        run = process_email(email, model)
        print(json.dumps(asdict(run.decision), indent=2, ensure_ascii=False))
        print(f"Model: {run.reply.model}")
        if run.reply.input_tokens is not None and run.reply.output_tokens is not None:
            print(f"Tokens: {run.reply.input_tokens} input, {run.reply.output_tokens} output")
        if run.reply.latency_ms is not None:
            print(f"Latency: {run.reply.latency_ms:.0f} ms")
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
