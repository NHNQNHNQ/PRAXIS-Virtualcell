# PRAXIS-VirtualCell 1.7.0 — Local RC Contract (Unpublished)

> Status: P30A-E1 `ENGINEERING_COMPLETE`; P30A-E2a/E2b `COMPLETE_NEGATIVE`; P30A-E2c
> `RECONCILIATION_ONLY / NO_RC_CLAIM`; P30A-E2d `OUTPUT_ROOT_PREFLIGHT_ONLY / NO_RC_CLAIM`; formal P30A
> `LOCAL_RC_INCOMPLETE / UNPUBLISHED`; P16R local authorization-preflight identity bridge
> `COMPLETE — IDENTITY_PREFLIGHT_ONLY`; actual P16R `AUTHORIZATION_REQUIRED / NOT_RUN`.
>
> P30A is local-only. Completed release-contract hardening and reproducibility probes do not yet
> prove a complete RC artifact set. P30A-E2b used a controlled archive-only runner and retained a
> negative result rather than accept caller-supplied test or artifact claims; E2c preserves that record
> without accepting a release artifact, and E2d preflights the current output-root capability only. This document does not publish an artifact,
> complete a remote CI gate, create or move a tag, promote a biological capability, or authorize
> deployment.
>
> P30 scope baseline: `694af3eebfca0e99ca07a6ecd8639b522b8ec3d4` (P29E docs closure).
> Post-formal-entrypoint engineering baseline: `d808735ebfd649df6a4c932b95140387aa412c7d`.
> P30A-E1 code evidence is `0a4d72b0825d9ec0ff3b7776bbc4f1f0023336f9`, tree
> `ba701d4ee6033e86a2d8abecc7e6ff25c1a05c14`, source-date epoch `1786335170`.
> P30A-E2a code evidence is `964b62214f346b15ec2d3f2a622b33f632dde466`, tree
> `eac19455bc9241e5347de27782a99942e3591cab`, source-date epoch `1786338523`; its write-new
> preflight record is `6cb91031…9019`. These are negative-preflight/probe identities, not a final
> candidate identity or a substitute for an immutable `release-manifest.json`.
> P30A-E2b code evidence is `12ad93d57e4f4e7438d2110b5ac9848c6b17ea33`, tree
> `14fe604111c18c558048bc282d23da936ac57088`, source-date epoch `1786343459`; its runner record
> is `72459a3b…63d2` and nested preflight is `064a479f…fec4`. These remain negative evidence only.

## Product promise

PRAXIS-VirtualCell 1.7.0 is a contract-governed foundation platform for programmable virtual
cells. Data that satisfies an explicit contract can be packaged as a `VirtualCellPack`. A
prediction is allowed only when the exact request, Pack, model, environment, adapter, evidence
and product policy are all compatible and executable. Missing, stale, incompatible,
out-of-distribution or insufficiently evidenced inputs produce an explicit abstention.

LLMs may parse natural language, propose candidate plans and explain an already-determined
result. They cannot create data truth, numerical predictions, compatibility, evidence,
promotion or a final scientific verdict.

## What 1.7.0 adds

The local candidate consolidates the P12–P29 engineering surface:

- immutable model, environment, task/output, adapter, evidence and policy identities;
- exact compatibility queries, revocation/supersession and fail-closed execution gates;
- deterministic adapter conformance, multi-omics alignment and controlled Pack registration;
- training, benchmark and curated-registry contracts that keep engineering, science and policy
  separate;
- contract-only interaction, community, host–microbiome, experiment-design, multi-agent and
  limited-world-model surfaces that abstain when their real prerequisites are absent;
- local RC tooling for deterministic wheel/OCI comparison, checksums, SBOM, licence inventory,
  dependency audit and unsigned provenance-candidate metadata.

The release classification is
[`release/p30a/capability-classification.json`](../release/p30a/capability-classification.json).
It is `authoritative_for_execution=false`: its release classes describe software exposure, not
scientific validation or production promotion.

| Release class | Count | Meaning in this candidate |
|---|---:|---|
| production | 1 | Non-predictive Model Zoo identity and fail-closed matching infrastructure; `prediction_allowed=false` and no new policy decision |
| preview | 6 | Software infrastructure with engineering contracts complete; disabled by default and not scientific evidence |
| experimental | 10 | Biological contracts or value-free/synthetic conformance surfaces; disabled and non-predictive |
| unsupported | 13 | Real science, operator or external-action windows that are absent, blocked or not authorized |

An interface, Pack, model card, catalog entry, successful synthetic run or UI element does not
make a biological capability predictable.

## Scientific and policy status

Scientific status is `NOT_RUN / SCIENCE_BADGE_INELIGIBLE`; product policy is
`NO_NEW_DECISION`. There is no science-qualified badge for 1.7.0:

- required real species capabilities: `3`; current: `0`;
- promoted community capability required: `true`; current: `false`;
- scientific evidence fingerprints supporting the badge: none;
- product-policy fingerprints supporting the badge: none;
- badge reason: `science_qualification_requirements_not_met`.

