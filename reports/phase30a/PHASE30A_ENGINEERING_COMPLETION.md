# P30A Engineering Completion Report — Local RC Remains Incomplete

**Work unit:** `P30A-E1 — release-contract hardening, governance, and local reproducibility probes`

**Outcome:** `ENGINEERING_COMPLETE`; formal P30A remains
`LOCAL_RC_INCOMPLETE / BLOCKED_EXTERNAL_DEPENDENCY_INPUT`

**P30 scope baseline:** `694af3eebfca0e99ca07a6ecd8639b522b8ec3d4` (P29E docs closure)

**Post-entrypoint engineering baseline:** `d808735ebfd649df6a4c932b95140387aa412c7d`

**Release-tool commits:**

- `15f3e9b4effdc9e353557631807b900ee8bed1d8` — fail-closed local RC contract tooling
- `0a4d72b0825d9ec0ff3b7776bbc4f1f0023336f9` — safe resolved out-of-tree output handling

**Code-evidence tree:** `ba701d4ee6033e86a2d8abecc7e6ff25c1a05c14`

**Source-date epoch:** `1786335170`

**Branch:** `codex/p30-foundation-rc`

## Scope and outcome

P30A-E1 adds a local-only, fail-closed release contract around the `1.7.0` source:

- exact-HEAD binding for release inputs, source reports, Pack classification, Python locks and
  frontend lock;
- deterministic source-archive and full-wheel builders that reject dirty source and unsafe output
  paths; the source-archive builder additionally rejects unsafe links and AppleDouble entries;
- target-profile wheelhouse validation, deterministic wheel comparison, OCI identity comparison,
  and release-metadata validation;
- a conservative capability classification with `authoritative_for_execution=false` and
  `prediction_allowed=false` for every record;
- release, contribution and operations documentation that separates software exposure from
  scientific validation, product policy and deployment authority.

The metadata tool deliberately cannot promote caller-supplied test/artifact claims. It emits
`LOCAL_RC_INCOMPLETE` until the next eligible local sub-unit, `P30A-E2`, provides a trusted local
finalizer that creates the full immutable artifact set from one frozen clean source. This is
intentional fail-closed behavior, not a release.

## Local engineering evidence

| Probe | Result |
|---|---|
| P30 release-tool / source-archive / packaging suite | `47 passed` (`27 + 6 + 14`) |
| Ruff and format (Python release tool/tests) | passed |
| Shell syntax (`build_release_wheel.sh`, `build_release_source_archive.sh`, `build_release_oci.sh`) | passed |
| React typecheck, lint, production build and bundle budget | passed; initial JS `212,826` raw / `66,893` gzip |
| Capability classification validation | passed; classification fingerprint `ae942fde63451ea806ef029d6cda1bc8fef40efe5927e0b6c62f978ba8b8eda5` |
| Formal Pack-aware entrypoint regression | `148 passed`; no-Pack requests produce V2 zero-step `pack_unregistered` abstention |

Toolchain observed for these local probes: CPython `3.13.12`, pip `26.0.1`, Node `25.8.2`, npm
`11.11.1`. These are local engineering facts, not an assertion that the local toolchain equals
the pinned OCI/CI environment.

## Reproducibility probes

Two independently built full wheels from exact commit `0a4d72b...` are byte-identical:

| Artifact | Size | SHA-256 | Structural check |
|---|---:|---|---|
| `praxis_virtualcell-1.7.0-py3-none-any.whl` | `1,264,708` | `44e5e905e706f87c9b43574a5f02afd41c7b37d9079a0e91956b511bca422303` | `378` ZIP entries; `14` static entries; `0` tests; `0` AppleDouble; ZIP integrity passed |

Two independently built source archives from the same commit are byte-identical:

| Artifact | Size | SHA-256 | Structural check |
|---|---:|---|---|
| `praxis-virtualcell-1.7.0.tar.gz` | `8,055,078` | `ba5e5d0dbe387575049f5603f8011af3359d4f99583f4856233be48dc796e642` | exact-HEAD archive projection; unsafe links and AppleDouble reject |

These were write-new out-of-tree probes. They are not a retained, clean-install-qualified P30
artifact bundle, do not have an accepted `release-manifest.json`, and must not be published or
treated as a final RC identity.

## Negative results and remaining RC gates

| Gate | Current result | Consequence |
|---|---|---|
| Runtime dependency wheelhouse | `BLOCKED_EXTERNAL_DEPENDENCY_INPUT`: offline cache lacks `pyjwt==2.13.0` and `pyyaml==6.0.3` | no clean runtime install or runtime wheelhouse manifest |
| Linux/arm64 OCI wheelhouse | unavailable locally; additionally missing `cffi==2.1.0`, `cryptography==49.0.0`, `pydantic-core==2.46.4` and `rpds-py==2026.6.3` | no OCI build, double-build comparison or container smoke |
| SBOM, licence inventory, SHA256SUMS, dependency audit and release manifest | not generated for a complete artifact set | no formal local RC |
| `pip check` in the shared environment | failed: missing `python-magic` plus unrelated pre-existing `vcbench` pin conflicts | not a clean-install qualification; environment was not mutated |
| Exact-SHA remote CI, push, tag, publication, staging and production | `NOT_AUTHORIZED / NOT_RUN` | P30B1–P30B4 remain separate windows |

No network access, package download, external asset read, installation into a new runtime,
training, remote compute, operator decision, remote Git action, tag, publication, deployment,
service restart, traffic change or production rollback was performed.

## Status ledger

| Layer | Status |
|---|---|
| P30A-E1 release-contract hardening | `ENGINEERING_COMPLETE` |
| P30A-E2 trusted local finalizer | `NEXT_ELIGIBLE_LOCAL_WORK_UNIT` |
| Formal P30A local RC | `LOCAL_RC_INCOMPLETE / BLOCKED_EXTERNAL_DEPENDENCY_INPUT` |
| Scientific evidence | `NOT_RUN / SCIENCE_BADGE_INELIGIBLE` (`0/3` real species; no promoted community) |
| Product policy | `NO_NEW_DECISION` |
| P30B1/P30B2 | `NOT_AUTHORIZED / NOT_RUN` |
| P30B3/P30B4 | `NOT_AUTHORIZED / NOT_DEPLOYED` |

The release classification remains software-release exposure only. It cannot create execution
authority, scientific evidence, policy promotion or a prediction. P14R, P15R and P16R remain
independent external scientific windows; P16R is still `AUTHORIZATION_REQUIRED / NOT_RUN`.

## Next work

The next eligible local work unit is `P30A-E2 — trusted local RC finalizer`. It must own the
build/test/inspection evidence instead of accepting caller-supplied claims, while preserving the
same `LOCAL_RC_INCOMPLETE` outcome when the exact runtime or Linux/arm64 wheelhouse is absent.
After that local work, a later authorization window must provide exact, licensed source(s) for the
missing hash-locked dependency closure and, if OCI work is requested, the exact Linux/arm64
wheelhouse/base-builder inputs. That window must freeze paths, sizes, SHA-256 values, licences,
network boundary, write-new output roots, expected artifacts and rollback/no-publication limits.

Separately, the highest-value biological capability remains P16R: the independently authorized,
fixed K562 Golden benchmark followed—only if positive—by an independent P16B product-policy
decision.
