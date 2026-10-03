# ActionMail core experiment protocol

## Objective

Identify current obligations for the named recipient of the newest email, preserve ownership, requested commitment and explicit deadlines, supply original-source evidence, and request review when decisive information is unavailable. Core acceptance does not require a live Gmail/model/Google Calendar loop.

The two experiments are a cross-model comparison of the full workflow and mechanism ablations on selected models. Quality, speed and actual fees are reported.

## Data and frozen conditions

The 60 development/regression cases contain 27 action, 23 no_action and ten needs_review labels, from public emails and authored challenges. They were reused for tuning and are not an independent blind test.

Inputs: `data/frozen-core/dataset.jsonl`; registry: `source_registry/`; measured runtime: `runtime/`; hashes: `manifest.json`. The measured business commit is c405d29. The runtime bundle manifest records the dataset and source hashes.

Models received identical inputs, schema, prompts, reading limits and retry budgets. All 60 initial case requests matched byte-for-byte except model. Temperature was 0 and max_tokens 2048. API-enforced JSON, explicit reasoning settings and fixed providers were not requested. Cross-family compatibility limits are disclosed.

The extraction prompt explicitly stated:

> Return only JSON with exactly: status, actions, reason, evidence.

Planning also required JSON, but models still supplied Markdown fences. The measured parser did not remove wrapping before JSON parsing. Format instructions were present; interface failures must not be interpreted as pure model ability differences.

## Experiment 1: completed cross-model benchmark

| Model | Family | Cases |
| --- | --- | ---: |
| GPT-6 Luna | OpenAI | 60 |
| GLM-5.3 Flash | Z.ai | 60 |
| Gemini 3.5 Flash Lite | Google | 60 |
| Gemini 3.8 Flash | Google | 60 |
| GPT-6.1 Sol | OpenAI | 60 |
| Claude Sonnet 5.5 | Anthropic | 60 |

Models rotated by case, with one formal trial per model/case: 360 analyses. Resume filled only missing observations. Per-case/per-request responses, retries, tokens, provider, timings and bills are retained.

The predefined main-ablation candidate gate was action precision and recall of at least 90%, subject to semantic review. On 2026-10-03 the owner selected Luna and Sonnet and authorized the ablations. Google/GLM compatibility diagnostics remained separate.

## Experiment 2: completed mechanism ablations

| Condition | Observations per model | Interpretation |
| --- | ---: | --- |
| Fresh full workflow | 60 | Same-batch paired comparator; benchmark observations are not new trials |
| One-call prompt baseline | 60 | Architectural baseline without external reading, repair or segment merging |
| No thread history | 12 | Ownership and currentness |
| No external reading | 17 | Missing required material and appropriate review must be disclosed |
| Read all sources | 17 | Removes selective planning; changes call count and exposure to corrupt inputs |
| No model repair | 60 | Keeps schema/original-source validation and safe fallback |
| Eight preselected cases repeated three times | 24 | Consistency is not correctness |

Each model completed 250 analyses; two models completed 500. Each email shared one model repair across planning/extraction/merging. Quote similarity is not probabilistic confidence and cannot automatically approve candidates. Format errors consuming the shared budget are analyzed separately.

Do not modify prompts after stage 1 and claim the same protocol. Fence removal, output/reasoning budget changes or provider-controlled experiments require separately identified factors and results alongside the original experiment. Explain business-code changes to the owner first.

## Metrics

- Separate strict status from pre-existing allowed status/count interpretations. Review on an answerable action counts as a recall miss.
- Review task units, omissions, ownership, commitment, deadlines and semantic evidence support separately; unreviewed fields remain pending.
- Literal quote matches do not establish semantic support; outputs without quotes do not receive 100% evidence quality.
- Record local case/request time, P50/P95, server timing and repair overhead. Billing-query overhead is separate; nonstreaming runs do not measure time to first token.
- Use key-usage differences and generation bills for actual cost. Token unit-price estimates are budgeting tools only.
- Count parsing, evidence, reading, API and output-limit failures, plus successful/failed/skipped repairs separately.

## Budget and remaining limitations

Overall authorized cap: USD 5. Benchmark usage-counter cost: USD 1.344801303. Ablation cost: USD 1.879727200. Total: USD 3.224528503; remaining: USD 1.775471497. The 595 known benchmark bills reconcile to the counter difference; one generation record is missing, so the complete per-request audit remains pending. All 579 ablation bills reconcile.

Six-model exhaustive semantic review, unused independent data, independent human review and the missing benchmark bill remain unresolved. The 500 ablation analyses and their Codex AI semantic reviews are complete. No new model calls are planned. Preserve raw records; maintain interpretation only in `REPORT.md`.

## Finalization and acceptance: 2026-10-03

The owner stopped additional models, conditions, calls and outcome-driven tuning and moved to report/demo delivery. The measured business version is c405d29. Forced-JSON and live-account upgrades are not part of this experiment.

Finalized scope: 360 benchmark observations, 500 ablation/repeat observations, original requests/responses, actual counter differences/bills and 500 Codex semantic reviews. The finalization manifest records hashes for 120 experiment files.

Acceptance concerns evidence completeness and supported conclusions, not a success threshold chosen after seeing scores:

- Inputs, runtime identity, configurations, model/condition names and all observations remain traceable.
- Status, allowed interpretations, task units, literal validation and semantic judgment are separate; all 500 ablation reviews retain reviewer identity and rationale.
- Quality, time, fees and failure chains remain traceable; total spend is below USD 5. Do not claim a complete per-request billing audit across 860 analyses.
- Claim development/regression findings only; Codex reviews are not independent human reviews and benchmark semantic scoring is not exhaustive.
- Independent first answers, provider routing and shared retries limit causal and family-ranking claims.

Independent tests/review, first-answer replay, forced JSON and real accounts are future work rather than mandatory post-finalization additions. Report, code and demo must identify the same measured evidence and its evaluation conditions.
