# PRAXIS-VirtualCell Versioning Contract

> Status: `P17_CONTRACT_COMPLETE_REAL_MULTI_MODEL_ACCEPTANCE_PENDING_P18_ELIGIBLE — LOCAL_REPORT_1.6.0_WITH_KNOWN_TAG_DRIFT`
>
> Local baseline: branch `codex/p17-virtual-cell-brain`; P17 starting SHA
> `ff525a0611901df422161a7143ebfe9d1e051008`; code SHA
> `16636f1b2c36e0a0fabb782a662b5b3b934891e0`; tree
> `321a59eed44c45bf2bb8798714352b3303b92e58`
>
> Workspace: `/Volumes/T7/PRAXIS-virtualcell`; Git metadata:
> `/Users/mzy/Projects/.PRAXIS-virtualcell-gitdir`

The repository historically mixed product release tags, package metadata, API/runtime labels, message schemas, governance artifacts, and model revisions. C2 implements the separation below; publication status remains governed independently by the three-way synchronization ledger.

## Current observed surfaces

| Namespace | Current value | Source | Meaning |
|---|---|---|---|
| P11B product code | anchor `bf44aac25b993e49d0146ccd52dddad5c2fa14de` | immutable local Git history | completed Cell-first product code; not P12 or a release identity |
| P12 Model Zoo v2 work unit | start `b19c896202bea56f894d0ad540501331af42a40c`; completion `1a5464fb0d2d9e105058f6797d92efd69783e5b2` | immutable local Git history plus `reports/phase12/PHASE12_COMPLETION.md` | engineering complete; no science run or new operator decision |
| P13 Model Adapter SDK work unit | start `f83c13db386cb552b3ce7a5643e5ffbead0ff573`; code `744d0a28d2cfc13d1b10e85b133b6c13b9426174`; tree `198e623120688d3704b9312990ddaa93c9a7b0e6` | immutable local Git history plus `reports/phase13/PHASE13_COMPLETION.md` | engineering complete and P14E-eligible; `Science: NOT_RUN`, `Policy: NO_NEW_DECISION`, no release/version bump |
| P14E E. coli growth contract work unit | start `0b193310009d6e4d2ebc0fc8abf95da20a56acdb`; prerequisite `c3401450fd79f7829c438d6b55c1902ea2f4cf5f`; code `8778e93c31c2dfe1ef0f77f06e7a80a425633736`; tree `fa85e049bb36f3fbd8e6d4a7503e4b5837ed7c78` | immutable local Git history plus `reports/phase14e/PHASE14E_COMPLETION.md` | contract engineering complete and P15E-eligible; P14R authorization required/not run; P14B not run; no real GEM, science, policy, release or version bump |
| P15E yeast deletion-fitness contract work unit | start `0ff6870a70a04d71098a16875e633f909e31cc5a`; code `62480a3951173a2aa7b006403af9b169521db138`; tree `64906691c4c989a843df4da97f0a93f32cd65ad2` | immutable local Git history plus `reports/phase15e/PHASE15E_COMPLETION.md` | contract engineering complete and P16E-eligible; P15R authorization required/not run; P15B not run; no real deletion screen/model/GEM, science, policy, release or version bump |
| P16E K562 Golden delta contract work unit | start `d1e2e37b69784bd2f440cba34f51cfb56dcc00b2`; code `9f6b14ea84cb0884b2bde2ed4c67c73aeb5a37e2`; tree `098cd563e3d865e080a0d121727b987e2d40ed18` | immutable local Git history plus P16E closure evidence | contract engineering complete and P17 contract-only eligible; P16R authorization required/not run; P16B not run; no real checkpoint/data/science, policy, release or version bump; local wheel `1,108,165` bytes / `d333180996a4...` / `365` entries / `14` React entries |
| P17 Virtual Cell Brain work unit | start `ff525a0611901df422161a7143ebfe9d1e051008`; code `16636f1b2c36e0a0fabb782a662b5b3b934891e0`; tree `321a59eed44c45bf2bb8798714352b3303b92e58` | immutable local Git history plus `reports/phase17/PHASE17_COMPLETION.md` | deterministic contract complete and P18 contract-only eligible; real multi-model acceptance pending because registry is 5 releases / 0 native / 0 promoted; science not run, no new policy/release/version bump; local complete wheel `1,118,410` bytes / `bd3752b90a6d...` / `366` entries / `14` React entries |
| GitHub published `main` | `8e0d06348ebdf22e076037e6d661094ae877c5d1` | last recorded read-only observation, not refreshed in this window | historical remote fact until separately authorized and refreshed |
| `.53` code mirror | recorded separately in the integration guide | not refreshed in this window | historical deployment evidence, not current authorization |
| local product metadata | `1.6.0` | `pyproject.toml` `[project].version` | these local bytes differ from the historical annotated `v1.6.0`; known version drift, not release identity |
| Python distribution | `1.6.0` | installed `praxis-virtualcell` metadata | derived from the only manually edited product source |
| inherited `praxis2.__version__` | `1.6.0` | compatibility alias | aliases `praxis_virtualcell.__version__`; no second literal |
| main package export | `1.6.0` | `praxis_virtualcell.__version__` | derived from installed distribution metadata |
| CLI | `praxis-vc 1.6.0` | installed `praxis-vc --version` | derived from the main package export |
| frontend private package | `1.6.0` | `package.json` plus lock root | generated npm mirror; not a scientific/API protocol or UI authority |
| OpenAPI product version | `1.6.0` | `FastAPI(..., version=__version__)` | product identity, not protocol compatibility |
| API protocol | `vc.api.v1` | `praxis_virtualcell.version` | HTTP request/response contract namespace |
| runtime protocol | `vc.runtime.v1` | `praxis_virtualcell.version` | workflow/result semantics namespace |
| legacy runtime label | `v0.3` | `/api/health.runtime_version` | temporarily preserved response field for compatibility |
| build identity | injected SHA or `unknown` | `/api/health.git_sha` | reads `GIT_SHA`, `GITHUB_SHA`, then `SOURCE_VERSION`; never guesses from `.git` |
| legacy PRAXIS-2 service | `v0.21.0` | `praxis2/auth/routes.py` | inherited `/api/info` line, separate from VirtualCell product/API |
| agent message schema | `vc.msg.v1` | `praxis_virtualcell/core/message.py` | message serialization/validation contract |
| VirtualCell request schema | `vc.request.v2` | `praxis_virtualcell/core/request_v2.py` | strict nested request contract; legacy `VirtualCellRequest` remains supported through explicit adapters |
| VirtualCell domain schemas | `vc.species-ref.v1`, `vc.cell-context.v1`, `vc.modality.v1`, `vc.dataset-ref.v1`, `vc.perturbation.v1`, `vc.task.v1` | `praxis_virtualcell/core/request_v2.py` | independently versioned JSON domain objects; unknown fields fail closed and validated nested JSON is recursively immutable |
| model I/O bundle schemas | `vc.model-input.v1`, `vc.prediction.v1` | `praxis_virtualcell/core/request_v2.py` | data references and named prediction vectors only; validated nested JSON is recursively immutable; no dataset loading, registry lookup, or model execution |
| VirtualCellPack manifest schema | `vc.pack.v0.1`, `vc.pack.v0.2`, `vc.pack.v0.3` | `praxis_virtualcell/data_packs/manifest.py` | v0.1 keeps its frozen fingerprint; v0.2 adds single-modality standard semantics; v0.3 adds strict H5MU modality declarations plus paired/partially-paired observation semantics without padding or imputation; no Pack version implies model compatibility or scientific validity |
| model feature contract | `vc.model-feature-contract.v1` | `praxis_virtualcell/data_packs/feature_alignment.py` | exact model/taxon/assembly/modality/namespace/ordered-feature input contract plus explicit reorder/drop/fill and mapping-asset identity; its SHA-256 fingerprint is not a model weight or performance claim |
| feature mapping asset | `vc.feature-mapping.v1` + mapping ID/version/SHA-256 | Pack-declared JSON asset consumed by `feature_alignment.py` | explicit alias and `sum`/`mean` aggregate rules only; bytes or version changes alter Pack and contract identity when their references are updated |
| feature alignment report | `vc.alignment-report.v1` | `praxis_virtualcell/data_packs/feature_alignment.py` | records source/target order and every applied alias/aggregate/drop/fill/reorder; proves contract transformation only, not model execution or scientific validation |
| strict model card | `vc.model-card.v1` + canonical JSON SHA-256 | `model_zoo/capability_registry.py`, `model_zoo/registry.yaml` | binds taxon/modality/assay/domain/perturbation/task/output/namespace/representation/assets/resources/uncertainty/OOD and wrapper revision; card presence is not execution or validation |
| model artifact identity | `vc.model-artifact.v1` + canonical JSON SHA-256 | `model_zoo/registry_v2.py` | binds relative cache key, size/hash, media type, licence/source and safe-load declaration; identity or `artifact_ready` is not safe execution or validation |
| model environment identity | `vc.model-environment.v1` + canonical JSON SHA-256 | `model_zoo/registry_v2.py` | binds PEP 503 distribution+version requirements, architecture, lock/image identity, resources/accelerators and adapter fingerprints; distribution names are not import-module probes |
| model adapter identity | `vc.model-adapter.v1` + canonical JSON SHA-256 | `model_zoo/registry_v2.py`, `model_zoo/adapter_sdk.py` | P12 binds adapter name/version/implementation locator and contract fingerprints; P13 resolves the exact registered runtime implementation without changing the P12 identity schema |
| adapter input contract | `vc.adapter-input-contract.v1` + canonical JSON SHA-256 | `model_zoo/adapter_sdk.py` | binds exact task/output/value type/shape/unit and explicit Pack-data/alignment requirements; contract validity is not data availability or scientific validity |
| prepared adapter input | `vc.prepared-adapter-input.v1` + canonical JSON SHA-256 | `model_zoo/adapter_sdk.py` | immutable request/Pack/compatibility/feature-alignment/model-input binding; preparation does not execute a model |
| adapter output contract | `vc.adapter-output-contract.v1` + canonical JSON SHA-256 | `model_zoo/adapter_sdk.py` | binds task/output/value type/shape/unit plus uncertainty/OOD/abstention requirements; a conforming shape is not a quality claim |
| adapter execution provenance | `vc.adapter-execution-provenance.v1` + canonical JSON SHA-256 | `model_zoo/adapter_sdk.py` | binds exact adapter and input/output contract fingerprints to request/Pack/compatibility inputs; provenance is not evidence or policy |
| adapter output envelope | `vc.adapter-output-envelope.v1` + canonical JSON SHA-256 | `model_zoo/adapter_sdk.py` | strict finite values, shape/unit, uncertainty, OOD, abstention, projection metadata and provenance; invalid or mixed envelopes fail closed |
| adapter conformance report | `vc.adapter-conformance-report.v1` + canonical JSON SHA-256 | `model_zoo/adapter_sdk.py` | records deterministic contract conformance and, for non-abstain outputs, projection conformance for an exact prepared input; it is not benchmark evidence or production promotion |
| E. coli growth scope | `vc.ecoli-growth-scope.v1` + canonical JSON SHA-256 | `model_zoo/ecoli_growth_contract.py` | exact K-12 MG1655/assembly plus GEM/release/artifact/environment/adapter/Pack/mapping/medium/condition/objective/solver identities; scope validity is not asset availability |
| E. coli growth validation protocol | `vc.ecoli-growth-validation-protocol.v1` + canonical JSON SHA-256 | `model_zoo/ecoli_growth_contract.py` | preregisters held-out groups, baseline, metric, paired CI, external and OOD requirements; it is not `vc.model-validation-evidence.v1` or a result |
| E. coli growth data binding | `vc.ecoli-growth-data-binding.v1` + canonical JSON SHA-256 | `model_zoo/ecoli_growth_contract.py` | binds one future growth-condition Pack identity; the P14E fixture is identity-only and not a real Pack |
| E. coli growth execution binding | `vc.ecoli-growth-execution-binding.v1` + canonical JSON SHA-256 | `model_zoo/ecoli_growth_contract.py` | exact medium, condition, objective/unit and deterministic solver configuration; deterministic does not imply correct |
| E. coli growth gene mapping | `vc.ecoli-growth-gene-mapping-binding.v1` + canonical JSON SHA-256 | `model_zoo/ecoli_growth_contract.py` | exact hash-bound NCBIGene→GEM mapping; no symbol, ortholog or implicit fallback |
| E. coli growth compatibility | `vc.ecoli-growth-compatibility-binding.v1` + canonical JSON SHA-256 | `model_zoo/ecoli_growth_contract.py` | P14E fixes assets_verified/executable false with reason p14r_not_authorized; record presence cannot authorize execution |
| E. coli growth adapter input | `vc.ecoli-growth-adapter-input-contract.v1` + canonical JSON SHA-256 | `model_zoo/ecoli_growth_contract.py` | binds predict_knockout_growth/growth_ratio, one NCBIGene target and all required exact identities |
| E. coli growth adapter output | `vc.ecoli-growth-adapter-output-contract.v1` + canonical JSON SHA-256 | `model_zoo/ecoli_growth_contract.py` | one dimensionless wild-type-relative ratio; uncertainty unavailable, OOD/abstain required and flux trace-only |
| E. coli prepared model input | `vc.ecoli-growth-prepared-model-input.v1` + canonical JSON SHA-256 | `model_zoo/ecoli_growth_contract.py` | cross-binds request/scope/protocol/execution/Pack/compatibility to prepared input; it does not execute a GEM |
| yeast deletion-fitness scope | `vc.yeast-deletion-fitness-scope.v1` + canonical JSON SHA-256 | `model_zoo/yeast_deletion_fitness_contract.py` | exact S288C/assembly, release/artifact/environment/adapter/Pack/mapping/condition/control/assay/platform/fitness identities; scope validity is not asset availability |
| yeast deletion-fitness validation protocol | `vc.yeast-deletion-fitness-validation-protocol.v1` + canonical JSON SHA-256 | `model_zoo/yeast_deletion_fitness_contract.py` | preregisters grouped split, baseline, metric, paired CI, external and OOD requirements; it is not evidence or a result |
| yeast deletion-fitness data binding | `vc.yeast-deletion-fitness-data-binding.v1` + canonical JSON SHA-256 | `model_zoo/yeast_deletion_fitness_contract.py` | identity-only future deletion-screen Pack binding; P15E does not read a real screen |
| yeast deletion-fitness execution binding | `vc.yeast-deletion-fitness-execution-binding.v1` + canonical JSON SHA-256 | `model_zoo/yeast_deletion_fitness_contract.py` | binds exact condition/control/assay/platform/fitness semantics and inference configuration; it is not an execution result |
| yeast deletion-fitness gene mapping | `vc.yeast-deletion-fitness-gene-mapping-binding.v1` + canonical JSON SHA-256 | `model_zoo/yeast_deletion_fitness_contract.py` | exact SGD systematic mapping and target universe; no symbol/case/version guessing or implicit fallback |
| yeast deletion-fitness compatibility | `vc.yeast-deletion-fitness-compatibility-binding.v1` + canonical JSON SHA-256 | `model_zoo/yeast_deletion_fitness_contract.py` | P15E fixes assets_verified/executable false with reason p15r_not_authorized; record presence cannot authorize execution |
| yeast deletion-fitness adapter input | `vc.yeast-deletion-fitness-adapter-input-contract.v1` + canonical JSON SHA-256 | `model_zoo/yeast_deletion_fitness_contract.py` | binds predict_deletion_fitness/fitness, one complete deletion target and all exact identities |
| yeast deletion-fitness adapter output | `vc.yeast-deletion-fitness-adapter-output-contract.v1` + canonical JSON SHA-256 | `model_zoo/yeast_deletion_fitness_contract.py` | one finite dimensionless matched-control-relative scalar; uncertainty unavailable and OOD/value-free abstain required |
| yeast deletion-fitness prepared model input | `vc.yeast-deletion-fitness-prepared-model-input.v1` + canonical JSON SHA-256 | `model_zoo/yeast_deletion_fitness_contract.py` | cross-binds request/scope/protocol/execution/Pack/compatibility; public projection remains prepared-only |
| K562 Golden perturbation scope | `vc.k562-golden-perturbation-scope.v1` + canonical JSON SHA-256 | `model_zoo/k562_golden_delta_contract.py` | exact K562/CVCL/assembly/assay/feature order, release/artifact/environment/adapter/Pack/perturbation/execution/compatibility and delta semantics; scope validity is not executable availability |
| K562 Golden validation protocol | `vc.k562-golden-validation-protocol.v1` + canonical JSON SHA-256 | `model_zoo/k562_golden_delta_contract.py` | preregisters frozen condition holdout, additive-ridge comparator, candidate-minus-comparator bootstrap, contamination/external/OOD and separate-scope requirements; it is not evidence or policy |
| K562 Golden data binding | `vc.k562-golden-data-binding.v1` + canonical JSON SHA-256 | `model_zoo/k562_golden_delta_contract.py` | binds checked-in P8 contract/Pack/manifest/assets/control/split identities without reading H5AD/NPY or claiming asset availability |
| K562 Golden perturbation binding | `vc.k562-golden-perturbation-binding.v1` + canonical JSON SHA-256 | `model_zoo/k562_golden_delta_contract.py` | binds one exact condition and ordered Ensembl targets while record membership remains unverified with reason p16r_not_authorized |
| K562 Golden execution binding | `vc.k562-golden-execution-binding.v1` + canonical JSON SHA-256 | `model_zoo/k562_golden_delta_contract.py` | native delta-expression and exact 5,045-feature order only; no normalization/reorder/fill/impute/dedup or silent absolute-to-delta conversion |
| K562 Golden compatibility | `vc.k562-golden-compatibility-binding.v1` + canonical JSON SHA-256 | `model_zoo/k562_golden_delta_contract.py` | P16E fixes assets_verified/executable false with reason p16r_not_authorized; checked-in manifests do not authorize execution |
| K562 Golden adapter input | `vc.k562-golden-adapter-input-contract.v1` + canonical JSON SHA-256 | `model_zoo/k562_golden_delta_contract.py` | binds predict_delta_expression/delta_expression, K562 Golden biology, single/combination scopes and all exact identities |
| K562 Golden adapter output | `vc.k562-golden-adapter-output-contract.v1` + canonical JSON SHA-256 | `model_zoo/k562_golden_delta_contract.py` | one finite ordered `(5045,)` delta vector; uncertainty unavailable and OOD/value-free abstain required |
| K562 Golden prepared model input | `vc.k562-golden-prepared-model-input.v1` + canonical JSON SHA-256 | `model_zoo/k562_golden_delta_contract.py` | cross-binds request/scope/protocol/perturbation/execution/Pack/compatibility; public projection remains prepared-only |
| validation evidence identity | `vc.model-validation-evidence.v1` + canonical JSON SHA-256 | `model_zoo/registry_v2.py` | binds exact Pack×model×environment×adapter×protocol, baseline, primary metric and result hash; record existence does not make the evidence pass |
| operator policy identity | `vc.model-operator-policy.v1` + canonical JSON SHA-256 | `model_zoo/registry_v2.py` | binds one named operator decision to one exact capability and evidence set; P12 creates no new promotion decision |
| model release/lifecycle identities | `vc.model-release.v1`, `vc.model-registry-event.v1`, `vc.model-registry-state.v1` | `model_zoo/registry_v2.py` | release graph plus append-only catalog/readiness/revoke/supersede history; registry state, evidence and product policy remain separate |
| Model Zoo v2 root/public catalog | `vc.model-registry.v2`, `vc.model-registry-catalog.v2` | `model_zoo/registry_v2.py`, `model_zoo/registry.py` | immutable layered registry and path-redacted read projection; v1 migration is `legacy_incomplete`; unsafe legacy `model_version` is public `null`, never rewritten or promoted |
| execution environment snapshot | `vc.environment.v1` or `vc.environment.v2` + canonical JSON SHA-256 | `model_zoo/capability_registry.py` | v1 preserves legacy planning; v2 binds one exact `EnvironmentIdentity`; `python_dependencies` are import-module availability and are not string-equaled to PEP 503 distributions |
| model compatibility report | `vc.compatibility-report.v1` or `vc.compatibility-report.v2` + canonical JSON SHA-256 | `model_zoo/capability_registry.py` | v2 binds exact request, Pack, release, artifact, environment, adapter, evidence, policy and lifecycle; fingerprint excludes runtime paths and display-only model version already bound by model/release identity |
| model execution plan | `vc.execution-plan.v1` or `vc.execution-plan.v2` + deterministic `plan_<sha-prefix>` | `model_zoo/capability_registry.py`, `agents/model_broker_agent.py` | v2 recomputes canonical plan ID and checks report/wrapper/agent step binding; an empty or executable plan is not a performance, evidence or promotion claim |
| Virtual Experiment DAG/node/edge | `vc.virtual-experiment-dag.v1`, `vc.virtual-experiment-node.v1`, `vc.virtual-experiment-edge.v1` + canonical JSON SHA-256 | `virtual_experiment.py` | binds request/cell/Pack/environment/plan/validated steps/capabilities and typed acyclic edges; contract existence is not execution or multi-model acceptance |
| Virtual Cell Brain context/decision | `vc.virtual-cell-brain-context.v1`, `vc.virtual-experiment-decision.v1` + canonical JSON SHA-256 | `virtual_experiment.py` | immutable request/Pack/model/release/capability/environment/adapter-contract/evidence/policy context and fail-closed verdict; P17 decision is always contract-only abstain |
| candidate DAG review/compilation | `vc.candidate-virtual-experiment-dag.v1`, `vc.candidate-dag-review.v1`, `vc.virtual-experiment-compilation.v1` | `virtual_experiment.py` | candidate review has its own checksum but is excluded from authoritative DAG/Brain/decision fingerprint; LLM output cannot authorize execution or change verdict |
| Pack product record/catalog | `vc.pack-record.v1`, `vc.pack-catalog.v1` with nested `vc.model-registry-catalog.v2` | `pack_product.py`, `/api/packs` | outer contract remains compatible; top-level `model_registry` and per-model `registry_releases` are path-redacted discovery projections, not per-request compatibility |
| local Pack index | `vc.pack-index.v1` + Pack fingerprint | `pack_product.py`, `PRAXIS_VC_PACK_INDEX` | binds a local canonical root to one Pack ID/version/fingerprint; every use revalidates bytes and semantics |
| Pack compatibility surface | `vc.pack-compatibility-surface.v1` | `pack_product.py`, `/api/packs/compatibility` | public path-redacted projection of v1/v2 execution plans; planning is read-only and is not execution evidence |
| job execution identity | `vc.job-execution-identity.v1`, `.v2`, or `.v3` + canonical JSON SHA-256 | `io/job_store.py` | v1 remains parseable; v2 locks request/report/outcome and Pack/release/component/evidence/policy state; v3 additionally binds Brain/DAG and contract-only report semantics; companion-backed load recomputes identity without rewriting historical bytes |
| public data catalog | `vc.data-catalog.v1` | `praxis_virtualcell/catalogs/data_catalog.yaml`, `praxis_vc_api/services/data_portal_service.py` | strict public metadata plus source terms and external-file size/hash allowlist; catalog/file availability does not imply Pack/model/scientific status |
| quarantined upload receipt | `vc.upload-receipt.v1` | `praxis_vc_api/services/data_portal_service.py` | one byte-preserving quarantine write identity; not content validation, Pack registration, user identity, or prediction evidence |
| Golden Norman contract | `vc.golden-norman.v1` + canonical JSON SHA-256 | `data/golden/norman_2019/contract.yaml`, `benchmarks/golden_norman.py` | binds one exact public source, source/derived semantics, predefined control/split, metric/bootstrap and simple-baseline definitions; changing any item requires a new identity |
| Golden baseline artifact | `vc.golden-baseline.v1` + per-file SHA-256 | external `model_cache/norman_*`, checked-in one-card registries | binds Pack fingerprint, ordered feature/target IDs, train conditions and fixed baseline arrays; not a general model revision or scientific validation |
| Golden evaluation artifact | `vc.golden-evaluation.v1` + file SHA-256 | external `evaluation/evaluation.json` | records all held-out formal-runtime calls, condition losses, paired bootstrap and three separate states; scores do not promote `scientifically_validated` |
| Golden artifact inventory | `vc.golden-artifact-manifest.v1` | `data/golden/norman_2019/artifact-manifest.json` | records exact external path/size/hash and compact scores; it is not the large data or model content |
| P9 OOD manifest | `vc.ood-manifest.v1` + canonical JSON SHA-256 | `data/benchmarks/p9/ood-manifest.json`, `benchmarks/ood_validation.py` | freezes eight ordered OOD axes, biological groups, data roles, metrics/CI/seeds, validation-only threshold and promotion gate; fixture groups are not scientific performance |
| P9 external result | `vc.ood-result.v1` + file SHA-256 | `data/benchmarks/p9/external-validation.json` | binds four public input hashes, exact shared features, predefined grouped split, adaptation-free condition results, selective metrics and fail-closed status; not a model-zoo registration or general validation |
| CommunityPack contract | `vc.community-pack.v1` + canonical JSON SHA-256 | `community_packs/contracts.py` | binds exact member Pack fingerprints, abundance, medium, compartment, time/well-mixed space, shared metabolite namespace and evidence; not a community model or scientific validation |
| Community exchange contracts | `vc.community-exchange-ledger.v1`, `vc.community-exchange-validation.v1` | `community_packs/contracts.py` | exact declared-amount conservation for a toy ledger; not flux, elemental, thermodynamic or experimental validation |
| Community plan/result contracts | `vc.community-execution-plan.v1`, `vc.community-run-result.v1` | `community_packs/contracts.py` | no-model plan and honest abstention; neither schema implies a real adapter, executable model, prediction or validation |
| memory frontmatter schema | `1` | `brains/_common/memory/rules/*.md` | inherited memory-content schema |
| governance feature schema | `v0.3.0` | `governance/learned_reliability.py` and artifact JSON | frozen learned-governance feature contract |
| governance models | `reliability_v0.3.0`, `abstain_v0.3.0` | `governance/artifacts/*.json` | immutable model revisions paired with content SHA-256 |
| model registry revisions | heterogeneous model/dataset identifiers | `model_zoo/registry.yaml` | per-engine/checkpoint revisions, not product SemVer |
| W4B donor call version | `donor_ml:<Class>@sha256:<content identity>` on `build_runtime_ml` | checkpoint `.json + .pt` bytes via `checkpoint_identity.py` | content identity for this call; not a checked-in integrity pin, product version, or proof of cross-device tensor hashing |

