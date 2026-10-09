# P30A-E2a Completion Report — Offline RC Preflight Negative Result

**Work unit:** `P30A-E2a — exact clean-source × offline hash-lock coverage preflight × write-new negative record`

**Outcome:** `COMPLETE_NEGATIVE`

**Starting SHA:** `40f433fef8704381de34aeb32d45399b6595c472`

**Completion code SHA:** `964b62214f346b15ec2d3f2a622b33f632dde466`

**Completion tree:** `eac19455bc9241e5347de27782a99942e3591cab`

**Source-date epoch:** `1786338523`

**Branch:** `codex/p30-foundation-rc`

## Scope and result

P30A-E2a adds and exercises an offline, write-new preflight record. It rechecks one clean committed
source identity before and after local dependency coverage inspection, but it deliberately does not
accept caller-supplied artifacts or test claims and cannot complete a release.

The exact result record is `praxis.local-rc-finalizer-preflight.v1`, SHA-256
`6cb91031c96b7ebec92e32f7c2eb8af307f48ceae3cbe4aac43c1939a0779019`. It was written outside the
repository and is not committed, published, signed, or an accepted `release-manifest.json`.

Both its pre- and post-preflight identities bind the completion SHA/tree/epoch above, and
`observed_stable_during_preflight=true`. Its content explicitly says
`future_execution_must_reverify=true` and `not_attestation=true`.

## Exact negative result

The preflight completed with `status=LOCAL_RC_INCOMPLETE` and exactly these dependency blockers:

| Target profile | Blocker | Exact unavailable inputs |
|---|---|---|
| `macos_arm64_cp313` | `offline_wheel_cache_incomplete` | `pyjwt==2.13.0`, `pyyaml==6.0.3` |
| `linux_arm64_cp313` | `offline_wheel_cache_incomplete` | `cffi==2.1.0`, `cryptography==49.0.0`, `pydantic-core==2.46.4`, `pyjwt==2.13.0`, `pyyaml==6.0.3`, `rpds-py==2026.6.3` |

The record marks `wheel` and `container` as `blocked_dependency`; `core`, `legacy`, `frontend`,
`ruff`, `pip_check`, `packaging`, and `source_archive` are `not_run` with
`precheck_only_not_executed`. This is not a failed clean install or a failed artifact build: neither
was attempted.

## Validation and authority boundary

- Targeted post-commit P30 suite: `55 passed` (`27 + 6 + 14 + 8` across release-candidate,
  source-archive, packaging, and E2a-finalizer tests).
- E2a implementation/test byte identities: `scripts/finalize_local_rc.py` SHA-256
  `4c882c25b866afd4e406fdf05361ab3a896f0f5869f709be8584b864c725195b`; and
  `praxis_virtualcell/tests/test_release_finalizer.py` SHA-256
  `19bafbc20022c419c001989c92773842cfbaac7129b7190a6124b5b474bf49aa`.
- The real clean-SHA preflight used CPython `3.13.12`; it recorded `network_used=false`.
- No package installation, wheel/source archive build, OCI build, full core/legacy/frontend/Ruff/
  packaging gate, SBOM, licence inventory, dependency audit, `SHA256SUMS`, release manifest, push,
  tag, publication, staging, deployment, or rollback occurred.
- `full_gate_execution=PRECHECK_ONLY_NOT_EXECUTED` and `software_rc_gates_passed=false` are
  permanent facts of this record, not missing fields that prose may fill in.

## Status ledger

| Layer | Status |
|---|---|
| P30A-E2a offline preflight | `COMPLETE_NEGATIVE` |
| Remaining P30A-E2b artifact-aware trusted finalizer | `NEXT_ELIGIBLE_LOCAL_WORK_UNIT` |
| Formal P30A local RC | `LOCAL_RC_INCOMPLETE` |
| Scientific evidence | `NOT_RUN / SCIENCE_BADGE_INELIGIBLE` |
| Product policy | `NO_NEW_DECISION` |
| P30B1/P30B2 | `NOT_AUTHORIZED / NOT_RUN` |
| P30B3/P30B4 | `NOT_AUTHORIZED / NOT_DEPLOYED` |

P30A-E2a cannot create execution authority, scientific evidence, product policy, a prediction, or a
release. P16R remains `AUTHORIZATION_REQUIRED / NOT_RUN` under its own external scientific window.

## Next work

`P30A-E2b — artifact-aware trusted finalizer / frozen source × clean install × full gate evidence
bundle` is the next eligible local work unit. It must independently revalidate the source, locks,
artifacts and test evidence; it cannot trust this preflight record as a release result. If the exact
wheelhouse inputs remain absent after E2b engineering is complete, formal P30A stays
`LOCAL_RC_INCOMPLETE` pending a separately authorized dependency-input window.
