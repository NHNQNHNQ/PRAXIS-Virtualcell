# Phase 17 — Virtual Cell Brain / Virtual Experiment DAG contract completion

Work unit: P17 — deterministic, auditable and replayable Virtual Experiment DAG engineering
contract

Outcome: `P17_CONTRACT_COMPLETE_REAL_MULTI_MODEL_ACCEPTANCE_PENDING`

Starting SHA: `ff525a0611901df422161a7143ebfe9d1e051008`

Completion code SHA: `16636f1b2c36e0a0fabb782a662b5b3b934891e0`

Completion tree: `321a59eed44c45bf2bb8798714352b3303b92e58`

Branch at completion: `codex/p17-virtual-cell-brain`

## Outcome and status separation

P17 added a direct, exact `vc.request.v2` + Pack-bound path that compiles the existing
CapabilityRegistry plan into an immutable Virtual Experiment DAG, Virtual Cell Brain context and
fail-closed verdict. It is deterministic, identity-complete and persistently replayable. It does
not execute a model.

Status at the completion code commit:

| Plane | State |
|---|---|
| engineering | `contract_defined=true`; `implementation_complete=true`; `tests_passed=true`; `artifact_ready=true` |
| science | `NOT_RUN`; no real model, benchmark, external validation or scientific evidence |
| product policy | `NO_NEW_DECISION`; no promotion or named operator decision |
| real multi-model acceptance | `PENDING` |
| artifact publication/release | none |

`artifact_ready=true` means only that the exact local code commit produced a reproducible complete
engineering wheel. It does not mean the wheel was published, released, tagged, pushed or deployed.

The exact registry inventory was 5 releases, 0 native releases and 0 production-promoted
capabilities; all five are legacy incomplete. Consequently every real P17 direct-v2 request
abstains, no authoritative execution node is available, and `execution_performed=false`.

## Implemented contract and integration

The new `praxis_virtualcell/virtual_experiment.py` defines strict, frozen, content-addressed v1
contracts for:

- Virtual Experiment nodes and typed edges;
- authoritative DAG identity and graph validation;
- immutable Virtual Cell Brain decision context;
- explicit conflict/partial/abstain/final-verdict decision state;
- optional non-authoritative candidate DAG and its deterministic review;
- complete compilation cross-binding.

The compiler consumes exact `VirtualCellRequestV2`, `ExecutionPlanV2` and `ModelRegistryV2`
contracts. It revalidates canonical object types, binds request/CellContext/Pack/environment/plan,
and resolves model, release, capability, adapter, contract, evidence and policy fingerprints back
to registry records. Node/edge identities are canonically ordered; duplicate, dangling,
self-referential, contract-incompatible or cyclic graphs fail closed.

`ModelBrokerAgent.plan()` exposes the existing CapabilityRegistry planner without wrapper
preparation. `virtual_experiment_payload()` is the dedicated direct-v2 Pack surface, and API
`run_job()` routes exact v2 requests to it only after strict validation and exact Pack identity.
The legacy Pack runner rejects a v2 marker, preserving path isolation.

The returned run-result shape is deliberately negative: prediction is null, models used and trace
are empty, reliability is low, abstention is true, and LLM use is false. No wrapper or model is
prepared or invoked, and no LLM is called; exact Pack validation remains part of the path.

At least two distinct production-promoted capabilities are required to make the participant set
multi-model eligible. P17 itself never authorizes execution: with fewer than two, reason is
`insufficient_production_promoted_capabilities`; with two or more, v1 would still abstain with
`contract_only_execution_not_authorized` pending a later explicit authorization.

## Candidate audit and authoritative identity

An optional LLM-shaped candidate DAG is data only; P17 never calls an LLM to obtain it. Strict
validation records `not_provided`, `matched`, `rejected` or `unavailable`, always with
`authoritative_dag_changed=false`.

The candidate review has its own `candidate_review_fingerprint`, so review status/reason tamper is
detectable. Candidate content, review and checksum are excluded from `authoritative_dict()` and
therefore cannot change the authoritative compilation, DAG, Brain, decision or JobStore identity.

## JobStore v3 replay hardening

Current exact-v2 jobs use `vc.job-execution-identity.v3`, which adds exact Brain and DAG
fingerprints to existing request/report/provenance/plan bindings. Save/load validation reparses the
compilation and cross-checks:

- top-level and structured-report provenance;
- request, Pack, plan, DAG, Brain and decision identities;
- execution step and participating capability sets;
- every DAG node against the corresponding execution plan step;
- companion request/report/trace/provenance files against the content-fingerprinted identity.

Recomputing only a locally modified object's fingerprint is insufficient if adjacent bindings disagree. A v3 job
with companions cannot be relabelled v2 to bypass Brain/DAG checks, and partial companions make the
job unavailable. Truly self-contained historical records without companions retain read-only v1/v2
compatibility.

## Test-only fifth taxon replay

Danio rerio / `NCBITaxon:7955` was constructed only inside a tiny temporary test fixture. It was
never added to a production Pack, model registry, default adapter or species branch.

Canonical fixture fingerprints:

| Identity | Fingerprint |
|---|---|
| Pack | `2d18a4ff702797774ec2faba9546f538e936a25a5bb9d27c40d796ecd949ad50` |
| plan | `d24c3202d63616d65b59cdb144995a7dcb0806a30ce1e034e0949317e548a207` |
| DAG | `19b1883cf48380c010d919d539b0eecfbe442713d1de1eb5a5a150501a80cdc6` |
| Brain | `1e4e4a7d591423d83e3bd9302281200e27ecfbf148c0f6f1966868b2e7538a5c` |
| authoritative compilation | `06eb1f07e15db983155c0d8b0be8207e1118610fc6508599b08bb136a54a48e3` |
| candidate review | `c37def4523924536e2a290b5ba4999ba9a376ef1c609635f8d89777f193ab749` |
| job identity | `5db65d8c268d91a17511bef54142d5d1b6b4af56b4bff28fa17251b4eea9e706` |

These are deterministic engineering replay anchors, not evidence of a Danio dataset, model,
capability or product registration.

## Frozen completion source identities

| Source | Bytes | SHA-256 |
|---|---:|---|
| `praxis_virtualcell/virtual_experiment.py` | 37,679 | `39fc848fc4475611408f1397d9cc62ce5aba694e4130a2af6e1e8e179278fc06` |
| `praxis_virtualcell/tests/test_virtual_experiment.py` | 46,842 | `53781199330e1d39a130ae6df8dd17dcf740d82ce7b2e526d4e474a462a2e11a` |
| `praxis_virtualcell/agents/model_broker_agent.py` | 9,598 | `f8357c26fb0b64951dc8cfb3e1db8dfa3d974a1a6fd5833bacd903c6ffdbfcc8` |
| `praxis_virtualcell/pack_product.py` | 31,769 | `73f965ceb9f66a14707d08ee5aa10d16a4be4a48ae1cc40e9ec9b4609d6762cc` |
| `praxis_vc_api/services/runtime_service.py` | 8,492 | `67203e3761bee9894766f24575ac4be6ea664f7f04fcbfc47731368c60726141` |
| `praxis_virtualcell/io/job_store.py` | 44,154 | `91f44d3a69227bd0d18b4b7bfcad53c9061479af3915e795a5f2049a62e40f98` |

No checked-in model registry, Pack, model card, wrapper, external dataset, scientific evidence,
operator policy, dependency declaration, version or release file was changed by the P17 code
commit.

## Validation bound to completion bytes

All validation was local and did not use network, external assets, LLM, GPU, remote services or
scientific runners.

- P17 contract suite: 41 passed.
- Adjacent contract/integration suites: 377 passed, 1 skipped.
- Safe gate excluding optional `mudata` and Golden/GEM/Norman science: 1,487 passed, 48 skipped,
  387 deselected.
- Authoritative `ruff check . --extend-exclude old --no-cache`: passed.
- Changed-path `py_compile`, diff and format checks: passed.

The optional `test_mudata_alignment` module could not collect because `mudata` was not installed.
It was not installed from the network and was not misreported as passing. Global `pip check` is not
valid P17 evidence because the shared base environment contains pre-existing invalid distributions
and dependency conflicts.

Adversarial coverage included strict-object reconstruction, subtype/extra-field drift, request and
Pack cross-binding, plan/report/registry re-signing, adapter tuple alignment, duplicate/dangling/
cyclic graph rejection, participant/step/node mismatch, candidate identity isolation, candidate
review checksum tamper, legacy/v2 hybrid rejection, public path redaction, JobStore companion
tamper and v3→v2 downgrade attempts. No remaining P1/P2 contract finding was retained.

## Packaging evidence and limitations

Packaging used exact code commit `16636f1b2c36e0a0fabb782a662b5b3b934891e0` and
`SOURCE_DATE_EPOCH=1786018775`. Two independent clean archive builds ran offline with Node
24.14.0 / npm 11.11.1 and Python 3.12.13 / setuptools 83 / wheel 0.47 / packaging 26.2. They
produced byte-identical complete wheels:

| Property | Result |
|---|---|
| wheel size | 1,118,410 bytes |
| SHA-256 | `bd3752b90a6d8e4d7a825b2f4925d00eb7e5204021fef3404b67e88f7a0e23bd` |
| archive entries | 366 |
| React static entries | 14 |
| test entries | 0 |
| AppleDouble / `__MACOSX` | 0 |
| `virtual_experiment.py` | present |

The official strict script failed closed because its offline isolated cache lacked the locked
`packaging==26.2` distribution. No fallback download was attempted. A clean bundled no-deps smoke
then failed because runtime `PyYAML` was absent. A no-deps smoke inheriting polluted system site
packages passed package import, static assets and CLI, but is explicitly non-authoritative and does
not prove dependency closure or a clean installation.

No wheel or other artifact was published.

## Explicitly not performed

P17 did not:

- access network or external scientific/model assets;
- import, instantiate or execute a model wrapper;
- call an LLM, train/tune a model, use a GPU or remote compute;
- run Golden, GEM, Norman or other science/benchmark workflows;
- create or promote validation evidence, policy or a production capability;
- register the fifth taxon outside a temporary test fixture;
- alter `old/**`, protected backup repositories, remote refs or history;
- push, open a PR, tag, bump a version, publish, release or deploy;
- operate `.53`, ports, services or production state.

Science remains `NOT_RUN`, product policy remains `NO_NEW_DECISION`, and real multi-model acceptance
remains pending. P14R/P15R/P16R and their product-decision phases were not implicitly advanced.

Next eligible local work unit: P18 contract-only multi-omics cell-state. It may build on P17
identity/replay contracts, but it cannot claim or inherit real execution, scientific evidence,
promotion, publication or release.
