# ActionMail v2.0 Design

Status: development, with partial implementation on `main`. The v1.5 branch and frozen v1.5 evaluation remain unchanged.

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
- Record source IDs read, source hashes, read failures, model calls, tokens, latency, and estimated cost for both passes. Compare safe abstention with full-content correctness; do not count an unread-source abstention as a full-content success. The current evaluation runner supports the v1 single-action result schema only.
- Integration tests cover one attachment, one snapshot link, a denied live link, an empty newest body, abbreviation-dot alignment, the A03 availability question, and two independent actions. Human review remains necessary for action wording and evidence support.
