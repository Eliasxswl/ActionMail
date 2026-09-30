# ActionMail v2.0 Design

Status: development, with partial implementation on `main`. The v1.5 branch and frozen v1.5 evaluation remain unchanged.

## Revised release scope (owner decision, 2026-09-30)

Attachment and link handling is a v2 release requirement. v3 is reserved for mailbox and calendar integration. Passing E01–E10 does not complete v2: their external snapshots contain only 44–79 characters and do not exercise real files, distracting documents, long content, or live retrieval.

Supported v2 attachment formats are plain text, HTML, CSV, text-based PDF, DOCX, and XLSX. DOCX/XLSX support is approved but not implemented yet. Scanned/image-only documents, login-protected pages, and JavaScript-dependent pages require an explicit manual-review reason. Spreadsheet formulas must not execute; cached values must be distinguished from formula text, and missing cached values must not be invented. Office macros, embedded objects, external relationships, and document instructions are never executed.

The current implementation below describes the prototype, not the final release contract. In particular, the two-source limit, rejection of text above 20,000 characters, and reading every inventoried source remain release gaps.

### Dataset audit

Audit of the downloaded data on 2026-09-30:

| Material | Count | Median newest-body characters | Longest newest body | Longest full thread |
| --- | ---: | ---: | ---: | ---: |
| `raw_threads` | 230 files | 83.5 | 1,275 | 2,830 |
| `full_data` | 1,500 JSON files | 389.5 | 3,059 | 3,122 |
| Frozen evaluation | 50 cases | 85 | 604 | 1,554 |

Raw lengths use the existing header/thread parser. JSON lengths join the supplied token arrays with spaces; punctuation spacing and tokenization differ from raw text. These are character counts, not model token counts. The downloaded files have only empty, `.txt`, and `.json` extensions; no attachment binaries are provided. No audited body or thread reaches 5,000 characters. The 50-case set further underrepresents even the longer available messages. Realistic long-content fixtures must therefore be added separately and identified as authored, without claiming they were supplied by MailEx.

### Required implementation sequence

1. **File extraction and provenance.** Add DOCX/XLSX readers, preserve PDF page and spreadsheet sheet/cell locations, and distinguish unread content from successfully extracted content. Record source hash, extraction method, byte/character counts, and live retrieval time and final URL. Exercise real `.eml` attachment bytes rather than only pre-extracted snapshots. Reject corrupt archives, encrypted files, and excessive expanded archive content safely.
2. **Source relevance and multiple documents.** Make the body/thread pass produce a validated reading plan tied to source IDs. Distinguish decisive, supporting, irrelevant, and unresolved sources, with reasons. Document text must not itself grant authority to act. An unrelated attachment or footer link must not create a task; a failed irrelevant source must not automatically block a body-supported task. Unknown relevance or unavailable decisive content requires review. Record skipped sources and reasons. Replace the unconditional read-all behavior and the hard two-source limit with explicit configurable reading budgets.
3. **Long-content coverage.** Read content in bounded segments with stable offsets or page/cell locations. Preserve complete coverage within configured budgets; merge candidates using the newest-message ownership and temporal context. Find requests near the beginning, middle, and end, and handle instructions split across adjacent segments. Do not treat a summary as verbatim evidence. Never silently truncate a source or claim `no_action` when decisive content remains unread. Exceeding the total budget requires an explanation identifying what was not read. Apply the same policy to long bodies and threads, not just external content.
4. **Links and traceability.** Finish and verify the existing allowlisted public HTTPS reader, including redirects, content-type handling, timeouts, unavailable pages, size limits, and blocked destinations. Preserve a local content snapshot or equivalent replay material for evaluated reads. Frozen snapshots provide repeatable model evaluation; transport tests verify live retrieval separately. A snapshot alone does not prove live-link functionality.
5. **Evaluation and release.** Keep the frozen 50 cases and historical results intact. Add a separately versioned challenge manifest with owner-approved multi-action references, per-source relevance, evidence locations, read expectations, and explicitly documented authorship. Validate tools offline before asking the owner to approve live model runs. Preflight estimates must include planning, all content segments, and merging rather than assume two calls.

### Challenge coverage required before release

Use 24 varied development cases as an initial coverage target, separate from the frozen benchmark:

| Group | Cases | Required differences |
| --- | ---: | --- |
| Long bodies and threads | 6 | Beginning/middle/end requests, stale quoted requests, unrelated recipient, and split-context instructions; mix real longer MailEx examples with explicitly authored long messages |
| Real attachments | 8 | Multi-page PDF, DOCX paragraphs/tables, XLSX sheets/cells, multiple documents, distracting attachment, conflicting versions, and unresolved file content |
| Links and mixed sources | 6 | Snapshot and live-reader paths, body-to-document references, distracting footer link, attachment-plus-page dependency, and conflicting or stale page content |
| Limits and hostile/unreadable content | 4 | Prompt injection, image-only/encrypted or malformed file, denied/unavailable link, and incomplete coverage after a budget limit |

Features can overlap, but denominators and feature tags must be visible. Include zero, one, two, and three required actions; an over-limit case; both required and irrelevant external content; resolvable and ambiguous deadlines. Long fixtures should vary in structure and meaning, rather than repeat identical filler paragraphs. Include bodies around 5,000–15,000 characters and documents above the current 20,000-character limit. A safe refusal measures failure handling; it does not count as successful long-content extraction.

Report status counts, action completeness and meaning, evidence support, deadline correctness, source selection, content coverage, read failures, calls, latency, and cost separately. E01–E10 remain useful short regression checks. They cannot establish realistic accuracy; the challenge set is a development benchmark and any prompt tuning against it must be disclosed. The v2 release requires the owner to review both the new gold references and the actual model results.

