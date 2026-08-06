# Phase 18 — Multi-omics model-input contract completion

Work unit: P18 — strict, ordered and fail-closed multi-omics model-input engineering contract

Outcome: **P18_CONTRACT_COMPLETE_REAL_MULTIOMICS_MODEL_ACCEPTANCE_PENDING**

Starting SHA: f253664239e4b1c9665301cf1bdf4e117a3e9c31

Completion code SHA: 626c71ffd1ce18a5adc200f6a6e376e57b269beb

Completion tree: 2b570398caff6cf955d789c3cb4a7a77dc13a082

Branch at completion: codex/p18-multiomics-cell-state

## Outcome and status separation

P18 adds a strict contract-only compiler for an exact vc.request.v2 request, an exact registered
vc.pack.v0.3 multi-omics Pack, a backed canonical MuData view, ordered model feature contracts and
a caller-declared adapter identity. It produces an immutable, content-addressed multi-omics model
input plus defensive runtime matrix snapshots. It does not select or execute a model.

Status at the completion code commit:

| Plane | State |
|---|---|
| engineering | contract defined, implementation complete, focused and safe validation passed |
| science | NOT_RUN; no real model, benchmark, external validation or scientific evidence |
| product policy | NO_NEW_DECISION; no promotion or named operator decision |
| real multi-omics model acceptance | PENDING |
| registry | unchanged: 5 releases, 0 native releases, 0 production-promoted capabilities |
| artifact publication/release | none |

The exact completion status is
P18_CONTRACT_COMPLETE_REAL_MULTIOMICS_MODEL_ACCEPTANCE_PENDING. Contract completion is not
evidence that a compatible joint multi-omics model, wrapper, registry release, environment,
scientific validation or production policy exists.

Every P18 model input is explicitly non-executable and abstaining:

~~~text
executable = false
execution_performed = false
execution_step_created = false
abstain = true
abstain_reason = contract_only_execution_not_authorized
~~~

## Completion diff and frozen source identities

The exact implementation diff from the starting SHA to the completion code SHA adds two paths:

- praxis_virtualcell/multiomics_input.py
- praxis_virtualcell/tests/test_multiomics_model_input.py

No registry, wrapper, model card, checked-in Pack, external asset, dependency declaration, version,
release, deployment or policy file was changed by the P18 code commit.

| Source | Bytes | SHA-256 |
|---|---:|---|
| praxis_virtualcell/multiomics_input.py | 72,430 | b3913d7d484f989f612a6124f71c5a0158ec3c64be2707fa2f6e216e50041006 |
| praxis_virtualcell/tests/test_multiomics_model_input.py | 46,906 | dd8fe3fe8f162339a25d99bcbb89ef951a5bfe2b542eed595b8a352ba5353cc7 |

These identities are bound to completion code SHA
626c71ffd1ce18a5adc200f6a6e376e57b269beb and completion tree
2b570398caff6cf955d789c3cb4a7a77dc13a082.

## Implemented contract surface

The implementation defines strict, frozen v1 contracts for:

- vc.multiomics-modality-slot.v1 — one ordered required or optional modality slot;
- vc.multiomics-input-contract.v1 — the joint model, biological scope, outputs, modality order,
  target modality, join policy, missingness policy and normalization policy;
- vc.multiomics-layer-input.v1 — one present or explicitly absent typed layer with observation,
  alignment, shape, storage and matrix identities;
- vc.multiomics-observation-semantics.v1 — observation-aligned condition, split, cell,
  perturbation, matched-control, dose and time semantics;
- vc.multiomics-model-input.v1 — the self-bound request, Pack, view, contract, adapter, join,
  missingness, layer and abstention identity;
- vc.multiomics-observation-join.v1 — deterministic join identity;
- vc.multiomics-missingness.v1 — deterministic missingness identity;
- vc.multiomics-view-identity.v1 — Pack-, observation-, semantics- and modality-bound view
  identity;
