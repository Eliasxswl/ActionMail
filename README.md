# ActionMail — final PE6201 submission

ActionMail helps a named email recipient review current obligations in the newest work email. Local JSON/EML, thread context and selected attachments become up to three tasks, supported explicit deadlines, reasons and original-source quotes. Unavailable decisive information produces review. Users approve tasks; models have no mailbox/calendar write capability.

## Start here

- [Final report (PDF)](report/FINAL_REPORT.pdf); [editable manuscript](report/FINAL_REPORT.tex).
- [Code and run instructions](ActionMail/README.md).
- [Final experimental findings](experiments/REPORT.md); [protocol](experiments/PROTOCOL.md).
- [Report reproduction and evidence mapping](report/README.md).

## Install from GitHub

Use Python 3.10 or newer. The following examples use Windows PowerShell from the **repository root**, the directory containing `ActionMail/`, `data/`, `experiments/` and `report/`. Keep all these directories together.

```powershell
git clone https://github.com/Eliasxswl/ActionMail.git
cd ActionMail
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ./ActionMail
.venv/Scripts/actionmail.exe --help
```

The cloned repository is named `ActionMail`, and its product subdirectory is also named `ActionMail`. Run `pip install -e ./ActionMail` from the outer directory. Installation can download dependencies; subsequent offline commands need no account or key. The commands below use executable paths so PowerShell activation is optional. On macOS/Linux use `python3` and `.venv/bin/python` / `.venv/bin/actionmail` instead.

## Run and inspect without accounts or model charges

```powershell
.venv/Scripts/actionmail.exe demo
.venv/Scripts/actionmail.exe eval --validate
.venv/Scripts/actionmail.exe results
.venv/Scripts/actionmail.exe results --case S02 --trace
.venv/Scripts/actionmail.exe doctor
```

| Command | Expected result / where to look |
| --- | --- |
| `demo` | Three scripted scenarios, one synthetic calendar event, zero real API calls; prints a fresh artifact directory under `ActionMail/results/private/` |
| `eval --validate` | `Validated 60 active v2 cases: 50 base + 10 supplementary; component hashes verified.` |
| `results` | Latest complete product regression summary; this is separate from the final cross-model experiments |
| `results --case S02 --trace` | One saved case as JSON, with model replies and source-read details |
| `doctor` | Python, optional packages, corpus and model readiness JSON; absent Google/UiPath settings do not prevent offline inspection |

The demo saves `summary.json`, `records.json`, `deadline.ics`, a SQLite store and synthetic events. These are scripted engineering evidence, not measured AI accuracy. Final measured results are already included under `experiments/results/`; inspect [the experiment report](experiments/REPORT.md) for cross-model metrics, cost and limitations.

For optional local interfaces:

```powershell
.venv/Scripts/actionmail.exe ui --no-browser --port 61933
.venv/Scripts/actionmail.exe review --no-browser --port 61934
```

Open the printed local URL. The first is a synthetic product workflow; the second inspects saved regression originals and traces. Both run until Ctrl+C. Different ports allow both simultaneously. For a terminal menu, run `.venv/Scripts/actionmail.exe start` interactively.

## Verify the delivery

```powershell
.venv/Scripts/python.exe -m unittest discover -s ActionMail/tests -q
.venv/Scripts/python.exe -m unittest discover -s experiments/code/tests -q
.venv/Scripts/python.exe ActionMail/tools/check_commands.py --report ActionMail/results/private/command-checks.json
.venv/Scripts/python.exe ActionMail/tools/check_repository.py
.venv/Scripts/python.exe experiments/code/pipeline.py --help
```

The command checker exercises installed entry points, prompts, local HTTP servers, offline evaluation and workflow transitions in isolated stores. External model/Google calls are blocked in its child Python processes. It reports each check and saves a JSON outcome; the [delivery check record](ActionMail/results/command_checks.json) is maintained separately from AI evaluation evidence. Repository validation checks data, sealed/localized hashes, links and English-only maintained text.

For detailed parameters, paid-run confirmation, input formats, environment configuration, long command entry points, persistent workflow examples and troubleshooting, read [the full command guide](ActionMail/README.md). In particular, short `actionmail eval` defaults to 60 v2 cases; long `actionmail-eval` defaults to the legacy 50-case suite. The product does not load `.env` files automatically. Real-account/model operations are optional and are not required to review the submission.

## Final evidence and metrics

Six models were compared on 60 reused development cases (360 observations); two selected models underwent 500 ablation/repeat observations. Measured service spend was USD 3.224528503 against the authorized USD 5 cap. The fresh full-workflow ablation attained 59/60 and 60/60 semantic-delivery passes for Luna and Sonnet under recorded Codex AI review. The prior model candidate gate targeted at least 90% action precision and recall. Strict status, permitted interpretations, task semantics, latency and fees remain separate metrics. These results establish neither blind-test generalization nor independent human accuracy. One benchmark generation bill remains missing. The experiment report preserves all denominators and compatibility failures.

## Layout and version boundaries

| Directory | Submission purpose |
| --- | --- |
| `ActionMail/` | Runnable product, tests and two core design/data documents |
| `experiments/` | Sealed code, original inputs, measured runtime snapshot, outputs, bills and reviews |
| `report/` | Final PDF, editable LaTeX, generated Markdown, figures, assets and evidence map |
| `data/` | Minimal original corpus for evaluation and negative tests, with provenance explainer |

The measured runtime originated at c405d29 in `experiments/data/frozen-core/`. The original 120-file seal is archived; current English-localized hashes and original/new provenance are in experiments/results/english_localization.json. Cleanup removes retired authoring commands/history dependencies. English localization translates review explanations and analysis labels, plus one equivalent Unicode-regex spelling, without changing model responses, scores, fees or adjudications. Real Google/UiPath connectivity is not claimed. Development history is maintained as one recoverable ZIP under `archive/`, excluded from submission.

The final version remains expanded. Only retired material and originals superseded by English translations are compressed under archive/. No current-submission archive is maintained.