P12 adds the layered identities above and a fail-closed exact
request×Pack×release×artifact×environment×adapter×evidence×policy×lifecycle gate. This is a
completed engineering contract, not evidence that any real release satisfies the gate.
Migrated v1 cards have no evidence or policy record and cannot be promoted. In-process execution
accepts only the declared `safe_load_policy=data_only`; the declaration is rechecked at planning and
instantiation but is not yet a type-level proof that an arbitrary wrapper loader is data-only.

P13 adds the six Adapter SDK schemas above without changing `vc.model-adapter.v1`, product
SemVer, API/runtime protocol or release tags. The default runtime registry contains only the
delta-expression reference adapter; P13's dummy growth/fitness adapters remain test-only contract
fixtures and are distinct from the later P14E local-only growth contract adapter.
Engineering completion does not create a real model, scientific run, validation evidence or named
operator decision. See [ADR-0010](ADR-0010-virtualcell-model-adapter-sdk.md), the
[runbook](runbooks/VIRTUALCELL-MODEL-ADAPTER-SDK.md), and the
[P13 completion report](../reports/phase13/PHASE13_COMPLETION.md).

P14E adds the nine E. coli growth schemas above without changing product SemVer, API/runtime
protocol, Model Registry root schemas, release tags or the default adapter registry. Its local-only
adapter and synthetic identities prove strict binding/conformance only. `P14R` remains
`AUTHORIZATION_REQUIRED / NOT_RUN` and `P14B` remains `NOT_RUN`. See
[ADR-0011](ADR-0011-virtualcell-ecoli-k12-growth-contract.md), the
[P14E runbook](runbooks/VIRTUALCELL-ECOLI-K12-GROWTH-CONTRACT.md), and the
[P14E completion report](../reports/phase14e/PHASE14E_COMPLETION.md).

