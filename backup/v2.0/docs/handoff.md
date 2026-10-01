# ActionMail development handoff

Updated: 2026-10-01 (Asia/Singapore).

## Full repaired regression passed automated checks; owner review pending

The owner completed `results/evaluation/v2-regression-repair-20261001`, run `20261001T130907Z-23a9fe51`. All 60 cases completed: status 60/60, action count 60/60, supplementary source-selection/read checks 10/10. There are no API or unexpected validation/read failures. S08 intentionally contains a malformed Office archive; its one recorded read/validation failure and incomplete coverage correctly result in `needs_review`, without a correction call.

C12 initially omitted evidence for its empty-body review decision; one correction added the supplied original historical recipient header and task quote. S02 initially altered the financial suffix again; strict validation rejected the quote and one correction used a shorter exact newest-message excerpt, preserving the no-action interpretation. Both initial and corrected replies remain saved; similarity did not approve the incorrect amount. Two repairs total, both validated.

Independent inspection reproduced all selected external reads locally, verified original source hashes and every coverage hash, and matched every final quote to its registered source. All 23 single-action deadline fields with directly comparable references match. `inspection.json` binds these checks to the saved cases-file hash; action meaning, completeness and broader generalization still require human review. No owner Pass values were invented and no live call was made during inspection. 78 calls, 101,010 input and 16,566 output tokens; estimated USD 0.018384. Port 61933 now serves this full run. This is the v2 acceptance candidate; release acceptance remains pending owner review.

## Live evidence-repair check passed

The owner completed `results/evaluation/v2-evidence-repair-20261001`, run `20261001T122851Z-af9a46a5`. All three cases match status and action count, with no API, final-validation or read failures. S02's first reply again changed `$25k-$50k` to `$25k-$50`; the 0.9852 diagnostic flagged a critical difference and did not accept it. One correction restored the amount and body soft-wrap newlines. The thread quote was safely aligned to the original stored span. Both replies and repair records are saved. Independent inspection confirms every final quote is an exact substring of its registered source and original MailEx hashes match.

C13 returns review for unavailable attached material with exact newest/older evidence and no retry. E10 reads the 66-character frozen page snapshot before returning no action; its text matches both the manifest and saved hash. Five calls, 8,002 input and 1,201 output tokens; estimated USD 0.0014007. These are three targeted checks, not full v2 acceptance or new owner Pass judgments. No additional model call was made during inspection. `inspection.json` records the independent checks, bound to the saved result-file hash. Port 61933 now serves this targeted run. Next: owner-run a fresh full 60-case regression and review any mismatches before v2 acceptance.

## Evidence diagnostics and one validation repair (offline verified)

The owner approved preserving model-selected quotes, adding matching diagnostics and returning validation failures for one correction. `guardrails/matching.py` performs a bounded lexical search within actually supplied sources. Scores are resemblance diagnostics, never semantic confidence or fuzzy acceptance. Numerical/unit/date and negation differences are flagged heuristically; every corrected quote still requires strict original-text validation. S02's altered amount yields about 98.5% similarity but remains invalid.

`workflow/repair.py` owns one correction allowance per email, shared by planning, extraction, segments and merge. Correction receives the original stage prompt, failed reply, validation error and candidate original excerpts; its result is revalidated. Hidden/unread sources cannot enter feedback. Valid review decisions, missing required material, API failures and budget failures do not cause retries. Both replies and actual usage are preserved; repair records and all raw replies are exposed in the review UI. Preflight conservatively budgets one possible extra call per v2 email.

All 68 offline tests pass, including saved S02 replay with a scripted exact-quote correction, repeated failure, shared allowance, prompt budget, transport failure, ambiguity/negation diagnostics and accounting for both replies. All 60 active cases and manifest hashes validate; the review JavaScript syntax check passes. No live model call was made and no historical row, score or owner judgment was rewritten. This does not prove a live correction will succeed. Next: owner-run S02 with C13/E10 controls in a fresh result directory, inspect the repair trace and exact evidence, then run the full 60 only if the check passes. Port 61933 still serves the earlier full regression.