P14R/P15R/P16R/P21B/P23B/P24/P25R/P26R/P27B/P27C and real P28/P29 work were not
performed by P30A. Synthetic fixtures and tiny deterministic dry-runs remain contract
conformance only. Negative results and abstentions remain valid recorded outcomes; no software
release class upgrades them into science or policy.

## Python support matrix

| Python | 1.7.0 status | Boundary |
|---|---|---|
| 3.13 | `EXACT_LOCKED_RC_TARGET` | Build and runtime dependency sets are hash-locked in `requirements/build-py313.lock` and `requirements/runtime-py313.lock`; the OCI contract uses the digest-pinned Python 3.13.14 base. An exact RC is qualified only by its immutable manifest and gate evidence. |
| 3.12 | `METADATA_COMPATIBLE_ONLY` | Allowed by `Requires-Python >=3.11`, but this RC provides no exact lock or exact-SHA release qualification for 3.12. |
| 3.11 | `METADATA_COMPATIBLE_ONLY` | Allowed by `Requires-Python >=3.11`, but this RC provides no exact lock or exact-SHA release qualification for 3.11. |
| below 3.11 | `UNSUPPORTED` | Rejected by package metadata. |

Metadata compatibility is not a tested support claim. A Python 3.11 or 3.12 installation may be
useful for development, but it must not be reported as an exact 1.7.0 RC reproduction.

## Local artifact and evidence contract

P30A outputs are write-new, local and out of tree. Their presence alone is not acceptance.

| Output | Required interpretation |
|---|---|
| full Python wheel | When generated: built from an exact clean commit with locked Python 3.13 build dependencies and rebuilt frontend bytes |
| source archive | When generated: an exact-HEAD `git archive` projection under the reviewed export policy; unsafe links and AppleDouble entries reject the build |
| OCI archive/layout | When generated: built without network access from the exact wheel and runtime wheelhouse; equality is checked by manifest, config and ordered layer identities |
| `SHA256SUMS` | Byte identities only; not a signature or publisher identity |
| CycloneDX SBOM | Component inventory for the exact bundle; not a vulnerability-clearance claim |
| licence inventory | Declared package licence metadata and any explicit unknowns; no inferred permission |
| dependency audit | Records the available audit boundary; without an approved dated vulnerability database, vulnerability status is `NOT_RUN` |
| provenance candidate | Unsigned in-toto/SLSA-shaped local statement; no signer, issuer or publication claim |
| `release-manifest.json` | Exact source/artifact/test/gate status for one local candidate; prose summaries cannot override it |

No wheel, source archive, OCI archive, SBOM or provenance file is committed as a substitute for immutable release
evidence. A failed or incomplete gate remains failed or incomplete in the manifest.

The source-archive policy is versioned in [`.gitattributes`](../.gitattributes): it excludes only
the test fixture whose purpose is to exercise a Pack-relative symlink escape. The fixture remains
in the repository and its tests; every other archive link or AppleDouble entry causes a build
failure rather than being silently followed or omitted.

## P30A-E1 completed local engineering evidence

P30A-E1 completed fail-closed release-contract hardening, governance classification and local
reproducibility probes. It did not finalize a release. The probes below bind only the exact code
identity stated above and were written new outside the repository.

| Probe | Result |
|---|---|
| release-tool, source-archive and packaging tests | `47 passed` (`27 + 6 + 14`) |
| formal Pack-aware entrypoint regression | `148 passed`; no-Pack requests produce a V2 zero-step `pack_unregistered` abstention |
| React typecheck, lint, production build and bundle budget | passed |
| wheel reproducibility probe | two identical `praxis_virtualcell-1.7.0-py3-none-any.whl`: `1,264,708` bytes, SHA-256 `44e5e905e706f87c9b43574a5f02afd41c7b37d9079a0e91956b511bca422303` |
| source-archive reproducibility probe | two identical `praxis-virtualcell-1.7.0.tar.gz`: `8,055,078` bytes, SHA-256 `ba5e5d0dbe387575049f5603f8011af3359d4f99583f4856233be48dc796e642` |

The wheel probe has `378` ZIP entries, `14` static entries, no test entries and no AppleDouble
entries; ZIP integrity passed. The archive probe is an exact-HEAD projection and rejects unsafe
links and AppleDouble entries. Neither probe is a retained clean-install-qualified artifact bundle,
an accepted release manifest, an SBOM, a licence inventory or a published artifact.

## P30A-E2a/E2b negative records, E2c reconciliation, E2d output-root preflight, and formal-RC gates

P30A-E2a independently rechecked clean source SHA/tree/epoch before and after an offline
dependency-coverage preflight. Its `praxis.local-rc-finalizer-preflight.v1` record is
`LOCAL_RC_INCOMPLETE`, SHA-256 `6cb91031c96b7ebec92e32f7c2eb8af307f48ceae3cbe4aac43c1939a0779019`.
The targeted post-commit P30 suite passed `55` (`27 + 6 + 14 + 8` across release-candidate,
source-archive, packaging and E2a-finalizer tests); the record sets `network_used=false`,
`full_gate_execution=PRECHECK_ONLY_NOT_EXECUTED`, and `software_rc_gates_passed=false`.

