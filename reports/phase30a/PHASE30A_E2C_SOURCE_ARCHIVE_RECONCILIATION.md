# P30A-E2c Source-Archive Reconciliation — Historical Causal Attribution Unreproducible

**Recorded:** 2026-08-10

**Work unit:** `P30A-E2c — append-only exact-source archive reconciliation × export-ignore proof`

**Outcome:** `COMPLETE — RECONCILIATION_ONLY / NO_RC_CLAIM`

## Completion evidence

- Starting SHA: `6ecea12e95c40d049e2544845d756e503937cbc8`.
- Branch: `codex/p30-foundation-rc`.
- Code/test SHA: `f9aa62d669c7bc3d5cbcca101e4e73ffd0bf821a`; tree
  `d364806f9a800680b40bdaaee8bb1aead748844c`; source-date epoch `1786349933`.
- Changed code path: `praxis_virtualcell/tests/test_release_source_archive.py` only; it covers the
  committed `export-ignore` treatment of an otherwise unsafe source link.
- Live docs closure: `README.md`, `CHANGELOG.md`, `docs/INDEX.md`, the current plan/checklist/
  integration/release/testing/versioning guides, ADR-0024/0025, their two runbooks, and this
  append-only report. No frozen completion report was changed.
- Contracts/schemas: none added or revised; E2c changes only source-archive evidence wording and
  its regression coverage.
- Focused source-archive tests: `8 passed`; Ruff/format passed for the changed Python test,
  `bash -n scripts/build_release_source_archive.sh` and diff checks passed. No full P30 suite is
  claimed by this record.
- Protected paths were preserved, including the frozen E2b report, legacy worktrees, `.53`, and
  unrelated user files. The separate docs-closure completion record will bind the final documentation
  commit SHA only after that commit exists.

## Scope and immutable boundary

This record does **not** amend or replace the frozen
[P30A-E2b archive-runner negative report](PHASE30A_E2B_ARCHIVE_RUNNER.md). E2b remains an
immutable `COMPLETE_NEGATIVE` record at exact SHA
`12ad93d57e4f4e7438d2110b5ac9848c6b17ea33`, tree
`14fe604111c18c558048bc282d23da936ac57088`, source-date epoch `1786343459`.
Its runner record `72459a3b51ba243d747ee2c0159d4105a30ba47d191b99ea05960343bbae63d2`
records two `source_archive_build_failed` results. Those failures remain historical facts.

E2b's prose attributed those failures to a tracked unsupported link. That *causal attribution*
is not reproducible from E2b's own exact committed source inputs:

- `15f3e9b4effdc9e353557631807b900ee8bed1d8`, which introduced the committed
  `.gitattributes` `export-ignore` rule for
  `praxis_virtualcell/tests/fixtures/data_packs/escaping_symlink`, is an ancestor of E2b;
- E2b's exact `.gitattributes` contains that rule, and the source-archive builder invokes
  committed-source `git archive` without `--worktree-attributes`;
- direct `git archive --format=tar 12ad93d57e4f4e7438d2110b5ac9848c6b17ea33` contains neither
  that fixture nor a link member; and
- the E2b runner retained hashes of command output, not raw stderr. It cannot establish a
  stronger root-cause claim retrospectively.

Therefore E2c preserves the E2b failure result while correcting the live status language from
"failed *because of* a tracked unsupported link" to "recorded two source-archive build failures;
the tracked-link attribution is unreproducible from the same committed tree." It does not claim
that the historical attempts succeeded or did not occur.

## Current exact-source reconciliation probe

The current E2c code/test identity is exact SHA
`f9aa62d669c7bc3d5cbcca101e4e73ffd0bf821a`, tree
`d364806f9a800680b40bdaaee8bb1aead748844c`, source-date epoch `1786349933`.
It adds an export-ignored-link source-archive test; it does not change the committed
`.gitattributes` rule or source-archive builder relative to E2b.

Two clean exact-HEAD, out-of-tree source-archive probes on the local APFS `/tmp` output path produced
byte-identical archives:

| Property | Observed value |
|---|---|
| Size | `8,103,649` bytes |
| SHA-256 | `06a202108e1e65f62baf01b3327680a06d6711a1266bd9bfb4de52c4391eaed6` |
| Members | `1,389` |
| Unsafe members | `0` links, `0` AppleDouble entries, `0` escaping-fixture members |

This is current local engineering evidence only. The probe outputs were not accepted as a
release artifact or manifest, and E2c did not perform a clean install, full core/legacy/frontend
gate, OCI build, SBOM, licence inventory, dependency audit, publication, tag, deployment,
scientific run, policy decision, or promotion.

## Status after reconciliation

| Layer | Status |
|---|---|
| P30A-E2b historical runner record | `COMPLETE_NEGATIVE` — immutable failure result; causal tracked-link attribution unreproducible |
| P30A-E2c reconciliation | `COMPLETE — RECONCILIATION_ONLY / NO_RC_CLAIM` |
| Formal P30A local RC | `LOCAL_RC_INCOMPLETE` — offline wheelhouse / clean-install / OCI / full-gate / manifest inputs remain unresolved |
| Scientific evidence | `NOT_RUN / SCIENCE_BADGE_INELIGIBLE` |
| Product policy | `NO_NEW_DECISION` |
| Actual P16R | `AUTHORIZATION_REQUIRED / NOT_RUN` |
| Local queue | `BLOCKED_EXTERNAL` |

The next external scientific gate remains actual P16R asset/candidate authorization and execution.
The separate P30 dependency-input window remains external; E2c neither opens it nor converts the
current probe into a formal release candidate.

## External actions not performed

No network access, asset discovery/download, model execution, training, benchmark, evidence or
policy write, registry change, push, tag, publication, staging, deployment, or production action
occurred.
