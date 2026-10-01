# PE6201 report writing guide

Delivery clarification, 2 October 2026: the owner selected CLI as the necessary foundation; the GUI is an optional evaluation-review aid. The [CLI guide](cli_guide.md) separates offline scripted engineering demonstrations, saved real-model experiment inspection and new authorized inference. Do not claim that the instructor requires a frontend or that UiPath integration has been implemented.

Updated 1 October 2026. This is a writing guide, not the final report. Write the final analysis in the first person as an individual project. Keep implemented, measured and proposed work distinct. AI evaluation evidence remains v2.0. V3 now has a local persistent review UI, ICS export and Google interface adapters verified with synthetic responses, not real-account integration. See [v3 demonstration](v3_demo.md) for the reproducible offline path and [integration limits](google_integrations.md). Do not report the scripted demo as new model accuracy or live connectivity.

## Source authority and submission requirements

Original course documents are retained locally in [course/](course/README.md). They are not redistributed in Git. Refer to the exact named files/pages below; do not cite a development memo as though it were the instructor's original message.

| Source | Verified requirement or instruction |
| --- | --- |
| `PE6201_Assessment_Timeline.pdf`, p.1 | Individual end-of-course project, 44% of the course grade. Submit problem statement, business and technical trade-off analysis capped at 1,200 words, working code in GitHub, and a recorded video presentation/demo. Submit to NTULearn unless a brief says otherwise. |
| `PE6201_Project_Proposal_Watchouts (1).pdf`, pp.1–3 | Project rubric weights: problem/significance 15%, trade-offs 25%, implementation/code 35%, demonstration/communication 25%. Name a baseline, dataset and measured target; own/rent by layer; costs, limitations and implemented mitigations; another person should be able to run the repository. Low-code is optional. |
| `PE6201_Project_Problem_Statement_Template (1).docx` | Mandatory formative problem-statement milestone; approximately one page; seeds project criteria 1 and 2. It calls smallest first version optional, but later Watchouts explicitly says required. |
| Submitted `PE6201_Project_Problem_Statement_ZHANGPEIQ.pdf`, pp.1–3 | Defines workplace-action extraction, threads/external context, user confirmation, rented model, proposed email OAuth and initially UiPath. This is the student's initial plan, not proof these features were delivered. |
| Owner-confirmed session / archived restart brief | Instructor extended the deadline to 4 October; project-specific feedback asked for 50 cases/four category counts, authored attachment/link count and resolution of the UiPath-versus-own-orchestration contradiction. The original feedback message is not present among local course documents. Label this as owner-reported feedback. |

The timeline's old final date is 20 September, 23:59 SGT. Use the owner-reported 4 October extension for planning and check the latest announcement for exact final cutoff/packaging. Full Rubric 2 wording, video duration, whether references/appendices count in 1,200 words, and final ZIP naming were not located. Do not invent them. Three notebooks are an A1 requirement, not an end-of-course requirement. The report, code and video must describe the same final version.

## A workable 1,200-word budget

| Section | Suggested words | What to substantiate |
| --- | ---: | --- |
| Problem, target user and success criterion | 140 | One office-worker persona; risk of missing requested work; specific intended use |
| Technology choice and business/technical trade-offs | 300 | Rules versus rented model; selective tool reading; own/rent; Python versus initial UiPath plan |
| Implemented workflow and safeguards | 180 | Recipient-aware proposals, evidence gate, review and bounded repair; external effects only if implemented |
| Data, evaluation and measured findings | 280 | Base/supplement counts, real/authored origins, baseline and limitations of 60/60 |
| Cost, risk, limitations and next steps | 180 | Actual model spend, repair/read trade-offs, silent errors, confirmation and v3 status |
| Headroom for captions/transitions | 120 | Preserve the cap; do not assume tables or references are exempt |

This allocation is a writing recommendation, not an instructor format. Keep a total word count and trim generic AI background. Report decisions and evidence, not a development diary or a list of libraries.

## Connect the original plan to the delivered system