## Eleven-case contract check: one quote failure remains

The owner completed `results/evaluation/v2-contract-check-20261001`, run `20261001T023554Z-750729c0`. Original scores: 10/11 status, 11/11 action count, 3/3 supplementary source/read checks; no API or read failures. N11 returned text/no action; A06/A08/A22/C02 now retain clear actions; C12 cites `thread:1:headers` successfully; C13 stays review for explicitly referenced missing material; E10 reads its 66-character snapshot; S03 correctly skips its informational PDF; S09 reads the 133-character attachment and returns the legitimate task. All accepted top-level/action evidence was independently matched to supplied source text.

S02 still fails: raw model judgment is `no_action`, but its body quote changes `$25k-$50k` to `$25k-$50` and replaces soft-wrap newlines with spaces while retaining equals signs. Do not accept the changed amount or call the check passed. This remaining issue is evidence generation, not another action-policy regression. Preserve the raw response and 10/11 score. Further full regression should wait for the quote issue to be handled. Inspection made no new model call or invented owner judgments; port 61933 still serves the earlier full regression, not these eleven rows.

## Regression-contract repairs (offline verified)

After owner instruction to fix the regression, the extraction contract now distinguishes identifying a task from executing it: absent business data/access/approval alone does not cancel an otherwise clear request. Missing externally referenced documents remain a dependency only when email text establishes that actual external relationship, preserving C13's attached-material case. Planning distinguishes a brief primary-content pointer (E10) from a self-contained informational balance report (S03). No case-ID branches were added.

V2 older-message headers now have exact source IDs `thread:N:headers`, shared by prompt construction, validation, segmentation and provenance. V1 body IDs/text remain unchanged. A quote mistakenly labeled with its thread body ID can be reassigned only to that same thread's exact registered header span. Offline replay of C12 passes with the original quote preserved; S02's altered amount is still rejected. The prompt requests minimal sufficient quotes rather than copying irrelevant financial ranges. The API output cap is now 2048 tokens; request construction and preflight share one constant, with header sources included in v2 token/segment estimation. No automatic retry or new paid model call was added.

All 60 offline tests pass. Scripted tests and replay do not prove the live semantic regressions are fixed. Next: targeted live run of N11/A06/A08/A22/C02/C12/S02/S03 plus C13/E10/S09 controls, with owner-run/consented calls, then a full regression only if these pass. Original full-run scores and owner adjudication remain preserved.

## Full regression did not pass

The owner completed `results/evaluation/v2-regression-20261001`, run `20261001T020143Z-08e74de7`. Port 61933 now serves it. All 60 rows completed, but original status/count matches are 54/60 and 56/60. C13/E10 fixes hold; other failures require work. See `docs/v2_regression_review.md`: overbroad missing-material/execution-prerequisite abstention (A06/A08/A22/C02), N11 response exhausted the 800-token cap without text, S02 changed an amount in its quote, C12 quoted a supplied header outside the registered body evidence contract, and S03 unnecessarily read an informative report. Expected malformed S08 remains correct. Do not declare v2 accepted or weaken evidence validation to raise scores. No new model calls were made during inspection.

## Targeted live check passed

The owner ran `results/evaluation/v2-fix-check-20261001`. Both C13 and E10 match status and action count, with no API, validation or read errors. Inspection confirms C13 returns `needs_review`, identifies unsupplied review material and cites the newest request exactly. E10 marks the primary link decisive, reads its 66-character frozen snapshot, returns `no_action`, and quotes both body and page. This is snapshot reading, not a live website fetch. Exact evidence and snapshot hash were independently verified. Three model calls; estimated USD 0.0006058. The inspection made no additional model call and did not invent owner Pass judgments. Next is a fresh 60-case regression run on the revised code; the earlier full run remains historical and port 61933 still serves it.

## Reading-policy fix and architecture review

