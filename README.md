# ActionMail

| Item | Value |
| --- | --- |
| Current released version | v1.5 (MVP and frozen evaluation baseline) |
| Main branch | v2.0 development; not yet released |
| First runnable MVP | v1.0 |
| Project type | Individual PE6201 end-of-course project |

ActionMail reviews a work email for an action directed at the target recipient. It proposes the action, an explicit deadline when one exists, and source evidence. The user reviews the proposal before any calendar output is produced.

The v1.0 application is runnable locally. Its integration path is covered by tests, and the sample email completed a live OpenRouter call with `openai/gpt-6-luna`. A first 50-case evaluation has also run; its initial counts and limitations are recorded below.

## Run the MVP

Use Python 3.10 or newer. Install the package from this repository with `python -m pip install -e .`, then set `OPENROUTER_API_KEY` and `ACTIONMAIL_MODEL` in your local environment. Do not put the key in a repository file. For example, in PowerShell:

```powershell
$env:OPENROUTER_API_KEY = "your-key"
$env:ACTIONMAIL_MODEL = "openai/gpt-6-luna"
actionmail examples/sample_email.json
```

Use an exact model ID from the [OpenRouter model catalog](https://openrouter.ai/models) if you choose another model.

The CLI asks before sending email content to OpenRouter and asks you to review the returned result. For a local `.eml` file, run `actionmail path/to/message.eml --recipient you@example.com`. The parser preserves complete email addresses from To and Cc separately when present. The default API endpoint is OpenRouter; `--api-url` and `--model` can override it. The MVP does not write to a calendar or mailbox.

The `review_reason` field explains an unresolved `needs_review` result. It is `null` for definitive `action` and `no_action` results. Earlier raw model responses sometimes supplied an explanation in this field even for an action; the parser now normalizes it to `null`. The raw response remains available in each evaluation record.

## Evaluate the frozen cases

The [annotation policy](evaluation/annotation_policy.md) and [50-case manifest](evaluation/cases.jsonl) define the owner-adjudicated gold v1.5. Versioned manifest and policy snapshots for v1.0 through v1.5 are preserved under `evaluation/`. The v1.5 manifest was frozen before the first v1.5 model evaluation.

C10 changed from `needs_review` to a follow-up `action` after owner review. Gold v1.2 temporarily moved C08 to `needs_review`; owner review restored `action` in v1.3 because Teb can act on the conditional correction even though Frazier also received the email. E05's authored snapshot was reworded to avoid implying Alex was in Cc when the email lists Alex in To. Gold v1.4 replaced C01 and C07 with C11 and C12, provisionally labeled `needs_review`. Gold v1.5 replaces nine repetitive explicit-action cases and C05 with ten more varied cases. The current full-content gold counts are 22 `action`, 20 `no_action`, and 8 `needs_review`.

The set contains 31 distinct MailEx raw-thread cases and 19 authored cases: 10 attachment/link challenges and nine direct-email challenges. MailEx raw files remain in the sibling `../data/raw_threads` directory; each selected file is checked against a SHA-256 hash. Authored content is fixed in the manifest. See the [MailEx paper](https://aclanthology.org/2023.emnlp-main.801/) and [source repository](https://github.com/salokr/Email-Event-Extraction) for the dataset origin.

The saved rule-baseline reference run is in [`results/evaluation/rules-v1-final-20260929`](results/evaluation/rules-v1-final-20260929/summary.json). Its status counts are a comparison point; the rule baseline uses a generic action phrase, so action wording and evidence support have not been credited as correct.

The [v1.1 rule baseline](results/evaluation/rules-v1-1-20260929/summary.json) uses the revised C10 label. It is a new run; the v1.0 baseline remains available for comparisons under the old labels.

The [gold v1.2 rule baseline](results/evaluation/rules-gold-v1-2-20260929/summary.json) uses both C10 and C08 revisions. These rule runs do not establish that the generic rule action wording is semantically correct.

The [gold v1.3 rule baseline](results/evaluation/rules-gold-v1-3-20260929/summary.json) uses the owner-reviewed C08 label. The [gold v1.4 rule baseline](results/evaluation/rules-gold-v1-4-20260929/summary.json) preserves the prior comparison. The [gold v1.5 rule baseline](results/evaluation/rules-gold-v1-5-20260929/summary.json) uses the current manifest.

For relative deadlines such as "tomorrow", the model receives the email's `received_at` time when available and should resolve the date in that timezone. MailEx raw threads lack a reliable received time, so their relative deadlines stay `null` rather than using the day of evaluation. Vague phrases such as "ASAP" also stay `null`; the current output has no separate field for the original time phrase. Date normalization currently relies on the model and output format checks, not an independent check that the computed date matches the source. Gold v1.5 includes two body-only exact deadlines and two resolvable relative deadlines.

The first [gold v1.5 GPT-6 Luna run](results/evaluation/20260929T163325Z-a6e361d8/summary.json) completed all 50 cases without API errors. It matched 37 full-content gold statuses: 15/22 actions, 16/20 no-actions, and 6/8 reviews. Status-only action precision was 15/16 and recall was 15/22. All 10 external-content cases safely abstained because the current pipeline did not read attachments or linked pages; these abstentions count as full-content status mismatches. Among the 40 cases with body-only or thread content, 37 statuses matched. The three other mismatches were A06 (an otherwise useful action was withheld after a quote punctuation mismatch), C12 (an empty newest body and missing amendment were treated as no action), and C13 (one of two tasks was proposed while the other task and unavailable material were omitted). A21-A24 matched both body-only absolute and resolvable relative deadlines, four non-null dates in total. The run recorded 34,915 input and 6,012 output tokens, with estimated cost USD 0.0064975 based on OpenRouter prices observed at preflight. Human review of model action wording and evidence support remains pending; status agreement does not prove their semantic correctness. A03, for example, proposes sending an updated chart when the email asks whether one is available.

The first full GPT-6 Luna run is in [`results/evaluation/20260928T195446Z-afaa6d56`](results/evaluation/20260928T195446Z-afaa6d56/summary.json). It produced 11 action predictions that passed the exact source-quote check, with no false action predictions; 15 gold actions were missed or errored. It correctly returned no action for 8 cases and safely requested review for all 10 attachment/link cases. There were 20 validation failures and 2 empty API completions. These are status counts, not a claim that every action phrase is semantically correct. The quoted token prices were operator supplied, so the saved cost is an estimate.

After inspecting this run, the response parser was adjusted to handle common harmless output shapes, exact quotes with whitespace differences, and a larger completion allowance. The original run is retained unchanged. Manual review of action wording and evidence support remains outstanding.

A targeted [C04/C09 rerun](results/evaluation/20260928T201957Z-50f578b4/summary.json) returned text for both cases. C09 matched its action label. C04 incorrectly turned a request in an older forwarded message into an action for the current recipient. The current prompt and evidence gate now require support from the newest message when an action cites an older thread.

The [revised 50-case GPT-6 Luna run](results/evaluation/20260928T204118Z-f3d5b625/summary.json) completed without API errors. It used the v1.0 manifest and predates the later historical-header and recipient-perspective changes. Its status counts under v1.0 gold are:

| Gold status | Correct definitive result | Review or other result |
| --- | ---: | ---: |
| Action | 18 of 26 | 8 of 26 |
| No action | 19 of 23 | 4 of 23 |
| Needs review | 0 of 1 | 1 false action |

The 10 attachment/link cases were all safely sent to review, since the body-only system could not read their external content. Among the 40 cases whose decisive content was available, 37 status decisions matched the then-current gold: 18 of 20 actions and 19 of 19 no-action cases; the remaining context case was a status mismatch. Five results had validation failures: one model quote differed from its source punctuation, and four definitive no-action predictions were downgraded because external content was unread. All 50 cases have token records; the estimated total cost was USD 0.0057647 using operator-supplied prices. These counts do not establish semantic correctness of the action text. The 16 checked deadline fields in that run were all `null`; all six gold cases with exact dates depend on unread external content. The body-only run therefore provides no measured exact-deadline extraction result.

An initial review of the 19 action predictions found two cases needing human judgment. A03 adds providing a chart if available, while the gold asks only to report availability. For C10, the owner identified that Darrell is the target recipient and the group is waiting to hear from him. The current gold records a follow-up response without asserting what Darrell's answer is. In the saved run, the model saw thread bodies without their From/To headers. The loader and prompt now preserve raw historical headers and complete email addresses where the source contains them; headers with only names are marked as lacking addresses. This later change has not been measured by the saved run.

In the first run, A06 had `status_correct: true` only because both gold and prediction had status `action`; its action wording omitted the source's `not apply` phrase. The project owner considers the proposed task understandable in context, so its semantic correctness must be recorded separately from the automatic status score. In the revised run, A06 was withheld by exact evidence validation because the model omitted the period in `Inc.?`. The project owner should adjudicate action wording and the Codex-drafted gold labels before using the results as final academic evidence. Earlier runs remain unchanged.

The present 50 cases include body-only exact-date extraction, resolvable relative dates, and multiple independent tasks. They do not measure real attachment/link retrieval, broad `.eml` formatting, multilingual emails, or prompt injection resistance. These require separate challenge cases or tests before claiming general performance. Owner review identified three later improvements without changing v1.5 gold: explain why a confirmed appointment such as N11 is not an action, preserve the unresolved relative deadline phrase in A09, and support multiple separately evidenced actions as in A16.

After `python -m pip install -e .`, inspect saved runs, validate the cases, and run the deterministic rule baseline without an API key:

```powershell
actionmail-eval --history
actionmail-eval --validate --manifest evaluation/cases_v1_5.jsonl
actionmail-eval --engine rules --manifest evaluation/cases_v1_5.jsonl
```

To run the current v1.5 gold with OpenRouter, set `OPENROUTER_API_KEY` locally. Check the balance and forecast first; this command sends no email content to the model:

```powershell
actionmail-eval --engine llm --model openai/gpt-6-luna --manifest evaluation/cases_v1_5.jsonl --preflight
```

The preview reports the current API key's usage and remaining spending limit when OpenRouter provides one. **A key limit is not the account's credit balance.** To see the actual account credit balance, set `OPENROUTER_MANAGEMENT_KEY` locally to a management key; the tool then queries the read-only credits endpoint. Never store either key in this repository. The cost forecast uses [current model catalog prices](https://openrouter.ai/docs/api/api-reference/models/get-model), an approximate input-token count, and previous output-token usage for the same model. It is not a guaranteed bill. The [current-key](https://openrouter.ai/docs/api/api-reference/api-keys/get-current-key) and [credit-balance](https://openrouter.ai/docs/api/api-reference/credits/get-credits) endpoints are separate.

First check one action case, then run all 50. Each live command repeats the preview before asking whether to send the case content:

```powershell
actionmail-eval --engine llm --model openai/gpt-6-luna --manifest evaluation/cases_v1_5.jsonl --case-id A01
actionmail-eval --engine llm --model openai/gpt-6-luna --manifest evaluation/cases_v1_5.jsonl
```

If live model pricing is unavailable, supply both `--input-price-per-million` and `--output-price-per-million` after verifying them yourself. Each command asks once before sending its cases. Every run gets a separate directory under `results/evaluation` with `run.json`, per-case `cases.jsonl`, and `summary.json`. If a run is interrupted, pass its directory with `--output-dir` and add `--resume` to skip completed cases. `--history` gives a compact list of these runs without combining scores across different gold versions. The saved status counts, abstentions, token use, latency, and estimated cost support later reporting and visualization. Action wording and whether evidence semantically supports it still require manual review.

### Prepare the v2 evaluation

The ten external-content cases E01-E10 have frozen attachment or page snapshots. Select them as a cohort, preview its cost without sending email content to the model, then run the full-content comparison:

```powershell
actionmail-eval --engine llm --schema v2 --model openai/gpt-6-luna --case-group external --external-mode snapshots --preflight
actionmail-eval --engine llm --schema v2 --model openai/gpt-6-luna --case-group external --external-mode snapshots
```

This cohort contains five attachment and five link cases. Snapshot mode reads the saved text and never fetches the example URLs. Its summary reports status and action-count checks against the existing full-content, single-action reference, along with source hashes, model calls, tokens, latency, and estimated cost. Action wording and evidence meaning still need human review.

The snapshot cohort does not need the optional PDF reader at runtime. If this editable installation predates the PDF feature, reinstall the package with the same Python interpreter (`python -m pip install -e .`) before reading a local PDF attachment. Without `pypdf`, a PDF is routed to `needs_review` instead of preventing the CLI from starting.

A16 and C13 have separate [draft multi-action references](evaluation/multi_action_draft.jsonl). They leave the frozen v1.5 labels unchanged. Inspect the two drafts without an API call, then preview and optionally run the v2 model on those two cases:

```powershell
actionmail-eval --prepare-multi
actionmail-eval --engine llm --schema v2 --model openai/gpt-6-luna --case-group multi-draft --preflight
actionmail-eval --engine llm --schema v2 --model openai/gpt-6-luna --case-group multi-draft
```

Both draft references await owner approval, so the v2 summary does not score them as correct or incorrect. A16 proposes two separately evidenced tasks. C13 names two candidate requests but remains `needs_review` because MailEx does not contain the attachment needed for the review task. The review page displays each v2 action and saves separate meaning and evidence checks for each predicted action. After a run, open its saved directory with `actionmail-review PATH_TO_RUN`; stop any existing review server on port 61933 first.

### Review cases in a local browser

Install the updated package with `python -m pip install -e .`, then open the current gold v1.5 model run to review its proposed actions and evidence:

```powershell
actionmail-review results/evaluation/20260929T163325Z-a6e361d8
```

The command opens a browser page served only on `127.0.0.1:61933`; press Ctrl+C in the terminal to stop it before opening another run on that port. The page shows the newest email, received time when available, earlier thread, reference label, model or rule result, exact evidence, annotation note, and any external snapshot that was unavailable to the body-only model. Newest-message To and Cc are separate. Historical From/To/Cc headers keep complete email addresses when the raw source supplies them; a name-only header is marked as lacking an address rather than guessed. An older run also shows a revised gold label beside its original label when they differ, without changing its score. The previous gold adjudication for the same frozen manifest is shown separately in the new model run; model-output review remains unsaved until explicitly submitted. Use the filters to focus on action predictions or status disagreements. These judgments are separate from automatic status counts.

Saved assessments go to `adjudication.json` inside that run directory. The original `cases.jsonl` and `summary.json` are not changed, and the review page makes no model API or calendar calls. The review file is tied to that run and its frozen manifest hash; keep it with the run when preparing a report. When opening a v1.0 run, the review tool automatically uses the matching v1.0 manifest snapshot.

## Technology decision

The main extractor uses **one LLM**. A deterministic rule matcher provides a non-AI baseline. An experimental **bounded tool-use workflow** on `main` reads local attachments or frozen page snapshots, and can read live HTTPS pages from explicitly allowed domains. It makes at most two model calls and reads at most two external sources per email; source selection from the first answer is still in development. A separately trained ML classifier is outside the initial scope because the available event labels do not directly match the recipient-specific action task.

Python code will own the orchestration, validation, and evaluation. UiPath is not a runtime dependency. The final report will explain this change from the formative problem statement.

## Version plan

| Version | Status | Scope |
| --- | --- | --- |
| v0.1 | Completed | Architecture and documented decisions. |
| v1.0 | Completed MVP | One local `.eml` or JSON email input; one LLM decision; structured action/deadline/evidence output; deterministic evidence checks; user review. |
| v1.5 | Completed baseline | Owner-adjudicated 50-case gold set, local review UI, cost preflight, run history, rule baseline, and first full model run. Model-output semantic review remains a separate evaluation task. |
| v2.0 | In development on `main` | Bounded attachment and link reading, improved evidence and empty-message handling, clearer question interpretation, and multiple action candidates. |

The `v1.5` branch preserves the released baseline. The experimental v2 CLI on `main` adds `--external-mode snapshots` for frozen content and `--external-mode allowed-live --allow-domain example.org` for explicitly approved HTTPS domains. `--schema v2` selects the multiple-action contract. It returns up to three separately evidenced actions by default; more than three require review. `--max-actions 1` or `--max-actions 2` can lower the limit for a controlled run. The v2 schema has not yet been evaluated against a multiple-action gold set. See the [v2 design](docs/v2_design.md) for the reading flow, safety limits, and remaining work.

These labels describe scope, not a claim that an in-development version has shipped. Update the release version and this table whenever a milestone is completed or its scope changes.

## Language convention

Repository documents, code comments, CLI messages, prompts, structured result fields, and demonstration output are in English unless the project owner explicitly requests another language. Source emails retain their original language.

## Intended boundaries

- Run locally and on demand. No inbox monitoring or browser plugin is required for the core evaluation.
- Process one target recipient. The released v1.5 contract returns at most one actionable item; the experimental v2 contract can return multiple separately evidenced candidates up to an explicit limit.
- Treat email, attachments, and linked pages as untrusted data.
- Never send a reply, alter the mailbox, or write to a calendar without an explicit user confirmation. The MVP only previews the result.
- Keep live Gmail OAuth and direct calendar integration outside the critical path. A future mail adapter can use the same normalized email contract.

## Documentation

- [Architecture and package boundaries](docs/architecture.md)
- [v2 development design and limits](docs/v2_design.md)

## Reproducibility status

The v1.0 command-line path is implemented, covered by integration tests, and verified once with a live OpenRouter call on the sample email. The v1.0 frozen evaluation set, rule baseline, and two full GPT-6 Luna batches are saved under `evaluation/` and `results/evaluation/`. The owner-adjudicated gold v1.5 set has now had one complete GPT-6 Luna run with the later prompt changes. The API key is configured only in the project owner's local shell.
