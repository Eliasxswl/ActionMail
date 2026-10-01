# Current architecture: v2.0 core with v3 application

Updated 1 October 2026. The extraction core below retains the v2.0 contract. V3 adds the local application described below. Real Google account connectivity remains unverified; [handoff.md](handoff.md) records the owner-approved scope.

```mermaid
flowchart LR
    A[Local JSON or EML] --> B[EmailPackage: target and source inventory]
    B --> C{External sources?}
    C -->|Yes| D[Validate reading plan]
    D --> E[Read selected sources within budgets]
    C -->|No| F[Extract current tasks]
    E --> F
    F --> G[Validate structure and original evidence]
    G -->|Repairable failure and allowance remains| R[One correction per email]
    R --> G
    G --> H[Action / no action / needs review]
    H --> I[Human review]
```

There is one model client and a bounded Python workflow, not an open-ended agent loop. Long inputs use overlapping segments and a complete candidate ledger for merging. Summaries are not evidence. An entire email shares one validation-repair allowance across planning, segments, merge and short extraction; transport errors, valid review decisions, unread required material and exhausted budgets do not cause retries.

## Modules and boundaries

| Module | Owns |
| --- | --- |
| `ingestion/`, `domain/email.py` | JSON/EML parsing; actual target, headers, timestamps, body, thread and attachment/link inventory |
| `content/` | Bounded extraction for text, HTML, CSV, text-based PDF, DOCX, XLSX; source hashes/locations; allowlisted HTTPS transport |
| `workflow/coverage.py`, `context.py` | Reading-plan contract, segment budgets and actual source availability |
| `workflow/multi_pipeline.py` | Planning, reading, extraction, merging and deterministic validation |
| `workflow/repair.py`, `guardrails/matching.py` | Shared repair allowance and bounded original-quote suggestions |
| `reasoning/`, `guardrails/evidence.py` | Model API, parsing, exact quote alignment and output checks |
| `evaluation/` | Immutable runs, cost preflight, approved reference comparison and owner reviews |
| `interfaces/` | CLI and a local single-column benchmark review UI |

The old `workflow/pipeline.py` and v1 parser are retained compatibility code. V2 currently shares source normalization with that module. Do not archive them without moving this shared dependency and updating callers; replacing this boundary is a later small refactor, not a reason to rewrite the application.

## Public decision and policies

V2 returns exactly `status`, `actions`, `reason`, `evidence`. Each action has `kind`, `text`, `deadline`, `evidence`. Array length is the count; at most three independently completable tasks are supported. Same-deliverable substeps normally form one action. Optional comments for consideration alone are no action; a concrete request to consider, decide or reply can be an action. Preserve the sender's level of commitment.

The target recipient is explicit. Older requests apply only when renewed by the newest message. Bodies use `thread:N`; original historical headers use `thread:N:headers`. Missing execution access or business inputs do not erase an identifiable request. Explicit missing document dependencies can require review.

Body content comes first. Read required external task details and links that carry the main message; skip unrelated reports, footer links and background. Skipped, unread and successfully read are different states. Never cite unseen content or claim it was checked.

Evidence must match supplied original text. Safe whitespace alignment and known MailEx soft wraps can restore an exact original span. Similarity only locates correction candidates; even a 98.5% match cannot approve a changed amount. Numeric/unit/date/negation markers are diagnostics, not complete semantic validation. Repairs are checked against the same stage's supplied sources, never hidden full documents. Both replies, usage and repair outcome are saved. A validated quote proves provenance, not that the paraphrased task is semantically correct or complete.

ISO deadlines require explicit resolvable source information. Relative dates use trustworthy received time and timezone; absence of that anchor stays null. Independent semantic date resolution is not implemented. File limits, corrupt/archive checks, missing cached spreadsheet values, private-network destination controls and source coverage produce visible review reasons. Scanned PDFs, legacy DOC/XLS, login-dependent pages and JavaScript-only pages are unsupported.

## V3 application boundary

The owner selected CLI-first delivery on 2 October 2026. `interfaces/workflow_cli.py` is a thin offline entry point to the same persistent service, with a repeatable demo and JSON source/analysis/history output. Existing extraction and evaluation CLIs retain real-model experiments. The GUI remains an optional review interface; TUI and UiPath integration are not required. See [CLI guide](cli_guide.md).

`application/store.py` persists private messages, analysis, reviewed proposals and calendar outcome history in SQLite. `application/service.py` invokes the same extraction workflow and owns explicit analyze/review/draft/confirm/write/export operations, unchanged-content deduplication, call caps and crash recovery. `integrations/mail.py` normalizes selected Gmail MIME/thread data into `EmailPackage`; `integrations/auth.py` manages separately enabled desktop OAuth features. `integrations/calendar.py` translates approved drafts into Google event payloads or ICS and reconciles stable operation IDs. `interfaces/app_server.py` serves a separate single-column mail/review/task product UI. Its default uses artificial provider responses and scripted model replies, clearly labelled in the UI. See [contracts and limits](google_integrations.md).

Calendar drafts require accepted tasks and complete user-reviewed dates; confirmation belongs to one saved revision. Changes invalidate it. A write is persisted before sending; unknown outcomes are reconciled without blind retry. No provider capability is exposed to the model. Rejected tasks cannot become calendar items. Private application records are independent of frozen evaluation evidence.

## Deployment boundary

The benchmark UI still reviews saved runs; the product UI is a separate application mode. Only one service uses port 61933 at a time. Gmail/OAuth/Calendar code is implemented against official interfaces and fake responses; real authorization and API writes are deferred. ICS export and the local product path work offline. No automated replies, external task execution or mailbox monitoring exists. Private content, API keys and provider tokens remain outside Git and ordinary evaluation logs. Default private files are local plaintext, not an encrypted vault; the service is for a single local user/process.
