# PRAXIS-VirtualCell Versioning Contract

> Status: P29E `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`; fixture evidence
> `SYNTHETIC_CONFORMANCE_ONLY`; umbrella `ENGINEERING_COMPLETE_SCIENCE_PENDING`; science
> `NOT_RUN`; policy `NO_NEW_DECISION`; the authoritative P29 graph is `empty_not_connected`
> with zero nodes/edges because real P29 has zero qualifying biological nodes.
> P27A-R historical replay remains
> `REPLAY_NOT_RUN / ASSET_PENDING`; P27B `AUTHORIZATION_REQUIRED / SHADOW_NOT_RUN`;
> P27C `AUTHORIZATION_REQUIRED / PILOT_NOT_RUN`; P30A-E1 release-contract hardening is
> `ENGINEERING_COMPLETE`; P30A-E2a clean-SHA offline preflight and P30A-E2b archive-only runner are
> `COMPLETE_NEGATIVE`; P30A-E2c is `RECONCILIATION_ONLY / NO_RC_CLAIM`. Formal P30A remains
> `LOCAL_RC_INCOMPLETE`; P16R local
> authorization-preflight identity bridge is `COMPLETE — IDENTITY_PREFLIGHT_ONLY`, while actual P16R remains
> `AUTHORIZATION_REQUIRED / NOT_RUN`; local queue is `BLOCKED_EXTERNAL`; science is
> `NOT_RUN / SCIENCE_BADGE_INELIGIBLE`; policy is `NO_NEW_DECISION`.
>
> Local baseline: branch `codex/p25e-virtual-microbiome`; starting SHA
> `90990c198c40d0e6655aedaad101a783cde003aa`; completion code SHA/tree
> `471767e5f38f9866fbe396f39836369d943f6657` /
> `d1dec19f06ec88f563406b45f2b544effabad915`; source date epoch `1786187523`
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
| P18 multi-omics model-input work unit | start `f253664239e4b1c9665301cf1bdf4e117a3e9c31`; code `626c71ffd1ce18a5adc200f6a6e376e57b269beb`; tree `2b570398caff6cf955d789c3cb4a7a77dc13a082` | immutable local Git history plus `reports/phase18/PHASE18_COMPLETION.md` | strict joint-input contract complete; real multi-omics model acceptance pending; registry unchanged at 5/0/0, science not run, no policy/release/version bump; local complete wheel `1,132,811` bytes / `015724a90656...` / `367` entries / `14` React entries |
| P19 Controlled Pack Factory work unit | start `871c5a8a4265f5b8fe5c2c6e35d418644bf1c4be`; code `42eabe63ea1a444d8b2ad14cecba6c9d6fa351d5`; tree `b4bd63833adc89bd1e30e9595d2cb6b38a3e005f` | immutable local Git history plus `reports/phase19/PHASE19_COMPLETION.md` | contract-only receipt→registration complete; v2 index reads v1, path-only register retired, public projection read-only; real external fixture/output root/operator/science/policy not run; no version/release bump; reproducible wheel `1,154,421` bytes / `1231f948e6f5...` / `368` entries |
| P20 Virtual Cell Training Pipeline work unit | start `f53e29e5722a8fe48aa2eb6fe63be01f61b5cc9a`; code `a4003704b70f06eb65297ddd32e0695ae8ee146b`; tree `d12d64a7c8d013d8d299272eea88a4ce0431ccab`; epoch `1786040663` | immutable local Git history plus `reports/phase20/PHASE20_COMPLETION.md` | `COMPLETE — CONTRACT_ONLY`; exact RegisteredPack-bound job/audit/checkpoint/result/candidate chain; success `candidate_cataloged_contract_only`; science `NOT_RUN`, policy `NO_NEW_DECISION`; no real training/test/external/benchmark/evidence/promotion or version/release bump; P21A system-only eligible; exact-local-source/toolchain wheel `1,178,805` bytes / `2273ee71fb58...` / `370` entries, not pinned dependency closure |
| P21A Virtual Cell Benchmark System work unit | start `5f3fc2d88c20e8083fb66a4c3399c5fe148241be`; code `20ecc12542e5df40c90d1fc367dbe86b563478b8`; tree `ffcd261dd7d506d0ad852023afcba0f5c97a2d72`; epoch `1786050825` | immutable local Git history plus `reports/phase21a/PHASE21A_COMPLETION.md` | `COMPLETE — SYSTEM_ONLY`; exact protocol/run/result/evidence and negative-ledger contracts; P21B exact authorization+run+result execution trust remains out of band; science `NOT_RUN`, policy `NO_NEW_DECISION`, P21B/P21C authorization required/not run; no real benchmark/promotion or version/release bump; P22 contract-only eligible; exact-local-source/toolchain wheel `1,202,180` bytes / `ee98d4b3c689...` / `371` entries, not pinned dependency closure |
| P22 Curated Virtual Cell Registry work unit | docs start `09792e13e29a76b5e4434507f3334eefb947789c`; prerequisite `20ecc12542e5df40c90d1fc367dbe86b563478b8`; code `bca5ad661856e8d9aa832c47f23c6ad7179ee0c9`; tree `f78476ac1dbe2f865e3c1bcdc71ecc512dbad22a`; epoch `1786056220` | immutable local Git history plus `reports/phase22/PHASE22_COMPLETION.md` | `COMPLETE — CONTRACT_ONLY`; exact One-Pack/P21B composition, quarantine-first append-only lifecycle, default-deny external trust and independently persisted checkpoint; science `NOT_RUN`, policy `NO_NEW_DECISION`, real lifecycle not run; no HTTP/UI/runtime/install/execute or version/release bump; P23A contract-only was then eligible and subsequently completed; exact-local-source/toolchain wheel `1,217,155` bytes / `3f978e9f3eb0...` / `372` entries, not pinned dependency closure |
| P23A Cell Interaction Evidence work unit | start `2b5c28ac152857dfa1109de41ed5d5ddc7ab06a4`; code `2b894966cd00b2af2fafbf8f009566dd69f393a7`; tree `00bd98b0fd14091f4528115dcc66730264d5803a`; epoch `1786061504` | immutable local Git history plus `reports/phase23a/PHASE23A_COMPLETION.md` | `COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE`; strict directed release/Pack/context/P18/same-experiment/scorer identities and P13-shaped score-only fixture projection; science `NOT_RUN`, policy `NO_NEW_DECISION`; no real release/data/model/baseline/CI/OOD execution; P23B and P24 authorization required/not run; exact-local-source/toolchain wheel `1,226,514` bytes / `e78f40f0f4fe...` / `373` entries, not dependency closure, clean-install or release proof |
| P25E Virtual Microbiome contract work unit | active baseline `ae5e93571783cb3cf49a6e0fab531a89e963f7ec`; code `039393e6be897b3014bb0b657d0a439d879578b6`; tree `b53e542940bf39fd44965fe55416798211ab580b`; epoch `1786171049` | immutable local Git history plus `reports/phase25e/PHASE25E_COMPLETION.md` | `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`; fixture evidence `SYNTHETIC_CONFORMANCE_ONLY`; independent fixed 2–3-member scope/endpoint/adapter-requirement/request/plan/result identities; P10 v1 bytes/semantics preserved; all adapter/model/environment/mapping/protocol/evidence/policy bindings absent and all results abstain; science `NOT_RUN`, policy `NO_NEW_DECISION`; P24/P25R authorization required/not run; exact-local-source/toolchain wheel `1,234,438` bytes / `c8529477974c...` / `374` entries; no product/API/runtime version or release bump |
| P26E Host–Microbiome contract work unit | active baseline `6bd02231449b6969e22aeb5bea6798fd334daef6`; code `5bd3e502a7a1f1cb0fd1b79ecfd109eeeaf265c4`; tree `b3d7303cafb5b874c8b5a441b53e32ff77ef2c54`; epoch `1786176771` | immutable local Git history plus `reports/phase26e/PHASE26E_COMPLETION.md` | `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`; exact host request/P25 contract, typed missing interface, topology-only DAG, P22 context-only audit and immutable negative compilation; fixture evidence `SYNTHETIC_CONFORMANCE_ONLY`; science `NOT_RUN`, policy `NO_NEW_DECISION`; P26R blocked external; exact-local-source/toolchain wheel `1,242,422` bytes / `69700bb63445...` / `375` entries; at P26 closure P27A-E was standing-local eligible and has subsequently completed; no product/API/runtime version or release bump |
| P27A-E Agentic Experiment Design work unit | active baseline `a12cf4f4b71efb653f8128afcb1f468211fdb837`; code `5875571bf9d8b518dc7a857feb935206f756de59`; tree `a7c65e7b30f51832660e66323b5946acbddcbf18`; epoch `1786180822` | immutable local Git history plus `reports/phase27ae/PHASE27AE_COMPLETION.md` | `COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE_ONLY`; exact request-derived value-free experiment design, structurally separated selection/outcome records, deterministic rank-then-reveal receipts, one primary strategy plus four baselines; historical replay `REPLAY_NOT_RUN / ASSET_PENDING`, science `NOT_RUN`, policy `NO_NEW_DECISION`; exact-local-source/toolchain wheel `1,251,560` bytes / `4bd584bdae75...` / `376` entries; P28E subsequently completed; no product/API/runtime version or release bump |
| P28E Multi-Agent Biology contract work unit | docs baseline `971f812faae09fa833dc66741e86ec9ffe97947c`; code `da4bfc042d96f830e2a7e8cdc62ba227c7ace949`; tree `e6f18371f5061c810b2cb87d9a278cfa6d6ac46b`; epoch `1786184568` | immutable local Git history plus `reports/phase28e/PHASE28E_COMPLETION.md` | `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`; six public typed role/handoff/DAG/trace/compilation records plus two non-public fingerprint payload versions; synthetic conformance only; real acceptance `BLOCKED / 0_OF_3_QUALIFYING_MODULES`, science `NOT_RUN`, policy `NO_NEW_DECISION`; local wheel `1,259,255` bytes / `0358bf4df9e9...` / `377` entries; P29E subsequently completed; no product/API/runtime version or release bump |
| P29E Limited Biological World Model contract work unit | docs baseline `90990c198c40d0e6655aedaad101a783cde003aa`; code `471767e5f38f9866fbe396f39836369d943f6657`; tree `d1dec19f06ec88f563406b45f2b544effabad915`; epoch `1786187523` | immutable local Git history plus `reports/phase29e/PHASE29E_COMPLETION.md` | `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`; three public strict requirement/subgraph/compilation records; graph `empty_not_connected`, biological nodes/edges `0`, all authority/value slots null; synthetic conformance only; real P29 `BLOCKED / 0_QUALIFYING_BIOLOGICAL_NODES`, science `NOT_RUN`, policy `NO_NEW_DECISION`; local wheel `1,263,199` bytes / `368a66a438c0...` / `378` entries; P30A-E1 subsequently completed; no product/API/runtime version or release bump |
| P30A-E1 release-contract hardening | P30 scope baseline `694af3eebfca0e99ca07a6ecd8639b522b8ec3d4`; post-entrypoint baseline `d808735ebfd649df6a4c932b95140387aa412c7d`; code `0a4d72b0825d9ec0ff3b7776bbc4f1f0023336f9`; tree `ba701d4ee6033e86a2d8abecc7e6ff25c1a05c14`; epoch `1786335170` | immutable local Git history plus `reports/phase30a/PHASE30A_ENGINEERING_COMPLETION.md` | `ENGINEERING_COMPLETE`; release-contract tooling and local probes only. Wheel probe `1,264,708` bytes / `44e5e905e706...2303`; source archive `8,055,078` bytes / `ba5e5d0dbe38...e642`; no formal RC artifact, clean install, OCI, SBOM, licence inventory, dependency audit, manifest, science or policy result |
| P30A-E2a offline preflight | start `40f433fef8704381de34aeb32d45399b6595c472`; code `964b62214f346b15ec2d3f2a622b33f632dde466`; tree `eac19455bc9241e5347de27782a99942e3591cab`; epoch `1786338523` | immutable local Git history plus `reports/phase30a/PHASE30A_E2A_PREFLIGHT.md` and out-of-tree record `6cb91031…9019` | `COMPLETE_NEGATIVE`; clean source stable, offline wheelhouse coverage insufficient for macOS/arm64 and Linux/arm64; no install/build/OCI/full gate/RC result, science or policy change |
| P30A-E2b archive-only runner | code `12ad93d57e4f4e7438d2110b5ac9848c6b17ea33`; tree `14fe604111c18c558048bc282d23da936ac57088`; epoch `1786343459` | immutable local Git history plus `reports/phase30a/PHASE30A_E2B_ARCHIVE_RUNNER.md`, runner record `72459a3b…63d2`, nested preflight `064a479f…fec4` | `COMPLETE_NEGATIVE`; source stable, immutable record retains two `source_archive_build_failed` attempts; its tracked-link causal attribution is unreproducible from the same exact committed `.gitattributes` / `git archive` inputs because raw stderr was not retained; wheelhouse profiles remain incomplete; no install/network/OCI/full gate/RC/science/policy result |
| P30A-E2c source-archive reconciliation | code `f9aa62d669c7bc3d5cbcca101e4e73ffd0bf821a`; tree `d364806f9a800680b40bdaaee8bb1aead748844c`; epoch `1786349933` | immutable local Git history plus `reports/phase30a/PHASE30A_E2C_SOURCE_ARCHIVE_RECONCILIATION.md` | `COMPLETE — RECONCILIATION_ONLY / NO_RC_CLAIM`; current exact-source export-ignore double probe preserves E2b failure result; no accepted artifact, formal RC, science, policy, promotion, or actual-P16R result |
| P16R-PREFLIGHT local authorization-preflight identity bridge | start `25fe60a9450765a9ecf3a2a38d198980ea7a7e15`; code `4f77255f84e33180d7d73b421fc9737ca3a1121d`; tree `f7aadb7b76a2aa55691d67d9c2948cc7b1e38e95`; epoch `1786347583` | immutable local Git history plus `reports/phase16r_preflight/PHASE16R_AUTHORIZATION_PREFLIGHT.md` | `COMPLETE — IDENTITY_PREFLIGHT_ONLY`; local declarations/fixed abstain only. Actual P16R remains `AUTHORIZATION_REQUIRED / NOT_RUN`; no asset I/O, model/benchmark/evidence/policy or route action is implied |
| Local queue | `BLOCKED_EXTERNAL` | exact authorization required | no planned local work remains; read-only candidate/asset inventory and P16R science run are separate windows; formal P30A remains `LOCAL_RC_INCOMPLETE` |
| GitHub published `main` | `8e0d06348ebdf22e076037e6d661094ae877c5d1` | last recorded read-only observation, not refreshed in this window | historical remote fact until separately authorized and refreshed |
| `.53` code mirror | recorded separately in the integration guide | not refreshed in this window | historical deployment evidence, not current authorization |
| local product metadata | `1.7.0` | `pyproject.toml` `[project].version` | P30A-E1 local source identity; it is not a released version or a completed RC identity |
| Python distribution | `1.6.0` | installed `praxis-virtualcell` metadata in the shared environment | stale shared environment; no clean-install gate may infer the `1.7.0` product identity from it |
| inherited `praxis2.__version__` | `1.6.0` | compatibility alias | aliases `praxis_virtualcell.__version__`; no second literal |
| main package export | `1.6.0` | `praxis_virtualcell.__version__` | derived from installed distribution metadata |
| CLI | `praxis-vc 1.6.0` | installed `praxis-vc --version` | derived from the main package export |
| frontend private package | `1.7.0` | `package.json` plus lock root | generated npm mirror for the local P30 source; not a scientific/API protocol, UI authority or release proof |
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
| multi-omics input/slot contracts | `vc.multiomics-input-contract.v1`, `vc.multiomics-modality-slot.v1` + canonical JSON SHA-256 | `praxis_virtualcell/multiomics_input.py` | binds ordered required/optional modalities, exact feature contracts, join/missingness policy, target modality and adapter-owned input identity; contract validity is not model acceptance |
| multi-omics layer/model input | `vc.multiomics-layer-input.v1`, `vc.multiomics-model-input.v1` + canonical JSON SHA-256 | `praxis_virtualcell/multiomics_input.py` | binds Pack/view/adapter, real observation membership, alignment and runtime matrix content while remaining non-executable contract-only abstain |
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
| K562 P16R external scope declaration | `vc.k562-p16r-external-scope-declaration.v1` + canonical JSON SHA-256 | `benchmarks/k562_p16r_preflight.py` | binds declared external K562 scope without byte receipt or membership proof; it is not a Pack verification or external result |
| K562 P16R authorization preflight | `vc.k562-p16r-authorization-preflight.v1` + canonical JSON SHA-256 | `benchmarks/k562_p16r_preflight.py` | binds P16/P12/P21 declarations into fixed `prediction=null` abstention; it is not authorization, execution, benchmark evidence, policy, or promotion |
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
| local Pack index | `vc.pack-index.v2` write, compatible v1/v2 read + Pack/factory fingerprints | `pack_product.py`, `PRAXIS_VC_PACK_INDEX` | v2 binds exact factory registration/store provenance; legacy v1 remains readable with null factory provenance; every use revalidates bytes, semantics and committed store chain |
| Controlled Pack Factory lifecycle/store | `vc.pack-candidate.v1`, `vc.pack-metadata-review.v1`, `vc.pack-validation-report.v1`, `vc.pack-operator-decision.v1`, `vc.factory-registered-pack.v1`, `vc.pack-supersession.v1` + canonical SHA-256; exact `.factory-store.json` bytes `{"schema_version":"vc.pack-factory-store.v1"}\n` | `pack_factory.py` | append-only receipt→registration identities in an explicitly initialized write-new store; named registration decision is not model policy, evidence, compatibility or execution |
| Pack Factory public catalog | `vc.pack-factory-catalog.v1` | `pack_factory.py`, `GET /api/pack-factory` | root-free read-only lifecycle projection with reviewer/operator raw IDs, rationale and reason redacted; `write_api_enabled=false`, model compatibility not evaluated, execution false |
| training job/environment/split/audit | `vc.training-environment.v1`, `vc.training-resource-limits.v1`, `vc.training-hyperparameter.v1`, `vc.training-asset-binding.v1`, `vc.training-split-asset.v1`, `vc.training-split.v1`, `vc.training-leakage-overlap.v1`, `vc.training-leakage-audit.v1`, `vc.training-job.v1` + canonical SHA-256 | `model_zoo/training/pipeline.py` | exact P19 registration, environment, trainer/code, allowlisted train assets and audit-before-label binding; declared lock digest is not authenticated environment truth |
| training worker/checkpoint/result | `vc.tiny-training-features.v1`, `vc.tiny-training-labels.v1`, `vc.tiny-trainer-input.v1`, `vc.tiny-json-checkpoint.v1`, `vc.candidate-checkpoint.v1`, `vc.training-metric.v1`, `vc.training-resource-observation.v1`, `vc.training-result.v1` + canonical SHA-256 | `model_zoo/training/pipeline.py`, `model_zoo/training/tiny_worker.py` | fixed trusted `python -I -S` worker and safe JSON checkpoint/result; isolation is not an OS syscall sandbox and tiny metrics are not benchmark evidence |
| training candidate/run bundles | `vc.training-model-identity.v1`, `vc.candidate-model-artifact.v1`, `vc.candidate-model-card.v1`, `vc.training-candidate-model.v1`, `vc.training-run-bundle.v1`, `vc.training-candidate-bundle.v1` + canonical SHA-256 | `model_zoo/training/pipeline.py` | candidate-only bidirectional identities; `candidate_cataloged_contract_only` is not registry insertion, scientific validation, promotion eligibility or production promotion |
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
| P25E Virtual Microbiome contracts | `vc.virtual-microbiome-scope.v1`, `vc.virtual-microbiome-primary-endpoint.v1`, `vc.virtual-microbiome-adapter-requirement.v1`, `vc.virtual-microbiome-contract.v1`, `vc.virtual-microbiome-request.v1`, `vc.virtual-microbiome-plan.v1`, `vc.virtual-microbiome-result.v1` + canonical JSON SHA-256 | `community_packs/virtual_microbiome.py` | exact fixed-scope identities and value-free abstention; schema or synthetic fixture existence does not imply P24/P25R execution, prediction, science, evidence, policy or promotion |
| P26E Host–Microbiome contracts | `vc.host-microbiome-interface-requirement.v1`, `vc.host-microbiome-dag.v1`, `vc.host-microbiome-contract.v1`, `vc.host-release-audit-snapshot.v1`, `vc.host-microbiome-compilation.v1` plus canonical `vc.host-microbiome-joint-scope.v1` fingerprint payload | `host_microbiome.py` | exact host/P25 requirement closure and value-free abstention; joint scope is not a sixth public model, P22 context match is not full-request binding, and schema/DAG existence does not imply releases, mapping, execution, science, policy or causality |
| P27A-E experiment-design/replay contracts | `vc.experiment-action.v1`, `vc.virtual-experiment.v1`, `vc.replay-selection-row.v1`, `vc.replay-selection-view.v1`, `vc.replay-outcome-row.v1`, `vc.replay-outcome-ledger.v1`, `vc.replay-protocol.v1`, `vc.replay-selection-receipt.v1`, `vc.replay-strategy-summary.v1`, `vc.replay-result.v1` plus canonical `vc.replay-outcome-contract.v1` fingerprint payload | `experiment_design.py` | request-derived value-free design and deterministic synthetic rank-then-reveal closure; outcome-contract is not an eleventh public model, and contracts/synthetic utility do not imply a historical replay, information gain, validated action domain, science, policy, shadow review, prospective pilot or execution |
| P28E Multi-Agent Biology contracts | `vc.multi-agent-role-policy.v1`, `vc.multi-agent-handoff.v1`, `vc.multi-agent-dag.v1`, `vc.multi-agent-trace-event.v1`, `vc.multi-agent-trace.v1`, `vc.multi-agent-biology-compilation.v1` plus canonical `vc.multi-agent-value-free-handoff.v1` and `vc.multi-agent-trace-root.v1` fingerprint payloads | `multi_agent_biology.py` | strict typed advisory handoffs bind only immutable identities; the authoritative compilation is value-free and empty because it has zero qualifying modules, not because it represents a connected biological subgraph; synthetic conformance does not imply real orchestration, model execution, evidence, science, policy or promotion |
| P29E Limited Biological World Model contracts | `vc.state-action-observation-time-requirement.v1`, `vc.connected-typed-subgraph.v1`, `vc.limited-world-model-compilation.v1` | `limited_world_model.py` | exact P28 identity closes a null requirement record, an `empty_not_connected` zero-node/zero-edge graph and value-free compilation; content hashes identify canonical bytes but do not authenticate an issuer; synthetic conformance does not imply a connected biological model, data/model execution, benchmark, science, policy or promotion |
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

