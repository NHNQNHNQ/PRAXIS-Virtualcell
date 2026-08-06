# Phase 22 — Curated Virtual Cell Registry completion report

Work unit: P22 — operator-curated, content-addressed Virtual Cell Registry contract

Outcome: **ENGINEERING COMPLETE — CONTRACT_ONLY**

Starting / documentation-parent SHA: 09792e13e29a76b5e4434507f3334eefb947789c

P21A prerequisite code SHA: 20ecc12542e5df40c90d1fc367dbe86b563478b8

Completion code SHA: bca5ad661856e8d9aa832c47f23c6ad7179ee0c9

Completion tree: f78476ac1dbe2f865e3c1bcdc71ecc512dbad22a

Source date epoch: 1786056220

Branch at completion: codex/p22-virtual-cell-registry

## Outcome and status separation

P22 adds the local engineering contract for composing an already evidenced and promoted One-Pack/P21B Virtual
Cell release, admitting it only through independently supplied operator trust, and maintaining append-only catalog
lifecycle. It does not create scientific evidence, product policy, installation state or executable runtime state.

| Plane | State |
|---|---|
| engineering | `COMPLETE — CONTRACT_ONLY`; exact code/tests/package evidence frozen below |
| default registry | absent; newly created registry is empty and deny-all |
| real release import | NOT_RUN |
| real catalog / quarantine / revoke / supersede | NOT_RUN |
| P21B / P21C | `AUTHORIZATION_REQUIRED / NOT_RUN` |
| scientific validation | NOT_RUN; P22 creates none |
| product policy | `NO_NEW_DECISION`; P22 creates none |
| HTTP / UI / Data Center / chat / job / runtime binding | NOT_IMPLEMENTED / NOT_RUN |
| installation / compatibility / execution | unknown / unknown / false |
| data / assets / weights / training / GPU / remote / network | NOT_RUN |
| publication / push / release / deploy | none |

The positive release and operator allowlists used by tests are transient synthetic conformance fixtures in pytest
temporary roots. They are not real evidence, operator decisions, catalog entries or completion artifacts. All
completion identities bind the committed implementation, not a test root or synthetic release fingerprint.

## Frozen contract surface

The implementation in `praxis_virtualcell/model_zoo/curated_registry.py` uses strict frozen Pydantic contracts and
canonical JSON SHA-256 identities. Its principal surface includes:

- `VirtualCellContextV1`, `WrapperApprovalV1` and `VirtualCellReleaseV1`;
- `build_virtual_cell_release()` and `compute_curated_import_fingerprint()`;
- `CuratedRegistryDecisionV1`, `CuratedRegistryEntryV1` and `CuratedRegistryHeadV1`;
- `CuratedRegistryTrustV1`, `CuratedReleaseStateV1` and `StoredCuratedRegistryEntry`;
- `CuratedVirtualCellRegistry.create()`, `open()`, `verify()`, `checkpoint()`, `import_release()` and
  `record_decision()`;
- `release()`, `state()`, `public_catalog()`, `query()` and `dependency_graph()`.

Unknown fields, malformed hashes, duplicate JSON keys, non-canonical bytes, stale nested identities, conflicting
logical IDs, unauthorized records, sequence/predecessor drift, head mismatch and pathname/inode replacement fail
closed. Validation errors do not echo arbitrary untrusted input values.

## Exact One-Pack/P21B v1 release closure

`VirtualCellReleaseV1` binds one exact context and one exact P19 `FactoryRegisteredPackV1` to one native P12
`ModelRegistryV2` release. The source registry must contain exactly one release, no prior lifecycle events, one
positive validation-evidence record and an exact promoted operator policy. The release also embeds the complete
P21A benchmark bundle and requires its P21B composite execution identity to reproduce.

The closure cross-checks Pack registration, model/card/artifact/environment/adapter identities, benchmark scope,
protocol/run/result, baseline and metric, validation evidence, P21C policy, reviewed wrapper source/entrypoint,
OOD and abstain policies, license/source/publisher/reviewer metadata, and a canonical full dependency set. Every
nested P12/P19/P21A object is reloaded through its exact contract before acceptance.

