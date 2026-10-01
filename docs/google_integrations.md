# Google integration contracts and offline verification

Checked against Google documentation on 1 October 2026. Owner decision: Gmail and Google Calendar only, interface implementation first, real-account testing deferred. No Google credentials, real mail, paid model calls or real calendar events were used in this slice.

## Official declarations

Both services provide REST documentation and machine-readable Discovery specifications:

- [Gmail reference](https://developers.google.com/workspace/gmail/api/reference/rest), [Gmail v1 Discovery](https://gmail.googleapis.com/$discovery/rest?version=v1).
- [Calendar reference](https://developers.google.com/workspace/calendar/api/v3/reference), [Calendar v3 Discovery](https://www.googleapis.com/discovery/v1/apis/calendar/v3/rest).
- [Desktop OAuth](https://developers.google.com/identity/protocols/oauth2/native-app), [Gmail quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python), [Calendar scopes](https://developers.google.com/workspace/calendar/api/auth).

The application uses an injectable REST transport and Google's optional Python OAuth libraries. It does not require the full generated API client to run the offline demo.

| Operation | Interface used |
| --- | --- |
| Actual account/target | `GET /gmail/v1/users/me/profile`, `emailAddress` |
| Inbox summaries | `GET /gmail/v1/users/me/messages`, then metadata-only message retrieval |
| Selected message | `GET /gmail/v1/users/me/messages/{id}?format=full` |
| Selected thread | `GET /gmail/v1/users/me/threads/{id}?format=full` |
| Detached MIME bytes | `GET /gmail/v1/users/me/messages/{id}/attachments/{attachmentId}` |
| Owned destinations | `GET /calendar/v3/users/me/calendarList?minAccessRole=owner&maxResults=100` |
| Create item | `POST /calendar/v3/calendars/{calendarId}/events?sendUpdates=none` |
| Reconcile item | `GET /calendar/v3/calendars/{calendarId}/events/{stableEventId}` |

Gmail uses `gmail.readonly` and exposes no mailbox send/update/delete operation. Calendar separately requests `calendar.events.owned` and `calendar.calendarlist.readonly`. The first integration requires the calendar primary account to match Gmail, and supports calendars owned by that account. Calendar listing stops at 100 entries; a known owned ID can also be entered manually.

Gmail `internalDate` supplies the received anchor, converted to the explicitly configured application timezone (default `Asia/Singapore`). The authored Date header does not override it. Thread messages are sorted by anchor; replies later than the selected message are excluded. Historical headers and attachment inventories retain distinct original-source IDs. MIME bytes, HTML/plain text and detached attachment content reach the existing ingestion/reading core. Lists fetch metadata only, while selection fetches a bounded thread and its declared attachment bytes. The cap is 50 thread messages and 20 MiB of combined body/attachment content, with visible failure on overflow.

Calendar uses `date` and exclusive end for all-day items, or offset-bearing `dateTime` and IANA `timeZone`. Dates, order and timezone offsets are checked. No attendees, invitations or conference details are added. Transparent availability keeps deadline items from automatically reserving busy time. See [event creation](https://developers.google.com/workspace/calendar/api/guides/create-events) and [events.insert](https://developers.google.com/workspace/calendar/api/v3/reference/events/insert).

## Test-data provenance and limits

No ready-to-use official inbox dataset or account-free sandbox was found in the documentation reviewed. Google's client library documents [mock HTTP responses](https://googleapis.github.io/google-api-python-client/docs/mocks.html); these test application interactions without proving real connectivity.

[demo_mail.json](../src/actionmail/integrations/demo_mail.json) contains authored synthetic Google-shaped responses: an attachment-dependent task, an informational message, a missing-workbook review and historical thread context. It is not Google-provided data, a captured inbox, or an AI accuracy dataset. Fixed `DemoModel` replies pass through the unchanged v2 reading/validation workflow. Other imported messages receive an explicitly labelled simulation review, not model inference. These fixtures are outside the active frozen 60-case registry.

Engineering checks cover target/time/MIME/thread normalization, attachment preservation, timezone boundaries, OAuth refresh and denied scopes through fakes, review/edit/rejection persistence, unchanged-message deduplication, confirmation invalidation, cancellation, duplicate clicks, event-ID conflict and timeout/crash reconciliation. Existing evaluation sources, hashes, model replies and owner judgments remain untouched.

## Local storage and effects

SQLite stores mail, private content hashes, analysis, reviewed proposals, drafts and outcome history independently of evaluation records. Windows default storage is `%LOCALAPPDATA%/ActionMail`. This is plaintext local storage protected by user-account permissions, not encrypted credential storage. OAuth tokens are separate per feature. Disconnect removes local credentials and disables the running feature while retaining saved mail/tasks; it does not revoke the Google grant. Revocation can be performed in Google Account settings.

Task acceptance does not authorize calendar writing. Each saved draft has a revision and operation key. Edits invalidate confirmation. The single application service serializes writes and saves `writing` before sending. A stable Google event ID and matching private operation property allow duplicate detection. Unknown transport/write outcomes and interrupted writes stay `unknown`; repeated clicks and restarts cannot resend. Reconciliation checks the existing event. A 404 stays unknown because it may be transient; unresolved or conflicting outcomes require manual resolution. Do not run two application processes against one store.

Confirmed ICS export uses stable UID, CRLF, text escaping, UTF-8-safe 75-octet folding and date/UTC fields. Export is recorded separately from an API write. The preview's destination is advisory for ICS: the importing calendar app selects the actual destination. The offline provider persists simulated events beside the demo store and labels every simulated outcome.

Actual OAuth authorization, real Gmail fetch, real Calendar creation and private-mail/model submission remain unverified. Organization policies, account permissions and live provider behavior must be checked later with owner approval. Do not claim production integration reliability from fake responses. A future smoke test should use one authored email and a selected test calendar, separate analysis-transmission consent and explicit final event confirmation; a new paid full benchmark is not required.