The original proposal selected foundation-model interpretation for complete email context, not isolated sentence classification. The delivered system keeps that focus and owns normalization, bounded source selection, evidence validation, review and evaluation. It rents `openai/gpt-6-luna` through OpenRouter; pypdf and the Python standard library handle bounded parsing, with DOCX/XLSX OOXML readers. Explain why commodity services are rented and why recipient/currentness/evidence policies remain owned.

Initial UiPath and Gmail/calendar plans were deferred while building a reproducible local Python core. The instructor says low-code is optional and Python API calls are code, not low-code. Explain the decision in terms of reproducibility, traceability and scope. Do not claim UiPath was tried without evidence. V3 now supplies a local application and Gmail/Calendar adapters using official contracts and authored fake responses; real OAuth/provider connectivity is deferred by owner decision. State the demonstrated offline behavior and exact commit, and keep live integration claims pending until a real smoke test.

Reason about alternatives: a keyword rule is cheap and inspectable but misses ownership/thread/external context; one model call is sufficient for short messages; attachments/main-content pointers justify additional bounded calls; reading irrelevant content adds cost and distracts. No vector database, training or unbounded agent framework was needed for the current task. Present the bounded workflow accurately, rather than calling every API invocation an autonomous agent.

## Evidence map for the report author

| Claim | Where to verify | Defensible wording |
| --- | --- | --- |
| Recipient-specific tasks with reason and evidence | `src/actionmail/workflow/multi_pipeline.py`, `docs/architecture.md` | Structured proposals for a named target, with original supplied quotes |
| Base 50, four scenario categories | `evaluation/cases.jsonl`, archived v1.5 policy | 15 no-action, 15 explicit-action, ten context, ten authored external challenges |
| Ten approved v2 supplements | `evaluation/supplement_v2_approved.jsonl`, active registry | 60-case development/regression suite, 34 real-derived and 26 authored inputs overall |
| Deterministic baseline | `backup/v1.5/results/evaluation/rules-gold-v1-5-20260929/summary.json` | 26/50 status match, precision 11/18, recall 11/22 under v1.5 labels |
| Earlier rented-model baseline | `backup/v1.5/results/evaluation/20260929T163325Z-a6e361d8/summary.json` | 37/50 status match, precision 15/16, recall 15/22; external contents unread |
| Latest v2 results | `results/evaluation/v2-regression-repair-20261001/summary.json`, `inspection.json` | 60/60 accepted status/count matches; original-text provenance checked; semantic review separate |
| A16/C11 reference amendments | `evaluation/v2_reference_overrides.json` and archived owner adjudication | Separately disclosed scope/ownership amendments; historical scores not overwritten |
| Repair behavior | Saved C12/S02 rows, `workflow/repair.py` | Two strict correction calls; both original and corrected responses retained |
| Hostile/unreadable content | Saved S08/S09 rows and offline tests | Correct handling of these fixtures; not universal prompt-injection resistance |
| Cost and latency | Saved usage/prices and `docs/evaluation.md` | USD 0.018384 estimated model spend, 78 calls, median summed model-call latency 3.48 s/email |
| V3 application | `docs/v3_demo.md`, `docs/google_integrations.md` | Persistent local review/ICS and Google adapters demonstrated offline with synthetic responses; real-account connectivity unverified |

The rule and v1.5 model share a frozen 50-case reference contract. An always-majority baseline on that set is 22/50 (44%). V2 uses more context, multi-action capacity and amendments, so comparisons across versions are developmental, not a controlled proof that any one change caused the improvement. Do not invent a new same-contract rule-vs-v2 experiment.

## Explain 60/60 carefully

The actual latest predictions are 28 action, 23 no-action, nine review. Single stored gold labels are 27 action, 23 no-action, ten review. Literal status agreement is 59/60; C11's action is an explicitly accepted alternative, producing the reported 60/60 accepted match. A16's two actions are separately amended, not silently relabeled. State these choices near the result, not buried after a perfect-accuracy headline.

All final quotes matched original registered text. That establishes provenance, not task completeness or faithful interpretation. The independent 23/23 deadline comparison includes null fields and cannot be called 23 successful date extractions. Nine reviews are 15% of cases; S08 is an intentionally malformed workbook, and its recorded failure is expected. The latest raw result and human assessment fields remain separate; no new individual owner Pass values have been fabricated.

