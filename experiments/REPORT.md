# Six-model benchmark and ablation report

Status: experiments were finalized on 2026-10-03 for report/demo delivery. Benchmark 360/360 and ablations 500/500 are complete; total charges were USD 3.224528503. Ablations are in section 11 and the 500 Codex semantic reviews in section 12. Exhaustive benchmark semantic review and forced JSON remain future work.

Updated 2026-10-03. The benchmark finished at 23:29 Singapore time on 2026-10-02: six models, sixty cases each, 360 separate model/case observations. Metrics/logs are in `results/model-benchmark/`. This analyzed existing logs without new calls or changes to measured business logic, prompts, parser or original scores.

## Conclusions and scope

Under this measured ActionMail workflow, OpenRouter routing and configuration, Luna offered the best operational value, Sol the same classification score, and Sonnet good usability. This does not establish superior GPT-family understanding over Google/GLM. Google losses mainly reflect format and shared cross-stage retries; GLM also faces reasoning-budget and routing effects.

No reasoning/parser branch selected by GPT/Gemini/Claude name was found; all sixty initial requests were byte-identical except model. Yet Luna was the development default, these cases were reused for tuning, and strict JSON plus one shared repair suited the measured GPT output habits. Equal prompts do not establish family neutrality or exclude implicit development adaptation. Earlier reporting understated this limit.

The main ablation selected **Luna + Sonnet**, representing low-cost usability and another usable family. Sol remains a same-family performance/price benchmark reference. Google/GLM need separate compatibility diagnosis; pipeline failure does not disqualify intrinsic ability. All 500 ablations and their semantic reviews are complete; the 360 benchmark outputs lack exhaustive semantic review.

## 1. What is measured

- Inputs: the same sixty development/regression cases, with 27 action, 23 no_action and ten needs_review labels; email context, external sources, actual attachments, long content and hostile/limit cases. This is not an independent blind test.
- Frozen conditions: Git c405d29; identical inputs, labels, attachments/page snapshots, recipients, prompts, schema, reading limits and scoring rules.
- Execution: six models rotated by case; resume filled only missing model/case observations. One formal trial per case cannot establish stability or statistical significance.
- Metrics: correct status is not correct task meaning; equal counts are not completeness; literal quotes are not semantic support. Independent human semantic ratings remain blank. The additional 500 ablation reviews explicitly identify Codex as AI reviewer.
- Action recall counts an answerable task diverted to review as a miss. Legitimate review and system-error fallback must be interpreted separately.

## 2. Status, speed and actual cost

Latency is local case wall time, including planning, extraction, merging and repair but excluding read-only billing queries; network/queues remain included. Fees are obtained generation bills for completed cases, not token-price estimates. Sonnet lacks one bill, so its row is a verified subtotal rather than complete actual cost.

| Model | Strict status match | Permitted status/count match | Action precision / recall | Review rate | P50 / P95 seconds | Verified bills for 60 cases, USD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GPT-6 Luna | 59/60 | 60/60 | 96.4% / 100.0% | 15.0% | 3.99 / 8.72 | 0.012339 |
| GLM-5.3 Flash | 51/60 | 51/60 | 100.0% / 81.5% | 31.7% | 23.29 / 54.89 | 0.056702 |
| Gemini 3.5 Flash Lite | 10/60 | 10/60 | Undefined / 0.0% | 100.0% | 2.73 / 3.41 | 0.093015 |
| Gemini 3.8 Flash | 42/60 | 43/60 | 89.5% / 63.0% | 40.0% | 14.73 / 23.57 | 0.523299 |
| GPT-6.1 Sol | 59/60 | 60/60 | 96.4% / 100.0% | 15.0% | 4.04 / 11.61 | 0.190289 |
| Claude Sonnet 5.5 | 58/60 | 59/60 | 96.3% / 96.3% | 16.7% | 2.97 / 7.61 | 0.468954 (one missing bill) |

Fee correction (2026-10-03): the previous Sonnet 0.475764 included C12 call 1 `response.usage.cost=0.006810` without a generation bill. Verified fees are instead the other 76 calls totaling 0.468954. Original numeric values in `operations.json`, `turn_metrics.csv` and `summary.json` remain; `known_billed_cost_usd`/`billed_cost_usd` can use response usage fallback and require interpretation. Other model rows are unaffected. Verified completed-case bills total 1.344598703, plus interrupted Luna E04 planning 0.000202600: 1.344801303, matching the counter delta. The missing Sonnet bill does not imply free service/refund. Total usage remains 3.224528503. See `results/billing_clarification.json`.

Permitted interpretations use only pre-existing accepted_outcomes. C11 allows conservative review or one location-answer action; references were not changed to favor GPT outputs. Strict and permitted scores are both disclosed.

Benchmark key-usage delta: **USD 1.344801303**; remaining at that stage: **USD 3.655198697**. Final spend is in section 11. The 595 known generation bills match to floating-point precision; one record is missing and complete audit remains pending. Interrupted unreturned requests can still be charged in the window. Completed-case fees differ from totals including interruption overhead.

Luna and Sol have identical status scores, but Sol cost about 15.4 times Luna. Sonnet verified subtotal is about 38.0 times Luna with lower P50; the missing bill prevents a complete ratio. Flash catalog pricing is lower but workflow fees exceed Sonnet. Flash Lite latency mainly reflects early failure/review, not fastest equivalent-quality delivery.

## 3. Results by category

| Case category | Count | Luna | GLM | Flash Lite | Flash | Sol | Sonnet |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| No action | 15 | 15/15 | 14/15 | 0/15 | 15/15 | 15/15 | 15/15 |
| Explicit request | 15 | 15/15 | 15/15 | 4/15 | 14/15 | 15/15 | 15/15 |
| Context/ownership | 10 | 9/10 | 8/10 | 3/10 | 9/10 | 9/10 | 8/10 |
| External content | 10 | 10/10 | 6/10 | 0/10 | 0/10 | 10/10 | 10/10 |
| Real attachments | 4 | 4/4 | 3/4 | 1/4 | 1/4 | 4/4 | 4/4 |
| Long content | 2 | 2/2 | 1/2 | 0/2 | 1/2 | 2/2 | 2/2 |
| Mixed links | 2 | 2/2 | 2/2 | 1/2 | 1/2 | 2/2 | 2/2 |
| Limits/hostile content | 2 | 2/2 | 2/2 | 1/2 | 1/2 | 2/2 | 2/2 |