- vc.multiomics-matrix.v1 — deterministic dense/CSR/CSC runtime matrix content identity.

PreparedMultiOmicsModelInput pairs the serializable contract identity with separately held
defensive matrix snapshots. All nested P18 objects are revalidated as exact canonical types;
unknown fields, subtypes, non-JSON values, stale fingerprints and coherently re-signed but
inconsistent or invalid adjacent bindings fail closed.

## Ordered modality and target contract

The joint contract requires at least two ordered slots with unique keys and unique modality
identities. Every slot binds:

- required versus optional state;
- exact modality name and ontology identity;
- matrix:X representation;
- exact model feature contract and its fingerprint;
- the same model name/version, taxonomy and assembly as the joint contract.

The target modality must be an explicitly required slot and must be present at compilation time.
At least two distinct contract layers must be present. A single-tensor adapter contract cannot
authorize a joint input.

An optional modality may be absent only as a typed absent layer. Such a layer has no observation
IDs, alignment report, matrix fingerprint, storage format or shapes. P18 never fabricates an
optional matrix to make a contract appear complete.

The compiler accepts only these policy pairs:

| Join policy | Missingness policy | Behavior |
|---|---|---|
| required_inner | reject | use only real observations shared by every present contract layer |
| global | explicit_mask | preserve each local matrix and expose exact membership masks over the real union |

For required_inner, input rows are selected from real source rows in canonical global observation
order. For global, matrices retain their own real local rows; masks describe membership but never
cause row padding. Zero-valued rows remain observed rows and are never reinterpreted as missing.

## Pack, view and observation semantic binding

Compilation requires an exact RegisteredPack whose fingerprint equals its embedded vc.pack.v0.3
manifest. The Pack must declare multi-omics modalities and an exact perturbation target modality.

The CanonicalMuDataView and every CanonicalModalityView must:

- have exact canonical dataclass types;
- remain backed;
- carry the exact Pack manifest fingerprint and manifest semantics;
- preserve Pack modality keys and order;
- preserve global and per-modality observation membership and order;
- use matrix location X and an actually matching dense, CSR or CSC storage format;
- match Pack taxonomy, assembly, modality ontology, feature namespace/version, feature format and
  declared feature width;
- make global observations equal the real modality union;
- make shared observations equal the real modality intersection;
- contain every global observation in every modality when pairing is declared paired.

Observation semantics bind conditions, splits, cell identity/state/context, perturbation
IDs/kinds/targets, matched controls, dose value/unit, time value/unit and split name in global
observation order. P18 checks equal cardinality, Pack declarations, canonical dose/time units,
condition-definition consistency, control self-matching, available matched-control context and
target-ID split leakage. Semantic changes alter the observation and view fingerprints.

## Per-layer feature alignment and request target identity

Every present layer is aligned independently through the existing explicit feature-alignment
contract. The alignment report is embedded and fingerprinted and must prove exact source and
target feature identities, source and target shapes, operation ordering and mapping-asset
identity.

Feature mappings are accepted only through an explicitly declared Pack JSON asset whose path,
media type and SHA-256 match the model feature contract. The mapping file is resolved inside the
Pack root and its bytes are checked during alignment. P18 permits explicit alias, drop, aggregate
and reorder provenance for matrix alignment, but forbids every fill step.

Request perturbation targets remain Pack source-feature identities. P18 requires:

- request kind gene for exactly one target or gene_combination for multiple targets;
- exact ordered genetic target declaration in the Pack;
- exact Pack perturbation target modality;
- each source target to exist in the target layer;
- identity or explicit alias proof from the Pack source target to a model feature;
- no dropped target;
- no aggregate-derived perturbation target identity;
- no collapse of distinct requested targets to one model feature.

Aggregate alignment is therefore allowed for matrix preparation but cannot be used to claim exact
perturbation-target compatibility. A request using the mapped model ID instead of the declared
Pack source ID also fails closed.

