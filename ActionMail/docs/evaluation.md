# Data and final evaluation evidence

Final evidence, 3 October 2026. The sole detailed experimental narrative is [experiments/REPORT.md](../../experiments/REPORT.md); the [protocol](../../experiments/PROTOCOL.md) records frozen conditions, targets and limits. The [course report](../../report/FINAL_REPORT.pdf) interprets them. Old development scores are not final model rankings.

## Inputs and provenance

The active registry contains 50 frozen base cases plus ten approved supplementary cases, with component hashes and owner-bound reference overrides in `evaluation/active_suite.json`. Strict labels are 27 action, 23 no_action and ten needs_review. Public MailEx/Enron-derived mail is combined with authored challenges. AI-assisted fixture/annotation origins must be disclosed. Cases were reused for development/tuning, not blind held-out evaluation. See [annotation policy](../evaluation/annotation_policy.md).

Original files are in [the minimal corpus](../../data/README.md). Six active authored fixtures retain legacy names under `evaluation/archive/fixtures_v2_1/`; S10 uses `evaluation/fixtures_supplement/S10_revision2.eml`. Missing decisive contents produce review. Input loaders verify original-source and attachment hashes.

Experiments retain a self-contained immutable `experiments/data/frozen-core/` bundle: dataset, supplied text/blobs, registry and measured business runtime c405d29. English-localized reasons and equivalent Unicode spelling have explicit original/current hashes. [Saved owner adjudications](../../experiments/data/owner_adjudications/README.md) preserve four explicitly judged cases, not human review of all outputs.

## Completed measurements

- Six-model benchmark: 360 observations, one formal trial per model/case; format compatibility, provider/default reasoning and shared retry budget affect interpretation.
- Two-model ablation/repeat study: 500 observations and 500 Codex AI semantic reviews, not independent human reviews.
- Fresh full-workflow semantic delivery: Luna 59/60; Sonnet 60/60. Corresponding strict status matches: 58/60 and 59/60. The six-model benchmark is a separate run.
- Actual cumulative service spend: USD 3.224528503 below USD 5. One benchmark generation bill is missing; counter reconciliation does not erase the limitation.

The prior candidate gate targeted at least 90% action precision/recall. Strict class labels, permitted status/count interpretations, task units, evidence provenance, semantic support, review burden, latency and fees remain separate metrics. Literal quote matching and count agreement do not establish semantic completeness. Independent test data/human review and human fallback costs remain limitations. Detailed tables and denominators are in the experiment report.

## Records and verification

The original 120-file finalization is archived. The current English derivative also lists 120 hashes, with separate localization provenance. Model calls/responses, bills, scores and verdicts are unchanged; review explanations and analysis labels are translated. The retained product `results/evaluation/` run is an earlier regression used by source inspection/tests; final conclusions use `experiments/results/`.

Use `actionmail eval --validate` for current inputs and `python tools/check_repository.py` for final evidence hashes and maintained links. Offline test suites are engineering verification. Paid inference is unnecessary for inspection and was not repeated during cleanup.