P16R-PREFLIGHT subsequently adds the two P16R identity-only schemas above at code
`4f77255f84e33180d7d73b421fc9737ca3a1121d`. They bind declarations without changing product
SemVer, API/runtime protocols, default registry, release state, evidence, policy, or execution
availability. Their only allowed public outcome is fixed value-free abstention; actual P16R stays
`AUTHORIZATION_REQUIRED / NOT_RUN`. See the
[P16R identity-preflight completion record](../reports/phase16r_preflight/PHASE16R_AUTHORIZATION_PREFLIGHT.md).

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

P18 adds the strict multi-omics slot/input/layer/model-input schemas above without changing product
SemVer (`1.6.0`), API/runtime protocols, release tags, registry or promotion policy. Its exact code
commit is `626c71ffd1ce18a5adc200f6a6e376e57b269beb`. Ordered modalities, Pack/view/adapter identity,
real observation joins or explicit masks, alignment reports and runtime matrix fingerprints are
contract properties; no Broker execution step or real model acceptance is implied. Two clean
offline archive wheels are byte-identical at `1,132,811` bytes, SHA-256
`015724a90656706c0441e4f4f873ee51f8db87dfaae9de35a3e841e7c70b2b7c`, with `367` entries,
`14` React entries, no tests or AppleDouble. The registry remains 5/0/0; science is `NOT_RUN`,
policy is `NO_NEW_DECISION`, and there was no execution, release, push or deploy. See
[ADR-0015](ADR-0015-multiomics-model-input.md), the
[P18 runbook](runbooks/VIRTUALCELL-MULTIOMICS-MODEL-INPUT.md), and the
[P18 completion report](../reports/phase18/PHASE18_COMPLETION.md).