## Product contract

ActionMail proposes recipient-specific next steps from the newest email, using earlier thread messages and explicitly read external sources as context. It does not send replies, change a mailbox, or write to a calendar. A human confirms any proposed step. A useful calendar event without a requested next step remains a separate future feature.

The experimental v2 result contains an `actions` array. Its length is the action count; the model does not make a separate counting call or return an independent count that can disagree with the array. Each action carries its own type, wording, deadline, and evidence. Initial action types are `answer_question`, `perform_task`, and `follow_up`. `no_action` requires an empty array and enough readable content to support that conclusion. `needs_review` covers unresolved ownership, contradictory instructions, unavailable decisive content, or more than three distinct actions. The project owner set the maximum at three. The CLI defaults to three and may use a smaller limit for a controlled run; it cannot raise the limit above three.

## External source inventory

The ingestion layer assigns stable `attachment:N` and `link:N` IDs. An inventory entry records kind, display name or URL, media type when known, and an optional frozen snapshot. The newest message and thread remain separate sources. A source is not cited until its text has actually been read. Binary attachment bytes and source content are not placed in a model prompt merely because they are present in an email. URLs appearing in the email body remain visible to the model, including any query string; private tokens should be removed from evaluation fixtures before a model call.

For evaluation cases E01-E10, the existing `external_sources` text is the frozen content. Link examples under `example.org` are identifiers for those snapshots, not live fetch targets. Snapshot text and its hash make the full-content run repeatable. The current body-only run remains the control condition.

## Bounded reading workflow

1. Parse the newest message, target recipient, prior thread, and external inventory. The CLI announces the message and asks before sending it to the model. An inventory preview remains to be added.
2. Run a body-and-thread first pass. The current prototype reads every inventoried source when there are at most two; more than two yields `needs_review`. Source selection based on the first result remains to be implemented.
3. For local attachments, support UTF-8 and declared-character-set text, CSV, HTML converted to visible text, and text-based PDF. Reject encrypted PDFs, image-only PDFs, unsupported formats, malformed content, or material above configured byte and text limits with a concrete review reason. The current prototype records the source ID and content hash; PDF page-level provenance remains to be added.
4. For links, prefer an operator-provided frozen snapshot. Optional live retrieval requires an explicit domain allowlist and a separate user confirmation. Accept HTTPS only; reject embedded credentials, IP literals, loopback and private destinations, and unapproved redirects. Recheck every redirect against the allowlist. Use strict time, redirect, byte, and extracted-character caps; do not send cookies or authentication headers or execute JavaScript. If a page requires login or dynamic rendering, route to review. The current prototype records the URL and content hash; retrieval time and content type should be recorded before a release claim. The live page may change, so it is not the frozen evaluation source.
5. Run at most one more model pass with the selected source text clearly delimited as untrusted data. The second pass may cite only source IDs actually read. A failed read, missing decisive content, or unsupported source remains `needs_review`.
6. Validate result shape, exact evidence spans, deadline syntax, and action limit. Ownership and deadline meaning are guided by the prompt and need separate semantic review. Show the final proposal and trace to the user. No external write follows automatically.

Initial limits are two external sources, 2 MiB per file or response, 20,000 extracted characters per source, two redirects, and ten seconds per live request. These are explicit configuration defaults, not guarantees against every hostile page. In particular, live fetch behavior needs network-level tests before claiming resistance to DNS rebinding or redirect attacks.

## Questions, punctuation, and empty messages

A question is classified by the response it asks of the target, not by the question mark. "Do you have an updated chart that I could send?" asks the target to report availability; it does not authorize inventing a task to send the chart. "Could you send the chart?" requests delivery. When the intended next step cannot be distinguished from the newest message and available context, return `needs_review`. The action type makes `answer_question` visible in the output and evaluation.

Evidence alignment may repair whitespace and a missing period in a known English abbreviation when the corresponding source span is unique. It must return the exact original span after alignment. It must not silently remove a negation, change a question mark, or use semantic similarity to create a quote. Model action wording is still reviewed for meaning independently of exact evidence matching.

An empty newest-message body is an abnormal input. A subject or old quoted thread alone does not justify a definitive `no_action`; the result is `needs_review` with an explanation. The v1.5 run stays unchanged for comparison.

## Evaluation and release gates

- Keep gold v1.5 and all historical run files unchanged. The first v2 comparison uses the same 50 cases in body-only and frozen full-content modes, with 15 no-action, 15 explicit-action, 10 context, and 10 external-content cases reported separately.
- Add development cases for real `.eml` attachments, unsupported binary content, allowlisted and blocked URLs, prompt injection, ambiguous question wording, and multiple actions. Do not silently add them to the frozen 50-case denominator.
- A16 and C13 now have separately validated candidate tasks in `evaluation/multi_action_draft.jsonl`. Both are marked `pending_owner`. A16 proposes two final tasks; C13 remains a review case because MailEx lacks the attached material. These are visible in the review UI but excluded from correctness scores until owner adjudication. A new approved multi-action gold revision must represent all independently required tasks before multi-action precision or recall is claimed. Status-only v1.5 metrics cannot measure completeness of an `actions` array.
- Record source IDs read, source hashes, read failures, model calls, tokens, latency, and estimated cost for both passes. Compare safe abstention with full-content correctness; do not count an unread-source abstention as a full-content success. The evaluation runner supports both v1 and v2 schemas; v2 scores only established external-case status and action-count references, while A16/C13 drafts remain unscored.
- Integration tests cover one attachment, one snapshot link, a denied live link, an empty newest body, abbreviation-dot alignment, the A03 availability question, and two independent actions. Human review remains necessary for action wording and evidence support.
