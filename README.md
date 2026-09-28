# ActionMail

| Item | Value |
| --- | --- |
| Current version | v1.0 (MVP; live OpenRouter path verified on one sample) |
| First runnable MVP | v1.0 |
| Project type | Individual PE6201 end-of-course project |

ActionMail reviews a work email for an action directed at the target recipient. It proposes the action, an explicit deadline when one exists, and source evidence. The user reviews the proposal before any calendar output is produced.

The v1.0 application is runnable locally. Its integration path is covered by tests, and the sample email completed a live OpenRouter call with `openai/gpt-6-luna`. This single successful run verifies the end-to-end path, not extraction accuracy. No measured evaluation results are claimed yet.

## Run the MVP

Use Python 3.10 or newer. Install the package from this repository with `python -m pip install -e .`, then set `OPENROUTER_API_KEY` and `ACTIONMAIL_MODEL` in your local environment. Do not put the key in a repository file. For example, in PowerShell:

```powershell
$env:OPENROUTER_API_KEY = "your-key"
$env:ACTIONMAIL_MODEL = "openai/gpt-6-luna"
actionmail examples/sample_email.json
```

Use an exact model ID from the [OpenRouter model catalog](https://openrouter.ai/models) if you choose another model.

The CLI asks before sending email content to OpenRouter and asks you to review the returned result. For a local `.eml` file, run `actionmail path/to/message.eml --recipient you@example.com`. The default API endpoint is OpenRouter; `--api-url` and `--model` can override it. The MVP does not write to a calendar or mailbox.

## Technology decision

The main extractor will use **one LLM**. A deterministic rule matcher will provide a non-AI baseline. A **bounded tool-use workflow** will read an attachment or linked page only when the initial email does not provide enough evidence. This is the limited agent capability planned for later versions; it is not an open-ended autonomous agent. A separately trained ML classifier is outside the initial scope because the available event labels do not directly match the recipient-specific action task.

Python code will own the orchestration, validation, and evaluation. UiPath is not a runtime dependency. The final report will explain this change from the formative problem statement.

## Version plan

| Version | Status | Scope |
| --- | --- | --- |
| v0.1 | Completed | Architecture and documented decisions. |
| v1.0 | Current MVP | One local `.eml` or JSON email input; one LLM decision; structured action/deadline/evidence output; deterministic evidence checks; user review. |
| v1.1 | Planned | Rule baseline, frozen 50-case evaluation, per-case outcomes, token usage, latency, and cost. |
| v1.2 | Planned | Bounded reading of supported attachments and linked-page snapshots, plus a body-only comparison on challenge cases. |

These labels describe scope, not a claim that a planned version has shipped. Update the **Current version** line and this table whenever a milestone is completed or its scope changes.

## Language convention

Repository documents, code comments, CLI messages, prompts, structured result fields, and demonstration output are in English unless the project owner explicitly requests another language. Source emails retain their original language.

## Intended boundaries

- Run locally and on demand. No inbox monitoring or browser plugin is required for the core evaluation.
- Process one target recipient and at most one actionable item automatically. Ambiguous or multiple actions require human review.
- Treat email, attachments, and linked pages as untrusted data.
- Never send a reply, alter the mailbox, or write to a calendar without an explicit user confirmation. The MVP only previews the result.
- Keep live Gmail OAuth and direct calendar integration outside the critical path. A future mail adapter can use the same normalized email contract.

## Documentation

- [Architecture and package boundaries](docs/architecture.md)

## Reproducibility status

The v1.0 command-line path is implemented, covered by integration tests, and verified once with a live OpenRouter call on the sample email. Evaluation data sources, annotation rules, and measured results will be added with v1.1. Do not treat the single live run or planned metrics as measured accuracy.