P19 adds the controlled Pack Factory schemas, `vc.pack-index.v2` and backward-compatible read-only
`GET /api/pack-factory` inside the same unpublished `1.6.0` candidate. Index v2 remains able to read
v1; legacy v1 entries have null factory provenance and are not retroactively approved. The old
path-only `PackIndex.register(pack_root)` write is intentionally retired. Registration requires an
explicit store and absolute index, and consumers treat the index→store interval as pending/fail
closed until the complete registration chain is committed.

P7 species values remain routing-only; exact taxon is the manifest identity separately confirmed
by the reviewer, so a coarse bacteria receipt does not imply *E. coli*. The public projection is
root-free and redacts raw operator/reviewer IDs, rationale and reason. P19 does not change product SemVer,
API/runtime protocol, model registry, evidence or promotion policy. Exact completion code/tree are
`42eabe63ea1a444d8b2ad14cecba6c9d6fa351d5` /
`b4bd63833adc89bd1e30e9595d2cb6b38a3e005f`; two offline clean-archive wheels are byte-identical at
`1,154,421` bytes / `1231f948e6f519b9cea66e5ab0e7ccb41b3b7f5a7aa73efdd7dbaf885bfa969f` /
`368` entries / `14` React entries, with no tests or AppleDouble. Real external
fixture/output root/operator/science/policy are not run.
See [ADR-0016](ADR-0016-controlled-pack-factory.md), the
[P19 runbook](runbooks/VIRTUALCELLPACK-CONTROLLED-PACK-FACTORY.md), and the
[P19 completion report](../reports/phase19/PHASE19_COMPLETION.md).

P20 adds the RegisteredPack-bound synchronous training contracts inside the same unpublished
`1.6.0` candidate. It starts at P19 docs-closure
`f53e29e5722a8fe48aa2eb6fe63be01f61b5cc9a` and completes at code/tree
`a4003704b70f06eb65297ddd32e0695ae8ee146b` /
`d12d64a7c8d013d8d299272eea88a4ce0431ccab` with source date epoch `1786040663`.
The runner replays exact P19 registration provenance and verifies trusted repository sources. Within
the Pack-root asset-byte boundary it reads the current manifest and split metadata before audit, then
opens train-consumed feature/label bytes only after audit; the stored P19 tree remains historical
provenance, and test/external/unconsumed/uploaded code-like assets are never opened. Its fixed trusted
worker is an isolated `python -I -S` subprocess, not an OS syscall sandbox. Environment identity
separates the caller-declared lock digest from the observed installed-distribution digest and makes
no authentication claim.

Success is exactly `candidate_cataloged_contract_only`. Focused P20 is `56 passed`; P19+P20 adjacent
is `99 passed / 1 skipped`; safe is `1,610 passed / 49 skipped / 387 deselected`; legacy is
`1,147 passed / 58 skipped / 105 deselected`. Ruff lint, targeted format, `py_compile` and diff
checks pass. Two
offline exact-code wheels are byte-identical at `1,178,805` bytes /
`2273ee71fb58fef543eae358d3df2aefccec42e80fe72a23380200718c223d79` / `370` entries / `14`
React entries, with no tests or AppleDouble; source/wheel hashes match for `pipeline.py`
(`dd7dbe480c3f000e5345b35fc6358fe2cc1b4377b035c31809d584ce3c869134`) and `tiny_worker.py`
(`4de1ba3b67a67ea24c16b7664058939ae3a634e06cf11601a528aca4c465f02b`). Builds used cached
`npm ci --offline` and the already-installed Python frontend with no isolation or dependency check;
they are not pinned dependency-closure or clean-install evidence. This changes no product SemVer,
API/runtime protocol, release or publication. Real training, test/external evaluation,
benchmark, science, evidence, registry promotion, push and deploy remain not run; policy is
`NO_NEW_DECISION`. At P20 closure P21A system-only was next eligible; it subsequently completed,
while P21B/P21C remain authorization-required and not run.
See [ADR-0017](ADR-0017-virtual-cell-training-pipeline.md), the
[P20 runbook](runbooks/VIRTUALCELL-TRAINING-PIPELINE.md), and the
[P20 completion report](../reports/phase20/PHASE20_COMPLETION.md).

P21A adds the strict Virtual Cell Benchmark System contracts inside the same unpublished
`1.6.0` candidate. It starts at P20 docs-closure
`5f3fc2d88c20e8083fb66a4c3399c5fe148241be` and completes at code/tree
`20ecc12542e5df40c90d1fc367dbe86b563478b8` /
`ffcd261dd7d506d0ad852023afcba0f5c97a2d72` with source date epoch `1786050825`.
The system binds and recomputes exact protocol, authorization, run, result, primary/CI,
calibration, selective/OOD/external and evidence identities. A positive authorized-candidate
derivation requires an independently trusted P21B composite fingerprint over exact authorization,
run and result; contract fields and content hashes do not authenticate their issuer. A normal
self-contained bundle therefore remains negative unless a P21B consumer supplies that trust
out of band.