Request dose value and unit must either both be absent or both be present. Present dose units reuse
the canonical P5 dose-unit set. Generic request units such as count, h or TPM cannot be smuggled
into a dose field.

There is no implicit gene-symbol lookup, ortholog conversion, unit conversion, feature fallback,
normalization, clipping, fill, deduplication, reordering outside an explicit report, padding or
imputation.

## Join, missingness and matrix identity

Every layer records source observation IDs, input observation IDs, a joined-observation mask,
alignment report and fingerprint, source/aligned/input shapes, storage identity and matrix
fingerprint. The root model input independently binds:

- ordered global observation IDs;
- deterministic joined observation IDs;
- join fingerprint;
- missingness fingerprint;
- ordered typed layers;
- observation semantics and view fingerprints.

The serialized model-input contract contains no matrix or matrices payload. Numeric arrays remain
separate runtime data and are bound by matrix fingerprints covering storage kind, little-endian
dtype identity, shape and exact canonical bytes.

PreparedMultiOmicsModelInput accepts only ordered keyed matrices for present slots. Runtime
matrices must be non-empty, two-dimensional, finite numeric dense, canonical CSR or canonical CSC
data. Their storage, shape and content fingerprints must match the layer identities.

Accepted matrices are copied into immutable byte-backed snapshots. Each matrices property access
materializes a fresh defensive view, so caller mutation cannot change the stored snapshot or its
fingerprint. Sparse index ordering and duplicate indices are rejected. Matrix values, dtype,
shape or dense/CSR/CSC storage changes alter identity or fail replay.

This is runtime input preparation only. Matrix snapshots are not serialized, published, stored as
model artifacts or evidence, and no matrix is passed to a wrapper or model.

## Adapter, Broker and execution boundary

The adapter identity is caller-declared data. P18 requires an exact AdapterIdentity that is not
legacy-incomplete and whose input-contract fingerprint, task and outputs exactly own the joint
contract. P18 does not resolve that identity through ModelRegistryV2, CapabilityRegistry or an
adapter registry and therefore does not prove that an implementation is installed, loadable,
executable, validated or promoted.

The fields:

~~~text
broker_agent = ModelBrokerAgent
broker_resolution = identity_only_not_registry_evaluated
~~~

are closed contract-only markers. They do not mean ModelBrokerAgent.plan or another Broker method
was called. No Broker registry evaluation occurred.

P18 does not import, instantiate, prepare or invoke a wrapper or model. It creates no execution
plan or execution step, returns no prediction, computes no scientific metric and changes no
registry, evidence or product-policy state.

## Fail-closed and adversarial coverage

Focused tests cover:

- strict ordered slot parsing and exact nested types;
- paired and partially paired observations;
- required-inner and global/explicit-mask behavior;
- real zero rows versus missing observations;
- malformed, duplicate, foreign or ambiguously ordered observation membership;
- required/optional modality absence and target-modality presence;
- at least two present modalities and rejection of single-tensor adapter identity;
- forbidden implicit normalization, fill, padding and imputation;
- exact per-layer modality, ontology, taxonomy, assembly, namespace and feature-format binding;
- explicit mapping asset path/hash/media identity and alignment provenance;
- source-target alias acceptance, mapped-ID request rejection, aggregate-target rejection and
  dropped-target rejection;
- exact request task, outputs, species, Pack, perturbation kind/cardinality, targets and dose
  units;
- condition, split, matched-control, dose/time and perturbation semantic tampering;
- observation join, mask, alignment, Pack, view, request, adapter and model-input re-signing;
- dense, CSR and CSC matrix storage, values, shape, finiteness and canonical sparse identity;
- runtime matrix mutation isolation and replay;
- broker/execution literal tampering;
- Pydantic model_construct, subtype, undeclared-field and non-JSON bypass attempts.

No remaining P1/P2 contract finding was retained after final read-only review.

## Validation bound to completion bytes

All validation was local and used no network, external scientific assets, model weights, LLM, GPU,
remote service or scientific runner.