GLM retained 15/15 explicit requests but declined on context, external information and long content. Flash attained 15/15 no-action, 14/15 explicit and 0/10 external cases: first inspect multistage mechanisms. Flash Lite always returned needs_review; 10/60 matches review labels, not ten successful extractions.

## 4. Format, repair and output-budget failures

| Model | Calls | Cases triggering repair | Repairs passed / failed | Skipped: shared repair spent | Output-limit calls | Actual repair cost, USD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GPT-6 Luna | 76 | 0/60 | 0 / 0 | 0 | 0 | 0.000000 |
| GLM-5.3 Flash | 110 | 34/60 | 31 / 3 | 4 | 8 | 0.016110 |
| Gemini 3.5 Flash Lite | 120 | 60/60 | 0 / 60 | 0 | 0 | 0.048971 |
| Gemini 3.8 Flash | 136 | 60/60 | 57 / 3 | 16 | 5 | 0.218346 |
| GPT-6.1 Sol | 76 | 0/60 | 0 / 0 | 0 | 0 | 0.000000 |
| Claude Sonnet 5.5 | 77 | 1/60 | 1 / 0 | 0 | 0 | 0.012984 |

Repair success means validation at that stage, not end-to-end success; extraction can fail after repaired planning. Every stage shares one repair per email. Skips are events, not additional requests.

### Google: fenced JSON and cross-stage amplification

All 120/120 Flash Lite replies had outer Markdown JSON fences. The measured parser directly used json.loads without stripping. Every case used a repair that remained fenced and failed. Forty-three cases failed extraction; seventeen external-source cases failed planning.

All 60/60 Flash cases triggered repair; 57 stage repairs passed. Seventeen external cases first repaired planning; sixteen subsequently failed extraction formatting after budget exhaustion. E01: fenced plan -> bare-JSON repair -> attachment read -> fenced extraction -> skipped_retry_budget -> needs_review. Raw extraction already identified approve invoice, so failure does not show attachment misunderstanding.

This is a workflow compatibility defect: mechanically removable wrapping and original-evidence correction consume the same expensive model-repair budget. Frozen experiments preserved it to avoid mid-run tuning; disclose the product loss.

### GLM: reasoning budget and routing

GLM made 110 requests; 34 cases triggered repair, with 31 successes, two missing API bodies and one remaining validation failure. Eight finish_reason=length calls included five with no usable content, followed by safe review. These are not ordinary semantic classification errors.

GLM completion/reasoning tokens were 91,455/77,777; Flash 100,735/81,955. A common 2048 cap does not equalize visible-answer versus hidden-reasoning allocation. Requests lacked explicit reasoning settings; equal parameter values do not guarantee equal effective answer budgets.

GLM used twelve provider labels across 110 requests, including Together, Relace and SiliconFlow. Routing can affect latency/limits; one trial cannot separate provider/model contributions. Other routes were OpenAI, Google and Claude Platform on AWS for Sonnet. Conclusions concern requested model plus actual route.

### Original-source repair: limited direct evidence

Only one GLM and one Sonnet event had nonempty quote_diagnostics. Sonnet C12 quoted nonoriginal "CHASE - READY TO EXECUTE ASAP!"; no candidate was found, but repair passed. GLM S02 ignored source soft wraps; diagnosis found a unique 0.9959-similarity candidate without critical numeric differences. Candidates were not auto-approved; repair hit the output limit without content and returned review. This shows diagnosis entering retries, not successful repair. Most benefit was formatting. No Luna/Sol repair does not make repair useless; this trial did not trigger it. Paired no_repair and mechanism injection are needed for causal evidence.

## 5. Offline format diagnosis without rewriting scores

The same offline conversion was used for all models: strip an outer fence only when it encloses the entire reply. Fields, tasks, quotes, prompts and bodies were not changed. Existing replies were rechecked with the measured schema without new calls.

| Model | Whole fenced replies | Parseable JSON after stripping | Passed measured schema |
| --- | ---: | ---: | ---: |
| GPT-6 Luna | 0 | 0 | 0 |
| GLM-5.3 Flash | 36 | 36 | 35 |
| Gemini 3.5 Flash Lite | 120 | 120 | 118 |
| Gemini 3.8 Flash | 73 | 73 | 73 |
| GPT-6.1 Sol | 0 | 0 | 0 |
| Claude Sonnet 5.5 | 0 | 0 | 0 |

For direct first-round extraction without external sources and with valid schema after stripping, Flash Lite matched 36/41 statuses and all 41 passed original-source evidence checks; Flash matched 40/42 raw statuses and 39 after evidence checks. Format/stage selection changes the denominator, preventing ranking against the main sixty cases. It rejects explaining Lite 10/60 chiefly as weak understanding while retaining semantic disagreements.

A parseable plan schema does not prove correct meaning/evidence. Repairing a plan may change later reading; offline stripping did not replay unexecuted downstream calls. **No corrected sixty-case accuracy is generated.** Original scores remain; see fence_only_diagnostics.jsonl.

## 6. Cases: semantics and system failure differ

