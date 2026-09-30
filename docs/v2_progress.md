# v2 implementation and acceptance status

Updated: 2026-09-30 (Asia/Singapore). Development on `main`; package version remains `1.5.0`.

## Implemented

- Actual `.eml` attachment bytes: text/CSV/HTML/text PDF/DOCX/XLSX. PDF page, DOCX paragraph/table and XLSX sheet/cell locations retain offsets. Spreadsheet expressions are not executed; cached values and missing caches are explicit.
- Office ZIP member/expanded-size/compression-ratio checks, corrupt/encrypted input handling, macro/embedded-object rejection, guarded XML and no external relationship resolution.
- Validated source-selection plans for every inventory ID. Only explicitly irrelevant sources are skipped, with reasons; required/unresolved failures prevent definitive results. Three or more documents are supported within configurable budgets.
- Complete overlapping body/thread/document windows, candidate merging, source-limited quote normalization and exact evidence validation. Budget failures identify unread input/ranges rather than silently truncating. Evidence locations enumerate all matching spans when a quote occurs more than once.
- Live response final URL, retrieval time, media type, raw-response replay and extracted-text records. Offline transport tests cover allowlisted redirects, private/mixed DNS answers, IP-pinned TLS/SNI, credentials/ports, timeout, HTTP failure, content type, compression, size and redirect bounds. Login/JavaScript barriers require review.
- A separate 24-case challenge loader and CLI, immutable reference-preview runs, hash-bound owner gold approval into a **new** manifest, source/read/coverage checks and manual completeness/deadline review fields. Planning/segment/merge costs are represented in preflight. All raw model responses are saved. A failed later API call preserves earlier replies and usage, records successful/failed call counts, and leaves total cost unknown instead of underreporting it.
- Review port uses exclusive binding on Windows; a second listener is rejected. The project server at `127.0.0.1:61933` serves the current reference preview.

## Verification

All **42 integration tests** pass with the bundled interpreter. The frozen 50-case and current 24-case manifests validate, and the review JavaScript passes its syntax check. Actual fixture extraction establishes page/cell/paragraph provenance, 26,780 extracted characters in a DOCX, distinct formula/cache handling, safe failure paths, selected/skipped sources, full overlapping coverage and supplied-evidence-only merging. Scripted model replies test workflow wiring and validation; they do **not** establish semantic/model accuracy.

The frozen `evaluation/cases.jsonl` SHA-256 remains `3113b2d774f89bc2acb2e568ffd491457dc3ec04f7743574be8d418744a66e3a`. Prior runs, labels and owner adjudications are preserved. No new live model call, live public-page retrieval, mailbox operation or calendar operation was performed during this continuation.

## Current challenge revision and reference review

The current manifest is `evaluation/challenge_v2_1_revision2.jsonl`, with 6 long-content, 8 real-attachment, 6 link/mixed and 4 limits/hostile cases. It contains 23 explicitly authored `.eml` fixtures and one authentic longer available MailEx thread. The real thread remains below 5,000 characters and is not described as a long-document test. Authored bodies range roughly 5,400–10,700 characters; L05 includes a separately represented long historical thread. Candidate gold covers zero, one, two and three actions; H04 additionally contains four independent requests behind an intentionally lowered coverage budget. A separate integration test verifies the four-action guard. Refusal cases are not successful long-content extraction cases.

The initial draft and `results/evaluation/challenge-v2.1-gold-preview` remain intact. Revision 2 fixes L06's actual boundary position: its current request occupies offsets **7969–8053**, crossing the 8000-character first-window boundary and appearing intact in the next overlapping window. The test now asserts this crossing explicitly, rather than merely finding the quote somewhere. Gold action wording and deadline are unchanged.

Review `http://127.0.0.1:61933/?case=L01`; the verified current run is `challenge-v2.1-gold-preview-r2`. The preview has **no model predictions**, no scores and no model reading claims; extracted material is provided only for gold review. Save the reference judgment for every case. The source-expectation and evidence-location details are expandable on the page. No owner judgment has been invented. If a reference needs correction, preserve its prior draft/review and prepare a new revision before scoring.

After all reference judgments are explicitly correct:

```powershell
actionmail-eval --benchmark challenge-v2.1 --approve-challenge-gold results/evaluation/challenge-v2.1-gold-preview-r2 --approved-manifest evaluation/challenge_v2_1_approved.jsonl
```

This command requires the matching reference-preview manifest/run hashes and all 24 saved owner gold judgments. It preserves the pending draft and writes an approved manifest with the adjudication hash. Live predictions cannot score pending gold; approved records enable status/count/source/read checks. Full action meaning, completeness, evidence and deadlines still need owner review after the model run.

## Remaining acceptance work

The owner agreed to run these 24 cases with `openai/gpt-6-luna` **after reference review passes**. That condition is still pending. Do not infer approval merely from elapsed time or the earlier snapshot-run consent.

1. Owner reviews/corrects current challenge gold and source/coverage expectations.
2. Produce the approved manifest from the saved reference judgments.
3. Check locally supplied `OPENROUTER_API_KEY`, current provider prices and allowance without exposing secrets; run the preflight against the approved manifest. The offline estimate uses historical prices only: about 56 calls and USD 0.036–0.054 in a conservative scenario. Approximate character/token estimates are not a guaranteed cost cap.
4. Run the conditionally consented batch into a new result directory and review its outputs, including failures, task completeness, evidence, deadlines, source choices and coverage. Disclose any challenge-driven prompt tuning. Do not relabel the old E01–E10 score.
5. Decide whether v2 acceptance passes. No release/version increment is justified yet.

## Practical limits

The content/segment/merge defaults and office safety bounds are documented in `docs/v2_design.md`. `ReadLimits` and `WorkflowLimits` configure them. This release scope excludes OCR, authenticated or JavaScript-rendered pages, mailbox/calendar integration and formula execution. Long extraction and source relevance remain model-dependent; offline scripted replies cannot prove their correctness. Prompt injection resistance is instructed and included in challenge gold, but requires the actual model run and human review. Offline socket tests verify the transport decisions; they do not prove real-page availability or all hostile-network behavior. The authored fixtures use structured operational observations with varied request placement/ownership; they do not estimate real-inbox prevalence.
