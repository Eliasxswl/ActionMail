# V3 development demo and run guide

The package remains `3.0.0.dev0`, pending owner acceptance. A local application and Google adapters now run with offline engineering verification. Real accounts have not been tested.

Implementation commit: `857db1d` on `main`. The frozen `v2.0` branch and saved evaluation outputs are unchanged.

## Install and run

From the repository root, with Python 3.10 or newer:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e .
.venv/Scripts/python.exe -m actionmail.interfaces.app_server --no-browser
```

Open `http://127.0.0.1:61933/`. Offline mode makes no Google/model requests and needs no credentials. Default private storage is outside the repository. For an ignored local demo store:

```powershell
.venv/Scripts/python.exe -m actionmail.interfaces.app_server --store results/private/v3-demo.sqlite3 --no-browser
```

Only one service may use port 61933. Stop an existing project server only after checking its command line; the benchmark review UI can still be launched separately using its existing command. Never run both at once.

## Demonstration path

1. **Refresh mailbox** loads three artificial Gmail responses through the same adapter as the future real account.
2. Select **Project brief due**. Inspect `demo@example.com`, target, sender, To/Cc, received time and body.
3. **Analyze this message** runs the existing v2 workflow: plan the attachment read, extract its supplied bytes and validate the scripted task/evidence. This is not paid inference or measured AI accuracy.
4. Edit if needed, then **Accept / save edits**. Inspect **Accepted tasks**. Reload/restart to verify local persistence.
5. Open **Calendar draft / ICS export**. Inspect the all-day date, exclusive end, timezone, title, minimal context and exact destination. Unknown deadlines require user-supplied dates.
6. **Save preview**, then **Confirm these exact saved fields**. **Export ICS** produces a local file. **Simulate one Calendar write** records an artificial event ID; duplicate clicks/restart do not repeat the write. A field edit requires a new preview and confirmation.
7. Analyze **Weekly update** and **Missing workbook** for no-action and review reasons with original evidence. Rejected proposals cannot produce drafts and stay out of accepted tasks.

The browser walkthrough verifies selection, attachment-backed scripted analysis, task acceptance, preview/confirmation, confirmation invalidation after an edit, simulated write with event ID, page reload and keyboard opening of source mail. A 390-pixel viewport check found no horizontal overflow. Offline tests cover restart and failure behavior. No real-account demonstration or recorded final video exists yet. The assignment demo must label synthetic integrations unless a later owner-approved live check is completed.

EML upload preserves original bytes and requires the target address. Offline analysis is scripted only for the supplied examples; other imports remain for review. The existing CLI real-model sample remains available with separately authorized model use.

## Future live setup (not run during this development)

Follow [desktop OAuth guidance](https://developers.google.com/identity/protocols/oauth2/native-app). Enable Gmail and Calendar APIs in a Google Cloud project, configure the owner's test user and obtain a Desktop client JSON in private storage. Do not commit credentials.

```powershell
.venv/Scripts/python.exe -m pip install -e '.[google]'
.venv/Scripts/python.exe -m actionmail.integrations.auth connect gmail --client-file C:/private/google-desktop-client.json
# Calendar permission is separate and optional:
.venv/Scripts/python.exe -m actionmail.integrations.auth connect calendar --client-file C:/private/google-desktop-client.json
.venv/Scripts/python.exe -m actionmail.interfaces.app_server --gmail --calendar --no-browser
```

Without `--live-model`, Gmail mode still uses a visibly labelled scripted model and does not transmit private mail. Only after owner consent to paid/private-mail analysis, set `OPENROUTER_API_KEY` locally and add `--live-model`. Analyze submits the selected package through the original bounded workflow, not an entire inbox. Unchanged messages reuse saved analysis; failures differ from no action and can be explicitly retried.

Calendar OAuth must use the same account as Gmail. The primary-calendar identity is checked before real writes are enabled. Owned destinations can be listed and the concrete calendar ID appears in the final preview.

Disconnect in the UI, or use `python -m actionmail.integrations.auth disconnect gmail` / `disconnect calendar`. Reconnect via the explicit desktop command and restart. An embedded OAuth wizard and background mailbox monitoring are not implemented.

## Checks and reporting boundary

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -q
.venv/Scripts/python.exe -m actionmail.evaluation.cli --benchmark v2-60 --validate
.venv/Scripts/python.exe tools/check_repository.py
```

The original 68 regression tests and 24 new engineering checks pass (92 total). Active manifest/component checks and 3,166 archive hashes pass. No new paid model evaluation was run. V2 figures and caveats remain in [evaluation.md](evaluation.md). Integration contracts, synthetic data provenance and remaining limitations are in [google_integrations.md](google_integrations.md).