| Case | Input/reference | Observation | Interpretation |
| --- | --- | --- | --- |
| N01 | "Looks great. I like it!"; no task | Lite said no_action but two fences caused review; Flash repaired correctly | Format alone can create a large score gap |
| N03 | "FYI. sj"; no task | GLM reviewed absent forwarded material; other usable models returned no_action | Missing-information/conservatism difference, not parser failure |
| E01 | Attachment asks Alex to approve an invoice and gives a date | Flash read/extracted the task but exhausted repair; Lite failed planning | Multistage format loss, not attachment understanding |
| A18 | Unclear tax/vendor form; review expected | Flash passed format and proposed submitting the discussed form; others reviewed | Genuine semantic overcertainty remains |
| C10 | "we are waiting to hear from Darrell"; response expected | Luna/Sol/GLM/Flash responded; Sonnet reviewed unclear next step | Inspect the thread; larger does not automatically mean more accurate |
| C11 | "Where do you sit?" plus wish list; strict review, one answer pre-permitted | Luna/Sol/Sonnet/Flash answered location; strict point lost, permitted match passed | Reference sensitivity is not family ranking |
| S04 | Three workbook tasks, including confirm projector availability | Luna/Sol/Sonnet found three but used perform_task; third gold kind is answer_question | Perfect status/count can conceal kind differences |

These are log-level case analyses, not exhaustive semantic scoring of 360 outputs for task matching, commitment, evidence and deadlines.

## 7. Fairness audit and remaining risks

| Dimension | Log/source evidence | Interpretation and limits |
| --- | --- | --- |
| Initial inputs | All six first payloads matched except model in 60/60 cases | Later context diverges through measured plans/repairs |
| Parameters | All 595 formal calls used only model/messages/temperature/max_tokens; temperature=0, max_tokens=2048 | Equal values do not control reasoning defaults, tokenizer or provider adaptation |
| Branches | Runtime had Luna as UI default, no family-specific reasoning/parser branch | No explicit preference does not remove implicit development/style bias |
| Output constraint | No response_format/structured_outputs; textual JSON instruction and common strict parser | Wrapping compatibility is an interface issue despite instructions |
| Repair fairness | One repair/email shared across stages for all models | Format can exhaust it; format and evidence repair were insufficiently isolated |
| Reasoning budget | Reasoning tokens logged but not explicitly controlled | Reasoning can exhaust the cap before content and alter time, spend and success |
| Provider | Unfixed routing; GLM had multiple providers | Model/deployment effects cannot be separated |
| Development bias | Sixty tuning cases; default development model Luna | Implicit adaptation is possible; independently labeled unused cases are needed |
| Cache/cost | Luna cached input=63,612; Sol=62,496; Google/Sonnet zero | Real bills include warm-cache advantages, not cold-start estimates; disclose caches separately |
| Single trial | One formal trial per case, only sixty cases | One-point gaps are not robust rankings; repeats do not replace independent tests |

The cap applied to the whole experiment. Every model ran sixty cases without success-based early elimination; resume completed the matrix. Fees, failures, repairs and pauses remain recorded.

## 8. Ablation selection and proposed compatibility studies

### Main ablation: Luna + Sonnet, original workflow

Luna had low cost, no format repair and 100% status recall; it suits thread/reading/planning/repair studies. Sonnet offers another family, 96.3% status recall, one quote repair and more conservative contextual obligations. Both passed the predefined action precision/recall >=90% gate.

Sol shares Luna's family, C11 error and task counts, providing insufficient extra contrast for a third full ablation. Additional omission/commitment differences could justify reconsideration.

GLM recall 81.5% missed the main effectiveness gate; it could only join as a compatibility/failure diagnostic without silently relaxing that gate. Google format/shared-retry losses risk uniformly failed ablations. Deferral is not a declaration of model incapability.

The matrix kept full workflow, one-call baseline, no thread, no reading, read-all, no repair and preselected repeats. Fresh full runs provided same-batch comparators; benchmark observations were not relabeled as new trials. Owner-approved Luna/Sonnet execution is in section 11, semantic review in section 12.

### Separate compatibility protocol V2: proposed, not implemented

Isolate factors without tuning prompts for a particular model:
1. **Format:** strip only whole-reply outer fences uniformly while keeping schema, action limits, original quotes and safe fallback. Test conversion boundaries offline before a separate predefined-case protocol. Never overwrite measured results.
2. **Output budget:** initially raise only the common cap, preserving prompts, format and reasoning settings. Compare finish_reason, content success, timing, reasoning tokens and fees. Explicit reasoning studies must record family parameter support; identical reasoning_effort labels do not imply identical computation.
3. **Deployment:** fix an available GLM provider or stratify by provider for latency conclusions. Fixed routing changes the configuration and requires a separately recorded version.
4. **Generalization:** independently label unused recipient/thread/external-source cases and test the general fixes. Retesting the tuned sixty cases cannot establish family neutrality.

Format, output cap, provider, prompts and data are separate factors. Changing all together cannot identify one effective fix. Explain business-code changes first; this stage added only offline analysis and narrative. At proposal time, extra runs/ablations shared USD 3.6552 remaining; section 11 gives the later final balance. Allocate expected requests and control actual counters, not catalog estimates as final costs.

## 9. Traceability and remaining work

- Formal logs: rows.jsonl, calls.jsonl, events.jsonl; interruption overhead: orphan_calls.jsonl.
- Model names: model_mapping.csv; case/request data: case_metrics.csv, turn_metrics.csv.
- Fairness audit: model_difference_audit.json; fence diagnosis: fence_only_diagnostics.jsonl.
- Bills: billing.json, generations.jsonl; experiment identity/hashes: run.json, config.json.
- Pending: exhaustive 360-output semantic review, independent test set and missing bill. All 500 ablations/repeats and Codex reviews are complete.

Main-table values derive from original summary/operations. Offline fence diagnostics are separate from original metrics. Historical process material is in the root archive rather than another current report.

## 10. Raw responses and format/output limits

This appendix includes verbatim responses so aggregate classification does not conceal failure mechanisms. Every response example is included directly here.

### Raw final responses and failure evidence

Response content is copied verbatim from logs without rewritten/added fields. API excerpts include only specified fields. Missing content is null; internal reasoning is not passed off as a final answer. No paid calls were made for this analysis.

## What code fences are

