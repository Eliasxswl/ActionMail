# Historical archive

Current work starts at root README and `docs/handoff.md`. This folder preserves superseded material by **version, then type**. It is not a second active codebase.

| Location | Contents |
| --- | --- |
| `v1.0` through `v1.5/docs`, `evaluation`, `results/evaluation` | Original annotation policies/manifests and their matching runs |
| `v1.0/docs/PROJECT_RESTART_BRIEF.md`, `ARCHITECTURE.md` | Initial workspace planning notes, including owner-reported teacher feedback |
| `v1.5/data/mailex` | Local-only tokenized corpus splits, full_data and prompt material not used by current runtime |
| `v2.0/docs` | Superseded v2 plans, cumulative handoff, investigations and old README |
| `v2.0/evaluation` | Draft supplements, old 24-case stress set, old multi-action reference proposal and provenance inventory |
| `v2.0/results/evaluation` | Earlier full/targeted/reference-preview runs, replies, scores and owner adjudication |
| `v2.0/code/tools` | Historical fixture generators and investigation scripts |
| `v2.0/code/generated` | Old generated package metadata, not maintained source |
| `v2.0/data` | Local-only additional corpus indexes and unused provenance/download samples |
| `legacy/code`, `legacy/data` | Local ZIP snapshots whose exact product version was not established |

`migration.json` records 76 original/destination paths and their original content hashes. Current active fixture copies are the only intentional historical duplicates. Local corpus archives, ZIPs, generated metadata and course originals are not uploaded; Git retains historical authored fixtures/manifests, results, policies and code. None of the relocated content was rewritten to claim a later result.

Historical docs contain then-current paths, dates, priorities and test counts. Read them as dated evidence. Latest commands and claims are only in the active docs. Old scripts use their original root-relative paths; do not run them inside backup expecting a current build. For exact generator/code reproduction, use checkpoint `282908e` (before organization) in a separate Git checkout with the original local corpus layout. Do not overwrite the active manifests. Archived manifests can be inspected/loaded using their new explicit paths; current tests reference them directly. V1 review resolves versioned manifests under backup by hash.

The active approved supplement still cites six fixture files under `evaluation/archive/fixtures_v2_1`; those files are required current inputs despite the inherited directory name. Full archived copies remain here so draft manifests are independently path-complete. The approved active references and latest full run retain their original hashes. Archive names such as v2.1 challenge denote experimental data revisions, not additional released product branches.