The exact dependency blockers are `offline_wheel_cache_incomplete` for
`macos_arm64_cp313` (`pyjwt==2.13.0`, `pyyaml==6.0.3`) and for `linux_arm64_cp313` (those two plus
`cffi==2.1.0`, `cryptography==49.0.0`, `pydantic-core==2.46.4`, `rpds-py==2026.6.3`). No clean
runtime install, artifact build, OCI double-build/container smoke, complete SBOM/licence inventory,
dependency audit, `SHA256SUMS` or accepted release manifest was generated.

P30A-E2b subsequently ran its source-stable, exact-HEAD archive-only runner at
`12ad93d57e4f4e7438d2110b5ac9848c6b17ea33` / tree
`14fe604111c18c558048bc282d23da936ac57088` / epoch `1786343459`. Its runner record
`72459a3b51ba243d747ee2c0159d4105a30ba47d191b99ea05960343bbae63d2` and nested preflight
`064a479fd35deba3b08d70e999171577b9171133873d5bc7a3d9968a57aafec4` are both negative: the immutable
record retains two `source_archive_build_failed` attempts. Its contemporary tracked-unsupported-link
causal attribution is unreproducible from the same exact committed `.gitattributes` / `git archive`
inputs because raw stderr was not retained; the two offline wheelhouse profiles remain incomplete. No
clean install, OCI build, full gate, SBOM, licence inventory, dependency audit,
`SHA256SUMS` or accepted release manifest was generated.

P30A-E2c then preserved that immutable E2b failure result in the append-only
[source-archive reconciliation](../reports/phase30a/PHASE30A_E2C_SOURCE_ARCHIVE_RECONCILIATION.md).
Its current exact-source export-ignore double probe is local engineering evidence only: no release
artifact or manifest was accepted and no formal RC, science, policy, promotion, or actual-P16R result
was created.

P30A-E2d then added a hard-link/no-replace capability preflight for the requested source-archive
output directory. Its selected local exFAT root safely exits before archive creation and retains no
archive or probe. This current output-root result is not evidence about E2b's historical cause and is
not a release artifact, clean install, full gate, formal RC, science, policy, promotion, or actual-P16R
result. See the append-only [output-root preflight record](../reports/phase30a/PHASE30A_E2D_OUTPUT_ROOT_PREFLIGHT.md).

Formal P30A therefore remains incomplete. The P16R local authorization-preflight identity bridge
subsequently completed as an in-memory, value-free declaration binder; it does not access real P16R
inputs or create science/policy. Actual P16R remains `AUTHORIZATION_REQUIRED / NOT_RUN`.
`pip check` in the shared environment remains disqualified because `python-magic` is absent and
unrelated pre-existing `vcbench` pins conflict.

## Compatibility and migration from the local 1.6.0 candidate

`1.7.0` is a new compatible minor product identity. It does not reuse or move historical
`v1.6.0`, and it does not change the independent `vc.api.v1` or `vc.runtime.v1` protocol
identities. Domain schemas, Packs, models, adapters, environments, evidence and policies retain
their own explicit versions and fingerprints.

No repository data migration or implicit registry promotion is required. Consumers should:

1. pin the exact 1.7.0 source/artifact digest rather than selecting by a mutable directory or
   unqualified version string;
2. revalidate every Pack, registry and model identity against the exact request;
3. keep preview, experimental and unsupported capabilities disabled unless a later exact-scope
   evidence and policy record authorizes them;
4. preserve old run/provenance records as immutable history rather than rewriting them to the new
   product version;
5. treat any new deployment as a separate P30B3/P30B4 operation, not as a package migration side
   effect.

## Known limitations

- No real species capability or community capability meets the science badge gate.
- P29 remains `empty_not_connected` with zero qualifying biological nodes.
- LLM-assisted behavior is not part of prediction or governance authority.
- A local unsigned candidate is not a published or security-supported release.
- Dependency hash locking proves identity, not absence of vulnerabilities.
- Platform claims outside the exact recorded Python 3.13 artifact/test environment remain
  unqualified.
- There is no formal local RC artifact yet: E2b retained only negative archive-only evidence, and clean
  dependency/install/OCI/SBOM/license/manifest gates remain unresolved.

## P30B authorization state

| Window | Scope | Status |
|---|---|---|
| P30B1 | push frozen candidate and run exact-SHA CI | `NOT_AUTHORIZED / NOT_RUN` |
| P30B2 | fast-forward main, create a new annotated tag and publish artifacts | `NOT_AUTHORIZED / NOT_RUN` |
| P30B3 | deploy an immutable candidate to a new staging ref/directory/port and run staging smoke | `NOT_AUTHORIZED / NOT_DEPLOYED` |
| P30B4 | production traffic switch, monitoring and real rollback verification | `NOT_AUTHORIZED / NOT_DEPLOYED` |

No network download, remote Git mutation, tag, publication, staging change, service restart,
traffic change or production rollback is authorized by these release notes. Operational templates
are documented separately in
[`runbooks/FOUNDATION-PLATFORM-OPERATIONS.md`](runbooks/FOUNDATION-PLATFORM-OPERATIONS.md).