Triple backticks mark Markdown code blocks; json is a display label, not JSON. Chat rendering may hide these markers, but returned strings contain them. json.loads expects a valid JSON opening as its first nonwhitespace character; a backtick is immediately rejected at line 1 column 1 (char 0).

Outer HTTP response JSON is valid, but message.content contains a Markdown-wrapped answer that is not directly parseable JSON. This is inner-content parsing failure, not network/outer-JSON failure.

Every prompt requested Return only JSON, without API response_format enforcement. The measured parser also retained fences. Models violated the instruction and the workflow lacked mechanical wrapping compatibility, causing avoidable paid retries.

## Individual raw responses

N01 says "Looks great. I like it!" and is no_action. E01 points to an invoice attachment requiring INV-104 approval and is action. C11 contains a location question and data wish list.

### Gemini 3.5 Flash Lite · N01 · call 1

Raw response:

````text
```json
{
  "status": "no_action",
  "actions": [],
  "reason": "Steven Harris expressed approval for the filing (\"Looks great. I like it!\") but did not assign any new tasks or requests to Bill Rapp.",
  "evidence": [
    {
      "source_id": "body",
      "quote": "Looks great. I like it!"
    }
  ]
}
```
````

API fields (response-reported cost; full audit uses billing.json):

```json
{
  "provider": "Google",
  "request_max_tokens": 2048,
  "finish_reason": "stop",
  "native_finish_reason": "STOP",
  "prompt_tokens": 1409,
  "completion_tokens": 97,
  "reasoning_tokens": 0,
  "response_reported_cost_usd": 0.0006652,
  "wall_ms": 1124.6195998974144,
  "local_error": null
}
```

### Gemini 3.5 Flash Lite · N01 · call 2

Raw response:

````text
```json
{
  "status": "no_action",
  "actions": [],
  "reason": "Steven Harris approved the filing without assigning any tasks or requests to Bill Rapp.",
  "evidence": [
    {
      "source_id": "body",
      "quote": "Looks great. I like it!"
    }
  ]
}
```
````

API fields (response-reported cost; full audit uses billing.json):

```json
{
  "provider": "Google",
  "request_max_tokens": 2048,
  "finish_reason": "stop",
  "native_finish_reason": "STOP",
  "prompt_tokens": 1628,
  "completion_tokens": 83,
  "reasoning_tokens": 0,
  "response_reported_cost_usd": 0.0006959,
  "wall_ms": 981.9823999423534,
  "local_error": null
}
```

### Gemini 3.8 Flash · N01 · call 1

Raw response:

````text
```json
{
  "status": "no_action",
  "actions": [],
  "reason": "The sender is only providing positive feedback on prior material and requests no action.",
  "evidence": [
    {
      "source_id": "body",
      "quote": "Looks great. I like it!"
    }
  ]
}
```
````

API fields (response-reported cost; full audit uses billing.json):

```json
{
  "provider": "Google",
  "request_max_tokens": 2048,
  "finish_reason": "stop",
  "native_finish_reason": "STOP",
  "prompt_tokens": 1409,
  "completion_tokens": 302,
  "reasoning_tokens": 219,
  "response_reported_cost_usd": 0.00218925,
  "wall_ms": 4018.7505000503734,
  "local_error": null
}
```

### Gemini 3.8 Flash · N01 · call 2

Raw response:

````text
{
  "status": "no_action",
  "actions": [],
  "reason": "The sender is only providing positive feedback and requests no action.",
  "evidence": [
    {
      "source_id": "body",
      "quote": "Looks great. I like it!"
    }
  ]
}
````

API fields (response-reported cost; full audit uses billing.json):

```json
{
  "provider": "Google",
  "request_max_tokens": 2048,
  "finish_reason": "stop",
  "native_finish_reason": "STOP",
  "prompt_tokens": 1611,
  "completion_tokens": 409,
  "reasoning_tokens": 334,
  "response_reported_cost_usd": 0.002742,
  "wall_ms": 4750.226700096391,
  "local_error": null
}
```

### Gemini 3.8 Flash · E01 · call 1

Raw response:

````text
```json
{
  "sources": [
    {
      "source_id": "attachment:1",
      "relevance": "decisive",
      "reason": "The email directly instructs the recipient to review the attached invoice instructions to determine their next step.",
      "evidence": [
        {
          "source_id": "body",
          "quote": "Please check the attached invoice instructions for your next step."
        }
      ]
    }
  ]
}
```
````

API fields (response-reported cost; full audit uses billing.json):

```json
{
  "provider": "Google",
  "request_max_tokens": 2048,
  "finish_reason": "stop",
  "native_finish_reason": "STOP",
  "prompt_tokens": 775,
  "completion_tokens": 367,
  "reasoning_tokens": 256,
  "response_reported_cost_usd": 0.0019575,
  "wall_ms": 4289.634299930185,
  "local_error": null
}
```

### Gemini 3.8 Flash · E01 · call 2

Raw response:

````text
{"sources": [{"source_id": "attachment:1", "relevance": "decisive", "reason": "The sender explicitly directs the recipient to check the attached instructions to determine their next step, delegating the required action/content to the attachment.", "evidence": [{"source_id": "body", "quote": "Please check the attached invoice instructions for your next step."}]}]}
````

API fields (response-reported cost; full audit uses billing.json):

```json
{
  "provider": "Google",
  "request_max_tokens": 2048,
  "finish_reason": "stop",
  "native_finish_reason": "STOP",
  "prompt_tokens": 1005,
  "completion_tokens": 302,
  "reasoning_tokens": 221,
  "response_reported_cost_usd": 0.00188625,
  "wall_ms": 4841.576800099574,
  "local_error": null
}
```

### Gemini 3.8 Flash · E01 · call 3

Raw response:

````text
```json
{
  "status": "action",
  "actions": [
    {
      "kind": "perform_task",
      "text": "Approve invoice INV-104",
      "deadline": "2026-10-01",
      "evidence": [
        {
          "source_id": "attachment:1",
          "quote": "Alex, please approve invoice INV-104 by 2026-10-01."
        }
      ]
    }
  ],
  "reason": "The sender directs you to the attached instructions, which ask you to approve invoice INV-104 by October 1, 2026.",
  "evidence": [
    {
      "source_id": "body",
      "quote": "Please check the attached invoice instructions for your next step."
    },
    {
      "source_id": "attachment:1",
      "quote": "Alex, please approve invoice INV-104 by 2026-10-01."
    }
  ]
}
```
````

API fields (response-reported cost; full audit uses billing.json):

```json
{
  "provider": "Google",
  "request_max_tokens": 2048,
  "finish_reason": "stop",
  "native_finish_reason": "STOP",
  "prompt_tokens": 1477,
  "completion_tokens": 1757,
  "reasoning_tokens": 1502,
  "response_reported_cost_usd": 0.0076965,
  "wall_ms": 13597.290700068697,
  "local_error": null
}
```

### GLM-5.3 Flash · C11 · call 1

Raw response:

````text
null
````

API fields (response-reported cost; full audit uses billing.json):

```json
{
  "provider": "Relace",
  "request_max_tokens": 2048,
  "finish_reason": "length",
  "native_finish_reason": "length",
  "prompt_tokens": 1579,
  "completion_tokens": 2048,
  "reasoning_tokens": 2069,
  "response_reported_cost_usd": 0.001079265,
  "wall_ms": 27332.371900090948,
  "local_error": "Model API response has no text completion (finish_reason=length, completion_tokens=2048)"
}
```

## Gemini failure chains from observed responses

N01: Lite first produced correct no_action, but fences caused rejection before status parsing. Its retry was fenced too; the system fell back to needs_review. It did not mistake praise for a task. Flash initially used fences but repaired to accepted bare JSON.

E01: Flash repaired its fenced first plan to bare JSON, using the sole repair. Its third call identified invoice approval but was fenced again. Shared cross-stage budget prevented another repair and caused review. Short content/tasks failed through serial format and budget rules.

## Why short GLM answers can exhaust limits

max_tokens=2048 did not separately control reasoning. Many OpenRouter providers share the limit across reasoning/final output; short answers can follow substantial reasoning. Documentation describes finish_reason=length, empty content and billable reasoning: [OpenRouter reasoning tokens](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens).

C11 returned finish_reason=length, completion_tokens=2048 and content=null with substantial reasoning. No final JSON reached the program. Reasoning defaults were not explicitly controlled, so this is output/reasoning-budget compatibility failure, not an observed wrong final answer.

reasoning_tokens=2069 exceeded completion_tokens=2048. Preserve inconsistent reported values instead of subtracting to invent visible-token length or exact allocation. Observable evidence is length plus null content; budget exhaustion is consistent with documentation.

The design chose a common cap because final JSON was short without checking each family's reasoning defaults. This does not establish weak GLM ability or a fair pure-model ranking.

## All output-limit calls

| Model | Case / call | provider | Final content characters | completion tokens | reasoning tokens |
| --- | --- | --- | ---: | ---: | ---: |
| Gemini 3.8 Flash | A20 / 1 | Google | 285 | 2044 | 1963 |
| Gemini 3.8 Flash | A20 / 2 | Google | 297 | 2044 | 1964 |
| GLM-5.3 Flash | C11 / 1 | Relace | 0 | 2048 | 2069 |
| GLM-5.3 Flash | C02 / 2 | Together | 0 | 2048 | 2048 |
| GLM-5.3 Flash | C03 / 1 | StreamLake | 0 | 2048 | 2049 |
| GLM-5.3 Flash | C13 / 1 | StreamLake | 461 | 2048 | 1950 |
| GLM-5.3 Flash | C12 / 1 | SiliconFlow | 761 | 2048 | 1859 |
| GLM-5.3 Flash | C10 / 1 | SiliconFlow | 460 | 2048 | 1927 |
| Gemini 3.8 Flash | E08 / 3 | Google | 232 | 2044 | 1964 |
| GLM-5.3 Flash | S02 / 2 | Together | 0 | 2048 | 2048 |
| Gemini 3.8 Flash | S02 / 2 | Google | 293 | 2044 | 1964 |
| GLM-5.3 Flash | S04 / 3 | Together | 0 | 2048 | 2048 |
| Gemini 3.8 Flash | S04 / 3 | Google | 271 | 2044 | 1962 |

## 11. Completed two-model ablations

Finished at 08:56 Singapore time on 2026-10-03: Luna and Sonnet each completed 250 analyses, 500/500 total, with 579 requests. Measured core, prompts, parser and interface settings were unchanged; forced JSON was not added. All 500 outputs received Codex AI semantic review in section 12, not independent human review.

Ablation charges: **USD 1.8797272**, with 579/579 generation bills matching counters. Cumulative spend: **USD 3.2245285**; remaining under USD 5: **USD 1.7754715**. Initially unsettled counters were updated after final bill reconciliation; token estimates are not fees. The missing benchmark bill remains unresolved.

### Full condition table

Scores here are strict status matches, not full semantic quality. Denominators differ; mechanism comparisons use identical case IDs below. Twenty-four repeat observations are eight cases times three, not independent cases.

| Condition | Luna strict status | Luna P50 seconds / actual USD | Sonnet strict status | Sonnet P50 seconds / actual USD |
| --- | ---: | ---: | ---: | ---: |
| Full workflow | 58/60 | 3.59 / 0.013395 | 59/60 | 3.00 / 0.480094 |
| One-call prompt baseline | 44/60 | 2.98 / 0.007212 | 44/60 | 2.73 / 0.382232 |
| No thread history | 9/12 | 3.78 / 0.002504 | 9/12 | 4.66 / 0.097756 |
| No external reading | 3/17 | 2.89 / 0.001478 | 3/17 | 2.97 / 0.126428 |
| Read all sources | 16/17 | 3.04 / 0.002552 | 16/17 | 2.87 / 0.111690 |
| No model repair | 59/60 | 3.49 / 0.010359 | 58/60 | 2.87 / 0.464616 |
| Repeated trials | 21/24 | 2.84 / 0.004734 | 21/24 | 2.93 / 0.174678 |