P15E similarly adds the nine yeast deletion-fitness schemas above without changing product
SemVer (`1.6.0`), API/runtime protocols, release tags or the default delta-only registry. Its
local-only adapter uses native P12 identities and a typed-negative compatibility record; finite
scalar passthrough and deterministic conformance are engineering properties, not fitness evidence.
`P15R` remains `AUTHORIZATION_REQUIRED / NOT_RUN`, `P15B` remains `NOT_RUN`, and no new policy
decision exists. See [ADR-0012](ADR-0012-virtualcell-yeast-deletion-fitness-contract.md), the
[P15E runbook](runbooks/VIRTUALCELL-YEAST-DELETION-FITNESS-CONTRACT.md), and the
[P15E completion report](../reports/phase15e/PHASE15E_COMPLETION.md).

P16E adds the nine K562 Golden schemas above without changing product SemVer (`1.6.0`),
API/runtime protocols, release tags or the default delta-reference registry. Its local-only adapter
uses native P12 identities, exact checked-in P8 Golden identities and typed-negative compatibility;
5,045-vector passthrough and deterministic conformance are engineering properties, not K562
science evidence. `P16R` remains `AUTHORIZATION_REQUIRED / NOT_RUN`, `P16B` remains `NOT_RUN`,
`Science: NOT_RUN`, and `Policy: NO_NEW_DECISION`. Two exact clean-archive wheels are byte-identical:
`1,108,165` bytes, SHA-256
`d333180996a4ed91161d364275589e992d0be634582cc83a57e9758b86c03c66`, `365` entries and `14`
React entries; none is a release or version bump. Because P14–P16 still have fewer than two
production-promoted capabilities, P17 subsequently completed only contract work. See
[ADR-0013](ADR-0013-virtualcell-k562-golden-delta-contract.md), the
[P16E runbook](runbooks/VIRTUALCELL-K562-GOLDEN-DELTA-CONTRACT.md), and the
[P16E completion report](../reports/phase16e/PHASE16E_COMPLETION.md).