The suite was reused during development and prompt tuning, including a formerly failing full run and targeted checks. It is not the untouched held-out set promised in the initial proposal. Be explicit about that limitation and propose independent future validation; the owner has deferred new evaluation for now. The 26 authored inputs include ten very short external snapshot challenges. S03 uses a genuine exported parent/PDF, not native RFC email. Do not generalize these counts to natural inbox prevalence or production attachment/security performance.

## Business analysis and responsible-use argument

Use the observed batch cost divided by 60 (USD 0.0003064/email) as a measured model-cost illustration, with its benchmark/provider/date assumptions. It excludes engineering, OAuth deployment, storage, hosting and user review effort. Record call/time totals separately. Avoid unsupported “hours saved” or business ROI claims. The proposal's “over 100 emails per day” statement needs a credible external source if reused; otherwise frame the persona without that statistic.

| Risk / trade-off | Delivered mitigation and remaining limit |
| --- | --- |
| Missed or overstated obligation | Named target/newest-message policy, reason and source review; exact quotes cannot independently detect every semantic omission |
| Altered amount or unsupported evidence | Strict original-text gate, diagnostic candidates and at most one revalidated correction; no fuzzy auto-approval |
| Irrelevant/hostile attachment | Inventory-bound selective reading and untrusted-content prompts; S09 is one fixture, not a complete security assessment |
| Unsupported or damaged required content | Explicit review, archive/size/coverage limits; S08 demonstrates refusal |
| False deadline / timezone | Explicit resolvable anchor policy and null when unknown; independent semantic deadline validation remains future work |
| Private mail leaving device | Public benchmark inputs and explicit submission choices currently; real-mail v3 requires clear data transmission consent, minimal scope and local private records |
| Duplicate/unapproved calendar write | No writes in v2; v3 implements preview, explicit final confirmation, stable operation ID and unknown-outcome reconciliation, verified offline only |

Tie each risk to implemented code or an explicitly future control. Do not use a disclaimer as a substitute for a safeguard. The teacher names governance/security frameworks as possible precise references; do not claim certification or compliance merely by mentioning them. External links/licences and provider requirements should be checked at report submission when making current factual claims.

## Data, attribution and reproducibility

Name [MailEx's paper](https://aclanthology.org/2023.emnlp-main.801/) and [source repository](https://github.com/salokr/Email-Event-Extraction); distinguish its event-extraction task from this project's own recipient/action labels. State actual selected counts rather than the downloaded corpus count. Record the Enron export parent/PDF relationship and original hashes. Source PDFs/emails are not interchangeable with invented missing attachments. No received time is fabricated for raw MailEx messages; authored test timestamps are labelled authored.

Disclose Codex assistance in code, authored fixtures and draft labels, and the owner's label/interpretation review. Historical generator scripts are committed under `backup/v2.0/code/tools`; the pre-organization checkpoint `282908e` preserves their original runnable paths. Real downloads are local-only; the repository supplies authored inputs, dependencies, verification commands and explicit corpus-path requirements. Check redistribution permissions before adding original corpus files to public Git. Do not claim the full 60-case validation needs no separate data download.

## Video and final hand-in checklist

Show one named-recipient email → proposed task or clear review → exact original evidence. Demonstrate an attachment-dependent case and an unreadable/ambiguous case. Show S02's rejected initial quote and one successful correction as reliability evidence. If v3 runs, demonstrate actual mail selection and a separate calendar preview/confirmation/write, including the provider result; if only ICS works, show ICS and say so. Mention the limits aloud and keep raw JSON behind diagnostics.

Before submission: report ≤1,200 words; problem statement included; GitHub branch/commit and install commands match the video; keys/private content excluded; denominators and reference amendments disclosed; real/authored counts and baseline named; reported numbers match saved files; code works from a clean checkout with documented data setup; calendar/mailbox claims backed by real demonstrations; references and AI assistance acknowledged. Confirm video length, final upload packaging and extended deadline cutoff from the latest course instructions rather than inventing them.