The append-only store admits only negative evidence. Its hash chain and durable head detect content
tampering and tail truncation, but without an external or signed anchor cannot detect a rollback or
deletion that also restores/removes the complete ledger head. Focused P21A is `35 passed`; affected
is `238 passed`; safe is `1,645 passed / 49 skipped / 387 deselected`; legacy is
`1,147 passed / 58 skipped / 105 deselected`; static checks pass. Two offline exact-code wheels are
byte-identical at `1,202,180` bytes /
`ee98d4b3c6895bb6a91be1c439a0f927050cb813e9f7e5c61a37552a15c326f1` / `371` entries /
`14` React entries, with no tests or AppleDouble. The source/wheel benchmark-system module SHA-256
is `583d14434216c26ddffa170e2c35f24963f03461d4e9f10c3fe105073624c4d0`.
Builds used `npm ci --offline` plus Python `--no-isolation --skip-dependency-check`, so this is not
pinned dependency-closure or clean-install evidence; host-polluted global `pip check` is invalid and
is not a passing gate. P21A creates no product/API/runtime version bump or release identity, and
does not run a real candidate, benchmark, science, operator policy, promotion, push or deploy.
P21B/P21C remain `AUTHORIZATION_REQUIRED / NOT_RUN`; P22 contract-only subsequently completed. See
[ADR-0018](ADR-0018-virtual-cell-benchmark-system.md), the
[P21A runbook](runbooks/VIRTUALCELL-BENCHMARK-SYSTEM.md), and the
[P21A completion report](../reports/phase21a/PHASE21A_COMPLETION.md).

P22 adds the Curated Virtual Cell Registry contracts inside the same unpublished `1.6.0`
candidate. It starts at P21A docs-closure
`09792e13e29a76b5e4434507f3334eefb947789c`, requires P21A code
`20ecc12542e5df40c90d1fc367dbe86b563478b8`, and completes at code/tree
`bca5ad661856e8d9aa832c47f23c6ad7179ee0c9` /
`f78476ac1dbe2f865e3c1bcdc71ecc512dbad22a` with source date epoch `1786056220`.
Its v1 release identity composes exactly one `FactoryRegisteredPackV1`, one existing P12
release/evidence/policy closure, one P21B evidence bundle and exact wrapper approvals. It consumes
but cannot create, upgrade or recompute scientific or operator-policy state. Multi-Pack and direct
P14/P15/P16 or other non-P21B evidence routes require a future schema version.

Imports begin quarantined; approve/quarantine/revoke/supersede change lifecycle metadata only.
External trust defaults deny-all and authorizes exact import/decision fingerprints. The stable
authorization reference binds authority, kind and subject fingerprint rather than mutable whole
trust. An independently persisted `{entry_count,last_entry_fingerprint}` checkpoint anchors the
prefix, after which every suffix entry is reauthorized against current trust. `checkpoint()` does
not persist that anchor; until a revoke/supersede tail is externally checkpointed, rollback to the
prior checkpoint remains possible. Content fingerprints and authorization references are not
signatures or issuer authentication.

Focused P22 is `35 passed / 43.55s`; affected is `289 passed / 1 skipped / 64.94s`; safe is
`1,680 passed / 49 skipped / 387 deselected / 334.23s`; legacy is
`1,147 passed / 58 skipped / 105 deselected / 60.48s`; static checks pass. Two exact-code wheels are
byte-identical at `1,217,155` bytes /
`3f978e9f3eb06ea17017c1838002762f28ae717ee08d987cfb8ea059162a2485` / `372` entries /
`14` React entries, with no tests or AppleDouble. Source/wheel
`praxis_virtualcell/model_zoo/curated_registry.py` SHA-256 is
`9678b2460aff6738935a2728e12abf398985c4475d66be96d37a721a21bf62ff`.
The local offline/no-isolation/skip-dependency-check toolchain result is reproducibility evidence,
not pinned dependency closure or clean-install proof.

The default curated store/catalog is absent or empty; public projection is a redacted,
non-executable Python library surface with installed/compatibility unknown. P22 adds no HTTP/UI,
Data Center/chat, runtime planning, asset installation/execution, real lifecycle, science, policy,
promotion, product/API/runtime version bump, release, push or deploy. P21B/P21C remain
`AUTHORIZATION_REQUIRED / NOT_RUN`; P23A subsequently completed contract-only. See
[ADR-0019](ADR-0019-curated-virtual-cell-registry.md),
the [P22 runbook](runbooks/VIRTUALCELL-CURATED-REGISTRY.md), and the
[P22 completion report](../reports/phase22/PHASE22_COMPLETION.md).

P23A adds the Cell Interaction Evidence contracts inside the same unpublished `1.6.0` candidate.
It starts at P22 docs-closure `2b5c28ac152857dfa1109de41ed5d5ddc7ab06a4` and completes at
code/tree `2b894966cd00b2af2fafbf8f009566dd69f393a7` /
`00bd98b0fd14091f4528115dcc66730264d5803a` with source date epoch `1786061504`.
Strict identities bind one directed sender and receiver to exact P22 release/Pack/context references,
typed but explicitly unverified P18 endpoint references, one indivisible same-experiment evidence
record and an explicitly untrusted P20/P21 scorer fixture. The adapter reuses P13 prepared input,
envelope and provenance shapes but is not added to the default registry.

The only public projection is `{"interaction_evidence_score": [x]}` on the unit interval with
`association_evidence_only` semantics. A `synthetic_conformance` projection normalizes a caller-supplied fixture; it
does not calculate a biological score or execute a model. Receiver response, effect size, causal
claim, legacy co-culture payload, extra output fields, unbound envelopes and abstaining projection
all fail closed. Missing paired evidence, failed baseline gate, unsupported/OOD scope, unauthorized
execution or unverified curated state produce exact abstention. Real data/model execution, paired
linkage, registry state, baseline comparison, paired CI and calibrated uncertainty remain false or
not available.

Focused P23A is `107 passed / 41.71s`; affected is
`495 passed / 1 skipped / 116.55s`; safe is
`1,787 passed / 49 skipped / 387 deselected / 367.11s`; legacy is
`1,147 passed / 58 skipped / 105 deselected / 57.38s`; static checks pass. Two exact-code wheels
are byte-identical at `1,226,514` bytes /
`e78f40f0f4fe7354e3c660d6612a8ee60a1b2dd61af2fc606a67d01e67ac601e` / `373`
entries / `14` React entries, with no tests or AppleDouble. Source/wheel
`praxis_virtualcell/model_zoo/cell_interaction_evidence_contract.py` SHA-256 is
`d1ba8d8054bf91c4a54a215c331fef65557df3954dba730998821ea9f70743cd`.
The toolchain is Python `3.13.12`, build `1.5.0`, setuptools `70.2.0`, packaging `26.0`, Node
`25.8.2`, npm `11.11.1` and Vite `8.1.2`; offline npm plus Python
`--no-isolation --skip-dependency-check` make this exact local source/toolchain reproducibility,
not dependency-closure, clean-install or release proof.

P23A performs no real asset read, model/baseline/benchmark/CI/OOD execution, science, operator
policy, promotion, product/API/runtime version bump, release, push or deploy. Engineering is
`COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE`; science is `NOT_RUN`; policy is
`NO_NEW_DECISION`. Optional P23B is `AUTHORIZATION_REQUIRED / NOT_RUN`. P24 is the next
sequential phase, but the First Real Community Adapter requires a separately authorized exact real
asset/model/output window and remains `AUTHORIZATION_REQUIRED / NOT_RUN`; no fake contract-only
scaffold is eligible. See [ADR-0020](ADR-0020-cell-interaction-evidence-contract.md), the
[P23A runbook](runbooks/CELL-INTERACTION-EVIDENCE.md), and the
[P23A completion report](../reports/phase23a/PHASE23A_COMPLETION.md).

P25E adds seven independently named `vc.virtual-microbiome-*.v1` schemas inside the same
unpublished `1.6.0` candidate. It starts from the observed active baseline
`ae5e93571783cb3cf49a6e0fab531a89e963f7ec` and completes at code/tree
`039393e6be897b3014bb0b657d0a439d879578b6` /
`b53e542940bf39fd44965fe55416798211ab580b`. It does not change P10
`vc.community-*.v1`, product SemVer, API/runtime protocols, the default adapter registry or any
published identity.

The schemas freeze an ordered 2–3-member Pack/taxonomy/assembly/strain/abundance/medium/time scope,
one end-time abundance endpoint and a typed negative adapter requirement. P24 adapter, model,
environment, mapping, benchmark protocol, evidence and policy fingerprints are null by construction;
every plan is non-executable and every result is value-free abstention. The synthetic fixture and
frozen fingerprints prove only local deterministic conformance.

Focused P25E is `21 passed`; adjacent P25E+P10 is `60 passed`; safe is
`1,809 passed / 49 skipped / 387 deselected / 449.43s`;
legacy is `1,147 passed / 58 skipped / 105 deselected / 57.14s`; static/frontend checks pass. Two
completion-code wheels are byte-identical at `1,234,438` bytes /
`c8529477974c6379f75bee05e4b0b589e3a03ed70302617ab46461954915d77e` / `374`
entries / `14` React entries, with no tests or AppleDouble. `pip check` remains a recorded failure
because the shared host environment has pre-existing dependency conflicts; no dependency was changed.

P25E performs no external asset read, P24/P25R execution, model/baseline/benchmark/CI/OOD run,
science, operator policy, promotion, product/API/runtime version bump, release, push or deploy.
Engineering is `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`; fixture evidence is
`SYNTHETIC_CONFORMANCE_ONLY`; science is `NOT_RUN`; policy is
`NO_NEW_DECISION`. See [ADR-0021](ADR-0021-virtual-microbiome-contract.md), the
[P25E runbook](runbooks/VIRTUAL-MICROBIOME-CONTRACT.md), and the
[P25E completion report](../reports/phase25e/PHASE25E_COMPLETION.md).

P26E adds five public `vc.host-microbiome-*.v1`/host-audit records and one canonical
`vc.host-microbiome-joint-scope.v1` fingerprint payload inside the same unpublished `1.6.0`
candidate. It starts from `6bd02231449b6969e22aeb5bea6798fd334daef6` and completes at code/tree
`5bd3e502a7a1f1cb0fd1b79ecfd109eeeaf265c4` /
`b3d7303cafb5b874c8b5a441b53e32ff77ef2c54`. It does not change P22/P25 schemas,
product SemVer, API/runtime protocols, registry state or any published identity.

The contract binds the complete host request, a P22-shaped context, exact P25E community identity,
typed missing interface and topology-only DAG. P22 v1 cannot bind the complete host request; community
release, matching release, mapping and source/target contract identities are null. Every compilation has
empty steps and null prediction/host/community/mediator values. K562 substitution and LLM/candidate
authority are rejected. These are conformance properties, not host–microbiome science.

