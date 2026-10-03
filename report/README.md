# Reporter entry point

Updated 3 October 2026. All report authoring and generated deliverables are maintained here.

## Review and edit

- [FINAL_REPORT.pdf](FINAL_REPORT.pdf): the current four-page typeset report.
- [FINAL_REPORT.tex](FINAL_REPORT.tex): the **sole editable manuscript**, including embedded vector figures and the local NTU logo asset. Continue revisions in this file and the same LaTeX editor.
- [FINAL_REPORT.md](FINAL_REPORT.md): generated review rendering; do not edit independently.
- Evidence paths and interpretation checks are maintained below in this README.
- [QA_RESULTS.json](QA_RESULTS.json): count, figure checks, compilation and visual-review record.

Current count: **1053 conservative lexical words**, including title, headings, title metadata, template attribution and references; whitespace count: 1021. Graphic contents and captions are excluded under the owner's confirmed rule. The owner requested formal system-centered prose, overriding the earlier first-person writing preference; individual-project attribution is preserved.

Four figures and two tables appear at their relevant paragraphs, with no separate figures section. Artwork contains only analytical panels, axes, legends and labels; captions supply short titles and necessary definitions. Evaluation conditions and review identity are maintained in Evaluation design. Integration status is maintained in System design and boundaries. Graphics do not repeat those declarations.

| Manuscript element | Stable asset |
| --- | --- |
| Figure 1: Workflow | figures/01_architecture.png |
| Table 1: Ownership | figures/06_scope_and_ownership.png |
| Figure 2: Case composition | figures/05_data_provenance.png |
| Figure 3: Six models | figures/02_model_comparison.png |
| Figure 4: Paired delivery | figures/03_paired_context.png |
| Table 2: Ablation metrics | figures/04_metrics_and_cost.png |

Asset prefixes are stable identifiers, not manuscript numbering. The PDF contains embedded vector graphics; PNG and SVG exports support Markdown and reuse.

## Regenerate

From the workspace root, using the Python environment installed by the root README, after changing graphic layout. Report regeneration additionally needs Pillow and ReportLab; ordinary product use does not require them:

```powershell
.venv/Scripts/python.exe -m pip install Pillow ReportLab
.venv/Scripts/python.exe report/tools/build_figures.py
.venv/Scripts/python.exe report/tools/sync_report.py
```

The first script updates only the generated-panel region of the same .tex source, preserving editorial content. The second derives Markdown and counts from that content. Prose-only edits need only the second command. Both generation and synchronization retain a structured visual-review status and mark it pending; inspect each graphic and all PDF pages before marking it complete. Citation keys, section anchors and figure/table references are also derived from the manuscript.

The built-in compiler returned `Unable to find standard directories for platform`. Installed MiKTeX successfully compiled the same source with its local logo asset. Local export from `report/`, with an installed `pdflatex` on PATH. Create the intermediate directory before compiling:

```powershell
New-Item -ItemType Directory -Force build | Out-Null
pdflatex --disable-installer -interaction=nonstopmode -halt-on-error -output-directory=build FINAL_REPORT.tex
Copy-Item -LiteralPath 'build/FINAL_REPORT.pdf' -Destination 'FINAL_REPORT.pdf'
```

Compilation needs normal compiler-cache access. Intermediate logs and page previews stay in build/. The final log has no warnings or overfull/underfull boxes. Prefer the built-in compiler when its environment is available; keep edits in the same .tex source.

The root README defines the submission layout; report/ and experiments/ sit beside ActionMail/. Exact extended cutoff, video duration and upload naming/location remain unconfirmed. No business code or experimental record was changed by Reporter.

## NTU styling and attribution

