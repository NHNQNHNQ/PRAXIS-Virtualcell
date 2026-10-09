# Phase 21A — Virtual Cell Benchmark System completion report

Work unit: P21A — frozen, system-only benchmark protocol, evidence derivation and negative ledger

Outcome: **COMPLETE — SYSTEM_ONLY**

Starting SHA: 5f3fc2d88c20e8083fb66a4c3399c5fe148241be

Completion code SHA: 20ecc12542e5df40c90d1fc367dbe86b563478b8

Completion tree: ffcd261dd7d506d0ad852023afcba0f5c97a2d72

Source date epoch: 1786050825

Branch at completion: codex/p21-benchmark-system

## Outcome and status separation

P21A adds the local engineering system that freezes a benchmark before candidate results, verifies exact run and
result bindings, deterministically re-derives layered evidence, replays the checked-in P8/P9 compatibility states,
and stores only admissible negative history. It does not execute a real candidate or make product policy.

| Plane | State |
|---|---|
| engineering | `COMPLETE — SYSTEM_ONLY`; exact code/tests/package evidence frozen below |
| real candidate execution | NOT_RUN; P21B authorization required |
| real raw/test/external access | NOT_RUN |
| assets / weights / training | NOT_RUN |
| GPU / remote / network | NOT_RUN |
| scientific validation | NOT_RUN |
| product policy | `NO_NEW_DECISION`; P21C authorization required |
| promotion / `production_promoted` | absent / false |
| publication / push / release / deploy | none |

Synthetic positive gate tests are transient conformance assertions only. They use in-memory fixtures and pytest
temporary roots, are never treated as real evidence, and are rejected by the negative ledger when contract-only or
promotion-eligible. All completion identities below bind final committed code, not an intermediate worktree,
temporary output or synthetic quality result.

## Frozen contract surface

The implementation in `praxis_virtualcell/benchmarks/system.py` consists of strict, frozen Pydantic contracts and
canonical JSON SHA-256 fingerprints. The principal surface includes:

- `BenchmarkScopeV1`, `DatasetBindingV1`, `BenchmarkSplitV1`, `BenchmarkBaselineV1` and
  `BenchmarkMetricV1`;
- `PairedCIPolicyV1`, `ThresholdPolicyV1`, `CalibrationPolicyV1`, `OODGateV1`, `ExternalPolicyV1` and
  `PromotionGateV1`;
- `BenchmarkProtocolV1`, `BenchmarkRunAuthorizationV1` and `BenchmarkRunV1`;
- `GroupIdentityV1`, `LeakageAuditV1`, `ReliabilityRowV1` and `ThresholdReceiptV1`;
- `PrimaryMeasurementRowV1`, `SeedResultV1`, `GroupMetricValueV1`, `PairedCIResultV1` and
  `PrimaryResultV1`;
- `CalibrationBinV1`, `ScalarCapabilityV1`, `OODResultV1`, `BenchmarkCapabilityProfileV1` and
  `ExternalResultV1`;
- `BenchmarkResultV1`, `BenchmarkPromotionEvidenceV1` and `BenchmarkEvidenceBundleV1`;
- `BenchmarkLedgerEntryV1`, `BenchmarkLedgerHeadV1`, `StoredBenchmarkEvidence` and
  `BenchmarkEvidenceLedger`;
- `audit_group_leakage()`, `select_validation_threshold()`, `compute_p21b_execution_fingerprint()`,
  `derive_evidence()` and `replay_checked_in_benchmarks()`.

Unknown fields, duplicate JSON keys, non-finite values, malformed hashes, stale nested identities, missing groups,
non-canonical row ordering, non-reproducible summaries and caller-edited derived status fail closed. Validation
errors are sanitized and do not echo arbitrary untrusted values.

## Pre-result protocol and biological split freeze

`BenchmarkProtocolV1` binds scope, Pack, internal and external dataset/platform identities, feature/output
contracts, biological split, simple train-only baseline, primary metric direction, seeds, paired-CI policy,
validation-only threshold policy, calibration, OOD, zero-adaptation independent external policy and all promotion
gates. It requires `candidate_result_observed=false`, `frozen=true` and `composite_score=null`; P21A defines no
composite quality score.

The split contains the exact validation/test/external group IDs, counts and canonical set fingerprints. Its frozen
leakage identity covers records across train, validation, test and external, including group ID, donor, condition,
replicate and batch. A passing `LeakageAuditV1` embeds the canonical records themselves and must reproduce both its
own fingerprint and the protocol-bound count/fingerprint. Re-signing altered non-overlapping records cannot detach
the audit from the frozen protocol. Any cross-partition biological identity overlap fails before evaluation.

## Exact P20 candidate, execution and authorization binding