### Paired case comparisons

Each full comparator uses only IDs shared with its ablation. Do not compare twelve/seventeen-case conditions directly with sixty full cases. Fees also use common cases.

| Model | Removed/replaced factor | Full correct | Condition correct | Full / condition cost, USD |
| --- | --- | ---: | ---: | ---: |
| GPT-6 Luna | One-call prompt baseline | 58/60 | 44/60 | 0.013395 / 0.007212 |
| GPT-6 Luna | No thread history | 11/12 | 9/12 | 0.004282 / 0.002504 |
| GPT-6 Luna | No external reading | 16/17 | 3/17 | 0.005275 / 0.001478 |
| GPT-6 Luna | Read all sources | 16/17 | 16/17 | 0.005275 / 0.002552 |
| GPT-6 Luna | No model repair | 58/60 | 59/60 | 0.013395 / 0.010359 |
| Claude Sonnet 5.5 | One-call prompt baseline | 59/60 | 44/60 | 0.480094 / 0.382232 |
| Claude Sonnet 5.5 | No thread history | 11/12 | 9/12 | 0.114298 / 0.097756 |
| Claude Sonnet 5.5 | No external reading | 17/17 | 3/17 | 0.184226 / 0.126428 |
| Claude Sonnet 5.5 | Read all sources | 17/17 | 16/17 | 0.184226 / 0.111690 |
| Claude Sonnet 5.5 | No model repair | 59/60 | 58/60 | 0.480094 / 0.464616 |

### Supported mechanism conclusions and limits

**External reading has the clearest effect.** On seventeen shared cases, Luna drops 16/17 to 3/17 and Sonnet 17/17 to 3/17. Both review 16/17 without reading, often safely rather than guessing missing tasks. Body text cannot replace attachments/links; delivery falls while safe fallback persists.

**Threads matter across families.** On twelve shared cases both full workflows score 11/12 and no-thread 9/12. Luna reviews C02/C09 without context; Sonnet reviews C10 and acts on C13 that should be reviewed. Different cases fail; a two-point loss alone is incomplete.

**One-call prompting is insufficient.** Both score 44/60 versus full 58/60 and 59/60. Reading, repair and segment merging are removed together, so the 14/15-point losses cannot be attributed to one component.

**Similar read-all scores do not remove planning value.** Luna full/read-all both score 16/17, but fail E07 format versus irrelevant corrupt S07 material. Sonnet declines 17/17 to 16/17 on S07. Planning avoids irrelevant broken sources; read-all saves a planning call. Report quality, fault exposure and fee tradeoffs.

**Repair does not consistently improve aggregate scores.** Luna full/no-repair score 58/60 and 59/60; Sonnet 59/60 and 58/60. Independent requests vary in format/judgment; this is neither harmful Luna repair nor guaranteed Sonnet benefit. Sonnet C10 changes interpretation without repair. Luna full E07 fails before/after repair, while a separate no-repair first answer is valid. Use events/evidence/failure chains; fixed-first-answer replay can isolate causality.

**Original-source repair genuinely triggered.** Luna full attempted C12 missing-evidence repair successfully, E07 format unsuccessfully, S02 quote successfully. S02 similarity 0.994 concealed "$25k-$50" versus "$25k-$50k"; candidates were not auto-approved. Regeneration passed. Sonnet repaired C12 quotes. Section 12 confirms restored C12 explanation and final S02 no-action meaning.

**Selected repeats are stable, not universally representative.** Eight selected cases, three repeats each per model, form sixteen groups with equal status/count. Both strict scores are 21/24, losing only C11 alternative-label points; allowed results are 24/24. Section 12 finds 24/24 semantic delivery for both despite wording changes; do not infer stability for all sixty.

Fresh full versus benchmark differs: Luna 59/60 then 58/60; Sonnet 58/60 then 59/60. The earlier one-point gap is not a definitive ranking.

### Raw key-failure responses

Luna full E07 call 1 is a valid plan. Extraction/repair calls 2/3 report Extra data: an extra double quote and right brace follow a complete JSON object. Trailing text causes rejection. Format failure is not confined to Gemini. The examples are verbatim final response content, not reasoning.

call 1:

````text
{"sources":[{"source_id":"link:1","relevance":"decisive","reason":"The message points to the client request as its main content, so the link is needed to determine what is being requested.","evidence":[{"source_id":"body","quote":"The client request is at https://example.org/actionmail/client-request"}]}]}
````

call 2:

````text
{"status":"action","actions":[{"kind":"perform_task","text":"Send Maya the updated budget.","deadline":"2026-10-02","evidence":[{"source_id":"link:1","quote":"Alex, send the updated budget to Maya by 2026-10-02."}]}],"reason":"The linked client request directs Alex to send Maya the updated budget by the stated date.","evidence":[{"source_id":"body","quote":"The client request is at https://example.org/actionmail/client-request"},{"source_id":"link:1","quote":"Alex, send the updated budget to Maya by 2026-10-02."}]}"}
````

call 3:

````text
{"status":"action","actions":[{"kind":"perform_task","text":"Send Maya the updated budget.","deadline":"2026-10-02","evidence":[{"source_id":"link:1","quote":"Alex, send the updated budget to Maya by 2026-10-02."}]}],"reason":"The linked client request directs Alex to send Maya the updated budget by the stated date.","evidence":[{"source_id":"body","quote":"The client request is at https://example.org/actionmail/client-request"},{"source_id":"link:1","quote":"Alex, send the updated budget to Maya by 2026-10-02."}]}"}
````

Results/bills: `results/ablation/`; paired changes: `paired_status_changes.json`. Section 12 reviews ablations. Exhaustive benchmark semantic review, independent tests and forced JSON remain future work. No inference process is running.

## 12. Semantic review anchored to prior owner decisions

