# ActionMail experiments

Start here to inspect the completed experiments. The final course report is [FINAL_REPORT.pdf](../report/FINAL_REPORT.pdf); its evidence map is maintained in [report/README.md](../report/README.md).

## Reading order

1. [Experimental report](REPORT.md): results, model differences, verbatim responses, fairness analysis and ablation interpretation. This is the sole maintained experimental narrative.
2. [Protocol](PROTOCOL.md): questions, data, metrics, frozen conditions, budget and acceptance scope.
3. Inspect [model mapping](results/model-benchmark/model_mapping.csv), [case metrics](results/model-benchmark/case_metrics.csv) and [request metrics](results/model-benchmark/turn_metrics.csv).

## Completed scope

Six models each completed 60 cases: 360 benchmark analyses. Luna and Sonnet completed 500 ablation/repeat analyses, followed by 500 Codex AI semantic reviews, not independent human reviews. Total measured spend was USD 3.224528503 under the USD 5 cap. Sonnet's benchmark fee correction is in `results/billing_clarification.json` and report section 2; original numeric tables remain unchanged.

Experiments were finalized on 2026-10-03. These 60 cases were reused for development/tuning and are not a blind held-out set. Format compatibility, shared retries, reasoning budget and provider effects are disclosed. The 360 benchmark outputs have not received exhaustive semantic review.

## Layout

| Path | Purpose |
| --- | --- |
| `code/` | Maintained experiment harness, configurations and offline tests |
| `data/frozen-core/` | 60 inputs, supplied originals and measured runtime snapshot |
| `data/owner_adjudications/` | Original evidence for four explicitly saved owner judgments |
| `results/model-benchmark/` | Six-model outputs, requests, metrics and bills |
| `results/rules-baseline/` | Rule comparison records |
| `results/ablation/` | Two-model ablations, repeats and semantic review |

`code/` is the maintained harness; the measured snapshot under `data/frozen-core/runtime/` isolates experiments from adjacent product development. The manifest records the runtime bundle hashes. The analysis generator is maintained under `code/`; normal inspection uses saved results.

## Offline checks

From the workspace root:

```powershell
python experiments/code/pipeline.py --help
python -m unittest discover -s experiments/code/tests -q
python ActionMail/tools/check_repository.py
```

These checks make no real-model calls. `code/configs/model-benchmark.json` records the approved six-model/USD 5 configuration. Other configurations support existing engineering tests and do not authorize additional paid runs. Edit narrative conclusions only in `REPORT.md`; do not overwrite measured results or execute archived recovery scripts.

## Delivery contents

The final files remain expanded in the workspace: this entry, report, protocol, `code/`, `data/` and `results/`. Only retired code, documents and data are compressed under the root `archive/`. No archive of the current submission is maintained. Credentials, local `.env` files, caches and API keys are not submission materials.
