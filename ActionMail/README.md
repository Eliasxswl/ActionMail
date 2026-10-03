# ActionMail: command guide

Start with [the submission overview](../README.md), [architecture](docs/architecture.md), and [data and evaluation](docs/evaluation.md). Final measured AI results are in [the experiment report](../experiments/REPORT.md).

## Install and choose a working directory

Use Python 3.10 or newer. All examples on this page use **Windows PowerShell inside `ActionMail/`**, with an activated environment. Clone the whole repository: the sibling `data/` and `experiments/` directories are required.

```powershell
cd ActionMail
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e .
.venv/Scripts/Activate.ps1
actionmail --help
```

Installation may download dependencies; offline operations need no account or model key. If you installed using the root README, activate that environment instead of creating another. If PowerShell blocks activation, use `.venv/Scripts/actionmail.exe` and `.venv/Scripts/python.exe` directly. On macOS/Linux use `python3`, `source .venv/bin/activate`, and the equivalents under `.venv/bin/`.

Installation registers `actionmail`, `actionmail-eval`, `actionmail-workflow`, `actionmail-app`, `actionmail-review`, and `actionmail-google-auth`. Every entry point accepts `--help`; use `actionmail COMMAND --help` for subcommand options.

## Common commands

| Command | Purpose and expected output | External activity |
| --- | --- | --- |
| `actionmail start` | Numbered menu: demo, evaluation, results, UI, exit | Depends on selected item |
| `actionmail demo` | Three scripted scenarios and the artifact directory | None |
| `actionmail eval --validate` | Validate 60 active v2 cases and component hashes | None |
| `actionmail results` | Latest complete saved product regression summary | None |
| `actionmail eval --saved` | Alias of saved results, without inference | None |
| `actionmail check` | Readiness JSON; nonzero exit for invalid manifests or unsupported Python | None |
| `actionmail doctor` | Python, package, corpus and model readiness JSON | None |
| `actionmail ui` | Synthetic mailbox and scripted product workflow | None by default |
| `actionmail review` | Original-source inspection of a saved regression run | None |
| `actionmail analyze FILE --schema v2` | Single-email decision, tasks, evidence and traces | Model API after confirmation |
| `actionmail eval --estimate` | Cost forecast, then stop before inference | Provider pricing/account queries may occur |
| `actionmail eval` | New 60-case LLM evaluation after a forecast and confirmation | Paid inference after confirmation |

`actionmail` alone opens the menu in a terminal; when piped/noninteractive it prints help and exits. `start` is a terminal menu, not a full TUI. Menu option 2 launches a new LLM evaluation; options 1 and 3 support offline inspection.

## Offline demo: run and inspect

```powershell
actionmail demo
actionmail demo --output-dir results/private/my-demo
```

The first command creates a unique timestamped output under `results/private/`. The second requires a **new** directory; choose another name on repeated runs. Expect three scenarios, one accepted task, one simulated event, zero real model calls and zero real provider requests. The flow imports synthetic emails, analyzes scripted replies, accepts a task, drafts/confirms a calendar entry, exports ICS and simulates an idempotent write.

| Artifact | What to inspect |
| --- | --- |
| `summary.json` | Scenario statuses, counters, paths and simulation boundary |
| `records.json` | Emails, decisions, proposals, source reads and traces |
| `deadline.ics` | Portable calendar export |
| `workflow.sqlite3` | Persistent workflow state |
| `workflow.demo-events.json` | Synthetic calendar event |

This demonstrates engineering behavior, not model accuracy. Private output directories are ignored by Git.

## Validate data and inspect saved results

```powershell
actionmail eval --validate
actionmail results --all
actionmail results --json
actionmail results --run v2-regression-repair-20261001
actionmail results --case S02
actionmail results --case S02 --trace
actionmail eval --saved --case S02 --trace
```

Validation prints `Validated 60 active v2 cases: 50 base + 10 supplementary; component hashes verified.` It loads original inputs without calling a model. `--mailex-root PATH` selects a relocated corpus.

`results` selects the latest complete run. `--all` includes incomplete runs; `--run` selects the displayed directory name; `--case` prints one JSON row; `--trace` includes replies and source-read/repair details and requires `--case`. `--json` provides machine-readable run summaries.

The retained `v2-regression-repair-20261001` result supports product regression/source inspection. It is **not** the final six-model benchmark or two-model ablation. Inspect those under `../experiments/results/` using [experiments/README.md](../experiments/README.md); no paid rerun is needed.

