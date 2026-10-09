# Phase 27A-E Completion — Agentic Experiment Design Contracts and Synthetic Replay Harness

Date: 2026-08-08
Branch: `codex/p25e-virtual-microbiome`
Starting SHA / active baseline: `a12cf4f4b71efb653f8128afcb1f468211fdb837`
Completion code SHA: `5875571bf9d8b518dc7a857feb935206f756de59`
Completion tree: `a7c65e7b30f51832660e66323b5946acbddcbf18`
Source date epoch: `1786180822`

## 1. Outcome and status separation

P27A-E is engineering complete for strict local contracts and a deterministic synthetic rank-then-reveal
harness. It did not run a canonical historical replay.

```text
Work unit: P27A-E — exact request-derived empty product design × synthetic comparator pool ×
           deterministic five-strategy rank-then-reveal replay
Engineering: COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE_ONLY
P27 umbrella: ENGINEERING_COMPLETE_SCIENCE_PENDING
Historical replay: REPLAY_NOT_RUN / ASSET_PENDING
Scientific status: NOT_RUN
Product policy status: NO_NEW_DECISION
P27B shadow review: AUTHORIZATION_REQUIRED / SHADOW_NOT_RUN
P27C prospective pilot: AUTHORIZATION_REQUIRED / PILOT_NOT_RUN
```

No interface, content hash, successful synthetic run or completion commit is scientific validation,
promotion eligibility, production policy, shadow review, prospective evidence or authorization for an external
action.

## 2. Changed code and immutable identities

| Path | SHA-256 |
|---|---|
| `praxis_virtualcell/experiment_design.py` | `ffa647094f117ef45adb726559ee23bcb0bd20427c87681ab6675522fa26f55f` |
| `praxis_virtualcell/tests/test_experiment_design_replay.py` | `99679162bea1d9cd6b5a7432b9694841d1fcd5f4e15e64645227cf3688c4a62b` |

The implementation adds ten strict public record types and four public functions in one module, with no new
dependency and no ActiveLearningAgent/LLM-candidate/default runtime/API/UI/registry wiring. This deliberate
deviation from the broader planned integration keeps the existing loose string queue non-authoritative. The public product `vc.virtual-experiment.v1`
record is deliberately empty and value-free because no exact-request executable + scientifically validated +
production-promoted action domain is available.

The ten public schemas are:

```text
vc.experiment-action.v1
vc.virtual-experiment.v1
vc.replay-selection-row.v1
vc.replay-selection-view.v1
vc.replay-outcome-row.v1
vc.replay-outcome-ledger.v1
vc.replay-protocol.v1
vc.replay-selection-receipt.v1
vc.replay-strategy-summary.v1
vc.replay-result.v1
```

`vc.replay-outcome-contract.v1` is a canonical fingerprint payload, not an eleventh public model.

## 3. Contract and replay closure

### Product design

- accepts an exact recursively revalidated `VirtualCellRequestV2`;
- stores request ID/full fingerprint and derived scope fingerprints, not raw metadata/constraint bytes;
- exposes no model, Pack, evidence, policy or action-catalog identity;
- keeps control, replicate and cost unavailable, with no selected actions;
- requires human approval and always abstains;
- offers no LLM candidate/action-space/numeric/verdict API.

### Synthetic action/replay harness

- covers perturbation/control/replicate/batch/endpoint/cost/constraint/feasibility and exact comparator identities;
- structurally separates selection view from outcome ledger;
- fixes ordered `active_heuristic`, random, uncertainty-only, diversity and expert-rule strategies;
- freezes every pre-outcome receipt before reveal;
- recomputes the deterministic receipts during evaluation;
- requires an exact action set and action→group binding in the ledger;
- preserves failed/unavailable rows without zero fill or implicit deletion;
- reports synthetic utility/cost/failure/uncertainty only, with `primary_passed=null`.

`synthetic_realized_utility` is not empirical information gain. Static expert-rule ranking is a baseline, not
P27B expert review.

## 4. Canonical synthetic conformance identities

The checked-in test builder deterministically yields the following identities. They are regression evidence only,
not scientific evidence or a real asset manifest.

| Identity | Exact value |
|---|---|
| request fingerprint | `8d543a289bb58997810ea62ffd7e54df0a19ac11f81366c13f31082cfb10f153` |
| experiment ID | `experiment_c6435497cd83c9f26953d634` |
| experiment fingerprint | `3c10f424953b528d6ef8f48be4ea2ca71c416333b6a98dd3e70cfcde631f5869` |
| selection-view fingerprint | `a8c8357b387d5c0d0c1c037319ee4c94117a9ed760bffffcb5a22180c17c7c33` |
| action-catalog fingerprint | `6a191d83f2943017b2b331f3ec9c3c5afc331bccee35702af2ab7f453aa80354` |
| manifest fingerprint | `937a22712ea5c20073d2c8a226f1f4a9c2c30aba40a497f2412a34426f986535` |
| synthetic group-split fingerprint | `2fb7a3af669c12516866e9e8bc54a08f00670da5366ef9476c34a3ba5aac48ca` |
| outcome-contract fingerprint | `896de5ccd21ffb57c6230f9914248d9af6aa33a1c7f04344f3ee33aa0c63bdd0` |
| protocol ID / fingerprint | `replay_protocol_2d4c9c941906a9c24657f3f0` / `45ff61ccc937ea238b36765cac9c0ed5f76afb305683d097ba40d93370247a5b` |
| outcome-ledger fingerprint | `9bf09bd246a39787c45a2fa04036003c4472544dba64c136882015e1260cfd27` |
| result ID / fingerprint | `replay_result_9404a25fee5814291d2561ea` / `dda3876805303b0194647ec2a8d3b628ffde87b4ed614c3a1370d466c43d5161` |