Focused P26E is `8 passed`; affected P26E+P25E/P10+P22/P17 is `144 passed`; safe is
`1,817 passed / 49 skipped / 387 deselected / 387.09s`; legacy is
`1,147 passed / 58 skipped / 105 deselected`; static/frontend checks pass. Two independent
archive-built wheels are byte-identical at
`1,242,422` bytes / `69700bb63445864a457cb651037e69dddd93d5be4b184c55a34c3f9332de265a` /
`375` entries / `14` React entries, with no tests or AppleDouble. Source/wheel P26E module SHA-256
matches exactly. `pip check` remains a recorded pre-existing shared-environment failure.

Engineering is `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`; fixture evidence is
`SYNTHETIC_CONFORMANCE_ONLY`; science is `NOT_RUN`; policy is `NO_NEW_DECISION`; P26R is
`BLOCKED_EXTERNAL / NOT_RUN`. At the P26E completion point, standing local authorization made P27A-E
strict contracts and the rank-then-reveal synthetic harness the next eligible work unit; that follow-on is
now complete. No canonical local historical replay pool exists, so P27A-R historical replay remains
`REPLAY_NOT_RUN / ASSET_PENDING`; P27B remains `AUTHORIZATION_REQUIRED / SHADOW_NOT_RUN` and
P27C remains `AUTHORIZATION_REQUIRED / PILOT_NOT_RUN`. See
[ADR-0022](ADR-0022-host-microbiome-contract.md), the
[P26E runbook](runbooks/HOST-MICROBIOME-CONTRACT.md), and the
[P26E completion report](../reports/phase26e/PHASE26E_COMPLETION.md).

P27A-E adds ten public experiment-design/replay records and the canonical
`vc.replay-outcome-contract.v1` fingerprint payload inside the same unpublished `1.6.0` candidate. It
starts from P26E docs closure `a12cf4f4b71efb653f8128afcb1f468211fdb837` and completes at
code/tree `5875571bf9d8b518dc7a857feb935206f756de59` /
`a7c65e7b30f51832660e66323b5946acbddcbf18`. It does not change P17/P21/P26 schemas,
product SemVer, API/runtime protocols, registry state or any published identity.

The public design derives from an exact recursively revalidated request but stores only request identity
and derived scope identities, not raw request metadata, secrets, paths or constraint values. Because no
exact-request executable + scientifically validated + production-promoted action domain exists, the
authoritative action catalog is empty, design numerics are null, human approval remains required,
`executable`/`execution_performed` remain false, and no prediction is produced; science/policy remain false.
The synthetic harness freezes all five deterministic strategy receipts before revealing outcomes and
rejects re-signed selection, domain, group or ledger drift. Its `synthetic_realized_utility` is not real
information gain or scientific evidence.

Focused P27A-E is `28 passed`; the exact nine-file affected suite is `301 passed`; safe is
`1,845 passed / 49 skipped / 387 deselected / 453.03s`; legacy is
`1,147 passed / 58 skipped / 105 deselected / 61.21s`; static/frontend checks pass. Two independent
archive-built wheels are byte-identical at `1,251,560` bytes /
`4bd584bdae75888b4e09d8cfb2211e002cb509155ca834adb7d00a6106abec99` /
`376` entries / `14` React entries, with no tests or AppleDouble. Source/wheel module SHA-256 matches
`ffa647094f117ef45adb726559ee23bcb0bd20427c87681ab6675522fa26f55f` exactly. `pip check`
remains a recorded shared-environment failure; no dependency was changed.

Engineering is `COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE_ONLY`; umbrella status is
`ENGINEERING_COMPLETE_SCIENCE_PENDING`; science is `NOT_RUN`; policy is `NO_NEW_DECISION`.
P27A-R remains `REPLAY_NOT_RUN / ASSET_PENDING`; P27B is
`AUTHORIZATION_REQUIRED / SHADOW_NOT_RUN`; P27C is
`AUTHORIZATION_REQUIRED / PILOT_NOT_RUN`. P28E contract-only orchestration subsequently completed;
real P28 acceptance remains blocked at zero of three qualifying modules. See
[ADR-0023](ADR-0023-agentic-experiment-design-contract.md), the
[P27A-E runbook](runbooks/AGENTIC-EXPERIMENT-DESIGN.md), and the
[P27A-E completion report](../reports/phase27ae/PHASE27AE_COMPLETION.md).

P28E adds six public multi-agent biology records and two canonical fingerprint payload versions inside
the same unpublished `1.6.0` candidate. It starts from P27 docs closure
`971f812faae09fa833dc66741e86ec9ffe97947c` and completes at code/tree
`da4bfc042d96f830e2a7e8cdc62ba227c7ace949` /
`e6f18371f5061c810b2cb87d9a278cfa6d6ac46b`. Role policies prohibit external I/O, dynamic execution,
numeric outputs and evidence/policy creation. Every advisory handoff and trace event is typed,
identity-bound and deterministic; an authoritative compilation accepts an exact same-request P17
compilation/P27 experiment plus an exact standalone replay-result fingerprint and is value-free with an empty
DAG and trace. `ReplayResultV1` has no request/experiment link, so the replay is identity-bound but not called
request-matched. This is an abstention caused by `0/3`
exact-scope executable + scientifically validated + production-promoted model modules; it is not a
connected biological subgraph or real multi-agent execution.

Focused P28E is `38 passed`; the exact ten-test-file affected suite is `339 passed`; safe is
`1,883 passed / 49 skipped / 387 deselected / 419.19s`; legacy is
`1,147 passed / 58 skipped / 105 deselected / 51.29s`; packaging/versioning is `18 passed`; Ruff and
static/frontend checks pass. Two independent archive-built wheels are byte-identical at `1,259,255` bytes /
`0358bf4df9e929be7c520e93f7c95dccc351895e7926773b53de8febf7eaec9f` /
`377` entries / `14` React entries, with no tests or AppleDouble. The P28 module source/wheel bytes
match at SHA-256 `aadb8fba6efb943799cfa8d9f296f2a7e03f27d45d52d22ce3e1b67b94b160ca`.
Global `pip check` remains a recorded failure because the shared environment lacks `python-magic` and has
pre-existing `vcbench` pin conflicts; no dependency or environment state was changed.

Engineering is `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`; fixture evidence is
`SYNTHETIC_CONFORMANCE_ONLY`; umbrella status is `ENGINEERING_COMPLETE_SCIENCE_PENDING`; real P28
acceptance is `BLOCKED / 0_OF_3_QUALIFYING_MODULES`; science is `NOT_RUN`; policy is
`NO_NEW_DECISION`. No LLM/tool/model execution, data/weight access, benchmark, comparison/ablation,
operator decision, release, push or deploy occurred. P29E limited-world-model contract-only work is
the historical handoff and subsequently completed. See [ADR-0024](ADR-0024-multi-agent-biology-contract.md), the
[P28E runbook](runbooks/MULTI-AGENT-BIOLOGY-CONTRACT.md), and the
[P28E completion report](../reports/phase28e/PHASE28E_COMPLETION.md).

P29E adds three public limited-world-model records inside the same unpublished `1.6.0` candidate. It starts
from P28 docs closure `90990c198c40d0e6655aedaad101a783cde003aa` and completes at code/tree
`471767e5f38f9866fbe396f39836369d943f6657` /
`d1dec19f06ec88f563406b45f2b544effabad915`. The compiler accepts only an exact recursively
revalidated P28 compilation. State/action/observation/time and all data/model/environment/adapter/compute/
benchmark/evidence/policy/result/tool identities remain unavailable; the authoritative graph is exactly
`empty_not_connected` with zero nodes and edges, and no placeholder molecule-to-organism chain exists.
Standalone replay is inherited only through the P28 identity and remains explicitly not request-bound.
Content fingerprints bind canonical bytes; they are not a signature or issuer attestation.

Focused P29E is `51 passed`; P28+P29 adjacent is `89 passed`; the exact eleven-test-file affected suite is
`390 passed`; safe is `1,934 passed / 49 skipped / 387 deselected / 427.59s`; legacy is
`1,147 passed / 58 skipped / 105 deselected / 58.07s`; packaging/versioning is `18 passed`; Ruff and
static/frontend checks pass. Two independent archive-built wheels are byte-identical at `1,263,199` bytes /
`368a66a438c036a3b9c24f1093fc478886885fbefaecfea52bb50ad616206c01` /
`378` entries / `14` React entries, with no tests or AppleDouble. The P29 module source/wheel bytes match at
SHA-256 `b730220099b36df99f7ba706be7dea6174b1c41329b62526dc45bda475c155ae`.

