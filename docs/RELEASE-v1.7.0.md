# PRAXIS-VirtualCell 1.7.0 — Local Release Candidate

> Status: `LOCAL_RC_INCOMPLETE / UNPUBLISHED`
>
> P30A is local-only. The local engineering and documentation work does not yet prove a complete
> RC artifact set. This document does not publish an artifact, complete a remote CI gate,
> create or move a tag, promote a biological capability, or authorize deployment.
>
> P30A baseline: branch `codex/p30-foundation-rc`, SHA
> `d808735ebfd649df6a4c932b95140387aa412c7d`. The final candidate source SHA and artifact
> digests, when available, are recorded in the out-of-tree `release-manifest.json`; the baseline
> above is not a substitute for that identity.

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

There is no science-qualified badge for 1.7.0:

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