| Gate | Result |
|---|---|
| focused P18 suite | 44 passed |
| adjacent contract suites | 259 passed |
| safe broad gate | 1,531 passed, 48 skipped, 387 deselected |
| Ruff check | passed |
| Ruff format check | passed |
| changed-source py_compile | passed |
| diff check | passed |

The optional mudata test module could not collect because mudata was not installed. It was not
installed from the network, and the collection error is not reported as a passing gate.

Global pip check is not authoritative P18 evidence because the shared environment is polluted by
pre-existing invalid distributions and dependency conflicts.

The focused fixtures are tiny deterministic engineering fixtures. Their successful compilation
and negative probes are contract conformance only, not scientific evidence for a real multi-omics
model.

## Packaging evidence and limitations

Packaging used exact completion code SHA 626c71ffd1ce18a5adc200f6a6e376e57b269beb and
SOURCE_DATE_EPOCH=1786027377. Two independent offline clean-archive builds produced
byte-identical wheels:

| Property | Result |
|---|---|
| wheel size | 1,132,811 bytes |
| SHA-256 | 015724a90656706c0441e4f4f873ee51f8db87dfaae9de35a3e841e7c70b2b7c |
| archive entries | 367 |
| React static entries | 14 |
| test entries | 0 |
| AppleDouble / __MACOSX entries | 0 |
| praxis_virtualcell/multiomics_input.py | present; bytes and SHA-256 match completion source |

The official strict offline packaging script failed closed because its isolated cache lacked
packaging 26.2. No network fallback or download was attempted.

A clean no-deps smoke failed at package import because pydantic was absent. This does not establish
dependency closure. A no-deps smoke inheriting the polluted system site passed package import,
all 14 static React entries and CLI startup, but it is explicitly non-authoritative.

The wheel was not pushed, published, tagged, released or deployed.

## Science, policy and registry state

Science remains NOT_RUN. P18 did not run a real joint multi-omics model, benchmark predictive
quality, compare a baseline, calculate confidence intervals, evaluate OOD behavior, validate an
external dataset, establish generalization or create evidence.

Product policy remains NO_NEW_DECISION. No named operator reviewed or promoted a P18 capability.
The registry remains unchanged at 5 releases, 0 native releases and 0 production-promoted
capabilities.

Accordingly, none of the following is claimed:

- that arbitrary multi-omics cells can be predicted;
- that any real RNA/protein/ATAC combination is scientifically supported;
- that a caller-declared adapter exists or is executable;
- that ModelBrokerAgent or a registry accepted the request;
- that a wrapper or model consumed the prepared matrices;
- that the local wheel is dependency-complete, published or released;
- that engineering conformance is scientific evidence or product approval.

## Explicitly not performed

P18 did not:

- access network or download data, weights, checkpoints or dependencies;
- read or create an external scientific/model asset;
- train, tune, benchmark, validate or execute a real model;
- invoke Golden, GEM, Norman or another scientific workflow;
- import, instantiate or call a model wrapper;
- ask a Broker, CapabilityRegistry, ModelRegistryV2 or policy engine to authorize execution;
- create evidence, promotion, operator policy or a registry release;
- normalize, fill, pad, impute or fabricate an observation or matrix value;
- alter old/**, protected repositories, external refs or Git history;
- push, open a PR, modify main or a tag, publish or release an artifact;
- deploy, restart a service, change a port, operate .53 or alter production state.

## Closure and next eligible work

P18 is complete only on the engineering contract plane. Real multi-omics model acceptance remains
pending until an exact model, environment, adapter implementation, registry binding, evidence and
named product-policy decision exist and pass their own authorized gates.

Next eligible local work unit: P19 Controlled Pack Factory, contract-only. Its permitted local
scope is:

~~~text
receipt
→ candidate
→ explicit review
→ strict validation
→ operator register
~~~

P19 may define and test that controlled workflow, but it must not train a model, create a real
checkpoint, invent evidence or make an operator promotion decision.
