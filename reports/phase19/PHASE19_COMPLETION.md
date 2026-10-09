# Phase 19 — Controlled Pack Factory contract completion

Work unit: P19 — explicit, append-only and fail-closed Pack ingestion/registration contract

Outcome: **P19_CONTRACT_COMPLETE_REAL_EXTERNAL_FIXTURE_OPERATOR_SCIENCE_POLICY_NOT_RUN**

Starting SHA: 871c5a8a4265f5b8fe5c2c6e35d418644bf1c4be

Completion code SHA: 42eabe63ea1a444d8b2ad14cecba6c9d6fa351d5

Completion tree: b4bd63833adc89bd1e30e9595d2cb6b38a3e005f

Source date epoch: 1786034362

Branch at completion: codex/p19-controlled-pack-factory

## Outcome and status separation

P19 replaces path-only Pack registration with a controlled local chain that binds one immutable
P7 quarantine receipt to an operator-authored Pack candidate, complete metadata/mapping review,
strict validation report, named registration-only decision, append-only factory store and v2 Pack
index provenance. It adds a root-free read-only API/UI projection that redacts reviewer/operator
raw IDs, rationales and reasons. It does not create a model or scientific result.

| Plane | State |
|---|---|
| engineering | COMPLETE; exact completion identity and validation ledger frozen below |
| Git-external real fixture | NOT_RUN; no authorized exact path/size/hash/license/source/usage |
| authorized new output root | NOT_RUN; no external write-new ingestion window |
| real operator | NOT_RUN; test identities are synthetic contract fixtures |
| science | NOT_RUN; no model, prediction, benchmark, external or OOD validation |
| product policy | NO_NEW_DECISION; registration-only decision is not promotion policy |
| model compatibility | NOT_EVALUATED in factory records |
| execution | false |
| publication/release | none |

The completion identity is the final marker-safety code commit. Contract completion does not imply
real data acceptance, scientific validation, model compatibility, execution or product promotion.

## Implemented contract surface

The implementation defines strict/frozen identities for:

- `vc.upload-receipt.v1` — reused P7 immutable quarantine receipt;
- `vc.pack-candidate-file.v1` and `vc.pack-candidate.v1` — complete source/file/manifest/claim
  identity before validation;
- `vc.pack-factory-feature-mapping.v1` and summary/supporting mapping schemas — versioned,
  hash-bound ordered mapping audit;
- `vc.pack-factory-metadata-claim.v1` and `vc.pack-factory-metadata-confirmation.v1` — exact claim
  origin and reviewer confirmation;
- `vc.pack-metadata-review.v1` — complete canonical review decision;
- `vc.pack-validation-check.v1` and `vc.pack-validation-report.v1` — deterministic full report;
- `vc.pack-operator-decision.v1` — named `pack_registration_only` decision;
- `vc.factory-registered-pack.v1` — exact receipt→decision registration chain;
- `vc.pack-supersession.v1` — append-only replacement edge without history rewrite;
- `vc.pack-factory-store.v1` — exact initialized-store marker owned by
  `PackFactoryStore.create()`; its exact marker bytes are
  `{"schema_version":"vc.pack-factory-store.v1"}\n`;
- `vc.pack-factory-catalog.v1` — root-free projection with reviewer/operator raw IDs, rationales
  and reasons redacted;
- `vc.pack-index.v2` — Pack root plus durable factory registration/store provenance.

All factory contracts reject unknown fields and non-canonical types. JSON file loads reject
duplicate keys. Fingerprints derive from canonical JSON and every derived truth is re-created from
current local bytes before it may be stored.

## Receipt, source asset and taxon boundary

The loader re-hashes the exact P7 payload and receipt bytes and rejects extra directory members,
symlinks, non-regular files, UUID/path mismatch, hash drift or size drift. Candidate identity binds
the complete receipt tuple and exact candidate file tree.

The receipt payload must be the Pack's actual matrix or multi-omics data asset; an unused declared
asset with identical bytes cannot masquerade as the data source. P19 performs no copy-transform,
normalization, fill, imputation, deduplication, reorder, random split or identifier conversion.