P17 adds the DAG/Brain/candidate-review/compilation schemas and job identity v3 above without
changing product SemVer (`1.6.0`), API/runtime protocols, release tags, registry releases or
promotion policy. Its exact code commit is `16636f1b2c36e0a0fabb782a662b5b3b934891e0`.
The current registry remains 5 releases / 0 native / 0 promoted, so real multi-model acceptance
is pending and the new direct-v2 path abstains without execution. Two offline clean-archive full
wheels are byte-identical at `1,118,410` bytes, SHA-256
`bd3752b90a6d8e4d7a825b2f4925d00eb7e5204021fef3404b67e88f7a0e23bd`, with `366` entries,
`14` React entries, no tests or AppleDouble, and the Brain module present. These are local
engineering artifacts, not a release. See [ADR-0014](ADR-0014-virtual-cell-brain.md), the
[P17 runbook](runbooks/VIRTUALCELL-VIRTUAL-EXPERIMENT-DAG.md), and the
[P17 completion report](../reports/phase17/PHASE17_COMPLETION.md).

The historical `v1.5.0` source tree declaring Python/frontend `0.0.0` is a release debt. Do not move or recreate the `v1.5.0` tag to conceal it.

## Namespace contract

| Name | Format | When it changes | Must not imply |
|---|---|---|---|
| `product_version` | PEP 440 `X.Y.Z` for stable releases; optional `.devN` while developing | user-visible product release scope changes | API/schema/model compatibility by itself |
| Git release tag | annotated `vX.Y.Z` | only on an approved release commit whose product metadata is `X.Y.Z` | a tag is published before GitHub confirms it |
| `api_protocol_version` | explicit contract identifier such as `vc.api.v1` | incompatible HTTP request/response contract change | product release cadence |
| `runtime_protocol_version` | explicit runtime/result contract identifier | incompatible workflow/result semantics change | product release cadence |
| `message_schema_version` | existing `vc.msg.v1` style | serialized agent-message compatibility change with migration/validation | product release cadence |
| request/domain/bundle schema version | explicit identifiers such as `vc.request.v2` and `vc.prediction.v1` | incompatible field, validation, or meaning change; compatible legacy projections stay explicit | product release cadence or scientific validity |
| Pack manifest schema version | explicit identifier such as `vc.pack.v0.1`, `vc.pack.v0.2`, or `vc.pack.v0.3` | incompatible manifest, validation, or fingerprint semantics | asset availability, model compatibility, or scientific validity |
| model feature contract schema + fingerprint | explicit `vc.model-feature-contract.v1` plus canonical JSON SHA-256 | incompatible model-input identity or explicitly allowed transformation changes | model availability, execution, accuracy, or scientific validity |
| feature mapping schema + ID/version/hash | explicit `vc.feature-mapping.v1` and content identity | mapping rules or bytes change | ontology truth, orthology, or an implicit fallback |
| alignment report schema | explicit `vc.alignment-report.v1` | incompatible provenance fields or operation semantics | a successful prediction or benchmark |
| model card schema + fingerprint | explicit `vc.model-card.v1` plus canonical JSON SHA-256 | model capability, asset/resource, uncertainty/OOD or wrapper contract changes | asset availability, successful execution, benchmark quality, or scientific validity |
| model artifact identity schema + fingerprint | explicit `vc.model-artifact.v1` plus canonical JSON SHA-256 | artifact identity, integrity, licence/source or safe-load declaration changes | artifact readiness proves executable, safe or scientifically valid |
| model environment identity schema + fingerprint | explicit `vc.model-environment.v1` plus canonical JSON SHA-256 | PEP 503 distribution/version, native/architecture/lock/image/resource/adapter requirements change | a distribution name is the same namespace as an import module, or the environment is currently satisfied |
| model adapter identity schema + fingerprint | explicit `vc.model-adapter.v1` plus canonical JSON SHA-256 | implementation locator or task/input/output contract changes | adapter implementation exists, conforms, or is scientifically valid |
| adapter SDK schemas + fingerprints | explicit `vc.adapter-input-contract.v1`, `vc.prepared-adapter-input.v1`, `vc.adapter-output-contract.v1`, `vc.adapter-execution-provenance.v1`, `vc.adapter-output-envelope.v1`, `vc.adapter-conformance-report.v1` plus canonical JSON SHA-256 | incompatible input/output, binding, envelope, conformance or projection semantics change | conformance is scientific evidence, a model is production-registered, or policy exists |
| E. coli growth contract schemas + fingerprints | explicit `vc.ecoli-growth-scope.v1`, `vc.ecoli-growth-validation-protocol.v1`, `vc.ecoli-growth-data-binding.v1`, `vc.ecoli-growth-execution-binding.v1`, `vc.ecoli-growth-gene-mapping-binding.v1`, `vc.ecoli-growth-compatibility-binding.v1`, `vc.ecoli-growth-adapter-input-contract.v1`, `vc.ecoli-growth-adapter-output-contract.v1` and `vc.ecoli-growth-prepared-model-input.v1` | exact biological scope, identity binding, protocol, compatibility, input/output or prepared semantics change incompatibly | a real GEM/Pack exists, FBA ran, science passed, the adapter is in the default registry, or policy exists |
| yeast deletion-fitness contract schemas + fingerprints | explicit `vc.yeast-deletion-fitness-scope.v1`, `vc.yeast-deletion-fitness-validation-protocol.v1`, `vc.yeast-deletion-fitness-data-binding.v1`, `vc.yeast-deletion-fitness-execution-binding.v1`, `vc.yeast-deletion-fitness-gene-mapping-binding.v1`, `vc.yeast-deletion-fitness-compatibility-binding.v1`, `vc.yeast-deletion-fitness-adapter-input-contract.v1`, `vc.yeast-deletion-fitness-adapter-output-contract.v1` and `vc.yeast-deletion-fitness-prepared-model-input.v1` | exact strain/condition/control/assay/platform/mapping/protocol/input/output/prepared semantics change incompatibly | a real deletion screen/model exists, fitness science passed, the adapter is default/runtime-ready, or policy exists |
| K562 Golden delta contract schemas + fingerprints | explicit `vc.k562-golden-perturbation-scope.v1`, `vc.k562-golden-validation-protocol.v1`, `vc.k562-golden-data-binding.v1`, `vc.k562-golden-perturbation-binding.v1`, `vc.k562-golden-execution-binding.v1`, `vc.k562-golden-compatibility-binding.v1`, `vc.k562-golden-adapter-input-contract.v1`, `vc.k562-golden-adapter-output-contract.v1` and `vc.k562-golden-prepared-model-input.v1` | exact K562/assembly/assay/ordered-feature/condition/perturbation/protocol/input/output/prepared semantics change incompatibly | a checkpoint or large asset was read, K562 science passed, the adapter is default/runtime-ready, or evidence/policy exists |
| validation evidence schema + fingerprint | explicit `vc.model-validation-evidence.v1` plus canonical JSON SHA-256 | exact capability/protocol/baseline/metric/result binding changes | evidence exists, passes, generalizes, or grants product policy |
| operator policy schema + fingerprint | explicit `vc.model-operator-policy.v1` plus canonical JSON SHA-256 | named operator, exact capability/evidence decision or policy version changes | engineering or evidence state can manufacture a promotion decision |
| model release/lifecycle schemas + fingerprints | explicit `vc.model-release.v1`, `vc.model-registry-event.v1`, `vc.model-registry-state.v1` | component graph or append-only lifecycle fact changes | catalog/readiness/revocation/supersession is scientific evidence or product policy |
| Model Zoo root/public catalog schemas | explicit `vc.model-registry.v2`, `vc.model-registry-catalog.v2` | layered registry or path-redacted public projection changes incompatibly | migration/catalog presence makes a release executable, validated or promoted |
| environment snapshot schema + fingerprint | explicit `vc.environment.v1` or `vc.environment.v2` plus canonical JSON SHA-256 | import-module/resource/runtime-adapter observation or v2 identity binding changes | import-module names must equal PEP 503 distribution names, or a missing resource is available |
| compatibility report schema + fingerprint | explicit `vc.compatibility-report.v1` or `vc.compatibility-report.v2` plus canonical JSON SHA-256 | compatibility checks, reason semantics, identity inclusion/exclusion or bound refs change incompatibly | display-only model version/path affects the canonical v2 binding, or computed/evidence/policy states are interchangeable |
| execution step/plan schema + plan ID | explicit `vc.execution-plan.v1`, or `vc.execution-step.v2` and `vc.execution-plan.v2` with content-derived `plan_*` | canonical step/report/wrapper/agent binding or plan identity semantics change incompatibly | plan creation proves prediction correctness, scientific validation or promotion |
| Pack product record/catalog/index schemas | explicit `vc.pack-record.v1`, `vc.pack-catalog.v1`, `vc.pack-index.v1`; catalog may nest `vc.model-registry-catalog.v2` | incompatible public metadata, index-field, identity binding or registry projection semantics | discovery/registration proves per-request compatibility or scientific validity |
| Pack compatibility surface schema | explicit `vc.pack-compatibility-surface.v1` | incompatible path-redaction or public execution-plan projection | a compatibility response proves successful execution |
| job execution identity schema + fingerprint | explicit `vc.job-execution-identity.v1`, `vc.job-execution-identity.v2` or `vc.job-execution-identity.v3` and content identity | incompatible request/report/outcome/Pack/release/component/evidence/policy identity-lock semantics; v3 also binds Brain/DAG and companion-backed contract-only report semantics | read-only loading may rewrite old bytes, schema downgrade may bypass current bindings, or immutable provenance proves model quality/validation/promotion |
| public data catalog schema | explicit `vc.data-catalog.v1` | incompatible metadata, source/terms, identity or file-verification semantics | file availability, Pack validity, model compatibility or scientific validity |
| upload receipt schema | explicit `vc.upload-receipt.v1` | incompatible quarantine identity/provenance semantics | internal file safety/quality, user authentication identity, Pack registration or model use |
| Golden benchmark contract + canonical hash | explicit `vc.golden-norman.v1` and content identity | source, semantic field, feature order, control/split, truth, metric/bootstrap or baseline definition changes | one successful run validates another dataset/model or creates scientific truth |
| Golden baseline/evaluation/inventory schemas + hashes | explicit `vc.golden-*.v1` and per-file identities | incompatible artifact semantics or regenerated bytes | lower MSE, executable runtime, or an inventory entry implies `scientifically_validated=true` |
| CommunityPack schema + fingerprint | explicit `vc.community-pack.v1` plus canonical JSON SHA-256 | incompatible member/reference/ecology-metadata semantics change | a valid contract supplies a community model or experimental truth |
| Community exchange/plan/result schemas | explicit `vc.community-*.v1` identities | incompatible ledger, conservation, planning or abstention semantics change | toy balance proves biological feasibility, or an empty plan proves execution |
| `memory_schema_version` | integer/content-schema identifier | memory frontmatter/content contract change | product release cadence |
| `feature_schema_version` | existing SemVer-like artifact contract | retraining/migrating the feature vector contract | UI/package version |
| governance `model_version` + SHA | immutable named revision plus content hash | genuinely regenerated/retrained artifact | product release cadence |
| registry `model_revision` | model/dataset/checkpoint-specific identifier plus asset SHA | specific model/checkpoint changes | whole-product version |
| frontend package version | generated mirror of the product version for release builds | synchronized by the release tool, never used as authority | API/runtime protocol version |
| `git_sha` / image digest | exact build identity | every build | semantic compatibility |

