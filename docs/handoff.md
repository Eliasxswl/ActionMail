# ActionMail development handoff

Updated: 2026-10-01 (Asia/Singapore).

## Current owner steering: original data first

Read `docs/real_data_plan.md` first. The owner accepts roughly 2,000–3,000 characters and wants existing original data prioritized, with research into genuine attachment/link datasets. The prior mostly authored 24-case batch is now a preserved synthetic regression suite, not the primary acceptance batch. Twelve hash-bound original MailEx candidates are staged without gold; three parent-matched public attachment samples have been downloaded outside Git and checked offline. Do not invent missing times or documents. Conditional consent for the old 24 references does not authorize a changed batch. The review server still shows the historical authored preview until a new real benchmark is prepared.

## Implementation continuation

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
