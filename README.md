# ActionMail

ActionMail identifies current tasks for a named email recipient and returns actions, explicit deadlines, a reason and original source quotes. It supports local JSON/EML inputs, selected attachments and bounded external reading. It proposes tasks for human review; mailbox and calendar integration are planned for v3.0.

The frozen baseline is **v2.0**, on branch `v2.0`. **`main` is the v3.0 development line**. The owner requested this version freeze after the 60-case regression passed. This does not imply that every output received a new individual human Pass judgment.

Start with [the v3.0 handoff](docs/handoff.md), [current architecture](docs/architecture.md), [evaluation facts](docs/evaluation.md), or [report writing guide](docs/report_guide.md). These are the authoritative current documents. Earlier plans, manifests, results and scripts live in [backup](backup/README.md).

## Run locally

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

This individual PE6201 project uses public MailEx/Enron-derived emails, authored challenge inputs, Python, pypdf and a model rented through OpenRouter. Dataset provenance and AI-assisted fixture/annotation history must be disclosed in the report; selected cases were reused for prompt tuning and are not a blind held-out evaluation. No Gmail OAuth, automatic calendar write, reply sending, task execution or production mailbox monitoring is currently implemented.
