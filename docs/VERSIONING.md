# PRAXIS-VirtualCell Versioning Contract

> Status: `IMPLEMENTED_C2 — 1.5.1_LOCAL_CANDIDATE_UNPUBLISHED`
>
> Audited: 2026-07-18; implementation commit `73f3324`

The repository historically mixed product release tags, package metadata, API/runtime labels, message schemas, governance artifacts, and model revisions. C2 implements the separation below; publication status remains governed independently by the three-way synchronization ledger.

## Current observed surfaces

| Namespace | Current value | Source | Meaning |
|---|---|---|---|
| local product milestone | annotated `v1.5.0 → 176019e` | Git tag/local `main` | latest local release checkpoint; not published on GitHub on 2026-07-18 |
| GitHub published main/tag | `v0.8.0 → 7fc4aa5` | live `ls-remote` | current published truth |
| local product candidate | `1.5.1` | `pyproject.toml` `[project].version` | cleanup/quality patch candidate; local only, not a tag or publication |
| Python distribution | `1.5.1` | installed `praxis-virtualcell` metadata | derived from the only manually edited product source |
| inherited `praxis2.__version__` | `1.5.1` | compatibility alias | aliases `praxis_virtualcell.__version__`; no second literal |
| main package export | `1.5.1` | `praxis_virtualcell.__version__` | derived from installed distribution metadata |
| CLI | `praxis-vc 1.5.1` | installed `praxis-vc --version` | derived from the main package export |
| frontend private package | `1.5.1` | `package.json` plus lock root | generated npm mirror; not a scientific/API protocol or UI authority |
| OpenAPI product version | `1.5.1` | `FastAPI(..., version=__version__)` | product identity, not protocol compatibility |
| API protocol | `vc.api.v1` | `praxis_virtualcell.version` | HTTP request/response contract namespace |
| runtime protocol | `vc.runtime.v1` | `praxis_virtualcell.version` | workflow/result semantics namespace |
| legacy runtime label | `v0.3` | `/api/health.runtime_version` | temporarily preserved response field for compatibility |
| build identity | injected SHA or `unknown` | `/api/health.git_sha` | reads `GIT_SHA`, `GITHUB_SHA`, then `SOURCE_VERSION`; never guesses from `.git` |
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

`pyproject.toml` `[project].version` is the only manually editable product-version source.

Implemented in C2:

1. The evidence through C2 is compatible cleanup, lint, CI, documentation, and version-surface repair, so the local candidate is `1.5.1`. If C3 actually accepts and commits user-visible theme/UI expansion, the candidate must be reassessed as `1.6.0` before D0 rather than pretending that scope was already accepted.
2. `importlib.metadata.version("praxis-virtualcell")` is exposed as `praxis_virtualcell.__version__`; an uninstalled source import returns the honest fallback `0+unknown`.
3. `praxis2.__version__` is a compatibility alias rather than a second literal.
4. `praxis-vc --version`, FastAPI/OpenAPI, and health use the same installed product value.
5. `/api/health` separately exposes product, API protocol, runtime protocol, and injected build SHA while retaining `runtime_version="v0.3"`.
6. The UI consumes backend `product_version` and `git_sha`; an E2E mock with product `9.9.9` proves that it does not invent this truth from frontend metadata.
7. `npm version 1.5.1 --no-git-tag-version` synchronized the private package and lock root as a generated mirror. Neither is manually authoritative.

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
