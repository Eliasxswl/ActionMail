# ActionMail

Start with [the final submission README](../README.md). This directory contains the runnable product. [Architecture and integration boundaries](docs/architecture.md) explain input/output, modules and capabilities; [data and evaluation](docs/evaluation.md) explain the registry and final evidence.

## Install and run

From this directory, with Python 3.10 or newer:

```powershell
python -m venv .venv
.venv/Scripts/Activate.ps1
python -m pip install -e .
actionmail start                 # terminal menu
actionmail demo                  # scripted offline demo, fresh private output
actionmail eval --validate       # 60-case input validation, no inference
actionmail doctor                # local runtime/data/provider readiness
actionmail ui                    # optional offline product UI
```

The demo saves JSON traces, SQLite records, an ICS file and one simulated event. It is engineering evidence, not an AI accuracy experiment. The UI defaults to authored Google-shaped responses and scripted replies at `http://127.0.0.1:61933/`. One service can use the port at a time; `--port` selects another. Use `actionmail ui --help` for controls.

## Results and analysis

The final benchmark/ablation uses the independent harness: [experiments/README.md](../experiments/README.md), [experiments/REPORT.md](../experiments/REPORT.md). `actionmail results` instead reads the retained older 60-case regression fixture used by source-review tests/UI; it is not the final cross-model experiment.

```powershell
actionmail results
actionmail results --all
actionmail results --case S02 --trace
actionmail eval --saved          # regression view, no inference
actionmail review               # optional original-source review
actionmail analyze examples/sample_email.json --schema v2 --external-mode snapshots
```

Real analysis requires local `ACTIONMAIL_MODEL` and `OPENROUTER_API_KEY` settings and confirmation before transmission. EML needs `--recipient ADDRESS`. Historical `actionmail INPUT ...` and detailed `actionmail-eval` remain compatible. The single-email CLI defaults to v1; select v2 for multiple tasks. `snapshots` reads selected attachment bytes and supplied link snapshots. Live HTTPS needs `--external-mode allowed-live --allow-domain DOMAIN`.

`actionmail eval --estimate` previews provider pricing/cost without inference; provider API queries may occur. `actionmail eval` selects v2-60 and asks before inference. Frozen experiments need not be rerun. Missing confirmation input stops the operation. Never overwrite sealed evidence. Use `actionmail eval --help` and `actionmail-workflow --help` for detailed controls. Retired pending-label and draft authoring commands are only in the historical ZIP.

## Verification and maintenance

```powershell
python -m unittest discover -s tests -q
python tools/check_repository.py
```

The sibling `../data` includes current original corpus files; `--mailex-root` selects another location. Active manifest/fixture paths remain hash-bound, including six active fixtures under the historically named `evaluation/archive/fixtures_v2_1/`. Current negative-test inputs live under `tests/fixtures/`; focused historical replies preserve their original provenance.

Measured code in `experiments/data/frozen-core/runtime/` is immutable and is not a second development branch. Product code lives in `src/actionmail/`. V1 helpers remain live dependencies of v2 and the rule baseline. Google adapters are implemented but verified only with fakes. UiPath, automatic replies and background monitoring are not implemented. Environments, private demos, build outputs and credentials are excluded from submission.

[package_submission.py](tools/package_submission.py) packages the final four-directory layout from the workspace root.
