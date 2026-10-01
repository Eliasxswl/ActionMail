# ActionMail v3.0 development handoff

## Delivery update — 2 October 2026

The owner clarified that CLI is a necessary foundation and GUI/TUI are optional. Running the core and evaluation without connecting accounts must remain possible. The current task is to assess UiPath integration for Gmail and Google Calendar, including authorization, full-path debugging, effort and a conditional build plan, before implementing it. Do not expand teacher-delivery documentation or migrate the system into UiPath. This clarification supersedes the earlier interpretation of CLI-first delivery.

`interfaces/workflow_cli.py` exposes the persistent application service offline: mailbox/fetch/import, list/show/analyze, review/tasks, draft/confirm/export and simulated write. `actionmail-workflow demo --output-dir NEW_DIRECTORY` runs three authored scenarios and saves JSON traces, SQLite records, ICS and one synthetic event despite two write requests. Model responses are scripted, not accuracy evidence. Existing extraction/evaluation commands remain the real-model experiment paths; saved v2 results can be inspected without new calls. No real accounts or new paid model runs were used. The owner requested removal of the separate teacher CLI guide.

Verification: 96 offline tests pass, including four CLI integration checks for persisted operations, review/confirmation gates, error output and overwrite refusal. The repository integrity check passes for 60 active cases and 3,166 archive hashes. Frozen evaluation results remain unchanged.

The owner confirmed access to Automation Cloud's Connections page. [UiPath integration assessment](uipath_assessment.md) recommends a 1–2 hour feasibility gate and estimates 10–18 focused hours for a thin-adapter implementation including debugging, conditional on permissions and callable schemas. No tenant discovery, SDK setup, mailbox reads, calendar writes or new inference were performed for the assessment.

## Implementation update — 1 October 2026

The owner selected Gmail + Google Calendar, authorized interface-based implementation and deferred real-account testing. The local persistent application, read-only Gmail adapter, separate desktop OAuth code, review UI, calendar preview/confirmation, ICS export and Calendar write/reconciliation adapter are now implemented. Offline verification uses explicitly synthetic Google responses and scripted model replies through the unchanged v2 core. No real accounts, paid model calls or calendar events were used. See [v3 run/demo guide](v3_demo.md) and [integration contracts](google_integrations.md). The roadmap below remains the original handoff context; its "not implemented" sections describe the starting state, not this update. Package version remains development-only until owner acceptance.

Updated 1 October 2026. Owner-approved priorities: **mail intake → end-to-end use → product UI → calendar integration**. Further model evaluation is deferred until the owner decides. Continue on `main`; `v2.0` is the frozen baseline branch. Do not develop v3 on the frozen branch.

Main package version is `3.0.0.dev0`; this marks development, not implemented v3 features. The frozen branch package version is `2.0.0`. Both the project metadata and runtime version agree.

## Start here

Read this file, [architecture.md](architecture.md), [evaluation.md](evaluation.md), [report_guide.md](report_guide.md), then the workflow and input domain. The authoritative current documents are these four plus the root README and active annotation policy. Backup is historical evidence, not another competing roadmap.

The owner asked to freeze the current code as v2.0 and prepare v3.0 for another agent. The v2 baseline has a passing full 60-case run, not a blind real-inbox evaluation. New per-output owner Pass judgments must not be invented. Latest run: `results/evaluation/v2-regression-repair-20261001`, ID `20261001T130907Z-23a9fe51`. Accepted status/count matches 60/60; all final quotes and coverage/source hashes independently checked. C12 and S02 used one correction each. S08's malformed workbook refusal is expected. Model bill estimate USD 0.018384, 78 calls. See evaluation.md for C11's accepted alternative and other caveats.

Before changes:

```powershell
git switch main
python -m pip install -e .
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -q
python -m actionmail.evaluation.cli --benchmark v2-60 --validate
python tools/check_repository.py
```

At handoff, 68 offline tests pass. The local bundled Python is `C:/Users/kiven/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`; use normal Python in another environment. The workspace is `E:/NTU Learn/PE6201/End_Course_project/ActionMail`. The sibling `../data` contains the original current corpus, excluded from Git. MailEx relative dates lack reliable received anchors; never fabricate them.

## Working rules

- Discuss with the owner in Chinese; repository documents, code comments and prompts stay English.
- Infer routine implementation choices and finish authorized work. Ask first about unresolved product/account choices, not each reversible refactor.
- Paid model runs need separate owner consent. Existing successful-run consent does not authorize a new batch or private-mail transmission.
- Never put API keys, OAuth credentials/tokens or private messages in Git or ordinary evaluation logs. Use environment configuration and local private storage.
- Use only one local service on port 61933. Verify process command line before replacing it; do not kill unrelated processes.
- Preserve the active manifest hashes, original result rows and review judgments. Do not tune case-ID-specific rules or “fix” gold to hide model failures.
- Keep the architecture small. One extraction core, one application service and thin provider adapters suffice; no second model, distributed agent framework or independent UI classifier.
- Development priorities are the four requested integrations. Do not expand model benchmarks, add providers or repeat paid full runs without the owner's later decision.