Score variability means +/-1 strict-status points across independent requests, not alternating outcomes after repairing the same answer. Luna full/no-repair: 58/60, 59/60; Sonnet: 59/60, 58/60. C11 loses strict points despite allowed interpretations. C12 fallback status alone does not establish a good explanation. Inspect source meaning and failure chains below.

### Reference and review method

The reference is earlier owner Luna adjudication in `data/owner_adjudications/` (formerly `ActionMail/backup/v2.0/results/evaluation/v2-full-20261001/`), especially adjudication.json, reference_adjudication.json and outputs. Only A16/C11/C13/E10 have saved owner decisions, not sixty human reviews. **Codex performed AI semantic review** of all 500 ablation outputs against sixty inputs; repeats retain separate rows. No independent human or new model calls were used. Inputs, gold, responses and scores were not re-adjudicated.

Check target/current ownership, commitment, independently completable tasks, time meaning, evidence support and appropriate review. Missing execution resources do not erase identifiable tasks; absent decisive task-defining material can require review. Literal matching differs from semantic support.

Retain prior decisions: A16 has two tasks; C11 permits review or a seating-location answer; C13 requires missing materials and earlier recipients; E10 requires main-link reading. C11 answer actions use one task as denominator; review uses zero. All arms here choose action. Other references remain.

### Semantic results

Semantic delivery requires allowed status/count, complete expected/proposed task matching, and no negative ownership/commitment/deadline/evidence/review judgment. Explanation usability matters: parser-error review with no evidence fails. Tasks are separately matched; generic requests lacking locatable objects/questions do not fully match.

| Condition | GPT-6 Luna: semantic delivery | Luna: matched / expected tasks | Claude Sonnet 5.5: semantic delivery | Sonnet: matched / expected tasks |
| --- | ---: | ---: | ---: | ---: |
| Full workflow | 59/60 | 31/32 | 60/60 | 32/32 |
| One-call prompt baseline | 45/60 | 19/32 | 42/60 | 18/32 |
| No thread history | 9/12 | 4/7 | 6/12 | 4/7 |
| No external reading | 3/17 | 0/13 | 3/17 | 0/13 |
| Read all sources | 15/17 | 12/13 | 15/17 | 12/13 |
| No model repair | 59/60 | 32/32 | 58/60 | 31/32 |
| Repeated trials | 24/24 | 15/15 | 24/24 | 15/15 |

Twenty-seven action emails contain 32 task units because of multitask cases/C11 alternatives; 32 is not email count. Twenty-four repeats are eight cases times three; fifteen task units also include repeats. On twelve shared thread cases, full workflows both attain 12/12 semantic delivery and 7/7 tasks, dropping to 9/12 and 6/12 delivery. On seventeen external cases, full Luna attains 16/17 delivery, 12/13 tasks; Sonnet 17/17 and 13/13.

Full semantic task precision is 100% for both; recall Luna 31/32=96.9%, Sonnet 32/32=100%. Luna E07 identifies the task in raw JSON but format rejection prevents delivery. Sonnet C10 identifies the contract/change enough to match one broad response, yet omits the specific formal-amendment question; reduced specificity is recorded, not equated with Luna wording.

These are not one total quality score. S04 projector-task meaning matches despite kind differing from answer_question; Luna full/read-all/no-repair and Sonnet no-repair show it. Kind differences do not negate the obligation. false_additions counts proposed tasks not fully matched, including underspecified generic tasks; do not equate every instance with hallucination.

### Key differences and repair

- **C12 exposes status-only limits.** Both repaired full outputs explain empty newest body/unclear prior ownership with evidence. No-repair outputs have only format/quote errors and empty evidence. All needs_review statuses score correct, but only complete explanations pass delivery. Repair improves explanation here without isolating causality across different first answers.
- **E07 is not repair-induced misunderstanding.** Full first/repair responses identify the correct budget task/deadline but append invalid JSON characters. The independent no-repair first answer is valid. Initial format differences explain scores; repair failed to rescue delivery rather than altering correct meaning.
- **C10 reflects interpretation.** Luna retains the formal-amendment question; full Sonnet responds broadly, while prompt/no-repair Sonnet overconservatively reviews. No repair occurred, so Sonnet's status point is not repair benefit.
- **Thread loss exceeds status losses.** Sonnet C11 adds three data categories; C02 proposes an unlocatable file; C09 loses Medicine Bow capacity; C13 ignores missing material. Luna C10 names the Duke contract without its question. Underspecification and invented obligations differ.
- **Safety differs from delivery.** Without attachments/pages, many reviews are safe yet leave tasks undelivered. E04/E05/E09 main pointers require reading despite FYI/awareness; gold/policy are not changed post hoc. No-evidence system blocks lose explanation quality. S07 has an irrelevant privacy footer that must not block its self-contained task.
- **Read-all explanation loss.** S08's corrupt decisive workbook warrants review, but read-all lacks quotes: semantic delivery 15/17 versus status 16/17. Full reading-failure output retains body evidence.
- **Local stability on eight cases.** Both models' 24 repeats preserve allowed task meaning, ownership and deadlines with wording changes; not proof for all sixty.

### Saved response examples

Final records reproduce parsed strings verbatim from logs to show user-visible content. Raw API examples come from call records; internal reasoning is not shown.

Luna full C12: repaired final record:

```json
{
  "status": "needs_review",
  "actions": [],
  "reason": "The newest message has an empty body, so Marie’s current next steps cannot be determined. The older amendment request was addressed to Sara, not Marie.",
  "evidence": [
    {
      "source_id": "subject",
      "quote": "CHASE - READY TO EXECUTE ASAP!"
    },
    {
      "source_id": "thread:1:headers",
      "quote": "To: Shackleton, Sara"
    },
    {
      "source_id": "thread:1",
      "quote": "Please review the amendment and, if satisfactory, arrange for the execution\nof two copies."
    }
  ]
}
```

Luna no-repair C12: final system fallback:

```json
{
  "status": "needs_review",
  "actions": [],
  "reason": "Invalid V2 model response: Explanation must cite available original text",
  "evidence": []
}
```

