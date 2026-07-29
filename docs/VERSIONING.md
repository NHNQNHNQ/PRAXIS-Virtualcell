# PRAXIS-VirtualCell Versioning Contract

> Status: `IMPLEMENTED_P8_PRODUCT_CLOSURE — 1.6.0_LOCAL_CANDIDATE_UNPUBLISHED`
>
> Audited: 2026-07-29; local Phase branch `codex/p8-product-closure`

The repository historically mixed product release tags, package metadata, API/runtime labels, message schemas, governance artifacts, and model revisions. C2 implements the separation below; publication status remains governed independently by the three-way synchronization ledger.

## Current observed surfaces

| Namespace | Current value | Source | Meaning |
|---|---|---|---|
| local product milestone | annotated `v1.5.0 → 176019e` | Git tag/local `main` | latest local release checkpoint; not published on GitHub on 2026-07-18 |
| GitHub published main/tag | `v0.8.0 → 7fc4aa5` | fresh D0 HTTPS `ls-remote`, 2026-07-18 20:38 CST | current observed published truth; still unchanged by this local candidate |
| local product candidate | `1.6.0` | `pyproject.toml` `[project].version` | accessible theme, workflow/UI, and supported-input expansion; local only, not a tag or publication |
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
| execution environment snapshot | `vc.environment.v1` + canonical JSON SHA-256 | `model_zoo/capability_registry.py` | records detected Python modules, declared resources, and implemented runtime task/output adapters; it is a local planning snapshot, not remote hardware attestation |
| model compatibility report | `vc.compatibility-report.v1` + canonical JSON SHA-256 | `model_zoo/capability_registry.py` | binds full request, registered Pack, model card and environment identities while keeping `pack_valid`, `model_compatible`, execution readiness and `scientifically_validated=false` separate |
| model execution plan | `vc.execution-plan.v1` + deterministic `plan_<sha-prefix>` | `model_zoo/capability_registry.py`, `agents/model_broker_agent.py` | ordered executable wrapper steps plus all compatibility reports; an executable plan is not a performance or scientific claim |
| Pack product record/catalog | `vc.pack-record.v1`, `vc.pack-catalog.v1` | `pack_product.py`, `/api/packs` | path-redacted, currently revalidated Pack metadata plus declared model capabilities; catalog presence is not per-request compatibility |
| local Pack index | `vc.pack-index.v1` + Pack fingerprint | `pack_product.py`, `PRAXIS_VC_PACK_INDEX` | binds a local canonical root to one Pack ID/version/fingerprint; every use revalidates bytes and semantics |
| Pack compatibility surface | `vc.pack-compatibility-surface.v1` | `pack_product.py`, `/api/packs/compatibility` | public path-redacted projection of the existing execution plan; planning is read-only and is not execution evidence |
| job execution identity | `vc.job-execution-identity.v1` + canonical JSON SHA-256 | `io/job_store.py` | locks the selected Pack and all planned model/card/compatibility fingerprints for one immutable job directory |
| public data catalog | `vc.data-catalog.v1` | `praxis_virtualcell/catalogs/data_catalog.yaml`, `praxis_vc_api/services/data_portal_service.py` | strict public metadata plus source terms and external-file size/hash allowlist; catalog/file availability does not imply Pack/model/scientific status |
| quarantined upload receipt | `vc.upload-receipt.v1` | `praxis_vc_api/services/data_portal_service.py` | one byte-preserving quarantine write identity; not content validation, Pack registration, user identity, or prediction evidence |
| Golden Norman contract | `vc.golden-norman.v1` + canonical JSON SHA-256 | `data/golden/norman_2019/contract.yaml`, `benchmarks/golden_norman.py` | binds one exact public source, source/derived semantics, predefined control/split, metric/bootstrap and simple-baseline definitions; changing any item requires a new identity |
| Golden baseline artifact | `vc.golden-baseline.v1` + per-file SHA-256 | external `model_cache/norman_*`, checked-in one-card registries | binds Pack fingerprint, ordered feature/target IDs, train conditions and fixed baseline arrays; not a general model revision or scientific validation |
| Golden evaluation artifact | `vc.golden-evaluation.v1` + file SHA-256 | external `evaluation/evaluation.json` | records all held-out formal-runtime calls, condition losses, paired bootstrap and three separate states; scores do not promote `scientifically_validated` |
| Golden artifact inventory | `vc.golden-artifact-manifest.v1` | `data/golden/norman_2019/artifact-manifest.json` | records exact external path/size/hash and compact scores; it is not the large data or model content |
| memory frontmatter schema | `1` | `brains/_common/memory/rules/*.md` | inherited memory-content schema |
| governance feature schema | `v0.3.0` | `governance/learned_reliability.py` and artifact JSON | frozen learned-governance feature contract |
| governance models | `reliability_v0.3.0`, `abstain_v0.3.0` | `governance/artifacts/*.json` | immutable model revisions paired with content SHA-256 |
| model registry revisions | heterogeneous model/dataset identifiers | `model_zoo/registry.yaml` | per-engine/checkpoint revisions, not product SemVer |
| W4B donor call version | `donor_ml:<Class>@sha256:<content identity>` on `build_runtime_ml` | checkpoint `.json + .pt` bytes via `checkpoint_identity.py` | content identity for this call; not a checked-in integrity pin, product version, or proof of cross-device tensor hashing |

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
| environment snapshot schema + fingerprint | explicit `vc.environment.v1` plus canonical JSON SHA-256 | dependency/resource/runtime-adapter declaration changes | a missing module/resource is available or remotely attested |
| compatibility report schema + fingerprint | explicit `vc.compatibility-report.v1` plus canonical JSON SHA-256 | compatibility checks, reason semantics or bound identities change incompatibly | `pack_valid`, `model_compatible`, executable and scientifically validated are interchangeable |
| execution plan schema + plan ID | explicit `vc.execution-plan.v1` and content-derived `plan_*` | step/report/identity semantics change incompatibly | plan creation proves prediction correctness or scientific validation |
| Pack product record/catalog/index schemas | explicit `vc.pack-record.v1`, `vc.pack-catalog.v1`, `vc.pack-index.v1` | incompatible public metadata, index-field or identity-binding semantics | discovery/registration proves model compatibility or scientific validity |
| Pack compatibility surface schema | explicit `vc.pack-compatibility-surface.v1` | incompatible path-redaction or public execution-plan projection | a compatibility response proves successful execution |
| job execution identity schema + fingerprint | explicit `vc.job-execution-identity.v1` and content identity | incompatible Pack/model identity-lock semantics | immutable provenance proves model quality or scientific validity |
| public data catalog schema | explicit `vc.data-catalog.v1` | incompatible metadata, source/terms, identity or file-verification semantics | file availability, Pack validity, model compatibility or scientific validity |
| upload receipt schema | explicit `vc.upload-receipt.v1` | incompatible quarantine identity/provenance semantics | internal file safety/quality, user authentication identity, Pack registration or model use |
| Golden benchmark contract + canonical hash | explicit `vc.golden-norman.v1` and content identity | source, semantic field, feature order, control/split, truth, metric/bootstrap or baseline definition changes | one successful run validates another dataset/model or creates scientific truth |
| Golden baseline/evaluation/inventory schemas + hashes | explicit `vc.golden-*.v1` and per-file identities | incompatible artifact semantics or regenerated bytes | lower MSE, executable runtime, or an inventory entry implies `scientifically_validated=true` |
| `memory_schema_version` | integer/content-schema identifier | memory frontmatter/content contract change | product release cadence |
| `feature_schema_version` | existing SemVer-like artifact contract | retraining/migrating the feature vector contract | UI/package version |
| governance `model_version` + SHA | immutable named revision plus content hash | genuinely regenerated/retrained artifact | product release cadence |
| registry `model_revision` | model/dataset/checkpoint-specific identifier plus asset SHA | specific model/checkpoint changes | whole-product version |
| frontend package version | generated mirror of the product version for release builds | synchronized by the release tool, never used as authority | API/runtime protocol version |
| `git_sha` / image digest | exact build identity | every build | semantic compatibility |

