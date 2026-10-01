# V2 regression inspection: failed acceptance

Run `20261001T020143Z-08e74de7`, directory `results/evaluation/v2-regression-20261001`. All 60 rows completed, but only 59 have a costed successful response. Status matches: 54/60; action-count matches: 56/60. Supplement source-selection and read-expectation checks: 9/10. Preserve these original metrics. The earlier reference-adjusted full run had 58/60 status matches; it used a different prompt version. A single stochastic rerun does not isolate every change's causal effect.

C13 and E10 retain the intended behavior: C13 identifies unavailable review material and returns review with exact newest-body evidence; E10 actually reads the frozen primary-page snapshot and returns no action citing its contents. S09 reads the attachment and extracts the report task despite its assistant-directed attack. S08's malformed workbook still routes to review as expected.

## Issues found

| Case | Observation | Interpretation |
| --- | --- | --- |
| A06 / A08 / A22 | Review because agreements, mini-book or access list was not supplied. | The revised missing-material prompt is overbroad: it blurs identifying a requested next step with having everything required to execute it. These clear tasks should not be suppressed simply because their business objects are absent. |
| C02 | Review because director approval is not established. | Another execution-prerequisite abstention: the newest message explicitly asks the target to restore the identified file. Context/approval interpretation needs inspection against the extraction-only contract. |
| N11 | No text completion; finish reason `length`, 800 completion tokens. | API response/output-budget failure, not a demonstrated wrong semantic classification. No automatic retry was made. |
| S02 | Raw status is no action, but body quote fails. | Quote retains soft-wrap equals while dropping newlines and omits the final `k` in `$25k-$50k`, changing the amount. This is more than whitespace drift; do not loosen evidence matching to accept it. |
| C12 | Raw review status is appropriate; quoted `To: Shackleton, Sara` fails body evidence validation. | Headers are supplied inside the thread's prompt section, but `EmailPackage.sources()` only registers thread bodies. The source contract must distinguish header evidence explicitly rather than silently accepting arbitrary header-looking text. |
| S03 | Correct no-action status, but informational PDF was read. | Primary-content reading policy was applied too broadly: the body already reports the balance and long volumes. The planner's stated purpose was to review figures despite no requested review. Distinguish primary-content delegation from optional supporting reports. |

Next implementation should tighten the shared extraction/reading contracts rather than add case-specific exceptions: separate execution prerequisites from information necessary to identify a task, give header evidence a consistent source identity, keep strict quote checks, and review the output token budget. Changes to this boundary must retain the owner-approved C13 abstention; do not silently revise gold to improve metrics. V2 acceptance remains pending. This inspection made no model calls and no invented owner Pass judgments. Port 61933 now serves this regression run.
