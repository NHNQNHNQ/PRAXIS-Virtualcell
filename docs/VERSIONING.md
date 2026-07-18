# PRAXIS-VirtualCell Versioning Contract

> Status: `DESIGN_ONLY — IMPLEMENT_IN_C2`
>
> Audited: 2026-07-18 at local checkpoint `db477ac`

The repository currently mixes product release tags, package metadata, API/runtime labels, message schemas, governance artifacts, and model revisions. This document separates those namespaces before any implementation changes.

## Current observed surfaces

| Namespace | Current value | Source | Meaning |
|---|---|---|---|
| local product milestone | annotated `v1.5.0 → 176019e` | Git tag/local `main` | latest local release checkpoint; not published on GitHub on 2026-07-18 |
| GitHub published main/tag | `v0.8.0 → 7fc4aa5` | live `ls-remote` | current published truth |
| Python distribution | `0.0.0` | `pyproject.toml` `[project].version` | incorrect placeholder relative to Git history |
| inherited `praxis2.__version__` | `0.0.0` | `praxis2/__init__.py` | compatibility namespace, currently locked by a legacy smoke test |
| main package export | absent | `praxis_virtualcell/__init__.py` | product version cannot currently be queried from the main namespace |
| CLI | no `--version` | `praxis_virtualcell/cli.py` | console entry exists but exposes no release identity |
| frontend private package | `0.0.0` | `praxis_vc_react/package.json` and lock root | build-package mirror placeholder; not a scientific/API protocol |
| OpenAPI info version | `0.6` | `praxis_vc_api/main.py` | historical API feature label, not a defined URL/protocol contract |
| runtime contract label | `v0.3` | `praxis_vc_api/services/runtime_service.py` | returned by `/api/health` and displayed by the UI |
| legacy PRAXIS-2 service | `v0.21.0` | `praxis2/auth/routes.py` | inherited `/api/info` line, separate from VirtualCell product/API |
| agent message schema | `vc.msg.v1` | `praxis_virtualcell/core/message.py` | message serialization/validation contract |
| memory frontmatter schema | `1` | `brains/_common/memory/rules/*.md` | inherited memory-content schema |
| governance feature schema | `v0.3.0` | `governance/learned_reliability.py` and artifact JSON | frozen learned-governance feature contract |
| governance models | `reliability_v0.3.0`, `abstain_v0.3.0` | `governance/artifacts/*.json` | immutable model revisions paired with content SHA-256 |
| model registry revisions | heterogeneous model/dataset identifiers | `model_zoo/registry.yaml` | per-engine/checkpoint revisions, not product SemVer |

The historical `v1.5.0` source tree declaring Python/frontend `0.0.0` is a release debt. Do not move or recreate the `v1.5.0` tag to conceal it.

## Namespace contract

| Name | Format | When it changes | Must not imply |
|---|---|---|---|
| `product_version` | PEP 440 `X.Y.Z` for stable releases; optional `.devN` while developing | user-visible product release scope changes | API/schema/model compatibility by itself |
| Git release tag | annotated `vX.Y.Z` | only on an approved release commit whose product metadata is `X.Y.Z` | a tag is published before GitHub confirms it |
| `api_protocol_version` | explicit contract identifier such as `vc.api.v1` | incompatible HTTP request/response contract change | product release cadence |
| `runtime_protocol_version` | explicit runtime/result contract identifier | incompatible workflow/result semantics change | product release cadence |
| `message_schema_version` | existing `vc.msg.v1` style | serialized agent-message compatibility change with migration/validation | product release cadence |
| `memory_schema_version` | integer/content-schema identifier | memory frontmatter/content contract change | product release cadence |
| `feature_schema_version` | existing SemVer-like artifact contract | retraining/migrating the feature vector contract | UI/package version |
| governance `model_version` + SHA | immutable named revision plus content hash | genuinely regenerated/retrained artifact | product release cadence |
| registry `model_revision` | model/dataset/checkpoint-specific identifier plus asset SHA | specific model/checkpoint changes | whole-product version |
| frontend package version | generated mirror of the product version for release builds | synchronized by the release tool, never used as authority | API/runtime protocol version |
| `git_sha` / image digest | exact build identity | every build | semantic compatibility |

## Single product-version source

`pyproject.toml` `[project].version` will be the only manually editable product-version source.

During C2:

1. Select the next version from actual completed scope. A cleanup-only release may be `1.5.1`; a release containing the planned E2E/theme/product changes may be `1.6.0`. Do not choose before Phase B/C evidence establishes scope.
2. Read the installed value with `importlib.metadata.version("praxis-virtualcell")` and expose it as `praxis_virtualcell.__version__`.
3. Make `praxis2.__version__` a compatibility alias rather than a second literal.
4. Add `praxis-vc --version` from the same distribution metadata.
5. Set FastAPI/OpenAPI's application version from `product_version`; separately expose `api_protocol_version` and `runtime_protocol_version`.
6. Extend `/api/health` with `product_version`, protocol versions, and `git_sha`; temporarily preserve the existing `runtime_version` field for client compatibility.
7. Make the UI display backend-provided `product_version` and build SHA. It must not invent product truth from a frontend constant.
8. Update the private frontend package/lock version with the normal npm mechanism as a generated release mirror; never hand-edit only the lockfile.

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
== annotated tag name without its leading "v"
```

The UI must show the same backend product version. GitHub `main`, local `main`, and the `.53` deployed checkout must resolve to the tagged commit before synchronization can be marked complete.

The equality above deliberately excludes `vc.msg.v1`, runtime/API protocol identifiers, memory schema, `feature_schema_v0.3.0`, governance model versions, registry model revisions, and artifact hashes. CI should validate their format/integrity and compatibility, not force them to equal the product release.

## Change policy

- Patch: compatible fixes, documentation, CI/test corrections, packaging repair, and no deliberate product capability expansion.
- Minor: backward-compatible user-visible capability, workflow, UI, or supported-case expansion.
- Major: intentionally incompatible public CLI/API/report/runtime behavior requiring a migration.
- Protocol/schema/artifact breaking changes require their own migration note and compatibility tests regardless of product SemVer.
- Scientific claims are not versioned into truth by bumping a number; they change only with reproducible evidence and an updated Phase gate.

## Required C2 verification

```bash
python -m build
python -m pip check
python -c "from importlib.metadata import version; print(version('praxis-virtualcell'))"
python -c "import praxis_virtualcell, praxis2; print(praxis_virtualcell.__version__, praxis2.__version__)"
praxis-vc --version
npm --prefix praxis_vc_react pkg get version
```

Also query OpenAPI and `/api/health` in a clean install, verify the UI value through Playwright, and test that all frozen governance artifact hashes still match their recorded content. Tagging, pushing, or changing `.53` remains a Phase D action requiring explicit approval.