Engineering is `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`; fixture evidence is
`SYNTHETIC_CONFORMANCE_ONLY`; umbrella status is `ENGINEERING_COMPLETE_SCIENCE_PENDING`; real P29 is
`BLOCKED / 0_QUALIFYING_BIOLOGICAL_NODES`; science is `NOT_RUN`; policy is `NO_NEW_DECISION`.
No real data/model/benchmark, execution, operator decision, release, push or deployment occurred. P30A-E1
release-contract hardening, P30A-E2a clean-SHA offline preflight and P30A-E2b archive-only runner
subsequently completed. Formal P30A remains incomplete after E2b's safely failed archive attempts and
missing wheelhouse inputs. P16R authorization-preflight identity bridge subsequently completed as
`IDENTITY_PREFLIGHT_ONLY`; actual P16R remains externally authorized/not run. See
[ADR-0025](ADR-0025-limited-biological-world-model-contract.md), the
[P29E runbook](runbooks/LIMITED-BIOLOGICAL-WORLD-MODEL-CONTRACT.md), and the
[P29E completion report](../reports/phase29e/PHASE29E_COMPLETION.md).

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
| K562 Golden delta and P16R-preflight schemas + fingerprints | explicit `vc.k562-golden-perturbation-scope.v1`, `vc.k562-golden-validation-protocol.v1`, `vc.k562-golden-data-binding.v1`, `vc.k562-golden-perturbation-binding.v1`, `vc.k562-golden-execution-binding.v1`, `vc.k562-golden-compatibility-binding.v1`, `vc.k562-golden-adapter-input-contract.v1`, `vc.k562-golden-adapter-output-contract.v1`, `vc.k562-golden-prepared-model-input.v1`, `vc.k562-p16r-external-scope-declaration.v1` and `vc.k562-p16r-authorization-preflight.v1` | exact K562/assembly/assay/ordered-feature/condition/perturbation/protocol/input/output/prepared/preflight semantics change incompatibly | a checkpoint or large asset was read, authorization was granted, K562 science passed, the adapter is default/runtime-ready, or evidence/policy exists |
| validation evidence schema + fingerprint | explicit `vc.model-validation-evidence.v1` plus canonical JSON SHA-256 | exact capability/protocol/baseline/metric/result binding changes | evidence exists, passes, generalizes, or grants product policy |
| operator policy schema + fingerprint | explicit `vc.model-operator-policy.v1` plus canonical JSON SHA-256 | named operator, exact capability/evidence decision or policy version changes | engineering or evidence state can manufacture a promotion decision |
| model release/lifecycle schemas + fingerprints | explicit `vc.model-release.v1`, `vc.model-registry-event.v1`, `vc.model-registry-state.v1` | component graph or append-only lifecycle fact changes | catalog/readiness/revocation/supersession is scientific evidence or product policy |
| Model Zoo root/public catalog schemas | explicit `vc.model-registry.v2`, `vc.model-registry-catalog.v2` | layered registry or path-redacted public projection changes incompatibly | migration/catalog presence makes a release executable, validated or promoted |
| environment snapshot schema + fingerprint | explicit `vc.environment.v1` or `vc.environment.v2` plus canonical JSON SHA-256 | import-module/resource/runtime-adapter observation or v2 identity binding changes | import-module names must equal PEP 503 distribution names, or a missing resource is available |
| compatibility report schema + fingerprint | explicit `vc.compatibility-report.v1` or `vc.compatibility-report.v2` plus canonical JSON SHA-256 | compatibility checks, reason semantics, identity inclusion/exclusion or bound refs change incompatibly | display-only model version/path affects the canonical v2 binding, or computed/evidence/policy states are interchangeable |
| execution step/plan schema + plan ID | explicit `vc.execution-plan.v1`, or `vc.execution-step.v2` and `vc.execution-plan.v2` with content-derived `plan_*` | canonical step/report/wrapper/agent binding or plan identity semantics change incompatibly | plan creation proves prediction correctness, scientific validation or promotion |
| Pack product record/catalog/index schemas | explicit `vc.pack-record.v1`, `vc.pack-catalog.v1`, v1-readable/`vc.pack-index.v2`-written index; catalog may nest `vc.model-registry-catalog.v2` | incompatible public metadata, index-field, identity binding or registry projection semantics | legacy readability or registration proves per-request compatibility or scientific validity |
| Pack Factory lifecycle/store/catalog schemas + fingerprints | explicit `vc.pack-candidate.v1`, `vc.pack-metadata-review.v1`, `vc.pack-validation-report.v1`, `vc.pack-operator-decision.v1`, `vc.factory-registered-pack.v1`, `vc.pack-supersession.v1`, exact `.factory-store.json` marker bytes `{"schema_version":"vc.pack-factory-store.v1"}\n` and `vc.pack-factory-catalog.v1` plus canonical JSON SHA-256 | receipt/candidate/review/validation/decision/registration/supersession identity, initialized-store ownership or public redaction semantics change incompatibly | an arbitrary directory is a store, or factory registration is model compatibility, execution, evidence, scientific validation or product policy |
| training pipeline schemas + fingerprints | explicit P20 job/environment/split/audit, worker/checkpoint/result and candidate/run schema literals listed above plus canonical JSON SHA-256 | job/environment/split/audit/checkpoint/result/candidate identity or serialization semantics change incompatibly | contract-only dry-run is real training, benchmark evidence, scientific validation, registry insertion or promotion policy |
| benchmark system schemas + fingerprints | explicit `vc.benchmark-*.v1`, `vc.p21b-execution-identity.v1`, `vc.benchmark-evidence-ledger.v1` and canonical JSON SHA-256 | protocol/run/result/measurement/evidence/bundle, independent P21B execution-trust lookup or negative-ledger identity/serialization semantics change incompatibly | a self-asserted authorization/content hash is authenticated, a synthetic passing fixture is science, evidence grants operator policy, or the ledger has an external rollback anchor |
| curated Virtual Cell release/registry schemas + fingerprints | explicit `vc.virtual-cell-context.v1`, `vc.virtual-cell-wrapper-approval.v1`, `vc.virtual-cell-release.v1`, `vc.curated-virtual-cell-import-identity.v1`, `vc.curated-registry-decision.v1`, `vc.curated-registry-entry.v1`, `vc.curated-registry-head.v1`, `vc.curated-registry-trust.v1`, `vc.curated-registry-authorization-reference.v1`, `vc.curated-release-state.v1`, exact marker `{"schema_version":"vc.curated-virtual-cell-registry.v1"}\n`, `vc.curated-virtual-cell-catalog.v1` and `vc.curated-release-dependency-graph.v1` | exact One-Pack composition, import/lifecycle/log/trust/checkpoint/public-projection/dependency semantics change incompatibly | a content hash authenticates its issuer, curated metadata creates science/policy, catalog means installed/compatible/executable, or a local head replaces an external checkpoint |
| cell-interaction evidence schemas + fingerprints | explicit `vc.p23-p18-endpoint-identity.v1`, `vc.interaction-endpoint.v1`, `vc.same-experiment-interaction-evidence.v1`, `vc.interaction-scorer-fixture.v1`, `vc.cell-interaction-evidence-input.v1`, `vc.interaction-evidence-adapter-input-contract.v1` and `vc.interaction-evidence-adapter-output-contract.v1` plus canonical JSON SHA-256 | directed endpoint/release/Pack/context/P18 identity, indivisible same-experiment linkage, ligand/receptor/evidence mapping, untrusted scorer fixture, score scale or projection semantics change incompatibly | a declared release/evidence/scorer is verified, a supplied fixture is model output or science, receiver response/effect/causality exists, or conformance grants policy/promotion |
| Pack compatibility surface schema | explicit `vc.pack-compatibility-surface.v1` | incompatible path-redaction or public execution-plan projection | a compatibility response proves successful execution |
| job execution identity schema + fingerprint | explicit `vc.job-execution-identity.v1`, `vc.job-execution-identity.v2` or `vc.job-execution-identity.v3` and content identity | incompatible request/report/outcome/Pack/release/component/evidence/policy identity-lock semantics; v3 also binds Brain/DAG and companion-backed contract-only report semantics | read-only loading may rewrite old bytes, schema downgrade may bypass current bindings, or immutable provenance proves model quality/validation/promotion |
| public data catalog schema | explicit `vc.data-catalog.v1` | incompatible metadata, source/terms, identity or file-verification semantics | file availability, Pack validity, model compatibility or scientific validity |
| upload receipt schema | explicit `vc.upload-receipt.v1` | incompatible quarantine identity/provenance semantics | internal file safety/quality, user authentication identity, Pack registration or model use |
| Golden benchmark contract + canonical hash | explicit `vc.golden-norman.v1` and content identity | source, semantic field, feature order, control/split, truth, metric/bootstrap or baseline definition changes | one successful run validates another dataset/model or creates scientific truth |
| Golden baseline/evaluation/inventory schemas + hashes | explicit `vc.golden-*.v1` and per-file identities | incompatible artifact semantics or regenerated bytes | lower MSE, executable runtime, or an inventory entry implies `scientifically_validated=true` |
| CommunityPack schema + fingerprint | explicit `vc.community-pack.v1` plus canonical JSON SHA-256 | incompatible member/reference/ecology-metadata semantics change | a valid contract supplies a community model or experimental truth |
| Community exchange/plan/result schemas | explicit `vc.community-*.v1` identities | incompatible ledger, conservation, planning or abstention semantics change | toy balance proves biological feasibility, or an empty plan proves execution |
| P25E Virtual Microbiome schemas + fingerprints | seven explicit `vc.virtual-microbiome-*.v1` scope/endpoint/adapter-requirement/contract/request/plan/result identities | incompatible ordered member/scope/endpoint/missing-binding/abstention semantics change; use a new schema version | a two-member synthetic fixture or valid schema proves a real adapter, prediction, science, evidence, policy or promotion |
| P26E Host–Microbiome schemas + fingerprints | five public strict interface/DAG/contract/host-audit/compilation records plus one canonical joint-scope fingerprint payload | incompatible host/P25/interface/DAG/audit/negative-compilation meaning changes; future executable community or matching releases require independent new schemas | a P22 context match binds the full request, P25E is a community release, topology is execution/causality, or synthetic conformance grants science/policy |
| P27A-E experiment-design/replay schemas + fingerprints | ten public strict action/design/selection/outcome/protocol/receipt/summary/result records plus one canonical outcome-contract fingerprint payload | incompatible request-derived design, domain/feasibility, selector/outcome separation, receipt, group, failure or result semantics change; use a new schema version | synthetic utility is information gain, historical replay ran, a validated action domain exists, or science/policy/shadow/prospective/execution was granted |
| P28E Multi-Agent Biology schemas + fingerprints | six public strict role-policy/handoff/DAG/trace-event/trace/compilation records plus canonical value-free-handoff and trace-root fingerprint payloads | incompatible role permissions, immutable binding, handoff/DAG/trace canonicalization, or value-free abstention semantics change; use a new schema version | advisory or empty authoritative records create a biological subgraph, model execution, evidence, scientific validation, policy or promotion |
| P29E Limited Biological World Model schemas + fingerprints | three public strict state/action/observation/time-requirement, connected-typed-subgraph and compilation records | incompatible upstream binding, requirement availability, graph connectivity, authority-null or abstention semantics change; use a new schema version | an empty graph is connected, a content hash authenticates its issuer, or synthetic conformance creates data/model execution, benchmark, science, policy or promotion |
| `memory_schema_version` | integer/content-schema identifier | memory frontmatter/content contract change | product release cadence |
| `feature_schema_version` | existing SemVer-like artifact contract | retraining/migrating the feature vector contract | UI/package version |
| governance `model_version` + SHA | immutable named revision plus content hash | genuinely regenerated/retrained artifact | product release cadence |
| registry `model_revision` | model/dataset/checkpoint-specific identifier plus asset SHA | specific model/checkpoint changes | whole-product version |
| frontend package version | generated mirror of the product version for release builds | synchronized by the release tool, never used as authority | API/runtime protocol version |
| `git_sha` / image digest | exact build identity | every build | semantic compatibility |

