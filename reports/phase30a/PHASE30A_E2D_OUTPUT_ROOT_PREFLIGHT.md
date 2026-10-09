# P30A-E2d Output-Root Hard-Link Preflight — Local Capability Boundary

**Recorded:** 2026-08-10

**Work unit:** `P30A-E2d — source-archive output-directory hard-link capability preflight`

**Outcome:** `COMPLETE — OUTPUT_ROOT_PREFLIGHT_ONLY / NO_RC_CLAIM`

## Completion evidence

- Starting SHA: `f3b7ace150630d81f381ccf56ba2b45e56f4df0e`.
- Branch: `codex/p30-foundation-rc`.
- Code/test SHA: `7bf3fa87e7440f9b0472e75ce558afda78e2d0af`; tree
  `2ed13227773563795d04a72f7cf60060cfb41fb7`; source-date epoch `1786351774`.
- Changed code paths: `scripts/build_release_source_archive.sh` and
  `praxis_virtualcell/tests/test_release_source_archive.py`.
- Exact changed-source identities: `scripts/build_release_source_archive.sh` is `6,665` bytes /
  SHA-256 `b20ae43d9dcd1125b7965dae42eafa1ccc87b80489add60bcc740bca120ccf06`; and
  `praxis_virtualcell/tests/test_release_source_archive.py` is `8,429` bytes / SHA-256
  `b38c82d314192bcca4d151d93dcdc35c24572a0f544a157c204aabe9561de47a`.
- Focused source-archive tests: `9 passed`; Ruff/format on the changed Python test,
  `bash -n scripts/build_release_source_archive.sh`, and diff checks passed. This record does not
  claim a full P30 suite.
- Independent review: `PASS`; E2d adds no broader architecture, public contract, or release-scope
  expansion.
- Protected paths were preserved, including frozen P30A-E1/E2a/E2b/E2c and P16 reports, legacy
  worktrees, `.53`, and unrelated user files. The separate docs-closure completion record will bind
  the final documentation commit SHA only after that commit exists.

## What E2d changes

The source-archive builder now performs a controlled hard-link capability probe in the requested,
already validated output directory before it creates an archive temp file or invokes `git archive`.
The probe requires the same hard-link primitive used by the later atomic no-replace publish. On
failure it removes its probe file through the existing cleanup trap and exits with:

```text
source archive output directory lacks required hard-link no-replace support
```

The later atomic no-replace publication remains unchanged. E2d adds no artifact schema, Pack,
model, environment, adapter, evidence, policy, registry, runtime route, or scientific contract.

## Actual local output-root result

The selected local exFAT output root returned exit `1` at the new capability preflight, before
archive creation. No source archive was created or accepted, no retained probe file remained, and
the probe temporary was deleted.

This establishes only that the selected current output root cannot satisfy the builder's required
hard-link/no-replace publication contract. It does **not** establish why the frozen E2b attempts
failed, does not identify an E2b output root, and does not make exFAT a historical root cause.
E2b remains its immutable `COMPLETE_NEGATIVE` record; E2c's conclusion that E2b's tracked-link
causal attribution is unreproducible remains unchanged.

## Status after output-root preflight

| Layer | Status |
|---|---|
| P30A-E2b historical runner record | `COMPLETE_NEGATIVE` — immutable historical failure result |
| P30A-E2c reconciliation | `COMPLETE — RECONCILIATION_ONLY / NO_RC_CLAIM` |
| P30A-E2d output-root preflight | `COMPLETE — OUTPUT_ROOT_PREFLIGHT_ONLY / NO_RC_CLAIM` |
| Formal P30A local RC | `LOCAL_RC_INCOMPLETE` — output root, wheelhouse, clean-install, OCI, full-gate, and manifest requirements remain unresolved |
| Scientific evidence | `NOT_RUN / SCIENCE_BADGE_INELIGIBLE` |
| Product policy | `NO_NEW_DECISION` |
| Actual P16R | `AUTHORIZATION_REQUIRED / NOT_RUN` |
| Local queue | `BLOCKED_EXTERNAL` |

The next external scientific gate remains actual P16R asset/candidate authorization and execution.
The separate P30 dependency-input window remains external; E2d does not open it or convert a
capability preflight into a formal release candidate.

## External actions not performed

No network access, asset discovery/download, model execution, training, benchmark, evidence or
policy write, registry change, push, tag, publication, staging, deployment, or production action
occurred.