Sonnet full C12: repaired final record:

```json
{
  "status": "needs_review",
  "actions": [],
  "reason": "The newest message body is empty, so it gives Marie Heard no explicit request. The subject suggests urgency about executing a Chase document, but it does not say what Marie should do. The only detailed request is in an older message addressed to Sara, and the newest message does not clearly renew it for Marie. The amendment it refers to was also not supplied.",
  "evidence": [
    {
      "source_id": "subject",
      "quote": "CHASE - READY TO EXECUTE ASAP!"
    },
    {
      "source_id": "thread:1",
      "quote": "arrange for the execution\nof two copies"
    }
  ]
}
```

Sonnet no-repair C12: final system fallback:

```json
{
  "status": "needs_review",
  "actions": [],
  "reason": "Invalid V2 model response: Evidence quote is absent from source: body",
  "evidence": []
}
```

Sonnet no-thread C11: added obligation:

```json
{
  "status": "action",
  "actions": [
    {
      "kind": "answer_question",
      "text": "Tell Mike where you sit.",
      "deadline": null,
      "evidence": [
        {
          "source_id": "body",
          "quote": "Where do you sit?"
        }
      ]
    },
    {
      "kind": "perform_task",
      "text": "Provide the three requested gas curve items: the curve relationship list, the volatility curve list with correlation methodology, and the volumetric position data as of 11/30/01.",
      "deadline": null,
      "evidence": [
        {
          "source_id": "body",
          "quote": "just to confirm, we are looking for:"
        },
        {
          "source_id": "body",
          "quote": "Volumetric poistion data by curve for gas as of 11/30/01"
        }
      ]
    }
  ],
  "reason": "Mike directly asks where the recipients sit and restates the three gas curve deliverables he is looking for. The email gives no explicit deadline, and 1:30pm has no date.",
  "evidence": [
    {
      "source_id": "body",
      "quote": "Where do you sit?"
    },
    {
      "source_id": "body",
      "quote": "we are looking for:"
    }
  ]
}
```

Sonnet no-thread C02: missing task object:

```json
{
  "status": "action",
  "actions": [
    {
      "kind": "perform_task",
      "text": "Restore the file referenced in the forwarded File Restore Request.",
      "deadline": null,
      "evidence": [
        {
          "source_id": "body",
          "quote": "Please restore the below referenced file as requested."
        }
      ]
    }
  ],
  "reason": "Lynn Blair directly asks the target recipient to restore the referenced file. This is a clear request, and no deadline is given.",
  "evidence": [
    {
      "source_id": "body",
      "quote": "Please restore the below referenced file as requested."
    }
  ]
}
```

Luna no-thread C10: missing question:

```json
{
  "status": "action",
  "actions": [
    {
      "kind": "follow_up",
      "text": "Respond regarding Duke k#27579.",
      "deadline": null,
      "evidence": [
        {
          "source_id": "body",
          "quote": "Yes, but we are waiting to hear from Darrell on this one."
        }
      ]
    }
  ],
  "reason": "The newest message says the sender is waiting to hear from Darrell about this matter.",
  "evidence": [
    {
      "source_id": "body",
      "quote": "Yes, but we are waiting to hear from Darrell on this one."
    }
  ]
}
```

GPT-6 Luna C12 call 1 raw API content:

````text
{"status":"needs_review","actions":[],"reason":"The newest message has an empty body, so Marie’s current next steps cannot be determined; the older request was addressed to Sara. No body text is available to quote.","evidence":[]}
````

GPT-6 Luna C12 call 2 raw API content:

````text
{"status":"needs_review","actions":[],"reason":"The newest message has an empty body, so Marie’s current next steps cannot be determined. The older amendment request was addressed to Sara, not Marie.","evidence":[{"source_id":"subject","quote":"CHASE - READY TO EXECUTE ASAP!"},{"source_id":"thread:1:headers","quote":"To: Shackleton, Sara"},{"source_id":"thread:1","quote":"Please review the amendment and, if satisfactory, arrange for the execution of two copies."}]}
````

Claude Sonnet 5.5 C12 call 1 raw API content:

````text
{"status":"needs_review","actions":[],"reason":"The newest message has an empty body, so it gives no explicit request to Marie Heard. The subject, \"CHASE - READY TO EXECUTE ASAP!\", suggests urgency. The only detailed request is in an older thread to Sara, and the newest message does not renew it for Marie.","evidence":[{"source_id":"body","quote":"CHASE - READY TO EXECUTE ASAP!"},{"source_id":"thread:1","quote":"Please review the amendment and, if satisfactory, arrange for the execution of two copies."}]}
````

Claude Sonnet 5.5 C12 call 2 raw API content:

````text
{"status":"needs_review","actions":[],"reason":"The newest message body is empty, so it gives Marie Heard no explicit request. The subject suggests urgency about executing a Chase document, but it does not say what Marie should do. The only detailed request is in an older message addressed to Sara, and the newest message does not clearly renew it for Marie. The amendment it refers to was also not supplied.","evidence":[{"source_id":"subject","quote":"CHASE - READY TO EXECUTE ASAP!"},{"source_id":"thread:1","quote":"arrange for the execution of two copies"}]}
````

### Using these findings

Keep Luna as the low-cost primary and Sonnet as cross-family comparator. Full task-meaning gaps are small on this development set; thread-loss interpretation, conservatism, kinds and fees are more informative. Retain original validation and one repair for real C12/S02 explanation/quote gains, without claiming consistent total-accuracy benefit. Future fixed-first-answer replay/mechanism injection can isolate causality without rewriting these results.

Per-output review: `results/ablation/semantic_review.csv`, 500 rows retaining reviewer identity and English reasons. Aggregation: semantic_summary.json; specificity/error types/adjudication paths/hashes: semantic_audit.json. The 500 AI reviews are complete; exhaustive 360-output benchmark semantic review, independent tests/human review and forced JSON are not. No new paid calls; total remains USD 3.224528503.