## Single product-version source

`pyproject.toml` `[project].version` is the only manually editable product-version source.

Implemented history through the current P29E contract-complete bytes:

1. C2's compatible cleanup candidate was `1.5.1`. C3 then accepted and committed user-visible theme, result, input, and workflow-state improvements, so the local candidate is now the required minor version `1.6.0`; `1.5.1` was never published.
2. `importlib.metadata.version("praxis-virtualcell")` is exposed as `praxis_virtualcell.__version__`; an uninstalled source import returns the honest fallback `0+unknown`.
3. `praxis2.__version__` is a compatibility alias rather than a second literal.
4. `praxis-vc --version`, FastAPI/OpenAPI, and health use the same installed product value.
5. `/api/health` separately exposes product, API protocol, runtime protocol, and injected build SHA while retaining `runtime_version="v0.3"`.
6. The UI consumes backend `product_version` and `git_sha`; an E2E mock with product `9.9.9` proves that it does not invent this truth from frontend metadata.
7. `npm version 1.6.0 --no-git-tag-version` synchronized the private package and lock root as a generated mirror. Neither is manually authoritative.
8. The normative full-release workflow requires hash-locked Python 3.13 build dependencies, packaged React UI, and clean-install verification against installed distribution metadata. P23A's contract-closure wheel is narrower exact-local-source/toolchain evidence and did not satisfy this release gate.
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
24. P18 code `626c71ffd1ce18a5adc200f6a6e376e57b269beb` adds strict ordered joint
    multi-omics input contracts, exact join/missingness identities, adapter ownership and
    content-bound runtime matrices inside the same unpublished candidate. It does not zero-fill,
    impute, normalize, create an execution step or accept a real model. Registry 5/0/0 is unchanged;
    science is `NOT_RUN`, policy is `NO_NEW_DECISION`, and no product/API/runtime version bump,
    release, tag, push or deploy is created. Two clean offline archive wheels are byte-identical at
    `1,132,811` bytes / `015724a90656706c0441e4f4f873ee51f8db87dfaae9de35a3e841e7c70b2b7c` /
    `367` entries / `14` React entries, with no tests or AppleDouble.
25. P19 starts at P18 docs-closure `871c5a8a4265f5b8fe5c2c6e35d418644bf1c4be`
    and adds the controlled receipt/candidate/review/validation/decision/registration chain,
    append-only store with exact `.factory-store.json`
    `{"schema_version":"vc.pack-factory-store.v1"}\n` initialization marker,
    v1-compatible/v2-writing Pack index, explicit local CLI dependencies and
    root-free read-only catalog/UI inside the same unpublished candidate. The former path-only
    registration bypass is rejected, and incomplete index/store commit remains unconsumable.
    P7 species remains routing-only; no exact taxon is inferred. Final code/tree are
    `42eabe63ea1a444d8b2ad14cecba6c9d6fa351d5` /
    `b4bd63833adc89bd1e30e9595d2cb6b38a3e005f`; reproducible wheel is `1,154,421` bytes /
    `1231f948e6f5...` / `368` entries. No product/API/runtime version bump, release, tag, training,
    checkpoint, evidence, push or deploy is created; network, external fixture/output root and real
    operator/science/policy remain not run.
26. P20 starts at P19 docs-closure `f53e29e5722a8fe48aa2eb6fe63be01f61b5cc9a`
    and adds an exact RegisteredPack-bound frozen job, pre-label leakage audit, fixed trusted tiny
    worker, safe JSON checkpoint/result and candidate-only identity chain. Final code/tree are
    `a4003704b70f06eb65297ddd32e0695ae8ee146b` /
    `d12d64a7c8d013d8d299272eea88a4ce0431ccab`; its exact-local-source/toolchain wheel is
    reproducible at `1,178,805` bytes / `2273ee71fb58...` / `370` entries, but is not pinned
    dependency-closure or clean-install evidence. Success is only
    `candidate_cataloged_contract_only`; science is `NOT_RUN`, policy is `NO_NEW_DECISION`, and no
    real training/test/external/benchmark/evidence/promotion, product/API/runtime version bump,
    release, tag, push or deploy is created. P21A system-only subsequently completed; P21B/P21C
    remain authorization-required and not run.
27. P21A starts at P20 docs-closure `5f3fc2d88c20e8083fb66a4c3399c5fe148241be`
    and adds exact benchmark protocol/run/result/evidence, out-of-band P21B execution-trust and
    negative-only content-addressed ledger contracts. Final code/tree are
    `20ecc12542e5df40c90d1fc367dbe86b563478b8` /
    `ffcd261dd7d506d0ad852023afcba0f5c97a2d72`; its exact-local-source/toolchain wheel is
    reproducible at `1,202,180` bytes / `ee98d4b3c689...` / `371` entries, but is not pinned
    dependency-closure or clean-install evidence. Engineering is `COMPLETE — SYSTEM_ONLY`, science
    is `NOT_RUN`, policy is `NO_NEW_DECISION`; P21B/P21C are authorization-required/not-run. No
    real benchmark, promotion, product/API/runtime version bump, release identity, tag, push or
    deploy is created. The product version remains unchanged at `1.6.0`; P22 contract-only
    subsequently completed.
28. P22 starts at P21A docs-closure `09792e13e29a76b5e4434507f3334eefb947789c`, with
    `20ecc12542e5df40c90d1fc367dbe86b563478b8` as its P21A prerequisite, and adds exact One-Pack/P21B
    release composition plus a quarantine-first append-only curated registry. Final code/tree are
    `bca5ad661856e8d9aa832c47f23c6ad7179ee0c9` /
    `f78476ac1dbe2f865e3c1bcdc71ecc512dbad22a`; its exact-local-source/toolchain wheel is
    reproducible at `1,217,155` bytes / `3f978e9f3eb0...` / `372` entries, but is not pinned
    dependency-closure or clean-install evidence. Engineering is `COMPLETE — CONTRACT_ONLY`,
    science is `NOT_RUN`, policy is `NO_NEW_DECISION`, and real import/catalog/revoke/supersede is
    `NOT_RUN`. Default-deny external trust and an independently persisted checkpoint remain caller
    responsibilities; hashes do not authenticate issuers. No product/API/runtime version bump,
    HTTP/UI/runtime/install/execution, release, tag, push or deploy is created. Product version stays
    `1.6.0`; P23A contract-only subsequently completed, while real release/data/execution remains gated.
29. P23A starts at P22 docs-closure `2b5c28ac152857dfa1109de41ed5d5ddc7ab06a4`
    and adds strict directed endpoint, same-experiment evidence and untrusted P20/P21 scorer-fixture
    identities plus a local P13-shaped adapter. Final code/tree are
    `2b894966cd00b2af2fafbf8f009566dd69f393a7` /
    `00bd98b0fd14091f4528115dcc66730264d5803a`; its exact-local-source/toolchain wheel is
    byte-identical at `1,226,514` bytes / `e78f40f0f4fe...` / `373` entries, but is not dependency-
    closure, clean-install or release evidence. The sole non-abstaining projection is the supplied
    synthetic fixture `interaction_evidence_score`; no biological scoring, real release/data/model
    verification, baseline/CI/OOD execution, receiver response or causal claim exists. Engineering is
    `COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE`, science is `NOT_RUN`, policy is
    `NO_NEW_DECISION`; P23B and P24 are authorization-required/not-run. No product/API/runtime
    version bump, release identity, tag, push or deploy is created. Product version remains `1.6.0`.
30. P25E starts from observed active baseline `ae5e93571783cb3cf49a6e0fab531a89e963f7ec`
    and adds independent virtual-microbiome scope/endpoint/negative-adapter/request/plan/result schemas
    while preserving P10 CommunityPack v1 bytes and no-model semantics. Final code/tree are
    `039393e6be897b3014bb0b657d0a439d879578b6` /
    `b53e542940bf39fd44965fe55416798211ab580b`; two local-toolchain wheels are byte-identical
    at `1,234,438` bytes / `c8529477974c...` / `374` entries. All execution bindings remain absent,
    plans/results abstain. Engineering is `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`, fixture
    evidence is `SYNTHETIC_CONFORMANCE_ONLY`, science is `NOT_RUN`, policy is `NO_NEW_DECISION`, and
    P24/P25R remain authorization-required/not-run. No product/API/runtime version bump, release
    identity, tag, push or deploy is created. Product version remains `1.6.0`.
31. P26E starts from observed active baseline `6bd02231449b6969e22aeb5bea6798fd334daef6`
    and adds exact host-request/P25 community closure, typed missing interface requirements, a fixed
    time-forward DAG, negative P22 audit and value-free compilation. Final code/tree are
    `5bd3e502a7a1f1cb0fd1b79ecfd109eeeaf265c4` /
    `b3d7303cafb5b874c8b5a441b53e32ff77ef2c54`; the local wheel is `1,242,422` bytes /
    `69700bb63445...` / `375` entries. P22 context match remains full-request-binding-insufficient;
    community/matching releases and interface mappings remain absent, all values remain null, and K562
    cannot substitute for the requested host. Engineering is
    `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`, fixture evidence is
    `SYNTHETIC_CONFORMANCE_ONLY`, science is `NOT_RUN`, policy is `NO_NEW_DECISION`, and P26R is
    `BLOCKED_EXTERNAL / NOT_RUN`. P27A-E contract/harness was the next standing-local unit and has
    subsequently completed; P27A-R historical replay remains `REPLAY_NOT_RUN / ASSET_PENDING`, and
    P27B remains `AUTHORIZATION_REQUIRED / SHADOW_NOT_RUN` and P27C remains
    `AUTHORIZATION_REQUIRED / PILOT_NOT_RUN`. No
    product/API/runtime version bump, release identity, tag, push or deploy is created. Product version
    remains `1.6.0`.