The owner approved reading E10-like primary-content pointers before deciding whether there are actions and requested a code/architecture review. `workflow/context.py` now builds one availability context for short, segmented and merge extraction: actual read sources, deliberately skipped sources and unsupplied sources, with validated planning reasons. Empty inventory is explicitly distinguished from proof of complete material. The prompt requires review for current requests to inspect unavailable material and preserves older-message ownership. The reading-plan prompt was rewritten to resolve the earlier contradiction between "no body task" and "primary content is in the link"; generic footer/background links remain skippable.

The runtime uses canonical `reason/evidence` rather than old explanation accessors. Status/count comparison is consolidated in `evaluation/references.py` and reused by CLI and review. No case-specific C13/E10 runtime branch, automatic model retry, new model layer or output schema was added. `docs/architecture.md` now describes the implemented v2 flow rather than the original unimplemented MVP design. Offline tests cover primary-page reading, unread primary-page failure, irrelevant-source exclusion, C13 context/ownership, and availability propagation through segmentation/merge. These tests verify orchestration with scripted replies; live semantic correctness remains unverified. No model calls were made during this work. Next: separately consented C13/E10 targeted live verification, then a fresh full run after fixes pass.

## Owner adjudication of the full run

The owner explicitly approved A16's two actions and requested gold alignment; C11's original review and model interpretation are both acceptable. Saved `adjudication.json` marks C13 and E10 model results incorrect. The active suite now hash-binds `v2_reference_overrides.json`, updating A16 gold and allowing C11's two ownership interpretations in status/count checks. Original `cases.jsonl` (the frozen 50), result rows and `summary.json` remain unchanged. The full run stores `manifest_snapshot.json`, `reference_adjudication.json` and a separate `adjudicated_summary.json` (58/60 adjusted statuses, 59/60 counts). This is reference-adjusted scoring, not a new run or full human semantic approval. Port 61933 serves the same full run with A16's updated reference and preserved original answer. C13/E10 remain acceptance issues; no further live run has been made.

## Completed full run, acceptance pending

The owner completed `results/evaluation/v2-full-20261001`, run `20261001T004254Z-3d2be39d`. Port 61933 now serves this result. All 60 cases completed; original automatic scores are 56/60 status and 57/60 action count. All ten supplementary statuses/counts and source/read checks match. S02 exact quotes pass; S09 actually received the 133-character attachment including the hostile instruction and returned the legitimate report task. The single validation/read failure is the intentionally malformed S08 workbook. No API errors. See `docs/v2_full_run_review.md` for the four mismatch investigations (A16/C11/C13/E10). A16's frozen label reflects the old one-action limit; do not count every mismatch as a proven model error or silently revise gold. Human adjudication and the E10 skip-versus-abstain inconsistency remain before v2 acceptance. No additional model run was made during inspection.

## Full v2 evaluation entry point

The owner requested one full rerun of all 60 active cases and intends to use the reviewed result for v2 acceptance. `actionmail-eval --benchmark v2-60` now loads the hash-bound `evaluation/active_suite.json`, uses v2 and snapshot inputs, and excludes historical pending multi-action drafts. All 50 frozen reference statuses/action counts and the ten approved supplementary references are scored; action meaning, grouping, evidence and deadlines still need human review. A mismatch against a frozen single-action reference can require adjudication under the current grouping policy; do not silently revise gold or claim a status/count match establishes semantic quality.

Port 61933 currently serves `results/evaluation/v2-60-review-preview`, a reference-only preview of all 60 cases. Earlier model runs remain separate. The UI supports combined case-set/status/review/external filters and case-insensitive word search across IDs, subjects, sender/recipient addresses, newest body and older thread text. The new full run uses a fresh result directory; do not overwrite historical results. Review server automatically recognizes the full-suite registry from run metadata. All 52 offline tests pass; browser checks confirm 60 total, ten supplementary matches and one match for S09. No model calls were made while implementing this entry point.

Owner's full-run command (from the repository, with the key already configured locally):