## Single product-version source

`pyproject.toml` `[project].version` is the only manually editable product-version source.

Implemented history through the current P17 contract-complete bytes:

1. C2's compatible cleanup candidate was `1.5.1`. C3 then accepted and committed user-visible theme, result, input, and workflow-state improvements, so the local candidate is now the required minor version `1.6.0`; `1.5.1` was never published.
2. `importlib.metadata.version("praxis-virtualcell")` is exposed as `praxis_virtualcell.__version__`; an uninstalled source import returns the honest fallback `0+unknown`.
3. `praxis2.__version__` is a compatibility alias rather than a second literal.
4. `praxis-vc --version`, FastAPI/OpenAPI, and health use the same installed product value.
5. `/api/health` separately exposes product, API protocol, runtime protocol, and injected build SHA while retaining `runtime_version="v0.3"`.
6. The UI consumes backend `product_version` and `git_sha`; an E2E mock with product `9.9.9` proves that it does not invent this truth from frontend metadata.
7. `npm version 1.6.0 --no-git-tag-version` synchronized the private package and lock root as a generated mirror. Neither is manually authoritative.
8. The full release wheel is built with hash-locked Python 3.13 build dependencies and contains the packaged React UI; clean-install verification reads the installed distribution metadata rather than the checkout.
9. The release container installs that same wheel into `/opt/venv`, injects `GIT_SHA` into both its OCI revision label and health response, and never infers identity from an image tag or embedded `.git` directory.
10. W4B donor adapters use a checkpoint-content identity as their per-call model version and validate the expected slot/class before loading weights. Other ML callers retain their existing explicit or class fallback, so this must not be generalized to every registry model.
11. P7 adds backward-compatible `vc.api.v1` endpoints and a user-visible data-resource page inside the still-unpublished `1.6.0` minor candidate. It adds independent `vc.data-catalog.v1` and `vc.upload-receipt.v1` contracts; no product tag or API/runtime protocol bump is inferred.
12. P8 adds an offline benchmark-specific Pack derivation, three simple one-card baseline wrappers and external artifact schemas inside the same unpublished candidate. It does not change the public API/runtime protocol, default model zoo, UI or product version, and does not infer a release tag.
13. P8 product closure adds backward-compatible Pack CLI/API/UI discovery, three tiny built-in Pack fixtures, a local index and immutable job execution identity inside the same unpublished minor candidate. It does not add a production model, change the core runtime protocol, transform P7 data or infer a tag/publication.
14. P9 adds offline OOD/result artifact contracts and one adaptation-free public external validation inside the same unpublished candidate. It does not change API/runtime/UI protocols, register the rejected candidate model, access `.53`, or infer a tag/publication.
15. P10 adds a model-free CommunityPack pre-interface, one synthetic yeast member Pack, exact toy exchange validation and deterministic no-model abstention. It does not change API/runtime/UI protocols, add a model/weight, modify the P8 catalog, or infer a release/tag.
16. P11A/P11B add the Data Center and Cell-first UI on the local branch without changing the
    API/runtime protocol or creating a new model, scientific validation, product policy or release.