## Current capabilities and gaps

Implemented: local JSON/EML ingestion; target-aware body/thread/header interpretation; up to three independent actions; explicit deadline fields; unified reason/evidence; selective attachment/link reading; bounded PDF/DOCX/XLSX/text/HTML/CSV extraction; original-source provenance; long-input coverage and merging; one strict validation repair per email; usage/cost accounting; benchmark review/search/filter UI.

Not implemented: mailbox login/list/fetch, stored everyday action lists, an inbox product UI, calendar drafts/export/write, deduplication across mailbox refreshes, background monitoring or automatic email replies. The benchmark UI must not be presented as an inbox product. V1 compatibility code remains because CLI/tests and shared quote normalization depend on it. Refactor that shared helper only if needed, with regression checks; do not delete it as unused.

## Target user path

Connect or import mail → select a message → show the actual account/target and received time → user requests analysis → same v2 core proposes tasks with original sources → user accepts, edits or rejects a proposal → optional calendar draft → show exact destination/title/date/timezone → explicit confirmation → write once or export → show persistent outcome and source-mail link.

The calendar step is distinct from model analysis approval. Selecting a date or accepting a task does not silently authorize an event write. An action with no deadline must not get an invented meeting time. A date-only deadline can become a user-confirmed all-day item; null/ambiguous dates need user input or remain a task. No-action and needs-review results stay visible with their reason and evidence.

## Proposed small architecture

Retain `EmailPackage` and `MultiActionResult` as the core boundary. Add provider identifiers in the application record, not as model-owned action authority. Proposed modules (not yet implemented):

| Area | Boundary and data |
| --- | --- |
| `integrations/mail.py` | List lightweight message summaries; fetch one selected full message/thread and attachment bytes; normalize to existing ingestion/domain inputs |
| `integrations/auth.py` | Provider authorization, token refresh, logout and local credential handling |
| `application/service.py` | Orchestrate explicit analyze/review/draft/write operations using the same workflow |
| `application/store.py` | One local SQLite store for message identifiers/hashes, analysis records, reviewed proposals and calendar write outcomes |
| `integrations/calendar.py` | Preview a user-approved draft; create an event once; record provider ID and reconcile unknown write outcomes |
| `interfaces/app_server.py` and small static UI | Product mailbox list, message detail, analysis/review and calendar preview; keep benchmark review separate |

Use stable provider/account/message IDs plus a content hash to detect unchanged mail. Do not hash private content into public experiment logs. Store states explicitly: unread/ready/analyzing/analyzed/reviewed/draft/confirmed/written/failed/unknown. These can be minimal enum/status fields, not a generic workflow engine. Calendar idempotency uses a stable operation key and recorded provider event ID; a timeout after sending must be reconciled before any retry. Never create an event merely because a model returned action.

## Implementation sequence and completion gates

### 1. End-to-end local vertical slice

First add the application service and one local message import/list/detail path. Run the existing extraction workflow through it. Persist results, user edits and rejection. Use an offline scripted model for integration checks and keep the existing real sample runnable. Complete when a selected EML can become a reviewed task and survive server restart without the benchmark runner. This establishes the user path before OAuth adds failure modes.

Build the UI alongside this slice: one column, email first, result below, detail tabs for sources/history as needed. Show the beneficiary account beside the subject, not hidden in diagnostics. Task cards expose action, deadline or unknown, one reason and exact quotes. Loading/error/review states are explicit. The owner disliked fragmented panels and duplicate explanations; reuse one reason and keep raw JSON/repair records in a secondary diagnostic tab. Do not build a complex design system or overload the screen with internal fields.

### 2. One read-only mail provider

Default implementation proposal is Gmail, consistent with the original proposal, but confirm the actual account/provider and local authorization route before requiring credentials. If the owner needs another provider, implement that one first rather than both. Use an adapter contract so local import remains a fallback, not a separate analysis path.

Implement connect, list bounded messages, select/fetch, normalize target/From/To/Cc/Date/thread, retrieve selected attachment bytes, refresh connection and disconnect. Fetch body and inventory for the selected email rather than scanning the entire mailbox into model context. Thread order and newest-message identity must be tested. Preserve provider IDs and real received anchors; do not confuse authored test times with live times. Existing selectors can decide which supplied attachment contents matter; the mailbox adapter must not silently drop declared dependencies.

