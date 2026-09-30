# Real-first evaluation data

Updated: 2026-10-01 (Asia/Singapore).

## Owner decision

The owner accepts roughly 2,000–3,000 characters and prioritizes available original dataset content. The earlier 5,000–15,000-character authored challenge is superseded as the primary accuracy evaluation. Preserve it as an explicitly synthetic regression/stress suite. Do not rewrite an original email, pad it, invent a timestamp, invent its missing attachment, or substitute a different document as though it belonged to that message.

Existing consent was conditional on reviewing the previous 24 references. It does not authorize a changed batch. No model calls were made for this data audit.

## Local corpus and staged candidates

The earlier audit (preserved in Git history) inspected all 230 MailEx raw threads. Body plus thread reaches 2,830 characters; the newest body reaches 1,275. Seven files contain literal HTTP(S) URLs and 73 mention attachments. A mention is not an available binary. The raw files lack a newest-message Date header, so received time stays unknown. The 1,500 tokenized `full_data` JSON records remain secondary because token joining changes original spacing and they lack usable recipient/date headers.

The owner subsequently fixed the active evaluation at **50 base + 10 supplementary = 60 cases**. The 12-candidate staging list and full audit output were removed from the working tree; their earlier versions remain in Git history. See `docs/evaluation_60.md` for the ten selected cases and coverage. `evaluation/active_suite.json` identifies the two active hash-bound manifests. The former 24-case challenge is archived for offline integration tests and historical reproducibility; it is excluded from the active denominator.

## External dataset findings

| Dataset | Evidence and suitability | Current disposition |
| --- | --- | --- |
| [CMU Enron/CALO](https://www.cs.cmu.edu/~enron/) | Original business mail; distributor explicitly says attachments are excluded. | Useful body/thread material, cannot supply missing binaries. |
| [EDRM Enron v2 via TREC](https://trec-legal.umiacs.umd.edu/corpora/trec/legal10/) | University listing provides email/attachment text (596 MB), native attachments (8 GB), and parent-document mappings. Old PST/XML scripts are explicitly obsolete. | Authoritative attachment-bearing lead; archive downloads not verified in this audit. Avoid downloading the whole corpus just for a few cases. |
| [Enron Archive mirror](https://huggingface.co/datasets/enronarchive/mail) | Individually downloadable mailbox JSON and attachments. Downloaded Blair index: 3,779 messages; 382 DOC, 270 XLS and 22 PDF attachment references, plus other types. These are references, not unique-file counts. | Two parent-matched samples downloaded and size/hash verified. Mirror is an exported representation, not untouched RFC mail; dates and Exchange recipient identities need validation. No DOCX/XLSX references in this mailbox index. |
| [W3C public mail archives](https://www.w3.org/email/) | Public threads, links and real attachments. [Storage buckets mail](https://lists.w3.org/Archives/Public/www-archive/2020Nov/0000.html) explicitly links its PDF and distinguishes sent/received times. | Parent page and PDF downloaded. Useful genuine PDF extraction sample, but this message has an empty body and is not an actionable corporate-mail accuracy example. |
| [Avocado](https://catalog.ldc.upenn.edu/LDC2015T03) | Real company mail/attachment collection with text/XML metadata. Requires licensing and access arrangements. | Secondary option; no download or purchase. Native modern Office format availability not established. |

The standard Enron absence of attachments does not mean all Enron distributions lack them. Conversely, finding a binary in a different distribution does not establish that it matches a MailEx email: require an exact parent/message relationship before joining them.

## Downloaded sample verification

Local downloads remain outside Git under `../data/`. Reproducible checks and provenance are in `tools/inspect_external_samples.py` and `evaluation/real_data_candidates/external_samples.json`.

- Enron `Bushton Balance` / `nov25.pdf`: 17,901 original bytes; indexed parent ID `496fbb1c751d22557bfd74a63732c608`; existing PDF reader extracted 3,043 characters with one page location. This supplies a genuine document of the requested approximate length.
- Enron `FW: Recap of the NNG Winter Operations Meeting` / `Customer Feedback Action Plan 0901.doc`: 27,648 original bytes; parent ID `00a44f790251c904faa3fa72e25942cf`; legacy OLE signature verified. Current reader explicitly rejects this unsupported DOC. Preserve that outcome instead of renaming it DOCX or silently converting it.
- W3C `TPAC_2020_Storage_Buckets_API.pdf`: 190,655 bytes; original archived parent-to-attachment relationship verified. Existing reader extracted 4,950 characters across 25 page locations.

Downloaded parent JSON records preserve the mirror values verbatim. Exported parent files are representations with their own hashes, not original `.eml` files. Index `date` is not automatically equivalent to trusted received time. The mirror contains draft records with suspicious repeated dates and missing sender addresses, and some repeated attachment paths with inconsistent size metadata; exclude such records or review them rather than guess corrections.

## Next acceptance steps

1. Use the original MailEx candidates first, retaining unknown dates and unavailable material explicitly. Review candidate gold against complete unchanged body/thread content.
2. Add parent-matched Enron PDF/HTML samples with valid recipient identity. Verify genuine link context separately; do not present current content of an old URL as a historical snapshot without provenance.
3. For DOCX/XLSX, keep existing authored extraction tests clearly marked synthetic until suitable real modern Office email/attachment pairs are found. Legacy DOC/XLS samples can evaluate unsupported-format routing within current scope. Do not expand product format support merely to make the dataset fit.
4. Prepare a separate versioned real benchmark and reference-only preview on the existing review port. Preserve prior manifests, scores and adjudication files. Reference proposals stay pending until reviewed, then obtain consent for the revised live batch.

This audit verifies data availability and extraction, not action accuracy. No new evaluated denominator or accuracy claim is justified yet.