17. DOCS-CLOSURE is the immutable P12 starting baseline
    `b19c896202bea56f894d0ad540501331af42a40c`.
18. P12 current bytes add backward-compatible layered Model Zoo identities, append-only lifecycle,
    v1 migration, path-redacted public projections and v2 fail-closed planning inside the same
    unpublished candidate. The work unit is engineering-complete: it adds no real model/weight,
    scientific validation, new operator promotion, product/API/runtime version bump or release tag.
19. P13 code `744d0a28d2cfc13d1b10e85b133b6c13b9426174` adds a backward-compatible
    Adapter SDK, delta-only default registry, strict prepared-input/output/provenance binding and
    generic adapter-aware ensemble/report flow inside the same unpublished candidate. P13
    test-only dummy growth/fitness adapters do not enter the production registry. `Science: NOT_RUN` and
    `Policy: NO_NEW_DECISION`; no product/API/runtime version bump, release or tag is created.
20. P14E prerequisite `c3401450fd79f7829c438d6b55c1902ea2f4cf5f` hardens recursive SDK
    trust boundaries without changing the six frozen P13 fingerprints. P14E code
    `8778e93c31c2dfe1ef0f77f06e7a80a425633736` adds exact K-12 MG1655
    knockout→growth-ratio contracts and a local-only adapter inside the same unpublished candidate.
    The default registry remains delta-only; P14R/P14B are not run. No product/API/runtime version
    bump, release, tag, real asset, scientific evidence or operator decision is created.