```powershell
$env:PYTHONPATH = 'src'
python -m actionmail.evaluation.cli --benchmark v2-60 --model openai/gpt-6-luna --output-dir results/evaluation/v2-full-20261001 --yes
```

The command checks current provider pricing and prints the batch estimate before model calls. After completion, switch the existing 61933 service to this result directory. Check all 60 completed, API/validation failures, status/action-count/source/coverage mismatches and human Pass/Notes before recording v2 acceptance; the project is not yet declared released.

## Latest review and fixes (1 October)

This section supersedes the earlier continuation notes. The owner approved all ten supplementary references and ran `results/evaluation/supplement-v2-with-explanations` (run `20260930T223150Z-74fceffa`, model `openai/gpt-6-luna`). The active suite remains 50 + 10. Original status matches were 8/10 and action-count matches 9/10; these are automatic comparisons, not a complete human semantic assessment. The owner sampled other outputs without reporting problems; do not mark every output passed on their behalf.

- S02: the model's `no_action` was rejected because its older-thread quote omitted MailEx quoted-printable soft wraps (`=\n`, including one inside a word). Evidence alignment now recovers a unique match only for MailEx packages and restores the exact original span. The saved reply passes an offline recheck; original raw records and historical scores remain unchanged.
- S09: the run stopped after one planning call. That call saw the body and attachment inventory, but no attachment text. The assistant-directed attack in the fixture was never supplied, so this run does not evaluate injection resistance. Planning now treats absent content as normal before reading, and a bounded read can resolve an uncertain relevance plan. An offline scripted integration test verifies that attachment contents reach the subsequent extraction call; a new live result remains untested.
- New v2 responses have exactly `status`, `actions`, `reason`, and `evidence`. One reason is required for every status; original evidence supports it. Legacy `review_reason`/`explanation` outputs remain readable without rewriting history. Source-reading choices retain their individual reasons and quotes.
- Review main content is one column: email first, then Model / Reference / Reading / Raw reply tabs. Reference and model each have one Pass (Yes/No/Unsure), plus a shared optional note. Human-only attachment previews are clearly distinguished from text supplied to the model. Existing detailed review records remain preserved.

All 51 offline tests pass. This investigation made zero model calls. `investigation.json` in the run directory records the S02 replay and S09 diagnosis, tied to the original row hash. Port 61933 serves this run and `evaluation/supplement_v2_approved.jsonl`. Reload an existing browser tab to receive the updated interface. Any further live evaluation requires separate owner consent.

## Current owner steering: original data first

Read `docs/evaluation_60.md` and `docs/real_data_plan.md` first. The owner fixed the active evaluation at **50 base + 10 supplementary = 60 cases** and accepts roughly 2,000–3,000 characters, prioritizing original data. `evaluation/active_suite.json` identifies the active manifests; supplementary gold remains pending. The old 24-case challenge and fixtures moved to `evaluation/archive/` for offline tests/historical reproduction. The 12-candidate staging list was removed. Port 61933 now serves the ten-reference preview. Do not invent missing times or documents. Conditional consent for the old 24 references does not authorize a changed batch.

Latest owner feedback: optional comments "for your consideration" alone create no action (explicit corrected S01 choice). Group steps for the same deliverable; preserve independently completable tasks, maximum three. Reading plans prioritize body requests; skip external background not needed for action/ownership/deadline/conflict, even if readable. Still read sources explicitly required by body tasks. Active supplementary revision is `supplement_v2_revision2.jsonl`, preview `supplement-v2-gold-preview-r2`. Five unchanged correct judgments were carried with provenance; S01 follows explicit chat correction. S02 remains uncertain, S03/S05 reading expectations changed, S10 was replaced following rejection. Do not claim all gold approved. Target recipient is prominent in the UI; original attachments can be inspected. All 45 tests pass. The owner additionally asked whether every result/reading choice should have a short explanation with original evidence; structured explanation versus UI-only implementation is pending their choice. No live evaluation has been consented or run.

## Implementation continuation