The report uses a compact article layout, Times-style body text, running headers and a 55 mm original NTU master logo with 10 mm clear space below it. Logo artwork is supplied unmodified by [Chen Wang’s NTU thesis template](https://github.com/wang-chen/thesis_template_ntu), retaining the [MIT license notice](assets/chen_wang_template_LICENSE.txt). Its title treatment is a visual reference; the full dissertation class is not imported. Logo placement was checked against NTU’s [2018 Quick Brand Guide](https://www3.ntu.edu.sg/CorpComms2/NTU%20Quick%20Brand%20Guide%202018.pdf); the guide is archived in assets/ for reproducibility. These are typesetting references, not PE6201 submission requirements.

The manuscript includes 11 cited sources: Google, MailEx, two project records, three course-slide references, two OpenRouter documents, the template repository and the brand guide. Template acknowledgment cites the artifact actually used; the author’s invitation to cite his thesis or papers is optional, and unrelated research papers are not presented as design evidence.

PDF and Markdown include 19 internal links to figures, tables, the evaluation section and bibliography entries. The PDF also includes seven original-source URLs and six section bookmarks. All targets were checked. Table captions are above tables; figure captions are below figures. The final four pages and six graphics were visually checked after the last compilation.


## Report evidence and review record

Updated 3 October 2026. This supports the sole editable manuscript [FINAL_REPORT.tex](FINAL_REPORT.tex), its compiled PDF and generated Markdown review rendering. Paths below are relative to the workspace root. Evidence is maintained here rather than in repetitive graphic footers.

## Authority and original-source checks

- `ActionMail/docs/course/PE6201_Assessment_Timeline.pdf`, p.1: inspected extracted original text. Individual project, business/technical analysis capped at 1,200 words, GitHub code and recorded presentation/demo.
- `ActionMail/docs/course/PE6201_Project_Proposal_Watchouts (1).pdf`, pp.1-3: inspected extracted original text. Problem 15%, trade-offs 25%, implementation 35%, communication 25%; own/rent by layer; baseline, data, evaluation, limitations; low-code optional.
- Course PDFs were checked for textual requirements, not visually audited or redistributed. The owner has separately confirmed figure exclusion from word count.
- [MailEx original publication](https://aclanthology.org/2023.emnlp-main.801/), checked 3 October 2026: Srivastava et al., EMNLP 2023, pp.12964-12987, DOI 10.18653/v1/2023.emnlp-main.801. Its task is event and argument extraction from conversational email threads, not the ActionMail obligation policy. The [author repository](https://github.com/salokr/Email-Event-Extraction) was also opened.
- [Google's task-creation documentation](https://support.google.com/mail/answer/9920317?hl=en), checked 3 October 2026: task creation from emails, with an additional route through Gemini summary cards. The report makes no unsupported claim that competing products lack AI task features and no commercial-product performance comparison.

## Numerical claims

| Report claim / figure | Authoritative path and field | Interpretation |
| --- | --- | --- |
| At most 3 independent tasks; 1 shared repair | `ActionMail/docs/architecture.md`, Public decision and policies; `workflow/multi_pipeline.py`, `workflow/repair.py` | Entire email budget spans planning, segments, extraction and merge. No automatic fuzzy acceptance. |
| Rule status 31/60; precision 60%; recall 44.4% | `experiments/results/rules-baseline/summary.json`, `arms.rules.strict_status_match`, `analyses`, `action_precision`, `action_recall` | Status-based action metrics. Baseline lacks equivalent external/multi-task capabilities. |
| Pre-specified 90% precision/recall shortlist | `experiments/PROTOCOL.md`, experiment one; `experiments/REPORT.md`, section 8 | Candidate selection criterion, not a retrospectively invented universal success threshold. |
| 60 cases; 27 action, 23 no_action, 10 needs_review | `experiments/data/frozen-core/dataset.jsonl`, `gold.status` | Single strict reference; C11's alternative is separate. |
| 33 MailEx, 1 Enron, 19 authored JSON, 7 authored EML | Same dataset, `origin` | 34 existing-email-derived, 26 authored. S03 is email/PDF export. Figure 2 sums the disjoint groups to 60. |
| 17 cases, 20 external entries: 13 attachments + 7 links | Same dataset, `email.external_sources`; source inventory in the sealed dataset | Per-case inventory, not accesses; 12 authored attachments, 1 Enron PDF. Twelve authored = 5 text snapshots + 7 actual byte files. Seven authored links = 6 snapshots + 1 unreadable footer. |
| Six models x 60 = 360 | `experiments/results/model-benchmark/summary.json`, `completed_analyses`, `arms.*.analyses`; `model_mapping.csv` | One formal trial per model/case; observations do not imply 360 independent emails. |
| Initial settings 0 temperature / 2,048 output cap | `experiments/PROTOCOL.md`; `experiments/REPORT.md`, sections 1, 7; saved `calls.jsonl` | No API-enforced JSON or fixed provider. Identical initial requests except model do not imply equal effective reasoning budgets. |
| Luna 59, GLM 51, Lite 10, Flash 42, Sol 59, Sonnet 58 | Benchmark `summary.json`, `arms.full_m01` through `full_m06`, `strict_status_match` | Each /60. Figure 3 also plots permitted joint matches: 60, 51, 10, 43, 60, 59. Neither metric is full semantic accuracy. |
| Benchmark P50/P95 | Benchmark `operations.json`, `by_arm.*.case_wall_ms.p50` and `.p95`, /1,000 | Luna 3.99/8.72; GLM 23.29/54.89; Lite 2.73/3.41; Flash 14.73/23.57; Sol 4.04/11.61; Sonnet 2.97/7.61 seconds. Local workflow wall time, not TTFT or decoding throughput. |
| Benchmark verified fees | `experiments/results/billing_clarification.json`, `generation_verified_cost_by_completed_arm_usd` | Luna .012339495, GLM .056702108, Lite .093015000, Flash .523299000, Sol .190289100, Sonnet .468954000 USD. Rounded to six decimals in Figure 3. |
| Sonnet missing bill | Same clarification, `missing_completed_call_generation_bills` | C12 first call. Original .475764 subtotal includes unaudited .006810 response usage fallback. Do not silently fill zero, claim refund or call the subtotal complete. |
| Flash Lite all review / fenced JSON; Flash repair amplification; GLM budget/routing | `experiments/REPORT.md`, sections 3-5 and 7; benchmark `events.jsonl`, `calls.jsonl` | Compatibility is a delivery failure; offline fence removal is not a new 60-case pipeline score. |
| 500 ablation observations | `experiments/results/ablation/summary.json`, `completed_analyses`; `semantic_summary.json`, `reviewed_analyses` | Two models x 250: 60 full + 60 prompt + 12 no thread + 17 no reading + 17 read all + 60 no repair + 24 repeated. |
| Full semantic delivery 59/60 and 60/60; prompt 45/60 and 42/60 | Ablation `semantic_summary.json`, `arms.full_m01/full_m06/prompt_only_m01/prompt_only_m06.delivery_semantic_pass` | Codex AI review. Strict full status is 58/60 and 59/60, not benchmark 59/60 and 58/60. |
| Paired no thread: full 12/12 each; reduced 9/12 and 6/12 | Ablation `semantic_review.csv`, filtered by comparison case IDs; `experiments/REPORT.md`, section 12 | Figure 4 derives each full comparator from identical IDs and reproduces saved semantic criteria. |
| Paired no reading / read all: full 16/17 and 17/17; no reading 3/17 each; read all 15/17 each | Same paired CSV aggregation; section 12 | Safe missing-content review differs from successfully delivered tasks. Read-all semantic counts differ from strict counts (16/17 each). |
| Full task matches 31/32 and 32/32; prompt 19/32 and 18/32; no repair 32/32 and 31/32 | Ablation `semantic_summary.json`, relevant `matched_tasks`, `expected_tasks` | Table 2. Obligation units, not email counts. Task kind / specificity exceptions remain separate. |
| No repair strict 59/60 and 58/60; semantic 59/60 and 58/60 | Ablation `summary.json` and `semantic_summary.json`, `no_repair_m01/m06` | Independent first answers; not proof that repair causes the one-point difference. |
| C12 evidence restoration; S07 footer obstruction | `experiments/REPORT.md`, sections 11-12; corresponding ablation case traces | Qualitative examples. Status-only scores conceal C12 explanation failure; S07 illustrates irrelevant reading exposure. |
| Full P50 3.59 and 3.00 s | Ablation `operations.json`, `by_arm.full_m01/m06.case_wall_ms.p50`, /1,000 | Fresh ablation, not benchmark latency. |
| Full fees .013394660 and .480094000 USD | Same file, `known_billed_cost_usd`; ablation `billing.json` | Ablation generation audit is complete (579/579); the benchmark missing record does not contaminate these full arms. |
| Per case .000223 and .008002; ratio 35.8x | Divide full fees by 60; .480094000/.013394660 = 35.8421938 | Measured model service fees only, not a deployment forecast, marginal cold-start rate or total operating cost. |
| Table 2 prompt / no-repair costs and time | Ablation `operations.json`, `by_arm.prompt_only_m01/m06` and `no_repair_m01/m06` | Exact input values saved in original file. Display rounded to 2 decimals for seconds, 6 decimals for USD. |
| Total 3.224528503 USD; cap 5 USD | `experiments/results/finalization.json`, `actual_total_usd`, `cap_usd`; `experiments/results/ablation/global-billing.json` | Total usage-counter cost. Benchmark 1.344801303 + ablation 1.879727200. Counter reconciliation does not erase missing individual bill. |
| Repeats on 8 selected cases | `experiments/PROTOCOL.md`; ablation `stability_m01/m06` | Each model has 8 x 3 = 24 observations. No independent-sample or universal-stability claim. |

## Semantic and scope checks

- The figure builder reproduces the saved semantic delivery totals for every ablation arm from the existing review rows. This verifies chart aggregation, not new judgments or gold corrections. No experimental summary is rewritten.
- Semantic delivery checks permitted status/count, complete task-unit matching, ownership/currentness, commitment, deadline, evidence and review appropriateness. It does not establish perfect wording, task-kind agreement, security or broad quality.
- C11's alternative interpretation existed before the experiment. Owner adjudications explicitly saved for A16, C11, C13 and E10 are distinguished from the 500 Codex reviews.
- Data reuse, original Luna tuning, incomplete benchmark semantic review, provider/default reasoning and warm-cache effects are disclosed.
- Figure 1 includes validation during planning/merging and a repair budget shared across stages. Its decision-to-review arrow has no bypass branch; accepted tasks and explicit saved-field confirmation gate calendar operations.
- System design and boundaries is the single implementation-status statement. Table 1 describes sourcing choices only, without repeating deployment claims.
- The original offline engineering totals are not included as accuracy evidence. No new engineering test suite was needed for this document/figure change.
- No actual time saved, ROI, product adoption, compliance certification or comprehensive prompt-injection protection is invented. Commercial assistants were not benchmarked.

## Presentation and visual review

The owner's latest direction supersedes the earlier first-person style and graphics appendix. The report now uses formal system-centered prose, four figures and two tables at their relevant paragraphs. Freeze conditions and review identity appear in Evaluation design; integration status appears in System design and boundaries. Those declarations were removed from artwork.

Graphic panels were redrawn without title banners, narrative subtitles, source footers or status callouts. The approach references [Nature's figure guidance](https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/) for clear axes, ticks, units and minimal decoration, and [IEEE's graphics guidance](https://books.ieeeauthorcenter.ieee.org/prepare-your-book-manuscript/create-original-graphics/) for sequential numbering and defined abbreviations. Their publishing rules are not course requirements.

All six compact graphic panels were opened and inspected after redesign and spacing correction. The compiled PDF was rendered and all four pages inspected. An initial vector-export issue displaced line segments; it was corrected, the report was recompiled, and all four final pages were inspected again. No label overlap, clipping, displaced borders or caption collisions remain. Axes are zero-based and labeled. Figure 3's percentile spans are not confidence intervals. Figure 4 uses identical case IDs within each comparison. Figure 2 identifies the tiny Enron segment through its legend.

The built-in compiler returned an environment error (`Unable to find standard directories for platform`). Installed MiKTeX successfully compiled the same source with its local logo asset; the final log has no warnings or overfull/underfull boxes. The four-page PDF contains vector graphics. The LaTeX file is the editable source and Markdown is generated from it, avoiding divergent manuscripts.

## Integrity and pending items

The 120 frozen experiment files matched `results/finalization.json` SHA-256 values. The measured business runtime is the c405d29 snapshot retained under experiments/data/frozen-core/. The current submission code has only packaging/cleanup changes relative to that snapshot. All Reporter-created files remain under `report/`.

Current count including title/headings/references: 1053 conservative lexical words, or 1021 whitespace tokens. Graphic contents/captions are excluded by owner confirmation. Still pending: exact extended submission cutoff, video length and upload naming/location. These do not require reopening sealed experiments.

## Citation and NTU presentation update (3 October 2026)

- Three course sources were checked against the local slide files: own/rent (Class 2 C2, pp. 2-3), evaluation (Class 2 C4, pp. 3-7; Class 3 C2, pp. 9-10, 13-15), and cost per successful task (Class 5 C2, p. 21). Their source PDFs are not redistributed.
- [OpenRouter Structured Outputs](https://openrouter.ai/docs/guides/features/structured-outputs), checked 3 October 2026: JSON-schema support is endpoint-dependent. This supports a proposed next step, not an implemented experimental feature.
- [OpenRouter Provider Routing](https://openrouter.ai/docs/guides/routing/provider-selection), checked 3 October 2026: default routing can distribute requests across providers. Saved run traces remain the authority for the experiment; current documentation is architectural context.
- [Chen Wang’s template repository](https://github.com/wang-chen/thesis_template_ntu) supplies the original 1000 x 358 pixel logo asset, placed at 55 mm (approximately 462 pixels per inch). The asset is unchanged. Its MIT notice is retained under assets/. The bibliography cites the repository, which is the reused artifact; the author’s optional invitation to cite his thesis is recorded without attributing unrelated research claims to it.
- [NTU Quick Brand Guide 2018](https://www3.ntu.edu.sg/CorpComms2/NTU%20Quick%20Brand%20Guide%202018.pdf) specifies original proportions, a clear background and clearance of half the crest height. At 55 mm logo width, half the crest height is approximately 9.85 mm; the title has 10 mm clearance. The original asset and final title area were opened and visually checked.
- Final bibliography has 11 entries, all cited; PDF has 19 resolved internal links, seven source URLs and six section bookmarks. Diagram links target their full panels. Markdown has the same 19 resolved internal anchors.
- All four final PDF pages were re-rendered and inspected after the final layout change. The cost paragraph now starts together on page 4, avoiding a single orphaned line. The last compilation has no warnings or overfull/underfull boxes. All 120 sealed files were rechecked and match their recorded SHA-256 hashes.
