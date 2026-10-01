# CLI delivery and experiment guide

Updated 2 October 2026. The owner selected CLI-first delivery. A teacher should be able to run checks, inspect results and follow experiments without UiPath, Google login or a browser. The review GUI remains an optional annotation tool; TUI and UiPath integration are optional future choices, not submission prerequisites.

There are three distinct paths: offline engineering verification, inspection of saved real-model experiments, and a new explicitly authorized model run. The scripted demo is not AI evaluation. A new model run requires model configuration and may incur cost; installing dependencies initially requires a package source.

## Quick start without accounts or keys

From the repository root with Python 3.10 or newer (PowerShell):

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e .
.venv/Scripts/python.exe -m actionmail.interfaces.workflow_cli demo --output-dir results/private/teacher-demo
.venv/Scripts/python.exe -m unittest discover -s tests -q
```

On macOS/Linux use `.venv/bin/python` instead. After installation, `actionmail-workflow` is also available as a console command inside the activated environment. The module form works without activation. The demo and tests use included authored inputs; they do not need the external MailEx corpus.

The output directory must be new. Choose another name to repeat the experiment; prior results are never overwritten. A failed operation exits with code 1 and a JSON error on stderr; success exits with code 0 and JSON on stdout. Argparse usage errors exit with code 2.

The demo runs synthetic Gmail data through the actual mail adapter and existing extraction core, using scripted model replies. It explicitly accepts the supplied task, previews and confirms an all-day deadline, exports ICS, then simulates writing twice. The summary records one simulated event and one simulated POST. These demonstrations of review/calendar behavior are engineering checks, not measured AI accuracy or real provider connectivity.

Artifacts under the selected output directory:

| File | Inspectable information |
| --- | --- |
| `summary.json` | Three scenario outcomes, accepted task count, simulated write counts and explicit verification boundary |
| `records.json` | Normalized source text, target, received time, reading plan, source reads, model replies, validation/repair details, proposals and operation history; attachment bytes omitted |
| `deadline.ics` | Standards-compliant local calendar export |
| `workflow.sqlite3` | Persistent private application records for subsequent CLI inspection |
| `workflow.demo-events.json` | Persisted synthetic provider event, not a real Google event |

Private artifacts stay in ignored `results/private/`; do not publish private imported emails or their traces. Generated IDs/timestamps differ between runs; synthetic source inputs and intended outcomes are fixed.

## Inspect the process and operate step by step

All workflow commands use synthetic providers and a scripted model. Imported messages that have no supplied script remain for review. This command does not enable live Google or model calls. Use a dedicated offline store, separate from any live UI store, and run one application process per store.

```powershell
# Inspect the completed demo without recomputing:
.venv/Scripts/python.exe -m actionmail.interfaces.workflow_cli --store results/private/teacher-demo/workflow.sqlite3 list
.venv/Scripts/python.exe -m actionmail.interfaces.workflow_cli --store results/private/teacher-demo/workflow.sqlite3 tasks
# Replace RECORD_ID with an ID returned by list:
.venv/Scripts/python.exe -m actionmail.interfaces.workflow_cli --store results/private/teacher-demo/workflow.sqlite3 show RECORD_ID
```

For a fresh manual session, global `--store` must precede the subcommand. The following captures returned IDs rather than requiring database access:

```powershell
$cliStore = 'results/private/manual-cli.sqlite3'
.venv/Scripts/python.exe -m actionmail.interfaces.workflow_cli --store $cliStore mailbox
$imported = .venv/Scripts/python.exe -m actionmail.interfaces.workflow_cli --store $cliStore fetch m1 | ConvertFrom-Json
$recordId = $imported.result.id
$analysis = .venv/Scripts/python.exe -m actionmail.interfaces.workflow_cli --store $cliStore analyze $recordId | ConvertFrom-Json
$proposalId = $analysis.result.proposals[0].id
.venv/Scripts/python.exe -m actionmail.interfaces.workflow_cli --store $cliStore review $recordId $proposalId --state accepted
.venv/Scripts/python.exe -m actionmail.interfaces.workflow_cli --store $cliStore show $recordId
```

`show` exposes the saved source/analysis/history; `analyze` reuses unchanged saved analysis. `review --text 'Edited task' --deadline 2026-10-03` saves edits; `--deadline null` clears the date. `review --state rejected` retains the rejection. `import INPUT.json` and `import INPUT.eml --recipient you@example.com` provide local intake.

Calendar operations remain explicit: `draft RECORD_ID PROPOSAL_ID --fields fields.json`, `confirm RECORD_ID PROPOSAL_ID --revision REVISION`, `export RECORD_ID PROPOSAL_ID --output NEW_FILE.ics`, and optionally `simulate-write RECORD_ID PROPOSAL_ID`. `draft` returns the exact revision to confirm; new fields invalidate confirmation. Export requires confirmed fields and refuses existing output files. A rejected task cannot be exported or written. Use this field shape, selecting the actual intended dates (all-day end is exclusive):

```json
{
  "title": "Reviewed deadline",
  "description": "Approved context",
  "start": "2026-10-03",
  "end": "2026-10-04",
  "timezone": "Asia/Singapore",
  "calendar_id": "demo@example.com",
  "all_day": true
}
```

## Inspect saved AI experiments without new inference

```powershell
.venv/Scripts/python.exe -m actionmail.evaluation.cli --history
Get-Content results/evaluation/v2-regression-repair-20261001/summary.json
Get-Content results/evaluation/v2-regression-repair-20261001/inspection.json
$savedCases = Get-Content results/evaluation/v2-regression-repair-20261001/cases.jsonl | ForEach-Object { $_ | ConvertFrom-Json }
$savedCases | Where-Object case_id -eq 'S02' | ConvertTo-Json -Depth 30
```

The saved rows contain predictions, replies, source planning, validation/repair traces, usage and cost data. `run.json` and `manifest_snapshot.json` identify configuration and inputs. Reading this saved evidence does not require an API key or the separate original corpus. See [evaluation.md](evaluation.md) for reference amendments, exact denominators and the development-set limitation. The current accepted status/count match of 60/60 is not a blind evaluation or universal semantic accuracy claim.

Revalidating the full 60-case source manifest additionally requires original inputs in sibling `../data`, as described in [README](../README.md):

```powershell
.venv/Scripts/python.exe -m actionmail.evaluation.cli --benchmark v2-60 --validate
.venv/Scripts/python.exe tools/check_repository.py
```

Do not describe those two commands as reproducible from a source-only clone until the separate public inputs have been acquired. The included offline demo/tests and saved-result inspection work independently.

## New real-model experiments (optional, separately authorized)

For a single supplied example, set the model and API key locally and use the existing extraction CLI. Its transmission prompt is explicit:

```powershell
$env:ACTIONMAIL_MODEL = 'openai/gpt-6-luna'
# Set OPENROUTER_API_KEY locally; never write it into source or a report.
.venv/Scripts/python.exe -m actionmail.interfaces.cli examples/sample_email.json --schema v2 --external-mode snapshots
```

For batch reproduction, the existing evaluation CLI supports preflight, selected cases, fresh result directories and explicit confirmation. Consult `python -m actionmail.evaluation.cli --help` and [evaluation.md](evaluation.md). Do not run a new paid batch or transmit private email merely to demonstrate the offline workflow. No new paid inference or real-account check was performed for this CLI change.