The benchmark run binds the complete P20 candidate chain: training job/result, checkpoint, artifact, model card,
candidate model, factory registration, Pack, feature/output contracts, trainer source and training environment. It
also binds adapter and compatibility receipts, evaluation environment/code, Broker contract and runtime receipt.
The execution path is fixed to `model_adapter_broker_runtime`, with direct model invocation and direct asset access
forbidden. These fields are a formal receipt contract only; P21A did not execute a model, adapter, Broker or runtime.

`BenchmarkRunAuthorizationV1` content-binds its exact run payload, protocol, scope, candidate, asset manifest and
output-root identity. Authorization and run fingerprints prove identity/content integrity, not issuer
authentication. A caller cannot turn a self-authored record into trust merely by making its hashes internally
consistent.

For an authorized-candidate result, P21A computes `vc.p21b-execution-identity.v1` over three exact identities:

~~~text
authorization fingerprint + complete run fingerprint + final result fingerprint
~~~

The P21B consumer must pin that composite independently and pass the exact expected value out of band. Missing
trust yields `p21b_execution_not_verified`; a mismatched trusted value fails closed. Because the result fingerprint
is part of the composite, an authorization alone cannot authenticate an unknown future result and cannot be reused
as a bearer token.

`BenchmarkEvidenceBundleV1` is deliberately self-contained but untrusted. It serializes protocol, run, result and
the negative-by-default evidence derivation; it does not serialize a trust bit or trusted execution fingerprint.
Loading or reconstructing a bundle re-derives evidence without P21B trust. Only the consumer-side
`derive_with_p21b_execution()` path accepts the independently pinned composite for the current evaluation.

## Deterministic measurement and gate reproduction

Completed results embed the exact records needed for reproduction rather than trusting summaries:

- group×seed candidate, baseline and paired-difference rows for test and external primary results;
- canonical biological-group differences and paired-CI inputs;
- canonical validation reliability rows and the selected threshold receipt;
- canonical test selective rows;
- observed calibration bins and OOD values for every frozen test group;
- the external leakage audit and full external evaluation receipt.

Canonical means use `math.fsum`. Primary summaries and per-seed/per-group values are rebuilt from embedded rows.
Paired intervals reproduce through the frozen P8 helper with `0.95` confidence, `2,000` replicates, seed `0`,
`numpy.PCG64` and linear quantiles. Threshold selection is validation-only and reuses the public P9
`select_threshold`; test selective values reuse P9 `selective_metrics`. Calibration and OOD aggregates are rebuilt
from their bins/group values, and each content receipt is re-hashed.

The decision plane re-derives primary paired difference and CI bounds from the embedded records. This blocks
summary-only or floating-tolerance changes from turning ties into improvements. Exact dataset, split, group-set,
baseline, metric, candidate, runtime, seed, threshold and external bindings are checked again while evidence is
derived.

`derive_evidence()` keeps three states distinct: internal `benchmark_passed`, independent
`scientifically_validated`, and gate-complete `promotion_eligible`. It never produces operator policy or a
`production_promoted` state. A contract fixture remains contract-only even when its synthetic measurements would
otherwise pass.

## Frozen P8/P9 compatibility boundary

`replay_checked_in_benchmarks()` performs a read-only, exact-size/exact-SHA replay from an explicit absolute
canonical repository root. It re-opens the P9 files after validation so an identity change during the check is
detected.

- P8 remains a historical inventory with availability/benchmark/promotion unbound and science false. It is not
  converted to negative evidence and is not appended to the ledger.
- P9 remains the exact negative/unbound validation result with the original
  `primary_not_better_than_baseline` and `primary_ci_not_below_zero` reasons. The exact accepted legacy receipt
  fingerprint is `a03d455b97994c27fb7f0b5e1b2f31d4014993a46d503a8c15826def7f6fab62`.

This is compatibility identity/status verification in memory and pytest temporary state. It is not a published
replay, a new scientific run or a substitute for the missing exact historical output-root authorization.

## Negative-only durable ledger

`BenchmarkEvidenceLedger.create()` requires an explicit absolute canonical write-new root. It creates a randomized
`0700` sibling staging directory, retains parent/staging descriptors and inode identities, writes and fsyncs the
marker, empty durable head, stable lock and entries directory, then publishes with an atomic no-replace rename.
An existing target, symlink, replaced staging inode or unsupported no-replace platform fails closed.

Append uses a stable held lock, held entries descriptor, canonical content-addressed entry, exclusive staging/link,
fsync, predecessor hash chain and durable head. Verification reconstructs sequence, chain, logical IDs,
protocol/run/authorization ID-to-content bindings, result/run uniqueness and single-use authorization. A crash
after publishing exactly one valid entry but before updating the head can be recovered under the append lock;
other head/entry disagreement is rejected as truncation or tamper.

