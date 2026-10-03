# ActionMail — final PE6201 submission

ActionMail helps a named email recipient review current obligations in the newest work email. Local JSON/EML, thread context and selected attachments become up to three tasks, supported explicit deadlines, reasons and original-source quotes. Unavailable decisive information produces review. Users approve tasks; models have no mailbox/calendar write capability.

## Start here

- [Final report (PDF)](report/FINAL_REPORT.pdf); [editable manuscript](report/FINAL_REPORT.tex).
- [Code and run instructions](ActionMail/README.md).
- [Final experimental findings](experiments/REPORT.md); [protocol](experiments/PROTOCOL.md).
- [Report reproduction and evidence mapping](report/README.md).

## Run without accounts or model charges

From this extracted directory, with Python 3.10 or newer:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ./ActionMail
.venv/Scripts/actionmail.exe demo
.venv/Scripts/actionmail.exe eval --validate
.venv/Scripts/python.exe -m unittest discover -s ActionMail/tests -q
.venv/Scripts/python.exe -m unittest discover -s experiments/code/tests -q
.venv/Scripts/python.exe ActionMail/tools/check_repository.py
```

The demo uses authored mail and scripted replies and records zero real API calls. Tests are offline engineering checks. Final measured results are included under `experiments/results/`; no account/key or new paid run is needed to inspect them. The experiment README explains its independent frozen harness.

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