License/source/publisher/reviewer fields are curated metadata bound into the exact import identity. P22 validates
their contract and credential-free HTTPS URI syntax, but does not fetch the source or live-verify license,
publisher or source truth.

This first version is deliberately One-Pack/P21B-only. Multi-Pack releases, direct P14–P16 evidence/policy imports,
non-P21B evidence routes and other future closure shapes are deferred. P22 cannot accept arbitrary hashes as a
substitute for those contracts.

P22 composes pre-existing truth only. It never derives or changes `benchmark_passed`,
`scientifically_validated`, `promotion_eligible` or `production_promoted`. The synthetic fixture constructs a
positive source registry solely to exercise the acceptance boundary; that state is not persisted outside pytest.

## Operator trust and authentication boundary

The default `CuratedRegistryTrustV1.deny_all()` has empty import and decision allowlists and an empty checkpoint.
An import must match an independently provided exact `vc.curated-virtual-cell-import-identity.v1`. Every lifecycle
decision must independently match its decision fingerprint. The stored authorization reference binds authority ID,
authorization kind and exact subject, making the provenance stable across reopen and retry.

These fingerprints prove content identity, not issuer authentication. A self-consistent release, candidate-provided
allowlist or caller-authored trust object is not sufficient. Authentication and secure storage of the operator
allowlist/checkpoint remain outside this module.

An externally persisted checkpoint authenticates an exact prefix. Entries after that prefix are reauthorized one
by one against the configured authority, so a suffix written under another authority is rejected even if its own
hash chain is valid. `checkpoint()` verifies and returns the local tail; it does not persist or advance the external
trust record.

Local head and chain detect ordinary truncation and an unanchored tail. They cannot detect an attacker who restores
both entries and head to an older coherent state. An independently stored checkpoint detects that rollback only if
it was advanced through the later entry, especially a revocation. Until then, revocation rollback remains a known
risk.

## Catalog-only lifecycle

Every trusted import begins quarantined. `approve_catalog` and later `quarantine` may change visibility; `revoke`
and `supersede` are terminal. Supersession requires two active cataloged versions of the same Virtual Cell ID and
leaves the target active. The original release bytes and imported science/policy remain unchanged throughout.

The decision contract fixes its effect to `catalog_metadata_only` and forces science change, policy change, asset
installation and execution flags to false. The same Virtual Cell ID/version may never bind different bytes, even
after revocation. Decision IDs also cannot be reused with different content.

## Append-only local store

Registry creation requires an explicit absolute canonical write-new root. A randomized sibling staging directory
is set to `0700`; marker, empty head, stable lock and entries directory are written and fsynced before an atomic
no-replace rename publishes the exact held inode. Existing targets, symlinks, noncanonical parents and unsupported
publication paths fail closed.

Append holds stable layout descriptors and an exclusive lock, writes canonical content-addressed entries through
exclusive staging/link, fsyncs the entries directory, and atomically updates the durable head. Reads take a shared
lock and revalidate root, entries and lock identities, marker, canonical entry bytes, strict JSON, chain, logical
IDs, lifecycle and authorization provenance on every operation.

A retry of the exact trusted record with the same authorization provenance may recover one entry published before
a head-update failure. A different record, different authorization or ordinary verification does not silently
repair it.

Before publication, write-new failure leaves the final target absent and may retain the randomized `0700` staging
directory. If no-replace publication succeeded and a later fsync/post-publication verification failed, the final
target may instead remain. The library recursively deletes neither kind of residue through an untrusted pathname.
Any separately authorized manual recovery must quiesce writers and recheck exact inode, owner, mode and
non-symlink contents immediately before action.

## Python-only redacted public projection

`public_catalog()`, `query()` and `dependency_graph()` expose a read-only Python projection. It redacts local paths,
artifact/cache source details, source URI, license detail, wrapper entrypoint, operator/reviewer identity and decision reason.
Inactive releases are hidden by default.

The projection fixes `write_api_enabled=false` and `executable=false`. Asset installation and
model/environment/adapter compatibility are `null` because P22 neither checks nor changes them. Any visible
benchmark/science/policy booleans are copied from the already imported immutable source truth; catalog operations
cannot change them.

No HTTP endpoint, UI, Data Center/chat/job binding, execution-plan integration, installation or runtime execution
was implemented or exercised in P22.