Unified explanation implemented after owner instruction: every new v2 response requires `explanation: {text, evidence}` for action/no_action/needs_review. Definitive results require exact source evidence; model explanations are validated against actually supplied text, including segment and merge ledgers. Reading plans require reasons and evidence for every select/skip choice. System read failures reuse validated plan quotes when available; unavailable quotes are explicit. Legacy reference/history parsing remains compatible without inventing old model explanations. Review UI displays explanations and source-choice evidence. Approved gold manifests remain unchanged. No new model run is authorized; all 48 offline tests pass.

Latest acceptance update: all ten revision-2 reference judgments passed. The active supplementary manifest is now `evaluation/supplement_v2_approved.jsonl`, hash-bound to the saved owner adjudication. Active suite remains 60 cases. No new model evaluation has run or been separately authorized; unified explanation implementation awaits the owner's output-design choice. Earlier pending-review notes below are historical.

The authorized implementation work on 30 September adds DOCX/XLSX and provenance, inventory-bound source plans, coverage-aware segments/merge, live-response replay traces, transport tests, and a separately versioned 24-case challenge. See `docs/v2_progress.md` for current verification, limits and remaining acceptance work. The original handoff below records the starting state; its gap list and 27-test count are historical. No new live model evaluation has been made. The owner agreed to a 24-case GPT-6 Luna run **after** reference review passes; do not run before that condition is satisfied.

## Start here (original handoff)

Continue v2 development from `main` in `E:\NTU Learn\PE6201\End_Course_project\ActionMail`. Read this file, `docs/v2_design.md`, and the current code before changing anything. The owner rejected the idea of deferring realistic attachment/link handling beyond v2. The next work is implementation and meaningful evaluation, not another visual redesign.

The last committed implementation before this handoff is `b60acd9` (successful short-snapshot evaluation). This handoff commit also preserves revised scope, owner adjudication, and regenerated installation metadata. It does not implement DOCX/XLSX or the new long-content workflow.

## Owner requirements and working rules

- Discuss work with the owner in Chinese. Repository documents, comments, prompts, interface text, and structured output use English.
- Delivery deadline: 4 October, as extended by the instructor. Prioritize practical completion.
- Ask about unresolved product decisions before implementing them. For a technical blocker, try at most three remedies, then continue independent work and report the unresolved blocker.
- Obtain the owner's consent before running a live model evaluation. Existing consent applied to earlier runs; do not treat it as unlimited permission for new batches.
- Never put an API key in chat, code, logs, or Git. The owner's PowerShell has the key; the agent environment previously did not. Use `OPENROUTER_API_KEY` and `ACTIONMAIL_MODEL`; the evaluated model ID is `openai/gpt-6-luna`.
- Maintain a small set of useful integration tests. Preserve historical runs, reference labels, and owner review records.
- Serve the review UI on one port, `61933`. Do not spawn another review server on a different port. Verify and reuse or stop the project server before replacing it; do not kill unrelated Python or PowerShell processes.
- The original prohibition on generating documents applied to the initial MVP task. The owner subsequently authorized README updates and explicitly requested this handoff document.

## Repository and environment