Every P7 species value is routing-only. Exact taxon is taken from the candidate manifest and
separately confirmed by the reviewer. In particular, a coarse bacteria receipt never infers
*E. coli* or another exact taxonomy. The validation check is `taxon_review_binding`, not a receipt
taxonomy assertion.

## Review, mapping and validation boundary

An approval review must confirm every canonical topic in order: taxon, assembly, cell identity,
modality, feature namespace, value semantics, condition, control, unit, split, leakage group and
feature mapping. An inferred candidate claim remains only a proposal until its exact fingerprint
is confirmed.

Mappings are Pack-declared JSON assets bound by ID/version/path/size/hash, namespaces, complete
source/target feature sets, duplicate/unmapped/out-of-domain reports and order fingerprints.
Registration requires an identity-only, order-preserving, complete same-namespace mapping.

The full validation report separates strict `pack_valid` from `registration_allowed`. The latter
requires every canonical check to pass and no warning. A valid Pack with changed/undeclared files,
ambiguous mapping, missing confirmation or receipt/source drift cannot be registered.

## Operator and registration boundary

The registration decision binds exact candidate/review/report/Pack fingerprints and is limited to
`pack_registration_only`. Its scientific-evidence and product-promotion decision flags are false.
A second decision for the same Pack identity cannot silently replace the durable provenance.

The append-only store separately retains receipts, candidates, reviews, validations, decisions,
registrations and supersessions. Generic record insertion cannot persist forged validation or
registration truth; those artifacts require runtime reproduction of the entire chain.

## Explicit store/index and fail-closed commit

Registration requires an explicitly injected exact `PackFactoryStore` and an explicit absolute
Pack index in an existing canonical directory. No home/default index or inferred store may be used
for controlled writes.

`PackFactoryStore.create()` is the only supported initializer. It creates a new directory and writes the
exact `.factory-store.json` bytes `{"schema_version":"vc.pack-factory-store.v1"}\n` with
exclusive/non-following file creation, file fsync and directory fsync. `open()` byte-validates that
regular non-symlink marker and rejects arbitrary existing directories. This prevents a CLI typo
from turning a user directory into a factory output root.

`vc.pack-index.v2` adds the factory registration fingerprint and exact store root. Readers remain
compatible with v1; legacy entries acquire null factory provenance and remain readable without
being retroactively labelled factory-approved. New writes always use v2. The former
`PackIndex.register(pack_root)` path-only bypass is disabled.

The commit is intentionally consumer-fail-closed across two durable resources. The index first
records the expected registration/store identity, which is a pending state until the corresponding
registration artifact and complete chain exist in the store. Every consumer revalidates the store;
a crash between writes therefore makes the entry invalid, never trusted. After the store append,
the consumer reread proves committed state. The same exact chain can be retried without changing
identity.

## CLI migration

The removed behavior was:

~~~bash
praxis-vc pack register /absolute/path/to/pack
~~~

The P19 command requires the complete chain and both durable destinations:

~~~bash
praxis-vc pack register \
  --upload-directory /absolute/quarantine/<upload-id> \
  --pack-root /absolute/operator-authored-pack \
  --candidate /absolute/contracts/candidate.json \
  --review /absolute/contracts/review.json \
  --validation /absolute/contracts/validation.json \
  --decision /absolute/contracts/decision.json \
  --index /absolute/existing-parent/pack-index.json \
  --store /absolute/initialized-factory-store
~~~

The CLI strictly reloads and reproduces these inputs; it does not author metadata, approve a
decision or fall back to path-only registration.

## Read-only public projection

`GET /api/pack-factory` is the only public Pack Factory route. No HTTP write route exists and the
catalog fixes `write_api_enabled=false`. If no store is configured, the endpoint returns an empty
`configured=false` catalog without creating a root.

The catalog separates receipt, candidate, review, validation, decision, registration and
supersession. It omits roots/directories and reviewer/operator raw IDs, rationales and reasons;
operator identities are hashed and validation details are reduced to canonical status fields.
React presents quarantine, candidate, factory-registered, model-compatible and executable as five
separate layers and exposes no write control.

Factory registration fixes:

~~~text
factory_registered=true
pack_valid=true
model_compatible=null
environment_compatible=null
adapter_compatible=null
executable=false
training_performed=false
checkpoint_created=false
model_card_created=false
benchmark_performed=false
evidence_created=false
scientifically_validated=false
promotion_eligible=false
production_promoted=false
~~~

## Fail-closed and adversarial coverage

The focused suite covers deterministic replay, complete receipt tuple binding, actual source-asset
ownership, every review topic, full validation reports, decision tamper, source/tree drift,
mapping duplicate/order/namespace/hash/out-of-domain failures, forged derived records, append-only
supersession, second-decision conflicts, explicit initialized-store/index requirements, path-only
bypass retirement, ordinary unmarked-directory rejection, public root and reviewer/operator ID,
rationale and reason redaction, read-only HTTP routing and unknown fields. The combined adjacent
gate also covers v1→v2 index compatibility. Pending index→store consumer failure and
duplicate-key-safe JSON loading
are implementation invariants; this completion report does not mislabel them as separate directed
test cases.

## Validation bound to completion bytes

| Gate | Result |
|---|---|
| focused P19 suite | 23 passed, 1 skipped |
| combined focused + adjacent four-file gate | 108 passed, 1 skipped |
| safe Python gate | 1,554 passed, 49 skipped, 387 deselected |
| legacy gate | 1,143 passed, 58 skipped, 105 deselected |
| frontend typecheck/lint/build | passed |
| Ruff check; changed-P19-file format; py_compile; diff check | passed |
| reproducible packaging / archive integrity | passed; exact evidence below |

The one focused/combined skip is the optional positive MuData path because `mudata` is not
installed locally; it was not installed from the network and is not reported as a pass. The broad
and legacy skips/deselections preserve their existing external/optional boundaries. No real
scientific runner or external fixture was included.

## Packaging evidence and limitations

Two independent offline clean-archive builds used completion SHA
`42eabe63ea1a444d8b2ad14cecba6c9d6fa351d5` and
`SOURCE_DATE_EPOCH=1786034362` and produced byte-identical wheels:

| Property | Result |
|---|---|
| wheel size | 1,154,421 bytes |
| SHA-256 | `1231f948e6f519b9cea66e5ab0e7ccb41b3b7f5a7aa73efdd7dbaf885bfa969f` |
| archive entries | 368 |
| React static entries | 14 |
| test entries | 0 |
| AppleDouble / `__MACOSX` entries | 0 |
| `praxis_virtualcell/pack_factory.py` source/wheel SHA-256 | `06fb5267c47e8fcf8bcc596e18c9d12e3cb429b0670b662eb0b2ae448b560508`; exact match |
| ZIP integrity | passed |

This is reproducibility and content-integrity evidence, not a release or a separately claimed
dependency-closure/clean-install proof. The wheel was not published, released or deployed.

## External, science and policy non-runs

P19 did not receive or use the plan's exact Git-external fixture path, size, SHA-256, licence,
source or usage authorization. It did not receive an exact new write-only external output root.
All successful fixtures are tiny deterministic engineering fixtures under test-controlled local
temporary roots; they are not a new real species/dataset acceptance result.

No real reviewer/operator used the production workflow. Synthetic named identities prove only
binding semantics. No model, wrapper, Broker, training job, GPU, checkpoint, benchmark, test/
external result, scientific evidence, model operator policy or promotion was created or run.

P19 also did not access the network, operate `.53`, push, open a PR, modify main/tag, publish,
release, deploy or change product SemVer/API/runtime protocol.

## Closure and next eligible work

P19 is complete only on the local engineering-contract plane at the exact code/tree above. Real
ingestion and operator acceptance remain NOT_RUN; science is NOT_RUN and product policy is
NO_NEW_DECISION.

After the final P19 code identity and docs closure are frozen, P20 Training Pipeline is the next
eligible contract-only work unit. P20 may consume only an exact P19 `FactoryRegisteredPackV1` chain
and may implement tiny deterministic dry-run contracts, but it cannot infer authorization for real
training, checkpoint publication, benchmark evidence or promotion.

See [ADR-0016](../../docs/ADR-0016-controlled-pack-factory.md) and the
[Controlled Pack Factory runbook](../../docs/runbooks/VIRTUALCELLPACK-CONTROLLED-PACK-FACTORY.md).
