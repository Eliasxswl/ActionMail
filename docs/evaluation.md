# Evaluation facts and reproduction

Updated 1 October 2026. Source of truth: `evaluation/active_suite.json` and the saved run `results/evaluation/v2-regression-repair-20261001`.

## Active data

The denominator is 60: frozen base 50 plus ten approved supplements. Base categories are 15 no-action, 15 explicit-action, ten context-dependent and ten attachment/link challenges. Supplement categories are two long-content, four real-attachment, two link/mixed and two limits/hostile cases. Category names describe scenario selection, not predicted status.

Origins across the 60 are 33 original MailEx raw-thread cases, one Enron exported parent/PDF case, 19 authored JSON cases and seven authored EML fixtures. Thus 34 inputs are based on existing email data and 26 are authored. The ten base external examples are short authored snapshots, not retrieved real web pages. The corpus was audited locally; do not claim all download files were evaluated. MailEx annotations are not this project's recipient-specific action labels.

The base manifest SHA-256 remains `3113b2d774f89bc2acb2e568ffd491457dc3ec04f7743574be8d418744a66e3a`. Owner amendments in `v2_reference_overrides.json` permit A16's two tasks and either approved C11 ownership interpretation. The active registry SHA-256 is `ba35ae3661652627d9add022cf4336b2c38db0ee4c33a0c7fad68c11ff51922c`. Archive relocation did not change active fixture, manifest or latest-run bytes.

## Latest measured run

Run `20261001T130907Z-23a9fe51`, model `openai/gpt-6-luna`, snapshot/actual-attachment mode:

| Measure | Observed |
| --- | ---: |
| Completed | 60/60 |
| Accepted status / action-count match | 60/60 each |
| Literal status equality against the single stored gold | 59/60; C11 has an approved alternative |
| Supplement source-selection / read-expectation match | 10/10 each |
| Supplement complete content coverage | 9/10; S08 intentionally unreadable |
| Validation repairs | 2; C12 and S02, both validated |
| Unexpected API / validation / read failures | 0 |
| Expected malformed-file review | 1; S08 |
| Final quote provenance | Every quote independently matched to its registered source |
| Directly comparable single-action deadline fields | 23/23; includes null fields |
| Model calls | 78 |
| Input / output tokens | 101,010 / 16,566 |
| Estimated batch / mean email cost | USD 0.018384 / 0.0003064 |
| Median / mean model-call time summed per email | 3.48 / 4.39 seconds |

Latency sums recorded model calls per email; it is not measured inbox-to-calendar response time. Prices came from preflight (USD 0.10/M input and 0.50/M output); this is an estimated model bill, excluding host cost, engineering effort and integrations. Do not extrapolate a snapshot benchmark as a production billing guarantee.

Predictions are 28 action, 23 no-action and nine reviews (15% review rate). Reference single labels are 27 action, 23 no-action and ten reviews, because C11 also permits action. C12 corrected missing review evidence. S02's changed `$50k` suffix was rejected despite high similarity; correction selected a shorter exact quote. S08's broken workbook was correctly refused without retry. E10 read the main project-details snapshot; S03 skipped a self-contained informational PDF; S09 read its hostile fixture and preserved the legitimate request. These cases illustrate safeguards, not a universal security guarantee.

## Historical comparison and limits

Under frozen v1.5 labels, the rule baseline matched 26/50 statuses, with status-only action precision 11/18 (61.1%) and recall 11/22 (50%). The v1.5 body-only model matched 37/50, with precision 15/16 (93.75%) and recall 15/22 (68.18%). Both are retained under `backup/v1.5/results/evaluation/`. An always-majority-action baseline is 22/50 (44%) on that v1.5 set. Do not compare that majority count to the v2-60 denominator.

V2 changes available sources, action capacity, interpretation rules and accepted references; the historical scores are developmental evidence, not a controlled ablation. No current v2 rule-vs-model controlled comparison or fresh blind held-out test has been run. The suite has been repeatedly used for tuning. Exact quotes and count agreement cannot score semantic task completeness. Owner reference review is recorded; a new per-output review of the latest full run is still pending. Do not invent Pass judgments or call 60/60 real-inbox accuracy. Status precision/recall on v2 require an explicit policy for C11's alternative and review-class errors, not reuse of the v1 metric implementation.

## Paths and commands

Active manifests: `cases.jsonl`, `supplement_v2_approved.jsonl`, `v2_reference_overrides.json`, `active_suite.json` under `evaluation/`. Six active fixtures retain legacy paths in `evaluation/archive/fixtures_v2_1`; one is `evaluation/fixtures_supplement/S10_revision2.eml`. S03 needs `../data/external_samples/496fbb1c751d22557bfd74a63732c608.parent.json` and `enron_nov25.pdf`. MailEx inputs are under `../data/raw_threads`; supply an alternate root using `--mailex-root`.

```powershell
$env:PYTHONPATH = 'src'
python -m actionmail.evaluation.cli --benchmark v2-60 --validate
python tools/check_repository.py
python -m actionmail.interfaces.review_server results/evaluation/v2-regression-repair-20261001 --port 61933 --no-browser
```

A new paid run requires owner consent and a fresh output directory. Archived runs retain their original scores and raw replies. The superseded 24-case stress manifest remains available for offline tests at `backup/v2.0/evaluation/archive/challenge_v2_1_revision2.jsonl`; it is never added to the 60-case denominator.
