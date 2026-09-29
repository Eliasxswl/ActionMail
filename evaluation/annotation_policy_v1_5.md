# ActionMail Evaluation Annotation Policy

Version: 1.5. The v1.0 through v1.4 policies and manifests are preserved as separate snapshots. Existing runs retain their original labels; new runs use this revision.

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
- Use `deadline_kind`: `none`, `exact`, `relative_resolvable`, `relative_unresolvable`, or `vague`. An exact source date is `exact`. A relative date such as "tomorrow" is `relative_resolvable` only when the email has a trustworthy received timestamp and timezone; record the resolved ISO date or datetime as `deadline`. MailEx raw threads do not provide that anchor, so their relative dates remain unresolved and are excluded from deadline-field accuracy. Vague urgency such as "as soon as possible" is not an exact deadline.
- For an action, record at least one verbatim quote and its source ID. Quotes must be substrings of the body, subject, an included thread message, or a saved external snapshot. A quote supports the decision; it need not contain every detail in the action paraphrase.
- Annotate from the source before seeing a model prediction. MailEx event labels are not ActionMail gold labels.

## Case selection and reporting

The frozen set contains 50 cases: 15 no-action, 15 explicit-action, 10 context-dependent, and 10 authored external-content cases (five attachment, five link). This is a deliberately stratified challenge set, not an estimate of natural inbox prevalence. The MailEx cases reference local raw-thread files and record their file hashes; the authored cases include fixed text snapshots. Report category denominators, status confusion counts, correct no-action decisions, correct body-only abstentions, and separate action/deadline/evidence checks. Semantic correctness of action wording and evidence support requires human adjudication; do not infer it from string equality alone.

The category `explicit_action` means the newest message contains an explicit request. It does not guarantee that the one-action output can safely resolve the request; unclear ownership, conflicting instructions, and multiple independent tasks receive `needs_review`.

Gold v1.5 has 22 `action`, 20 `no_action`, and 8 `needs_review` labels. It replaces nine repetitive raw explicit-action cases (A02, A04, A05, A07, A10, A12, A13, A14, A15) with five distinct review cases (A16-A20), two body-only exact-deadline cases (A21-A22), and two relative-deadline cases with received timestamps (A23-A24). It also replaces C05 with MailEx case C13, which contains two independent requests and unavailable attached material. The replaced cases remain in the v1.4 snapshot. The current set has 31 distinct MailEx raw-thread cases and 19 authored cases. The deadline-kind counts are 37 `none`, 8 `exact`, 2 `relative_resolvable`, 1 `relative_unresolvable`, and 2 `vague`. These are intentionally sampled challenge counts, not inbox prevalence or a requirement for equal status counts.

The 19 authored cases and initial gold labels were drafted with Codex assistance for this project. The project owner has reviewed all 50 case labels. Any correction after a model run must create a new manifest version and a new run; earlier result files remain unchanged.

## Owner adjudication and deferred improvements

The project owner reviewed all 50 current cases and accepted the v1.5 gold labels on 30 September 2026. Three initial objections were resolved without changing the frozen labels:

- N11: the confirmed appointment is useful calendar information, but the newest message does not request a new task from the target. Future work could identify calendar candidates separately and explain this distinction.
- A09: "today" is a relative deadline phrase, but the raw email has no trustworthy received timestamp. The action remains `action`, `deadline_kind` remains `relative_unresolvable`, and the ISO deadline remains null. Future output could preserve the original phrase and explain why it was not normalized.
- A16: two independent tasks exceed the MVP's one-action output contract, so `needs_review` remains appropriate. Future versions could return multiple actions with separate evidence and deadlines.

These are scope and explanation improvements, not corrections to the v1.5 gold. The owner's review notes are saved separately from evaluation predictions and scores.