Gmail `gmail.readonly` is classified as restricted; public distribution can involve additional verification. See [official Gmail scopes](https://developers.google.com/workspace/gmail/api/auth/scopes) and [desktop OAuth guidance](https://developers.google.com/identity/protocols/oauth2/native-app). Start with the owner's test account/local authorization, with configuration instructions and visible disconnect. Do not promise production verification within the assignment deadline.

Gate: authorized account can list and fetch one email, current target and timestamp are correct, normalization reaches the existing workflow, denied/expired authorization has a usable error, and no mailbox write/send capability is exercised. Do not transmit real private mail to a model until the owner has authorized that use.

### 3. Product review workflow and reliability

Finish accepted/edit/rejected states and an everyday task list. Make it clear which account and recipient each analysis serves. Avoid duplicate analysis of unchanged messages unless explicitly requested. Reload the page without losing reviewed edits. A rejected proposal stays rejected and cannot be written. Changes to draft fields invalidate prior confirmation. Cap analysis calls and keep model failure distinguishable from no action.

Gate: local import and provider mail follow the same UI flow; keyboard use, narrow screens, source display and connection/error states work; private application records are separate from frozen evaluation evidence. The benchmark server remains usable on 61933 when launched in review mode. Reuse an existing simple Python/static UI approach unless a concrete requirement warrants a new framework.

### 4. Calendar draft, export and provider write

Implement calendar preview first, then a standards-compliant ICS fallback, then one provider adapter. Google Calendar is a proposed pairing with Gmail, not an already implemented integration. Verify current provider event/date/timezone/scope requirements against [official event creation](https://developers.google.com/workspace/calendar/api/guides/create-events) when coding. Request calendar permissions only when the user enables that feature.

Draft fields: title, description with minimal approved context/source reference, start/end or all-day date, timezone, destination calendar and stable operation key. Do not include attendees or send invitations by default. The UI must let the user correct missing times, reject drafts and explicitly approve the final destination and fields. Keep a deadline task distinct from an appointment; do not schedule busy time automatically just because an email has a due date.

Gate: one explicit confirmation creates exactly one test event; repeated clicks/restart do not duplicate it; cancellation creates none; permission denial and timeout-after-send are handled without blind retry; write outcome/provider ID is recorded. Local ICS export remains available if API authorization is blocked, but report it as export rather than successful API integration.

### 5. Release, documentation and demonstration

Run meaningful offline checks after each slice and the existing regression tests when core context/contracts change. The owner deferred further model evaluation; do not add or run a new benchmark as a release prerequisite on your own. Ask for a narrowly scoped live integration demonstration when accounts or writes are required. Update docs to describe what actually runs, bump the eventual released package to 3.0.0 only when the owner accepts that release, and preserve v2.0 unchanged.

The academic deadline is owner-reported 4 October 2026 (extension from the old timeline). Prioritize a reproducible local end-to-end demo before broader deployment. If provider authorization blocks progress, preserve the functioning import/draft/export path and name the exact unimplemented provider feature; do not advertise it as complete. Each milestone should be a small reviewable commit. Finish with install/run instructions, one recorded real demonstration path and a clear list of measured versus planned claims for the report author.

## Meaningful checks to add during v3

Use adapter fakes for OAuth denial/refresh, message MIME/thread/target normalization, attachment byte preservation and disconnect. Exercise service persistence/edit/reject, repeated analysis, draft confirmation invalidation, date-only/null/timezone handling, duplicate clicks, timeout-after-write reconciliation and no-write-before-confirmation. These are engineering tests, not a newly authorized model accuracy evaluation. One owner-approved real-account smoke test is enough to establish integration connectivity; do not claim broad production reliability from it.

## Archive and continuation

`backup/<version>/docs`, `code`, `evaluation`, `results/evaluation`, `data` separate history by type. Raw downloads and course originals are local-only; see [backup index](../backup/README.md) and [course source index](course/README.md). `backup/migration.json` lists original/destination paths and content hashes. Archived generators are historical source, not active commands: the pre-organization checkpoint `282908e` has their original paths for reproduction in a separate checkout. Six active EML fixtures retain their legacy source paths for frozen hash integrity. Do not move these without a reviewed path migration and preserved snapshot manifests.

The full v2 result is the only active saved run. Older failing/full/targeted runs are in backup with their raw replies, original scores, reference amendments and review records. They remain useful evidence for the report. An archive name such as challenge-v2.1 describes an old experiment, not a released v2.1 product. Continue v3 in main; push ordinary reviewed commits without force-pushing or altering the frozen branch.
