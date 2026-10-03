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

## Configure your API key for real analysis and experiment reruns

The project uses **OpenRouter** for LLM requests. Create your own ordinary inference API key on the [OpenRouter API Keys page](https://openrouter.ai/settings/keys) and ensure your account can run the selected paid models. One OpenRouter key is used across the experiment's model families; separate OpenAI, Anthropic or Google keys are not required for this configuration. See [OpenRouter authentication](https://openrouter.ai/docs/api-reference/authentication).

From the repository root, set these variables in the **same PowerShell terminal** in which you will run the commands. Replace the quoted placeholders with your own values:

```powershell
$env:OPENROUTER_API_KEY = "PASTE_YOUR_OPENROUTER_API_KEY_HERE"
$env:ACTIONMAIL_MODEL = "openai/gpt-6-luna"
```

`OPENROUTER_API_KEY` is the actual credential. `ACTIONMAIL_MODEL` selects the model for product analysis/evaluation; the example model is the ID recorded in this project's experiments. You can use another OpenRouter model ID for a new run. These assignments last for this terminal session; repeat them in a new terminal. The product and `pipeline.py` read environment variables directly and **do not automatically load `.env` files**. No Google account or UiPath configuration is needed for the LLM experiments.

Check the settings without displaying the key:

```powershell
if ([string]::IsNullOrWhiteSpace($env:OPENROUTER_API_KEY) -or $env:OPENROUTER_API_KEY -eq "PASTE_YOUR_OPENROUTER_API_KEY_HERE") {
    throw "Replace the API key placeholder with your own OpenRouter inference key."
}
Write-Output "OPENROUTER_API_KEY is configured (value hidden)."
Write-Output "Selected product model: $env:ACTIONMAIL_MODEL"
.venv/Scripts/actionmail.exe doctor
```

This checks presence, not provider acceptance. An invalid or expired key is reported when the provider is contacted. `doctor` should show `model.configured: true`; it does not print the key.

On macOS/Linux, use the corresponding shell exports:

```bash
export OPENROUTER_API_KEY="PASTE_YOUR_OPENROUTER_API_KEY_HERE"
export ACTIONMAIL_MODEL="openai/gpt-6-luna"
```

### Run a real single-email analysis or a small evaluation

```powershell
.venv/Scripts/actionmail.exe analyze ActionMail/examples/sample_email.json --schema v2 --external-mode snapshots
.venv/Scripts/actionmail.exe eval --estimate --limit 1
.venv/Scripts/actionmail.exe eval --limit 1 --output-dir ActionMail/results/private/live-smoke
```

Analysis asks permission before sending content. The estimate can query provider pricing/account information but does not generate answers. Evaluation asks permission before inference. Choose a fresh output directory each time. A new real-model run uses your account and may incur charges; offline demo, validation and saved-result inspection remain available without a key.

### Rerun the six-model experiment

The experiment harness uses the **same `OPENROUTER_API_KEY`**, but reads model IDs and declared token prices from its configuration JSON rather than `ACTIONMAIL_MODEL`. The included benchmark config records the six original model IDs, prices at measurement time and a USD 5 run budget. Verify model availability and current prices before a paid rerun; copy the config for any changes and preserve the recorded one. [The protocol](experiments/PROTOCOL.md) explains the measured conditions.

```powershell
.venv/Scripts/python.exe experiments/code/pipeline.py plan --bundle experiments/data/frozen-core --config experiments/code/configs/model-benchmark.json
.venv/Scripts/python.exe experiments/code/pipeline.py run --bundle experiments/data/frozen-core --config experiments/code/configs/model-benchmark.json --output experiments/artifacts/my-benchmark --approve-paid
```

`plan` makes no model calls and lists 360 planned analyses. The second command is an explicit paid authorization, not an interactive prompt. It requires a new output directory and records requests, responses, metrics and billing observations separately from the original `experiments/results/model-benchmark/`. The generic harness has no `--resume`; do not assume the product evaluator's resume option applies to it. Original model availability, routing, stochastic answers and prices can change, so a rerun is a new measurement rather than a promise of identical scores or charges.

`OPENROUTER_MANAGEMENT_KEY` is **optional** and only enables additional account-credit accounting. Ordinary inference and API-key usage accounting use `OPENROUTER_API_KEY`. Leave the management variable unset if you do not need account-level credit observations; a management key is not an inference-key substitute. If you have a management key:

```powershell
$env:OPENROUTER_MANAGEMENT_KEY = "PASTE_YOUR_OPTIONAL_MANAGEMENT_KEY_HERE"
```

Do not commit either key. Local `.env` files are ignored by Git, but creating one alone does not configure the commands above. Historical `run_ablation.py` is tied to the original account baseline and output paths; use the [experiment entry point](experiments/README.md) and preserved protocol for interpreting those existing results rather than running that script as a general-purpose rerun command.

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