## Frozen fail-closed coverage

Directed tests cover strict/frozen release reproduction; stale/mixed closure and credential-bearing URI rejection;
empty/negative source registry rejection; default-deny trust; quarantine-first idempotent import; catalog,
quarantine, terminal revoke and supersede transitions; permanent ID/version binding; science/policy/install/execute
decision invariants; public redaction; read-only query/dependency graph; canonical write-new and symlink rejection;
duplicate-key, noncanonical, chain/head, truncation and unexpected-entry tamper; reopen/read revalidation;
external-checkpoint rollback detection; foreign-authority suffix rejection; lock and pathname identity checks;
exact-tail recovery; authorization provenance; collision/partial failure; failed initialization; no network/dynamic
wrapper import; and deterministic bytes across two stores.

## Validation bound to completion bytes

| Gate | Frozen result |
|---|---|
| focused P22 suite | `35 passed in 43.55s` |
| affected registry/benchmark/Pack/runtime matrix | `289 passed, 1 skipped in 64.94s` |
| safe Python gate | `1,680 passed, 49 skipped, 387 deselected in 334.23s` |
| legacy gate | `1,147 passed, 58 skipped, 105 deselected in 60.48s` |
| full Ruff excluding `old` / targeted format / `py_compile` / diff check | PASS |
| reproducible packaging / archive integrity | PASS; exact evidence below |

The safe gate followed the existing local policy by excluding Golden/GEM/Norman science and the unavailable
optional MuData test. The one affected-matrix skip was not reported as a pass. The matrix accessed no real release,
data, evidence, asset, weight, model, external service or network.

## Packaging evidence and limitations

| Property | Frozen result |
|---|---|
| wheel size | `1,217,155` bytes |
| wheel SHA-256 | `3f978e9f3eb06ea17017c1838002762f28ae717ee08d987cfb8ea059162a2485` |
| archive / React / test / AppleDouble entries | `372` / `14` / `0` / `0` |
| `curated_registry.py` source/wheel SHA-256 | `9678b2460aff6738935a2728e12abf398985c4475d66be96d37a721a21bf62ff`; exact match |
| ZIP integrity / reproducibility | PASS; two wheels byte-identical |

Two independent builds started from separate `git archive` trees of completion SHA with
`SOURCE_DATE_EPOCH=1786056220`. Frontend installation used the existing npm cache in explicit offline mode. Python
packaging used the already-installed local build frontend with no isolation and dependency checking skipped. No
download or network fallback occurred.

The observed toolchain was Python 3.13.12, build 1.5.0, setuptools 70.2.0 and packaging 26.0; Node 25.8.2, npm
11.11.1 and Vite 8.1.2. This proves byte reproducibility and content integrity for the exact local
source/toolchain boundary. It is not pinned dependency closure, a clean install, publication, release or deployment
proof.

## External, science and policy non-runs

P22 received no exact authorization for a real release, P21B evidence, P21C policy, registry output root, catalog
decision, data, asset, weight, installation, runtime, GPU, remote host or network. It performed no real import,
catalog approval, quarantine, revoke, supersede, scientific validation, operator promotion, push, release or deploy.

The repository default remains absent/empty. Synthetic positive closure and lifecycle tests are contract
conformance only. Science remains `NOT_RUN`, policy remains `NO_NEW_DECISION`, and P21B/P21C remain
`AUTHORIZATION_REQUIRED / NOT_RUN`.

## Closure and next numbered gate

P22 is complete only on the contract engineering plane. A real import still requires independently authenticated
exact release/evidence/policy identities, operator allowlists, an external checkpoint and an explicitly authorized
write-new root.

P23A is the next eligible local contract-only work unit. It may implement only a sender-to-receiver
`interaction_evidence_score` contract and synthetic conformance; it must not emit receiver response or causal
claims. Real release/data/asset/execution inputs remain separately gated, and optional P23B requires independent
authorization.

See [ADR-0019](../../docs/ADR-0019-curated-virtual-cell-registry.md), the
[Curated Virtual Cell Registry runbook](../../docs/runbooks/VIRTUALCELL-CURATED-REGISTRY.md), and the
[Phase 12–30 execution plan](../../docs/PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md).
