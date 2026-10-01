# ActionMail

ActionMail identifies current tasks for a named email recipient and returns actions, explicit deadlines, a reason and original source quotes. It supports local JSON/EML inputs, selected attachments and bounded external reading. V3 development adds a persistent mail/task UI, Gmail read-only adapter, calendar preview, ICS export and Google Calendar adapter. Integration verification currently uses synthetic offline responses; real accounts have not been tested.

The frozen baseline is **v2.0**, on branch `v2.0`. **`main` is the v3.0 development line**. The owner requested this version freeze after the 60-case regression passed. This does not imply that every output received a new individual human Pass judgment.

Start with [the v3.0 handoff](docs/handoff.md), [current architecture](docs/architecture.md), [evaluation facts](docs/evaluation.md), or [report writing guide](docs/report_guide.md). These are the authoritative current documents. Earlier plans, manifests, results and scripts live in [backup](backup/README.md).

For the application, read [the v3 demo/run guide](docs/v3_demo.md) and [Google contracts and verification boundaries](docs/google_integrations.md). Run `actionmail ui` for the offline product UI on port 61933. `actionmail review` opens the optional saved-run review UI.

## Run CLI without account integration

The CLI remains available without mailbox/calendar integration. The GUI is optional for annotation/review. The short `actionmail` commands dispatch to the existing analysis and evaluation code. The original `actionmail INPUT ...` interface and `actionmail-eval` remain available for detailed runs.

```powershell
python -m venv .venv
.venv/Scripts/Activate.ps1
python -m pip install -e .
actionmail start                 # small text menu in a terminal
actionmail demo                  # offline demo; writes to a fresh private folder
actionmail eval --estimate       # v2/60 cost and usage preflight only
actionmail eval --validate       # validate the active v2 suite without inference
actionmail eval                  # v2/60; shows estimate and asks before inference
actionmail results               # latest completed saved runs
actionmail eval --saved          # same saved results view
actionmail results --run RUN_ID --case S02 --trace
actionmail doctor                # local packages, data and provider readiness
actionmail check                 # verify active manifest/hash references
actionmail review                # review the latest complete run in a browser
```

The offline demo uses authored inputs and scripted replies. It makes no model or provider calls; its output is engineering evidence, not accuracy evidence. A new model evaluation displays an estimate and requests confirmation before inference. The active 60-case run also requires the original local corpus in `../data`; saved results can be inspected without it. For exact options, external-source controls and run recovery, use `actionmail-eval --help`.

## Analyze one email with a real model

Python 3.10 or newer:

```powershell
python -m pip install -e .
$env:ACTIONMAIL_MODEL = 'openai/gpt-6-luna'
# Set OPENROUTER_API_KEY in your local environment, never in repository files.
actionmail examples/sample_email.json --schema v2 --external-mode snapshots
```

For an EML file, supply `--recipient you@example.com`. Despite its historical name, `snapshots` mode also reads actual attachment bytes; links require a supplied snapshot. Live public HTTPS reading requires `--external-mode allowed-live --allow-domain example.org`. Reading is bounded and unsupported or unavailable required material results in review. The CLI still defaults to the historical v1 contract for compatibility, so current commands explicitly select v2.

## Verify and review

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -q
python -m actionmail.evaluation.cli --benchmark v2-60 --validate
python -m actionmail.interfaces.review_server results/evaluation/v2-regression-repair-20261001 --port 61933 --no-browser
```

The review service uses one port, `61933`; reuse or stop its existing project process before starting another. The saved 60-case run is already available without making new model calls. Its status and action-count matches are 60/60 under approved reference rules, with two successful bounded repairs and one expected malformed-file refusal. All final quotes were independently matched to original supplied text. See [evaluation facts](docs/evaluation.md) for limitations and denominators.

Full validation needs the original public evaluation files in sibling `../data`: `raw_threads/` and two selected `external_samples/` files. These downloads are local and are not silently included in Git. Use `--mailex-root PATH` to choose another corpus location. The sample JSON and authored EML fixture inputs are included and can be used without the external corpus. [The repository check](tools/check_repository.py) verifies required paths, archive hashes and documentation links offline.

```powershell
python tools/check_repository.py
```

Paid model runs require separate owner consent. New runs use fresh result directories; never overwrite frozen runs, references or review records. The frozen 50-case manifest remains byte-for-byte unchanged; v2 adds ten approved supplementary cases and hash-bound owner amendments. Legacy v1 workflow/parsing remains because current compatibility and regression checks depend on it; it is not a second maintained product roadmap.

## Repository layout

| Path | Current purpose |
| --- | --- |
| `src/actionmail/` | Runtime, evaluation and review interfaces |
| `tests/` | Meaningful offline regression and integration tests |
| `evaluation/` | Active 60-case registry, references and required fixtures |
| `results/evaluation/v2-regression-repair-20261001/` | Latest full v2 run, immutable raw records and independent inspection |
| `docs/` | Current handoff, architecture, evaluation and report guidance |
| `tools/` | Current repository integrity check |
| `backup/<version>/<type>/` | Historical docs, code, evaluation data and results |
| `../data/` | Current local public corpus inputs, outside Git |

The legacy-named `evaluation/archive/fixtures_v2_1/` now contains only six fixtures still used by the active approved manifest. Their paths are intentionally retained to preserve its hash. The full superseded challenge is in backup. Generated package metadata is not maintained as source.

This individual PE6201 project uses public MailEx/Enron-derived emails, authored challenge inputs, Python, pypdf and a model rented through OpenRouter. Dataset provenance and AI-assisted fixture/annotation history must be disclosed in the report; selected cases were reused for prompt tuning and are not a blind held-out evaluation. V3's OAuth/provider code is implemented but live authorization and writes remain unverified. Reply sending, task execution and background mailbox monitoring are not implemented. No calendar item is written merely because a model proposes a task.