21. P15E code `62480a3951173a2aa7b006403af9b169521db138` adds exact S288C single
    complete-gene-deletion→dimensionless-fitness contracts and a local-only adapter inside the same
    unpublished candidate. Native P12 bindings remain typed-negative with
    `reason=p15r_not_authorized`; the default registry remains delta-only. P15R/P15B are not run,
    and no product/API/runtime version bump, release, tag, real asset/GEM, scientific evidence or
    operator decision is created.
22. P16E code `9f6b14ea84cb0884b2bde2ed4c67c73aeb5a37e2` adds exact K562 Golden
    single-gene/combination→5,045-feature native delta-expression contracts and a local-only adapter
    inside the same unpublished candidate. Checked-in P8 identities are bound without reading H5AD/
    NPY or running Golden science; compatibility remains typed-negative with
    `reason=p16r_not_authorized`, and the default registry remains the P13 delta reference only.
    P16R/P16B are not run; no product/API/runtime version bump, release, tag, checkpoint/training,
    scientific evidence or operator decision is created. Two clean-archive wheels are byte-identical
    at `1,108,165` bytes, SHA-256
    `d333180996a4ed91161d364275589e992d0be634582cc83a57e9758b86c03c66`, with `365` entries and
    `14` React entries; these local build values are not release identity.