The ledger accepts only an authorized-candidate bundle whose untrusted serialized evidence is not promotion
eligible, or the exact P9 legacy negative receipt. Contract fixtures, P8 null history, promotion-eligible bundles,
conflicting logical identities, duplicate run/results and reused authorization are rejected.

The durable head detects tail truncation and removal of all entries while the head remains. Hash chain plus head
cannot detect whole-ledger rollback or deletion when the attacker restores/removes both entries and head; that
guarantee requires an external or signed anchor.

Failed initialization keeps the final target absent and intentionally does not recursively delete by pathname.
A randomized `0700` staging directory may remain. Manual recovery must first quiesce writers, hold and recheck the
exact inode, owner and mode, inspect only the expected non-symlink marker/head/lock/entries content, and repeat all
identity checks immediately before any separately authorized recovery or cleanup. An identity change means stop;
a replacement directory must remain untouched.

## Frozen fail-closed coverage

Directed tests cover strict protocol schemas; protocol/run/result cross-binding; leakage-record drift and overlap;
validation-only threshold selection; deterministic primary/CI/selective/calibration/OOD/external reproduction;
tiny negative, contract-only and transient positive gate states; missing/mismatched out-of-band P21B execution
trust; full-bundle tamper and model-copy revalidation; exact P8/P9 compatibility replay; and ledger write-new,
symlink, collision, inode-swap, chain/head tamper, truncation, crash-tail recovery, logical-ID conflict, duplicate
run/result, authorization reuse, P9-only legacy admission and positive/fixture rejection.

## Validation bound to completion bytes

| Gate | Frozen result |
|---|---|
| focused P21A suite | `35 passed` |
| affected benchmark/registry/training/runtime matrix | `238 passed` |
| safe Python gate | `1,645 passed, 49 skipped, 387 deselected in 285.21s` |
| legacy gate | `1,147 passed, 58 skipped, 105 deselected in 61.52s` |
| full Ruff lint / targeted format / `py_compile` / diff check | PASS |
| reproducible packaging / archive integrity | PASS; exact evidence below |

The safe gate excluded Golden/GEM/Norman science and the unavailable optional MuData test by the existing local
policy. No missing dependency was installed and no skip was reported as a pass. The test matrix read no real raw,
test or external data and ran no real candidate, training, GPU, remote or network work.

## Packaging evidence and limitations

| Property | Frozen result |
|---|---|
| wheel size | `1,202,180` bytes |
| wheel SHA-256 | `ee98d4b3c6895bb6a91be1c439a0f927050cb813e9f7e5c61a37552a15c326f1` |
| archive / React / test / AppleDouble entries | `371` / `14` / `0` / `0` |
| `system.py` source/wheel SHA-256 | `583d14434216c26ddffa170e2c35f24963f03461d4e9f10c3fe105073624c4d0`; exact match |
| ZIP integrity / reproducibility | PASS; two wheels byte-identical |

Two independent builds started from separate `git archive` trees of completion SHA with
`SOURCE_DATE_EPOCH=1786050825`. Frontend installation used the existing npm cache in explicit offline mode. Python
packaging used the already-installed local build frontend with no isolation and dependency checking skipped. No
download or network fallback occurred. This proves byte reproducibility and content integrity for the exact local
source/toolchain boundary; it is not a pinned dependency-closure, clean-install, publication or release proof.

Global `pip check` failed because the shared host environment was already polluted, lacked `python-magic`, and
contained pre-existing `vcbench` conflicts. That result is not a P21A gate and is not reported as passing or as new
dependency compatibility evidence.

## External, science and policy non-runs

P21A received no exact authorization for a real candidate, raw/test/external data, assets, weights, a manual
output root, training, GPU, remote host, network or private service. It performed no real benchmark, scientific
validation, operator review, revocation, promotion, push, PR, release or deployment.

All synthetic positive results are transient contract conformance only and never evidence. The formal
adapter/Broker/runtime chain is a typed receipt boundary, not an executed integration. Science remains `NOT_RUN`,
P21B/P21C remain `AUTHORIZATION_REQUIRED / NOT_RUN`, and product policy remains `NO_NEW_DECISION`.

## Closure and next eligible work

P21A is complete only on the system engineering plane. P21B may run one real exact candidate only after independent
authorization pins the full execution identity, and P21C may make product policy only after a separate operator
authorization; neither is implied by this completion.

The next eligible local work unit is P22 contract-only curated model registry. It may define schemas, provenance,
revocation and fail-closed empty/negative behavior, but P21A does not authorize importing an executable model
release or setting promotion state.

See [ADR-0018](../../docs/ADR-0018-virtual-cell-benchmark-system.md), the
[Virtual Cell Benchmark System runbook](../../docs/runbooks/VIRTUALCELL-BENCHMARK-SYSTEM.md), and the
[Phase 12–30 execution plan](../../docs/PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md).
