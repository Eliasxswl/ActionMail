# ActionMail Evaluation Annotation Policy

Version: 1.4. The v1.0 through v1.3 policies and manifests are preserved as separate snapshots. Existing runs retain their original labels; new runs use this revision.

## Unit and recipient

One case is one newest message addressed to a named target recipient. Explicit-action and no-action cases show only that message. Context-dependent cases also show the older messages in the same MailEx thread. The newest message determines whether an obligation is currently directed at the target. Older requests to another person, completed work, and the sender's own plans do not create a new target-recipient action.

## Gold decision

- `action`: exactly one request, obligation, or question requires the target to do something. Write a short English action with an observable verb. An action may have no deadline.
- `no_action`: the target receives information, a thanks, a completed-work update, or someone else's task, without a current request to the target.
- `needs_review`: the target or obligation is materially uncertain, or there are multiple distinct actions that the one-action output cannot represent. Record the specific ambiguity.
- A question requesting an answer counts as an action. An optional offer by the sender does not.
- Interpret the newest message from the target recipient's perspective. A current statement that the sender or group is waiting to hear from a named target recipient counts as a follow-up action when the thread identifies the pending matter. Describe the response or update without inventing the answer. A pending matter with no identifiable recipient or subject remains `needs_review`.
- A request to multiple recipients can still be an `action` for the target. Judge whether the target can take the stated step from their perspective; do not require exclusive ownership. Use `needs_review` only when the target's role or the requested step is materially unclear.
- For authored attachment and link cases, read the saved external snapshot when setting the gold decision. In the body-only run, unread external content should produce `needs_review`; record this safe abstention separately from full-content correctness.

## Deadline and evidence

- `deadline` is an ISO 8601 date or timezone-aware datetime only if the source explicitly supplies a resolvable deadline. A meeting date, past date, or document effective date is not automatically an action deadline.
- Use `deadline_kind`: `none`, `exact`, `relative_unresolvable`, or `vague`. Resolve relative dates such as "today" or "tomorrow" only when a trustworthy received timestamp and timezone are available. MailEx raw threads do not provide one, so their relative dates are excluded from exact-deadline accuracy. Vague urgency such as "as soon as possible" is not an exact deadline.
- For an action, record at least one verbatim quote and its source ID. Quotes must be substrings of the body, subject, an included thread message, or a saved external snapshot. A quote supports the decision; it need not contain every detail in the action paraphrase.
- Annotate from the source before seeing a model prediction. MailEx event labels are not ActionMail gold labels.

## Case selection and reporting

The frozen set contains 50 cases: 15 no-action, 15 explicit-action, 10 context-dependent, and 10 authored external-content cases (five attachment, five link). This is a deliberately stratified challenge set, not an estimate of natural inbox prevalence. The MailEx cases reference local raw-thread files and record their file hashes; the authored cases include fixed text snapshots. Report category denominators, status confusion counts, correct no-action decisions, correct body-only abstentions, and separate action/deadline/evidence checks. Semantic correctness of action wording and evidence support requires human adjudication; do not infer it from string equality alone.

Gold v1.4 replaces two straightforward context no-action cases with two MailEx `needs_review` cases: C11 has an unresolved addressee for a new question; C12 has an urgent subject, no newest-message body, and an unavailable amendment attachment. They are provisional reference judgments for owner review. Their source files are distinct from the other current cases. C01 and C07 remain available in the v1.3 snapshot.

The 10 synthetic attachment/link cases and initial gold labels were drafted with Codex assistance for this project. The project owner should review the case wording and labels before treating them as final academic evidence. Any correction after a model run must create a new manifest version and a new run; earlier result files remain unchanged.