32. P27A-E starts at P26E docs closure `a12cf4f4b71efb653f8128afcb1f468211fdb837`
    and adds ten public strict design/replay records plus the canonical outcome-contract fingerprint
    payload. Final code/tree are `5875571bf9d8b518dc7a857feb935206f756de59` /
    `a7c65e7b30f51832660e66323b5946acbddcbf18`; the local wheel is
    `1,251,560` bytes / `4bd584bdae75...` / `376` entries. The public experiment is exact-request-
    derived but redacts raw metadata/secrets/paths; the authoritative action space remains empty and
    value-free. The synthetic rank-then-reveal harness freezes one primary strategy plus four baseline
    receipts before outcomes and cannot create historical/scientific/product truth. Engineering is
    `COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE_ONLY`; P27A-R is
    `REPLAY_NOT_RUN / ASSET_PENDING`; science is `NOT_RUN`; policy is `NO_NEW_DECISION`; P27B is
    `AUTHORIZATION_REQUIRED / SHADOW_NOT_RUN` and P27C is
    `AUTHORIZATION_REQUIRED / PILOT_NOT_RUN`. P28E subsequently completed; real P28 acceptance remains
    `0/3`. No product/API/runtime version bump, release identity, tag, push or deploy is created.
    Product version remains `1.6.0`.
33. P28E starts at P27 docs closure `971f812faae09fa833dc66741e86ec9ffe97947c` and adds six
    public role-policy/handoff/DAG/trace-event/trace/compilation records plus the canonical
    value-free-handoff and trace-root fingerprint payloads. Final code/tree are
    `da4bfc042d96f830e2a7e8cdc62ba227c7ace949` /
    `e6f18371f5061c810b2cb87d9a278cfa6d6ac46b`; two exact-code wheels are byte-identical at
    `1,259,255` bytes / `0358bf4df9e929be7c520e93f7c95dccc351895e7926773b53de8febf7eaec9f` /
    `377` entries. Role policies permit only value-free immutable-identity handoffs. The authoritative
    compilation has an empty value-free DAG/trace because there are `0/3` qualifying modules; it is not
    a connected biological subgraph and cannot execute models or create evidence/policy. Engineering is
    `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`, fixture evidence is
    `SYNTHETIC_CONFORMANCE_ONLY`, science is `NOT_RUN`, policy is `NO_NEW_DECISION`, and real P28 is
    `BLOCKED / 0_OF_3_QUALIFYING_MODULES`. P29E subsequently completed; no product/API/runtime version bump,
    release identity, tag, push or deploy is created. Product version remains `1.6.0`.
34. P29E starts at P28 docs closure `90990c198c40d0e6655aedaad101a783cde003aa` and adds three
    public requirement/subgraph/compilation records. Final code/tree are
    `471767e5f38f9866fbe396f39836369d943f6657` /
    `d1dec19f06ec88f563406b45f2b544effabad915`; two exact-code wheels are byte-identical at
    `1,263,199` bytes / `368a66a438c036a3b9c24f1093fc478886885fbefaecfea52bb50ad616206c01` /
    `378` entries. The requirement identities remain null, the graph is `empty_not_connected` with zero
    nodes/edges, and every execution/science/policy/value slot remains unavailable or false. Content hashes
    are identity, not signature/attestation. Engineering is
    `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`, fixture evidence is
    `SYNTHETIC_CONFORMANCE_ONLY`, science is `NOT_RUN`, policy is `NO_NEW_DECISION`, and real P29 is
    `BLOCKED / 0_QUALIFYING_BIOLOGICAL_NODES`. P30A-E1, P30A-E2a and P30A-E2b subsequently
    completed; E2b is `COMPLETE_NEGATIVE`, and P16R authorization-preflight identity bridge then
    completed `IDENTITY_PREFLIGHT_ONLY`. No P30 release identity, tag, push or deploy is created.

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
`vc.k562-p16r-external-scope-declaration.v1`,
`vc.k562-p16r-authorization-preflight.v1`,
`vc.model-validation-evidence.v1`, `vc.model-operator-policy.v1`,
`vc.model-release.v1`, `vc.model-registry-event.v1`, `vc.model-registry-state.v1`,
`vc.model-registry.v2`, `vc.model-registry-catalog.v2`,
`vc.model-registry-legacy-receipt.v1`,
`vc.model-registry-legacy-migration-report.v1`, `vc.environment.v1`,
`vc.environment.v2`, `vc.compatibility-report.v1`,
`vc.compatibility-report.v2`, `vc.execution-plan.v1`,
`vc.execution-step.v2`, `vc.execution-plan.v2`, the other `vc.*.v1`
domain/bundle schemas, `vc.pack-record.v1`, `vc.pack-catalog.v1`,
`vc.pack-index.v1`, `vc.pack-index.v2`, `vc.pack-candidate.v1`,
`vc.pack-metadata-review.v1`, `vc.pack-validation-report.v1`,
`vc.pack-operator-decision.v1`, `vc.factory-registered-pack.v1`,
`vc.pack-supersession.v1`, `vc.pack-factory-store.v1`, `vc.pack-factory-catalog.v1`,
`vc.pack-compatibility-surface.v1`,
`vc.training-environment.v1`, `vc.training-resource-limits.v1`,
`vc.training-hyperparameter.v1`, `vc.training-asset-binding.v1`,
`vc.training-split-asset.v1`, `vc.training-split.v1`,
`vc.training-leakage-overlap.v1`, `vc.training-leakage-audit.v1`,
`vc.training-job.v1`, `vc.tiny-training-features.v1`,
`vc.tiny-training-labels.v1`, `vc.tiny-trainer-input.v1`,
`vc.tiny-json-checkpoint.v1`, `vc.candidate-checkpoint.v1`,
`vc.training-metric.v1`, `vc.training-resource-observation.v1`,
`vc.training-result.v1`, `vc.training-model-identity.v1`,
`vc.candidate-model-artifact.v1`, `vc.candidate-model-card.v1`,
`vc.training-candidate-model.v1`, `vc.training-run-bundle.v1`,
`vc.training-candidate-bundle.v1`,
`vc.virtual-cell-context.v1`, `vc.virtual-cell-wrapper-approval.v1`,
`vc.virtual-cell-release.v1`, `vc.curated-virtual-cell-import-identity.v1`,
`vc.curated-registry-decision.v1`, `vc.curated-registry-entry.v1`,
`vc.curated-registry-head.v1`, `vc.curated-registry-trust.v1`,
`vc.curated-registry-authorization-reference.v1`, `vc.curated-release-state.v1`,
`vc.curated-virtual-cell-registry.v1`, `vc.curated-virtual-cell-catalog.v1`,
`vc.curated-release-dependency-graph.v1`,
`vc.p23-p18-endpoint-identity.v1`, `vc.interaction-endpoint.v1`,
`vc.same-experiment-interaction-evidence.v1`, `vc.interaction-scorer-fixture.v1`,
`vc.cell-interaction-evidence-input.v1`,
`vc.interaction-evidence-adapter-input-contract.v1`,
`vc.interaction-evidence-adapter-output-contract.v1`,
`vc.job-execution-identity.v1`, `vc.job-execution-identity.v2`,
`vc.job-execution-identity.v3`,
`vc.data-catalog.v1`, `vc.upload-receipt.v1`,
`vc.golden-norman.v1`, `vc.golden-baseline.v1`,
`vc.golden-evaluation.v1`, `vc.golden-artifact-manifest.v1`,
`vc.community-pack.v1`, the `vc.community-*.v1` exchange/plan/result schemas,
the seven `vc.virtual-microbiome-*.v1` scope/endpoint/adapter-requirement/contract/request/plan/result schemas,
the P27A-E `vc.experiment-action.v1`, `vc.virtual-experiment.v1`,
`vc.replay-selection-row.v1`, `vc.replay-selection-view.v1`, `vc.replay-outcome-row.v1`,
`vc.replay-outcome-ledger.v1`, `vc.replay-protocol.v1`, `vc.replay-selection-receipt.v1`,
`vc.replay-strategy-summary.v1`, `vc.replay-result.v1` schemas and canonical
`vc.replay-outcome-contract.v1` fingerprint payload,
the P28E `vc.multi-agent-role-policy.v1`, `vc.multi-agent-handoff.v1`,
`vc.multi-agent-dag.v1`, `vc.multi-agent-trace-event.v1`, `vc.multi-agent-trace.v1`,
`vc.multi-agent-biology-compilation.v1` schemas and canonical
`vc.multi-agent-value-free-handoff.v1` and `vc.multi-agent-trace-root.v1` fingerprint payloads,
the P29E `vc.state-action-observation-time-requirement.v1`,
`vc.connected-typed-subgraph.v1` and `vc.limited-world-model-compilation.v1` schemas,
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

The commands below remain a future formal-P30A finalization target, not evidence that it has completed.
P30A-E2a recorded clean-SHA offline coverage as incomplete; P30A-E2b then recorded stable source but
safely failed archive attempts and no clean-install/OCI/full-gate execution. Formal P30A remains
`LOCAL_RC_INCOMPLETE`.

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
scripts/build_release_oci.sh /absolute/linux-arm64-wheelhouse /tmp/release-one.oci.tar
scripts/build_release_oci.sh /absolute/linux-arm64-wheelhouse /tmp/release-two.oci.tar
python3.13 scripts/release_candidate.py compare-oci \
  /tmp/release-one.oci.tar /tmp/release-two.oci.tar \
  --source-sha "$(git rev-parse HEAD)" --output /tmp/oci-comparison.json
```

The verifier queries the installed API/health and same-origin static UI. The opt-in Docker smoke separately proves that the OCI revision, health SHA, installed CLI, UI assets, and offline API report all refer to the candidate commit. Playwright remains the browser-level UI gate, and frozen governance artifact hashes remain separate integrity checks. Tagging, pushing, or changing `.53` remains a Phase D action requiring explicit approval.