- Repository: `E:\NTU Learn\PE6201\End_Course_project\ActionMail`.
- Downloaded corpus: `E:\NTU Learn\PE6201\End_Course_project\data` (outside the repository).
- Branch `v1.5` preserves baseline commit `ea9cbc6`; it was pushed to `origin/v1.5`. Develop v2 on `main`.
- Remote: `git@github.com:Eliasxswl/ActionMail.git` (private). This handoff request authorizes a local commit; check before assuming a new push is requested.
- Package version remains `1.5.0` while v2 is in development. Do not label v2 released before its acceptance gates pass.
- The current chat's working directory may still be the A1 assignment. Set the repository working directory explicitly. It may be outside the agent's writable sandbox; use the supported approval/escalation mechanism where needed.
- Owner interpreter: `C:\Users\kiven\AppData\Local\Programs\Python\Python314\python.exe`.
- Bundled test interpreter: `C:\Users\kiven\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.
- `pypdf>=6,<7` is declared in `pyproject.toml`. Its import is lazy so missing PDF dependencies do not break plain-text evaluation startup. Install with `python -m pip install -e .` when needed.
- Tracked `src/actionmail.egg-info` files are generated installation metadata. Their changes in this handoff reflect the owner's editable install, not new functionality.

## Implemented behavior

- Local `.eml` and JSON ingestion; newest message, older thread, target recipient, full available From/To/Cc addresses, and timezone-aware received time are separately represented.
- Python owns orchestration. One LLM is the primary extractor; deterministic rules provide a baseline. No UiPath runtime or separately trained ML model is required.
- v1 returns one action. Experimental v2 returns `status`, `actions`, and `review_reason`. Each action has `kind`, `text`, `deadline`, and evidence. Types: `answer_question`, `perform_task`, `follow_up`.
- The owner fixed the maximum at three actions. Count is derived from the array. More than three requires review; do not silently truncate or merge distinct tasks.
- Empty newest bodies require `needs_review`. Relative deadlines use received time, not processing time; unresolved or vague dates remain null.
- Evidence is checked against sources actually supplied. Narrow normalization restores whitespace or known abbreviation periods to the exact original span. Unknown source IDs can be recovered only when the quote uniquely identifies one available source. Negation and question marks must remain intact.
- External inventory and reading support snapshots, local plain text/CSV/HTML/text PDF, and explicitly allowlisted public HTTPS pages. Live transport has bounded redirects, public DNS checks, IP-pinned TLS, timeouts, and byte limits. Network-level verification remains incomplete.
- Review UI displays messages, references, model outputs, sources, and per-action meaning/evidence checks. It writes `adjudication.json`, not mail or calendar changes.
- Evaluation supports preflight balance/cost estimates, history, v1/v2 schemas, snapshots, and pending multi-action drafts. Semantic correctness still requires human review.

## Results to preserve

Frozen manifest: `evaluation/cases_v1_5.jsonl`; current `evaluation/cases.jsonl` has SHA-256 `3113b2d774f89bc2acb2e568ffd491457dc3ec04f7743574be8d418744a66e3a`.

| Run directory under `results/evaluation/` | What it establishes |
| --- | --- |
| `20260929T163325Z-a6e361d8` | v1.5 full 50-case run: 37/50 status matches; 37/40 body/thread cases; all ten unread external cases safely abstained. Status-only metrics do not establish action wording or completeness. |
| `20260929T210927Z-6ea72a10` | First v2 external snapshot run: 4/10 status matches. Failures exposed descriptive source IDs and singleton evidence objects; preserve the original score. Offline replay after fixes is not a new live run. |
| `20260930T112003Z-66fd690c` | Second v2 external snapshot run: 10/10 statuses and action counts; 12,079 input and 2,700 output tokens, estimated USD 0.0025579. Owner reviewed all ten reference labels and all six proposed actions/evidence as correct. Review is saved in this run's `adjudication.json`. |

The ten E cases are authored short snapshots, not real attachments or live pages. Their external text is only 44–79 characters. Passing them establishes the short snapshot path, not realistic external handling. Do not call the v1-to-v2 difference a controlled model improvement: available input and workflow changed.

`evaluation/multi_action_draft.jsonl` contains A16/C13 proposals marked `pending_owner`. A16 proposes two independent tasks. C13 requires missing attachment content and remains a review proposal. Do not score draft gold as approved.

Earlier semantic decisions: polite questions can request an answer without requesting delivery (A03); A06's exact quote must preserve punctuation/negation even if a paraphrased confirmation action is acceptable. C10 taught us to anchor ownership to the user's full address and distinguish outgoing requests, waiting, and incoming obligations. C08's two recipients alone do not imply uncertain ownership. N11 implicit social obligations and fuller explanations were recorded as later improvements; do not silently broaden the current action definition.

## Confirmed v2 scope

The owner approved adding **DOCX and XLSX** alongside plain text, CSV, HTML, and text PDF. Scanned/image-only files, login-protected pages, and JavaScript-dependent pages explicitly route to manual review. Mailbox and calendar integration belongs to **v3**.

v2 must implement and evaluate multiple documents, irrelevant/distraction attachments and links, long bodies/threads/documents, conflicts, provenance, and explicit failures. The detailed release contract and proposed 24-case challenge coverage are in `docs/v2_design.md`.

Current gaps:

1. `content/reader.py` reads every inventory item, allows only two sources, rejects extracted text above 20,000 characters, and treats any read failure as blocking. This cannot handle a harmless distracting attachment or footer link well.
2. `workflow/multi_pipeline.py` makes a body/thread decision, reads all external sources, then makes another decision. The first output is not a source-selection plan. The preflight assumes this two-call prototype.
3. DOCX/XLSX are not implemented. PDF page-level evidence locations and spreadsheet sheet/cell provenance are absent. ZIP expansion limits and safe handling of office relationships/formulas must accompany new readers.
4. Long content has no coverage-aware segmentation/merge path. Merely increasing the character cap or returning review for every long input does not evaluate extraction ability. No silent truncation or summary-as-verbatim-evidence is acceptable.
5. Live read records lack final URL, retrieval timestamp, media type, and reproducible fetched content. Actual transport/redirect safety and failure paths need verification.
6. `evaluation/cases.py` enforces the frozen 50-case distribution and single-action reference contract. Add a separate versioned challenge manifest/loader rather than altering historical denominators. Extend v2 metrics/review to approved multi-action gold and source/coverage expectations.

## Dataset audit and new cases

Local audit on 30 September found 230 raw thread files and 1,500 `full_data` JSON files. Raw newest bodies have median 83.5 and maximum 1,275 characters; raw full threads reach 2,830. JSON token arrays joined with spaces have median newest-body length 389.5, maximum 3,059, and maximum full-thread length 3,122. None reaches 5,000 characters. The selected 50 cases are shorter still (maximum newest body 604, full thread 1,554). JSON token spacing differs from the original text; these are approximate character measures, not model tokens.

The downloaded tree contains text/JSON and extensionless files, with no attachment binaries. Use available longer MailEx messages where appropriate, but author realistic long and external fixtures separately and label their origin. Do not invent missing original attachments and describe them as authentic MailEx content. Long fixtures must vary in structure, ownership, request position, and distractors; repeated filler is inadequate.

Suggested implementation order:

1. Real-file extraction and provenance, including DOCX/XLSX and archive safety.
2. Validated source-reading plan and relevance handling, with explicit budgets.
3. Coverage-aware segmentation and candidate merging for body/thread/external content.
4. Complete live-link trace and offline transport tests.
5. Challenge tooling and varied candidate gold; owner review; updated balance/cost preflight; consented live evaluation; result review.

## Verification and commands

At handoff, all **27 existing tests passed** using the bundled interpreter. No new model API call was made during handoff. Existing tests do not establish the missing v2 capabilities above.

From the repository, offline verification:

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -q
actionmail-eval --validate
actionmail-eval --history
```

Review the latest owner-adjudicated run (reuse port 61933 if already serving this run):

```powershell
actionmail-review results/evaluation/20260930T112003Z-66fd690c --port 61933 --no-browser
```

Open `http://127.0.0.1:61933/?case=E01`. A server was running there earlier; check current state rather than assuming it still exists. The Codex browser/terminal opening tool previously returned queued without visibly opening a panel; do not interpret that as proof of a running server.

For the existing short-snapshot batch only, after owner consent and local key setup:

```powershell
actionmail-eval --engine llm --schema v2 --model openai/gpt-6-luna --case-group external --external-mode snapshots --preflight
actionmail-eval --engine llm --schema v2 --model openai/gpt-6-luna --case-group external --external-mode snapshots
```

These are not commands for the unimplemented challenge set. Do not rerun the same short fixtures as a substitute for completing the new capabilities.