## Single product-version source

`pyproject.toml` `[project].version` is the only manually editable product-version source.

Implemented through C5:

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

The UI must show the same backend product version. GitHub `main`, local `main`, and the `.53` deployed checkout must resolve to the tagged commit before synchronization can be marked complete. The current candidate has no approved tag, so tag equality is intentionally not asserted yet.

The equality above deliberately excludes `vc.msg.v1`, `vc.request.v2`, all
`vc.pack.*` versions, `vc.model-feature-contract.v1`, `vc.feature-mapping.v1`,
`vc.alignment-report.v1`, `vc.model-card.v1`, `vc.environment.v1`,
`vc.compatibility-report.v1`, `vc.execution-plan.v1`, the other `vc.*.v1`
domain/bundle schemas, `vc.pack-record.v1`, `vc.pack-catalog.v1`,
`vc.pack-index.v1`, `vc.pack-compatibility-surface.v1`,
`vc.job-execution-identity.v1`, `vc.data-catalog.v1`, `vc.upload-receipt.v1`,
`vc.golden-norman.v1`, `vc.golden-baseline.v1`,
`vc.golden-evaluation.v1`, `vc.golden-artifact-manifest.v1`,
runtime/API protocol identifiers, memory schema,
`feature_schema_v0.3.0`, governance model versions, registry model revisions, and
artifact hashes. CI should validate their format/integrity and compatibility, not
force them to equal the product release.

## Change policy

- Patch: compatible fixes, documentation, CI/test corrections, packaging repair, and no deliberate product capability expansion.
- Minor: backward-compatible user-visible capability, workflow, UI, or supported-case expansion.
- Major: intentionally incompatible public CLI/API/report/runtime behavior requiring a migration.
- Protocol/schema/artifact breaking changes require their own migration note and compatibility tests regardless of product SemVer.
- Scientific claims are not versioned into truth by bumping a number; they change only with reproducible evidence and an updated Phase gate.

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
