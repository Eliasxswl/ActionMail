# Active evaluation: 50 + 10

The owner fixed the active evaluation at exactly **60 cases**. `evaluation/active_suite.json` records the counts and hashes. The frozen 50 remain unchanged, preserving prior comparisons. The active supplementary manifest is now `evaluation/supplement_v2_revision2.jsonl`. The owner reviewed the previous ten references; prior adjudication remains unchanged. Revised S01 follows the owner's explicit corrected choice (no action). Unchanged correct judgments are carried with provenance; changed source expectations, the rejected/replaced case, and an uncertain judgment require further review. No new live model consent has been given.

| Supplement | Primary coverage | Origin |
| --- | --- | --- |
| S01 | Optional comments for consideration create no obligation; unknown date, original longer thread | Original MailEx |
| S02 | Longer original informative reply, older requests must not become current obligations | Original MailEx |
| S03 | Genuine informative PDF; no task dependency, so skip it for model context; original remains viewable | Enron exported dataset; original PDF |
| S04 | XLSX, multiple sheets, cell evidence, three independent tasks | Synthetic format gap test |
| S05 | Two tasks in text + DOCX; historical CSV is irrelevant and skipped | Synthetic format gap test |
| S06 | Contradictory attachment and webpage instructions, no authoritative version | Synthetic conflict test |
| S07 | Irrelevant footer link; unavailable irrelevant material must not block a body task | Synthetic relevance test |
| S08 | Corrupt decisive workbook; explicit review instead of guessing | Synthetic failure test |
| S09 | Malicious instructions inside untrusted content; legitimate request and evidence | Synthetic hostile-content test |
| S10 | Short clear body containing four independently completable requests, exceeding the three-action limit | Synthetic limit test |

The three dataset cases prioritize available original material. Seven targeted synthetic cases fill capabilities not supplied by the downloaded corpus, particularly modern Office files and controlled conflict/failure conditions. They are explicitly labelled in the review UI. The base 50 themselves contain **31 MailEx cases and 19 authored cases**; the whole active suite therefore contains 34 dataset-derived and 26 authored cases. Do not describe it as 60 real emails or hide this mixture.

The base covers no-action/explicit-action/context/external content (15/15/10/10), positive and negative attachment/link snapshots, recipient ownership, outgoing requests, evidence punctuation/negation, and deadlines. Its deadline labels comprise 37 none, 8 exact, 2 vague, 2 resolvable relative and 1 unresolvable relative. A09 covers unknown-date relative deadlines; A23/A24 cover resolvable relative deadlines. Source records contain no exact duplicates. Semantic redundancy may remain, but length alone does not justify removing a case: a short negated request can fail independently of a long document. Keep the owner-requested base 50 for now; any smaller replacement should preserve these distinctions and have its own denominator.

Sixty examples cover representative release scenarios, not every possible input. Coverage budgets and low-level failure branches (encrypted/image-only PDFs, ZIP limits, login/JavaScript pages and redirect/DNS/transport failures) remain deterministic integration tests, rather than additional model-evaluation cases. Full live transport and semantic accuracy still need their respective checks.

The 24-case draft and its fixtures are now in `evaluation/archive/`, used for offline tests and historical reproduction only. The 12-case candidate staging list and large audit inventory were removed. Existing historical runs and owner reviews remain intact; none adds to the active 60-case denominator. External provenance downloads are not additional evaluation cases.

Reference review (ten new cases only):

```powershell
actionmail-review results/evaluation/supplement-v2-gold-preview-r2 --manifest evaluation/supplement_v2_revision2.jsonl --port 61933 --no-browser
```

Open `http://127.0.0.1:61933/?case=S01`. This is a reference-only preview: predictions are unrun, not errors. The page prominently names the target recipient and offers original binary attachments for inspection. Review S02 (uncertain ownership/currentness judgment), S03/S05 (changed reading expectations), and S10 (replacement); previously correct unchanged judgments need not be repeated. Existing fifty labels and historical scores are not overwritten.

Offline validation:

```powershell
actionmail-eval --validate
actionmail-eval --benchmark supplement-v2 --validate
```

After all ten references are reviewed correct, approval can create a new manifest with `--benchmark supplement-v2 --approve-challenge-gold ... --approved-manifest ...`. Update the active-suite component hash to that approved manifest when adoption is explicitly completed. The two components have different reference contracts and approval histories; retain separate results instead of combining old scores into a claimed 60-case accuracy. Obtain consent before running this revised batch.
