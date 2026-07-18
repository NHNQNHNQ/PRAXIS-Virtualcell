# PRAXIS-VirtualCell Repository Layout and Artifact Policy

> Audited: 2026-07-18
>
> Status: `CURRENT_LAYOUT_POLICY`

This document assigns responsibilities to tracked trees and separates versioned scientific evidence from rebuildable output. It is a preservation policy, not a cleanup authorization.

## Tracked-file accounting

At audit anchor `24475f2`, the repository had exactly 1,126 tracked files:

| Mutually exclusive responsibility | Files | Scope |
|---|---:|---|
| Product code | 361 | `praxis_virtualcell` excluding tests, inherited `praxis2`, API, React excluding E2E, and web entry |
| Tests | 377 | root legacy `tests`, `praxis_virtualcell/tests`, and React E2E specs |
| Documentation | 248 | `docs/` current, historical, findings, paper, plans, and handoffs |
| Curated data | 19 | tracked subsets, provenance, manifests, and small deterministic fixtures under `data/` |
| Audit/report evidence | 35 | `_audit/` and `reports/` tracked snapshots |
| Support/operations | 75 | `scripts`, `brains`, `deploy`, `migrations`, `examples`, and `.github` |
| Root configuration/metadata | 11 | build, license, baseline, provenance, ignore, and service configuration |
| **Total** | **1,126** | exact `git ls-tree -r --name-only 24475f2` count |

Before this A4 change, checkpoint `b52ab5c` had 1,133 tracked files: the baseline plus seven consolidation documents. This A4 change adds two documentation files, so its completed commit should have 1,135 tracked files. Any future count change must be explained by named commits rather than treated as an automatic cleanup target.

## Top-level responsibilities

| Path | Responsibility | Release/test treatment |
|---|---|---|
| `praxis_virtualcell/` | VirtualCell product runtime, agents, predictors, governance, model registry, CLI, and authoritative core tests | maintained product scope; `praxis_virtualcell/tests` is the core pytest boundary |
| `praxis2/` | inherited PRAXIS-2 runtime compatibility layer | retained dependency; do not confuse its legacy service/version line with the VirtualCell product |
| `praxis_vc_api/` | thin FastAPI/local-service adapter | maintained product API surface |
| `praxis_vc_react/` | current React/Vite local UI and Playwright E2E | maintained frontend; build/test output is generated |
| `praxis_vc_web/` | inherited/optional web entry | supporting component until version/packaging review decides its lifecycle |
| `tests/` | inherited PRAXIS-2 legacy/integration suite | run and report separately; never use it to inflate or block the core KPI without explicit policy |
| `docs/` | current navigation/status plus historical plans, findings, handoffs, and paper drafts | preserve; lifecycle is defined by `docs/INDEX.md`, not directory age |
| `data/` | tracked curated subsets/provenance plus ignored large local reproducibility data | never delete by extension; distinguish tracked curated evidence from ignored source datasets |
| `_audit/` | versioned audit snapshots | evidence, not cache |
| `reports/` | versioned quality/capability reports; some raw generated intermediates are ignored | evidence documents stay tracked |
| `scripts/` | maintenance, evidence-generation, packaging, and phase-runner source | source code; `scripts/audit` generates `_audit` evidence but is not the evidence itself |
| `brains/` | inherited/runtime domain rules and memory content | packaged/supporting runtime data |
| `deploy/` | install, Docker, service, and deployment definitions | operations source; executing deployment remains separately authorized |
| `migrations/` | database migration history | immutable operational history unless a new migration is added |
| `.github/` | CI definitions | product-quality policy, not generated output |

## Evidence and history that must remain versioned

- `_audit/`: structured host/software/skill evidence.
- `reports/phase10/`: Phase 10 gate, summary, cases, failures, trace audit, UI report, and screenshot.
- `docs/findings/`: scientific findings plus JSON/JSONL ledgers and evaluation snapshots.
- `docs/history/`: inherited project/status/deployment history.
- `docs/paper/`: manuscript drafts, review, figures, literature, and result synthesis.
- tracked `data/`: curated subsets, manifests, provenance, and model fixtures.

Do not apply extension-wide deletion rules to JSON, JSONL, CSV, TSV, TXT, PNG, or Markdown. Those extensions occur in controlled evidence trees.

## Rebuildable/generated output

| Output | Policy |
|---|---|
| `.venv/`, `node_modules/`, Python caches, `.pytest_cache/`, `.ruff_cache/`, `*.egg-info/` | rebuild in Phase B; never migrate as environment truth |
| `build/`, root/React `dist/`, wheels/sdists | regenerate from the reviewed commit |
| `runs/` | local job output; use explicit test temp paths |
| React `test-results/`, `playwright-report/`, `blob-report/` | Playwright output; not source evidence unless deliberately promoted into a report |
| `.playwright-mcp/` | browser-tool session logs and page snapshots; recovery copy is checksummed, live path is ignored |
| `reports/phase10/junit-*.xml`, `trace_bundle.json` | raw generated Phase 10 intermediates; APFS copy is preserved locally but Git ignores them |
| AppleDouble `._*` and `.DS_Store` | filesystem metadata noise; ignored everywhere, never manually removed from the active Git object database |

`.claude/` is deliberately not ignored. Its sole current `launch.json` is portable and secret-free, but whether it is team configuration or personal configuration remains a recorded user decision. Do not solve that decision by ignoring the whole directory silently.

## Ignore-rule boundaries

- `build/`, `/dist/`, explicit React `dist/`, and React-local ignore rules cover known project builds. Do not broaden `/dist/` to every nested `dist/` until all package trees are checked for intentionally tracked directories.
- React Playwright outputs are explicitly scoped to `praxis_vc_react/`; add other scopes only when a real runner creates them.
- `runs/` and AppleDouble rules apply recursively through Git ignore matching.
- Ignored scientific datasets are still user assets. Their exact APFS/T7 hashes are recorded in the recovery manifest; “ignored” does not mean disposable.

For external-disk Git storage and AppleDouble handling, follow [External-Disk Git Maintenance](runbooks/EXTERNAL-DISK-GIT-MAINTENANCE.md).