## Optional local interfaces

```powershell
actionmail ui --no-browser --port 61933
actionmail review --no-browser --port 61934
```

Open the printed `http://127.0.0.1:PORT/` URL. The product UI offers synthetic mailbox import, scripted analysis, human task review, calendar preview, confirmation and simulated export/write. Unknown imports receive scripted `needs_review` unless a real model is explicitly enabled. The review interface shows originals, saved outputs, attachments and traces.

Both keep running until **Ctrl+C**. Both default to port `61933`, so choose different ports when running together. `--no-browser` suppresses automatic browser opening. Product `--store PATH` selects its SQLite database. Default UI storage is `%LOCALAPPDATA%/ActionMail/demo.sqlite3` on Windows or `~/.local/share/ActionMail/demo.sqlite3` otherwise; `ACTIONMAIL_PRIVATE_DIR` overrides the directory. UI data persists between launches.

Long equivalents are `actionmail-app` and `actionmail-review results/evaluation/v2-regression-repair-20261001`. Short `review` finds the latest complete run; the long review entry point requires its path.

## Analyze one email with a model

Set configuration **in the current process environment**. The product does not automatically load `.env` files. Replace these placeholders before running:

```powershell
$env:ACTIONMAIL_MODEL = "YOUR_MODEL_ID"
$env:OPENROUTER_API_KEY = "YOUR_API_KEY"
actionmail analyze examples/sample_email.json --schema v2 --external-mode snapshots
actionmail analyze evaluation/archive/fixtures_v2_1/A04.eml --recipient alex@example.com --schema v2
```

The CLI shows the target/external inventory and asks permission to transmit content. `y` proceeds; Enter or `n` cancels before transmission. Missing confirmation input stops the command. Output contains the decision, tasks, reasons/evidence, available token/latency information and read traces. The final approval prompt is a review decision; this single-email command does not change mail or calendars.

| Option | Meaning |
| --- | --- |
| `--recipient ADDRESS` | Required for EML; normalized JSON contains the target |
| `--schema v2` | Final multi-action workflow with reasons, quotes and traces |
| `--max-actions 1` | V2 limit: 1, 2 or 3; invalid with v1 |
| `--external-mode body-only` | Default: no external-content reading |
| `--external-mode snapshots` | Selected attachment bytes and supplied link snapshots |
| `--external-mode allowed-live --allow-domain example.com` | Explicit live HTTPS allowlist; repeat the domain option if needed |
| `--model ID` | Override `ACTIONMAIL_MODEL` |
| `--api-url URL` | Override `ACTIONMAIL_API_URL`; default OpenRouter chat completions |
| `--api-key-env NAME` | Read the key from this named environment variable |

Single-email analysis defaults to **v1**, so select v2 for multi-action output. The compatible spelling `actionmail examples/sample_email.json --schema v2` has the same behavior. API URLs must use HTTPS except a local `http://127.0.0.1:PORT/` test server. Live links require the allowlist and an additional confirmation when needed.

## New evaluations and the offline rule baseline

```powershell
actionmail eval --estimate --limit 1
actionmail eval --case-id S02 --output-dir results/private/s02-check
actionmail eval --limit 3 --output-dir results/private/model-smoke
actionmail eval --output-dir results/private/new-v2-run
```

These require the model settings above. Short `eval` defaults to `v2-60`, forces v2/snapshots and previews pricing before inference. Estimates may query provider pricing/accounts but generate no answers. `--limit`, `--case-id` and `--case-group` are mutually exclusive; repeat `--case-id` to select multiple cases. Final measured results do not need rerunning.

`--yes` skips the inference confirmation and is only for deliberately authorized automation. Declare both `--input-price-per-million` and `--output-price-per-million`, or neither. Forecasts are not billed charges. Outputs are `run.json`, `cases.jsonl`, `summary.json`, plus `manifest_snapshot.json` for v2-60. Existing output directories are refused. `--resume` skips saved cases and requires matching path, cases, model, code and recorded settings. A partial legacy run can show an incomplete full-suite summary.

```powershell
actionmail eval --benchmark frozen --engine rules --output-dir results/private/rules-check
actionmail-eval --validate
actionmail-eval --history
```

The offline rule baseline supports only v1/body-only, so explicitly select `frozen`; default v2-60 is incompatible. It runs 50 cases without an LLM. Long `actionmail-eval` defaults to the legacy 50-case suite; short `actionmail eval` defaults to 60 cases. Detailed options remain available via `actionmail-eval --help`.