Receipt fingerprints in canonical strategy order are:

```text
active_heuristic  f48e88c58a332a9c8faab93b51f193e821ed79b23e1af3c458ce91674cdb7f45
random            dd1883ff56cc2ce3cef6cca283765de1ae162398be0787d4627b8e5551b3c29f
uncertainty_only  8b711a8b9810da2b98f99b634f89e81e0b9d5742c538410e6492bd435e23a582
diversity         d9310211d372d62accb3ae84783d353d8e21d66f8f53d5a03792b37c137690a1
expert_rule       4978a3254c399900e3193c4041975b7ba52bb48e103458df4f6f19fdb640cacd
```

## 5. Verification matrix

| Gate | Result |
|---|---|
| P27A-E focused | `28 passed` |
| P27A-E + P17/P21/request/adapter/ActiveLearning affected | `301 passed` |
| safe local suite | `1,845 passed, 49 skipped, 387 deselected in 453.03s` |
| legacy suite | `1,147 passed, 58 skipped, 105 deselected in 61.21s` |
| full Ruff | passed |
| targeted Ruff format | passed |
| Python compile/import | passed |
| `git diff --check` | passed |
| React typecheck / lint / build / bundle budget | passed |
| `pip check` | failed on pre-existing shared-environment dependency conflicts |

Adversarial coverage includes nested model/subclass drift, re-signed receipt selection, stale protocol/result
identities, mixed comparator scope/unit, invalid control/replicate/batch/cost, selection-time outcome injection,
non-exact ledger set, action→group drift, missing/failed outcomes, status elevation, secret/path echo and the
closed candidate API. No dependency was installed, removed or changed in the normative workspace.

## 6. Local package evidence

Two independent `git archive` trees from the exact completion code SHA used `npm ci --offline` and Python
`--no-isolation --skip-dependency-check`. They produced byte-identical local wheels:

| Property | Exact value |
|---|---|
| product/distribution version | `1.6.0` — unchanged |
| filename | `praxis_virtualcell-1.6.0-py3-none-any.whl` |
| size | `1,251,560` bytes |
| SHA-256 | `4bd584bdae75888b4e09d8cfb2211e002cb509155ca834adb7d00a6106abec99` |
| ZIP entries | `376` |
| React entries | `14` |
| test entries | `0` |
| AppleDouble entries | `0` |
| source/wheel P27A-E module SHA-256 | exact match: `ffa647094f117ef45adb726559ee23bcb0bd20427c87681ab6675522fa26f55f` |
| toolchain | Python `3.13.12`; build `1.5.0`; setuptools `70.2.0`; packaging `26.0`; Node `25.8.2`; npm `11.11.1`; Vite `8.1.2` |
| SBOM / license inventory | `NOT_RUN` — formal P30A RC work, not a P27A-E gate |

This proves exact-source reproducibility under the current local toolchain. It is not a pinned dependency closure,
clean install, signed artifact, publication, release candidate, staging or production evidence. `pip check` still
reports the known missing `python-magic` and incompatible `vcbench` pins in the polluted shared environment; no
environment mutation was attempted.

## 7. Historical replay asset audit and explicit non-events

No canonical local P27 historical pool exists. The M1 ledger mixes selector features with outcomes and lacks the
required P27 manifest/license/design/model identities. Golden Norman real assets remain remote; P9 and tiny Packs
are negative/synthetic contract fixtures. The audit inspected checked-in structure/metadata read-only, but none of
these candidates was consumed by the P27 harness or relabeled as P27A-R evidence; no Golden remote asset was opened.

P27A-E did not download or consume a real experimental asset, weight or checkpoint in the harness; train/tune/execute
a model; access a hidden test/external set; run P27A-R/P27B/P27C; contact experts; send messages; control devices; purchase materials;
perform wet-lab work; create scientific evidence/policy/promotion; mutate a registry; push, tag, release, deploy or
touch `.53`, PRAXIS-2, `old/**`, protected refs or services.

## 8. Next work

P27A-R remains `REPLAY_NOT_RUN / ASSET_PENDING`; P27B and P27C still require independent authorization.
The next eligible local work unit is P28E contract-only multi-agent orchestrator, typed handoff, trace and value-free
abstention. Real P28 acceptance remains blocked at `0/3` qualifying modules until at least three exact-request,
exact-scope, executable, scientifically validated and production-promoted model modules exist; synthetic/rule/advisory modules
do not count.

See [ADR-0023](../../docs/ADR-0023-agentic-experiment-design-contract.md), the
[P27A-E runbook](../../docs/runbooks/AGENTIC-EXPERIMENT-DESIGN.md), the
[canonical completion ledger](../../docs/PHASE12-30-DETAILED-COMPLETION-CHECKLIST.md), and the
[Phase 12–30 execution plan](../../docs/PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md).
