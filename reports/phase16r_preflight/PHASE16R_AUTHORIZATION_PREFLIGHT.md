# P16R local authorization-preflight identity bridge

> Work unit: `P16R-PREFLIGHT`
>
> Engineering: `COMPLETE — IDENTITY_PREFLIGHT_ONLY`
>
> Actual P16R: `AUTHORIZATION_REQUIRED / NOT_RUN`
>
> Science: `NOT_RUN`
>
> Product policy: `NO_NEW_DECISION`

## Outcome

This local work unit adds a value-free, in-memory identity compiler for a future P16R K562
science authorization. It does not select or verify a real candidate. It binds declarations only and
always produces a non-evidence abstention record.

| Field | Value |
|---|---|
| starting SHA | `25fe60a9450765a9ecf3a2a38d198980ea7a7e15` |
| completion code SHA | `4f77255f84e33180d7d73b421fc9737ca3a1121d` |
| completion tree | `f7aadb7b76a2aa55691d67d9c2948cc7b1e38e95` |
| source date epoch | `1786347583` |
| branch | `codex/p30-foundation-rc` |
| module SHA-256 | `5304854d55958dc9fd4be1afdbc65cc3644c60ae210e11d1c16db9d0b75aab71` |
| test SHA-256 | `1cf90b09924ac1d0f963e318233b9100e8df73e6fd61e1ca5e7def2957307477` |

Changed code is limited to
`praxis_virtualcell/benchmarks/k562_p16r_preflight.py` and
`praxis_virtualcell/tests/test_k562_p16r_preflight.py`.

The documentation closure updates `README.md`, `CHANGELOG.md`, `docs/USER-GUIDE.md`,
`docs/RELEASE-v1.7.0.md`, `docs/INDEX.md`, `docs/TESTING.md`, `docs/VERSIONING.md`, the
current execution plan/checklist/integration guide, the P16 ADR/runbook, and dated P28/P29
handoffs. This report is the only new completion record; frozen P16E and P30 completion reports
remain unchanged.

## Completion record and protected state

The completion code SHA records completion of the local identity-preflight implementation. This
report closes its documentation record only; neither the code SHA nor this documentation closure
means that actual P16R was authorized, run, evidenced, policy-approved, or promoted.

Protected paths and state were preserved: `old/**`; the legacy worktrees
`/Users/mzy/Projects/PRAXIS-virtualcell-p9`, `/Users/mzy/Projects/PRAXIS-virtualcell`, and
`/Users/mzy/Projects/PRAXIS-virtualcell-recovery-20260718`; `.53` preview state; `vc_api.log`;
`/home/zkyd/data1/mzy/PRAXIS-2`; existing services (including gunicorn); and existing Git refs.
None was read as current runtime input, modified, cleaned, reset, stashed, overwritten, moved, or
deleted by this work unit.

External actions not performed: network access or download; new external asset/weight access;
real training, GPU, or remote compute; remote Git, push, PR, main/tag/release/publication;
operator promotion; staging/production deployment, restart, traffic, or port/configuration change.

## Contracts and trust ceiling

The module introduces exactly two strict schemas:

- `vc.k562-p16r-external-scope-declaration.v1`
- `vc.k562-p16r-authorization-preflight.v1`

It cross-binds the frozen P16E K562/P8 scope and preregistration, P12 candidate
release/artifact/environment/adapter identities, and P21 protocol/group declarations. The external
scope declaration is explicitly unverified: it records no asset-byte receipt and no record-membership
proof. Synthetic test declarations are conformance inputs only, not candidate, Pack, benchmark, or
scientific evidence.

Every compiled record is fixed to:

~~~text
record_role                         authorization_preflight_not_evidence
authorization_fingerprint           null
assets_verified                     false
record_membership_verified          false
leakage_audit_fingerprint           null
benchmark_passed                    null
scientifically_validated             false
promotion_eligible                  null
evidence_fingerprints               []
policy_fingerprint                  null
production_promoted                 false
executable                          false
abstain                             true
prediction                          null
~~~

The ordered abstention reasons are `p16r_authorization_missing`,
`p16r_asset_bytes_unverified`, `p16r_record_membership_unverified`, and
`p16r_science_not_run`.

## Validation

- focused P16R-preflight suite: `18 passed`;
- affected suites: `399 passed` (`18 + 231 + 35 + 60 + 55`);
- Ruff check and format check: passed;
- `git diff --check`: passed.

An additional local package probe is explicitly non-authoritative: `test_packaging.py` passed
`14`, while `test_versioning.py` had `4 passed / 1 failed` because the shared interpreter still
has installed `praxis-virtualcell 1.6.0` while this checkout declares `1.7.0`. `pip check` also
failed in that pre-existing shared environment (missing `python-magic` and incompatible
`vcbench` pins). No installation or environment mutation was performed to hide either result.

The negative tests reject a wrong/revoked candidate release, cross-scope or feature/output protocol
drift, unsafe artifact load policy, incomplete group partitions, unverified external-cell drift,
subtype/model-copy drift, accidental execution surfaces, and any attempt to elevate the fixed
negative status.

## Explicit non-actions and limitations

No asset I/O occurred. No candidate/model/comparator execution, benchmark run, leakage audit,
evidence creation, policy decision, release, registry/runtime/API/CLI route, promotion, network,
remote compute, push, tag, publication, staging, or deployment occurred. The bridge neither makes a
candidate executable nor grants P16R authorization.

Actual P16R still needs a separately authorized, exact asset/candidate window with read-only paths,
sizes, SHA-256 values, licenses, sources, environments, adapters, output root, run boundary, and
frozen scientific gates. That window must perform the real contamination audit, three-seed runs,
scope-separated paired CI, independent K562 external gate, OOD evaluation, and evidence handling.

Formal P30A remains `LOCAL_RC_INCOMPLETE` because its dependency inputs are still absent.

## Next work

There is no further planned local P16 work unit. The local queue is `BLOCKED_EXTERNAL`: the next
action is a separately authorized, narrow read-only candidate/asset inventory to establish exact
identities, followed by an independently authorized P16R science run. Neither action is authorized
by this record.