## Persistent offline workflow, step by step

Every `actionmail-workflow` command uses synthetic resources/scripted replies. Put global `--store` **before** the subcommand. This PowerShell example reads IDs/revisions from JSON:

```powershell
$store = "results/private/manual-workflow.sqlite3"
actionmail-workflow --store $store mailbox
$record = (actionmail-workflow --store $store fetch m1 | ConvertFrom-Json).result
$recordId = $record.id
$record = (actionmail-workflow --store $store analyze $recordId | ConvertFrom-Json).result
$proposal = $record.proposals[0]
$proposalId = $proposal.id
actionmail-workflow --store $store review $recordId $proposalId --state accepted
$start = [datetime]::ParseExact($proposal.deadline, "yyyy-MM-dd", $null)
$fields = @{
    title = $proposal.text; description = "Offline manual workflow"
    start = $start.ToString("yyyy-MM-dd"); end = $start.AddDays(1).ToString("yyyy-MM-dd")
    timezone = "Asia/Singapore"; calendar_id = "demo@example.com"; all_day = $true
}
$fields | ConvertTo-Json | Set-Content results/private/draft-fields.json -Encoding utf8
$record = (actionmail-workflow --store $store draft $recordId $proposalId --fields results/private/draft-fields.json | ConvertFrom-Json).result
$revision = $record.proposals[0].draft.revision
actionmail-workflow --store $store confirm $recordId $proposalId --revision $revision
actionmail-workflow --store $store export $recordId $proposalId --output results/private/manual-deadline.ics
actionmail-workflow --store $store simulate-write $recordId $proposalId
actionmail-workflow --store $store tasks
```

`description` must be text (empty is allowed). Confirmation requires the exact saved revision; stale revisions fail. Export refuses an existing ICS. Repeating `simulate-write` for one confirmed draft preserves one synthetic event. Start with a fresh store/output name when repeating the full example.

Other commands: `list`, `show RECORD_ID`, `import FILE [--recipient ADDRESS]`, and `review ... --state rejected`. Review accepts `--text` and `--deadline` (`null` clears it); `analyze --force` requests reanalysis. `actionmail-workflow demo --output-dir NEW_DIR` is the long demo equivalent. Without `--store`, commands use `cli-demo.sqlite3` under the private directory. None writes to a real account.

## Optional real Google connection

Adapters exist, but live Google integration has not been accepted or measured. Offline coursework inspection needs no Google setup. `actionmail-google-auth --help` documents separate `connect`/`disconnect` operations for `gmail` and `calendar`. Connect requires `--client-file PATH` and Google extras (`python -m pip install -e ".[google]"`); OAuth is explicitly invoked and tokens stay in private storage.

UI flags: `--gmail` enables real mail; `--calendar` requires Gmail and separate calendar authorization; `--live-model` enables real LLM analysis on user action. Use a separate store for real data. The workflow CLI stays synthetic. UiPath, automatic replies and background monitoring are not implemented.

## Verification and troubleshooting

```powershell
python -m unittest discover -s tests -q
python -m unittest discover -s ../experiments/code/tests -q
python tools/check_commands.py --report results/private/command-checks.json
python tools/check_repository.py
```

The command checker executes installed entry points, menu flows, a 50-case rule batch, a scripted local HTTP model, workflow transitions and both HTTP interfaces. Its child Python processes block external connections. It checks account/payment guards without real OAuth, model calls or provider billing queries. Temporary/private outputs preserve measured evidence. [The delivery command-check record](results/command_checks.json) is separate from AI metrics.

| Symptom | Action |
| --- | --- |
| Command not found | Activate the environment or use its full executable path |
| Model/key missing | Export variables in this terminal; `.env` alone is insufficient |
| Original source missing | Clone all folders or supply `--mailex-root` |
| Address already in use | Stop the other server with Ctrl+C or choose another port |
| Existing output refused | Choose a fresh path; resume only a matching evaluation |
| Confirmation input unavailable | Run interactively or use deliberately authorized batch controls |
| Optional packages absent | Google/UiPath are unnecessary for offline inspection |

The measured runtime in `../experiments/data/frozen-core/runtime/` isolates finalized results from product changes. Its manifest records file hashes for integrity checks. Product development belongs in `src/actionmail/`.