23. P17 code `16636f1b2c36e0a0fabb782a662b5b3b934891e0` adds deterministic
    Virtual Experiment DAG/Brain/decision contracts, a plan-only direct-v2 Pack path, candidate
    review isolation and companion-bound job identity v3 inside the same unpublished candidate.
    It does not instantiate wrappers, execute models, call an LLM, add a registry release or make
    evidence/policy claims. The registry remains 5/0/0 releases/native/promoted, so real
    multi-model acceptance is pending. No product/API/runtime version bump, release, tag, push or
    deploy is created. The exact full wheel identity is `1,118,410` bytes /
    `bd3752b90a6d8e4d7a825b2f4925d00eb7e5204021fef3404b67e88f7a0e23bd` / `366` entries /
    `14` React entries and is not a published release.

## Release invariants

A release candidate is invalid unless automated checks prove:

```text
pyproject product version
== importlib.metadata distribution version
== praxis_virtualcell.__version__
== praxis2 compatibility alias
== praxis-vc --version
== OpenAPI application product version
== /api/health product_version
== frontend release-package mirror
== annotated tag name without its leading "v" (only once an approved release tag exists)
```

The UI must show the same backend product version. GitHub `main`, local `main`, and the `.53`
deployed checkout must resolve to the tagged commit before synchronization can be marked complete.
The current local bytes differ from the historical annotated `v1.6.0` tag; that tag must never be
moved or reused. A future release needs a new SemVer and separately authorized release windows.

The equality above deliberately excludes `vc.msg.v1`, `vc.request.v2`, all
`vc.pack.*` versions, `vc.model-feature-contract.v1`, `vc.feature-mapping.v1`,
`vc.alignment-report.v1`, `vc.model-card.v1`, `vc.model-artifact.v1`,
`vc.model-environment.v1`, `vc.model-adapter.v1`,
`vc.adapter-input-contract.v1`, `vc.prepared-adapter-input.v1`,
`vc.adapter-output-contract.v1`, `vc.adapter-execution-provenance.v1`,
`vc.adapter-output-envelope.v1`, `vc.adapter-conformance-report.v1`,
`vc.ecoli-growth-scope.v1`, `vc.ecoli-growth-validation-protocol.v1`,
`vc.ecoli-growth-data-binding.v1`, `vc.ecoli-growth-execution-binding.v1`,
`vc.ecoli-growth-gene-mapping-binding.v1`,
`vc.ecoli-growth-compatibility-binding.v1`,
`vc.ecoli-growth-adapter-input-contract.v1`,
`vc.ecoli-growth-adapter-output-contract.v1`,
`vc.ecoli-growth-prepared-model-input.v1`,
`vc.yeast-deletion-fitness-scope.v1`,
`vc.yeast-deletion-fitness-validation-protocol.v1`,
`vc.yeast-deletion-fitness-data-binding.v1`,
`vc.yeast-deletion-fitness-execution-binding.v1`,
`vc.yeast-deletion-fitness-gene-mapping-binding.v1`,
`vc.yeast-deletion-fitness-compatibility-binding.v1`,
`vc.yeast-deletion-fitness-adapter-input-contract.v1`,
`vc.yeast-deletion-fitness-adapter-output-contract.v1`,
`vc.yeast-deletion-fitness-prepared-model-input.v1`,
`vc.k562-golden-perturbation-scope.v1`,
`vc.k562-golden-validation-protocol.v1`,
`vc.k562-golden-data-binding.v1`,
`vc.k562-golden-perturbation-binding.v1`,
`vc.k562-golden-execution-binding.v1`,
`vc.k562-golden-compatibility-binding.v1`,
`vc.k562-golden-adapter-input-contract.v1`,
`vc.k562-golden-adapter-output-contract.v1`,
`vc.k562-golden-prepared-model-input.v1`,
`vc.model-validation-evidence.v1`, `vc.model-operator-policy.v1`,
`vc.model-release.v1`, `vc.model-registry-event.v1`, `vc.model-registry-state.v1`,
`vc.model-registry.v2`, `vc.model-registry-catalog.v2`,
`vc.model-registry-legacy-receipt.v1`,
`vc.model-registry-legacy-migration-report.v1`, `vc.environment.v1`,
`vc.environment.v2`, `vc.compatibility-report.v1`,
`vc.compatibility-report.v2`, `vc.execution-plan.v1`,
`vc.execution-step.v2`, `vc.execution-plan.v2`, the other `vc.*.v1`
domain/bundle schemas, `vc.pack-record.v1`, `vc.pack-catalog.v1`,
`vc.pack-index.v1`, `vc.pack-compatibility-surface.v1`,
`vc.job-execution-identity.v1`, `vc.job-execution-identity.v2`,
`vc.data-catalog.v1`, `vc.upload-receipt.v1`,
`vc.golden-norman.v1`, `vc.golden-baseline.v1`,
`vc.golden-evaluation.v1`, `vc.golden-artifact-manifest.v1`,
`vc.community-pack.v1`, the `vc.community-*.v1` exchange/plan/result schemas,
runtime/API protocol identifiers, memory schema,
`feature_schema_v0.3.0`, governance model versions, registry model revisions, and
artifact hashes. CI should validate their format/integrity and compatibility, not
force them to equal the product release.

## Change policy

- Patch: compatible fixes, documentation, CI/test corrections, packaging repair, and no deliberate product capability expansion.
- Minor: backward-compatible user-visible capability, workflow, UI, or supported-case expansion.
- Major: intentionally incompatible public CLI/API/report/runtime behavior requiring a migration.
- Protocol/schema/artifact breaking changes require their own migration note and compatibility tests regardless of product SemVer.
- Scientific evidence is not versioned into truth by bumping a number; it changes only with
  reproducible exact-scope evidence. Operator product policy is separate and cannot be created by
  either a version bump or scientific evidence alone.

## Required candidate verification

```bash
PYTHON_BIN=python3.13 scripts/build_release_wheel.sh /tmp/release-one
PYTHON_BIN=python3.13 scripts/build_release_wheel.sh /tmp/release-two
cmp /tmp/release-one/praxis_virtualcell-*.whl \
    /tmp/release-two/praxis_virtualcell-*.whl

python3.13 -m venv /tmp/release-venv
/tmp/release-venv/bin/python -m pip install \
  --require-hashes -r requirements/runtime-py313.lock
/tmp/release-venv/bin/python -m pip install \
  --no-deps /tmp/release-one/praxis_virtualcell-*.whl
/tmp/release-venv/bin/python -m pip check
(cd /tmp && /tmp/release-venv/bin/python \
  /absolute/path/to/repository/scripts/verify_release_install.py)

npm --prefix praxis_vc_react pkg get version
scripts/build_release_container.sh praxis-virtualcell:local
```

The verifier queries the installed API/health and same-origin static UI. The opt-in Docker smoke separately proves that the OCI revision, health SHA, installed CLI, UI assets, and offline API report all refer to the candidate commit. Playwright remains the browser-level UI gate, and frozen governance artifact hashes remain separate integrity checks. Tagging, pushing, or changing `.53` remains a Phase D action requiring explicit approval.
