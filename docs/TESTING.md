# PRAXIS-VirtualCell 测试指南

> 当前文档基线：P29E 分支 `codex/p25e-virtual-microbiome`；active baseline
> `90990c198c40d0e6655aedaad101a783cde003aa`
>
> 规范工作树：`/Volumes/T7/PRAXIS-virtualcell`；Git metadata：
> `/Users/mzy/Projects/.PRAXIS-virtualcell-gitdir`
>
> 状态：P29E `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`；umbrella
> `ENGINEERING_COMPLETE_SCIENCE_PENDING`；science `NOT_RUN`；policy
> `NO_NEW_DECISION`；completion code SHA
> `471767e5f38f9866fbe396f39836369d943f6657`；tree
> `d1dec19f06ec88f563406b45f2b544effabad915`；source date epoch `1786187523`。
> 下述 P4.3–P28E 和 CI 数字仍只绑定各自 exact SHA/日期。P29E 只证明 strict
> state/action/observation/time requirement、empty-not-connected typed graph 与 value-free
> compilation；fixture evidence 为 `SYNTHETIC_CONFORMANCE_ONLY`。真实 P29 为
> `BLOCKED / 0_QUALIFYING_BIOLOGICAL_NODES`，science `NOT_RUN`，policy `NO_NEW_DECISION`。
> P28E 只证明 strict
> advisory policy、typed value-free handoff/DAG、hash-bound no-run trace 与 authoritative 0/3 abstention；
> fixture evidence 为 `SYNTHETIC_CONFORMANCE_ONLY`。真实 P28 为
> `BLOCKED / 0_OF_3_QUALIFYING_MODULES`，comparison/ablation `NOT_RUN`。
> P27A-E 只证明 strict
> experiment-design contracts 与 deterministic rank-then-reveal harness 的 synthetic conformance；
> authoritative product action space 仍为空并 value-free abstain。P27A-R historical replay 为
> `REPLAY_NOT_RUN / ASSET_PENDING`；P27B 为 `AUTHORIZATION_REQUIRED / SHADOW_NOT_RUN`；
> P27C 为 `AUTHORIZATION_REQUIRED / PILOT_NOT_RUN`。P21B/P21C、P23B、P24、P25R 和所有
> real asset/model/output 窗口均未授权或未运行；P26R 仍为 `BLOCKED_EXTERNAL / NOT_RUN`。
> P30A-E1 release-contract hardening、P30A-E2a clean-SHA offline preflight 与 P30A-E2b
> archive-only runner 均已完成；E2a/E2b 均为 `COMPLETE_NEGATIVE`，不是 full gate execution。
> formal P30A 仍 `LOCAL_RC_INCOMPLETE`。P16R local authorization-preflight identity bridge 已完成
> `COMPLETE — IDENTITY_PREFLIGHT_ONLY`；真实 P16R 仍 `AUTHORIZATION_REQUIRED / NOT_RUN`，当前
> local queue 为 `BLOCKED_EXTERNAL`。
> P30A-E1、E2a 或 E2b 都不授权 push、tag、artifact publication、staging 或 production。

## P30A-E1 `ENGINEERING_COMPLETE`; P30A-E2a/E2b `COMPLETE_NEGATIVE`; P16R-PREFLIGHT complete

P30 scope baseline is `694af3eebfca0e99ca07a6ecd8639b522b8ec3d4`; the post-formal-entrypoint
engineering baseline is `d808735ebfd649df6a4c932b95140387aa412c7d`. The completed E1 probe code is
`0a4d72b0825d9ec0ff3b7776bbc4f1f0023336f9` / tree
`ba701d4ee6033e86a2d8abecc7e6ff25c1a05c14` / epoch `1786335170`.

| Gate or probe | Result |
|---|---|
| release-tool / source-archive / packaging suite | `47 passed` (`27 + 6 + 14`) |
| formal Pack-aware entrypoints | `148 passed`; no-Pack is a V2 zero-step `pack_unregistered` abstention |
| Python release-tool Ruff/format and release-shell syntax | PASS |
| React typecheck / lint / production build / bundle budget | PASS |
| two wheel probes | byte-identical: `1,264,708` bytes / `44e5e905e706f87c9b43574a5f02afd41c7b37d9079a0e91956b511bca422303`; `378` ZIP entries, `14` static, zero test/AppleDouble entries, integrity PASS |
| two source-archive probes | byte-identical: `8,055,078` bytes / `ba5e5d0dbe387575049f5603f8011af3359d4f99583f4856233be48dc796e642`; unsafe links and AppleDouble reject |

The probes are local, write-new and out of tree. They are not a clean-install-qualified artifact
bundle, an accepted `release-manifest.json`, an OCI artifact, an SBOM, a licence inventory or a
published release. The shared-environment `pip check` failed because `python-magic` is absent and
unrelated pre-existing `vcbench` pins conflict; it is not a clean-install gate.

P30A-E2a then ran its independent preflight from clean exact SHA
`964b62214f346b15ec2d3f2a622b33f632dde466` / tree
`eac19455bc9241e5347de27782a99942e3591cab` / epoch `1786338523`. The targeted post-commit P30
suite passed `55` (`27 + 6 + 14 + 8` across release-candidate, source-archive, packaging and
E2a-finalizer tests); the write-new `praxis.local-rc-finalizer-preflight.v1` record has SHA-256
`6cb91031c96b7ebec92e32f7c2eb8af307f48ceae3cbe4aac43c1939a0779019`. It records stable pre/post
source identity, `network_used=false`, `full_gate_execution=PRECHECK_ONLY_NOT_EXECUTED` and
`software_rc_gates_passed=false`.

The actual E2a negative blockers are `offline_wheel_cache_incomplete` for both `macos_arm64_cp313`
(`pyjwt==2.13.0`, `pyyaml==6.0.3`) and `linux_arm64_cp313` (those two plus `cffi==2.1.0`,
`cryptography==49.0.0`, `pydantic-core==2.46.4`, `rpds-py==2026.6.3`). No install, artifact build,
OCI build, core/legacy/frontend/Ruff/packaging full gate, SBOM, manifest or release occurred. E2a
is therefore `COMPLETE_NEGATIVE`.

P30A-E2b subsequently completed at exact SHA
`12ad93d57e4f4e7438d2110b5ac9848c6b17ea33` / tree
`14fe604111c18c558048bc282d23da936ac57088` / epoch `1786343459`. Its write-new
`praxis.local-rc-artifact-aware-runner.v1` record is SHA-256
`72459a3b51ba243d747ee2c0159d4105a30ba47d191b99ea05960343bbae63d2`; the controlled nested
preflight record is `064a479fd35deba3b08d70e999171577b9171133873d5bc7a3d9968a57aafec4`. Source
was stable, but both source-archive attempts safely failed on a tracked unsupported link. The runner
therefore records `SOURCE_ARCHIVE_ONLY_NOT_FULL_RC`, `software_rc_gates_passed=false`, no
publication/sign/tag/deploy or policy decision, and the same two wheelhouse blockers. No install,
network, OCI or full gate occurred. Formal P30A remains `LOCAL_RC_INCOMPLETE`; science is
`NOT_RUN / SCIENCE_BADGE_INELIGIBLE` and policy is `NO_NEW_DECISION`. The P16R
authorization-preflight identity bridge subsequently completed as a value-free local contract, not a
P16R scientific run.

## Phase 29E `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION` 本地证据

P29E adds three strict public records for the state/action/observation/time requirement, connected-typed-
subgraph status, and authoritative compilation. The sole compiler input is an exact recursively revalidated
P28 compilation. Current biological identities are unavailable, the graph is exactly `empty_not_connected`
with zero nodes and edges, and every data/model/environment/adapter/compute/benchmark/evidence/policy/result/
tool/prediction slot is null. No placeholder scale chain, node/edge input, registry, asset, path, candidate or
LLM surface exists. Standalone replay remains explicitly not request-bound. Content fingerprints identify
canonical bytes but do not authenticate an issuer.

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_limited_world_model.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -rA \
  praxis_virtualcell/tests/test_limited_world_model.py \
  praxis_virtualcell/tests/test_multi_agent_biology.py \
  praxis_virtualcell/tests/test_virtual_experiment.py \
  praxis_virtualcell/tests/test_experiment_design_replay.py \
  praxis_virtualcell/tests/test_request_v2.py \
  praxis_virtualcell/tests/test_capability_runtime.py \
  praxis_virtualcell/tests/test_benchmark_system.py \
  praxis_virtualcell/tests/test_model_adapter_sdk.py \
  praxis_virtualcell/tests/test_active_learning_agent.py \
  praxis_virtualcell/tests/test_runtime_active_learning.py \
  praxis_virtualcell/tests/test_report_active_learning_request.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_packaging.py \
  praxis_virtualcell/tests/test_versioning.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -rA \
  praxis_virtualcell/tests \
  --ignore=praxis_virtualcell/tests/test_mudata_alignment.py \
  -k 'not golden and not gem and not norman'

python -m ruff check . --extend-exclude old --no-cache
python -m ruff format --check \
  praxis_virtualcell/limited_world_model.py \
  praxis_virtualcell/tests/test_limited_world_model.py
python -m py_compile \
  praxis_virtualcell/limited_world_model.py \
  praxis_virtualcell/tests/test_limited_world_model.py

npm --prefix praxis_vc_react run typecheck
npm --prefix praxis_vc_react run lint
npm --prefix praxis_vc_react run build

python -m pip check
git diff --check
~~~

| Gate | Result |
|---|---|
| P29E focused | `51 passed` |
| P28E + P29E adjacent | `89 passed` |
| P29E affected (exact eleven-test-file suite above) | `390 passed` |
| safe local suite | `1,934 passed / 49 skipped / 387 deselected / 427.59s` |
| legacy suite | `1,147 passed / 58 skipped / 105 deselected / 58.07s` |
| post-commit P27/P28/P29 directed | `117 passed` |
| packaging + versioning | `18 passed` |
| Ruff / targeted format / compile / diff | PASS |
| React typecheck / lint / build / bundle budget | PASS |
| `pip check` | FAIL: missing `python-magic` + pre-existing `vcbench` pin conflicts in shared environment; no environment mutation |
| reproducible local packaging | PASS: two byte-identical wheels; `1,263,199` bytes / `368a66a4…6c01` / `378` entries |

The first broad test attempt without the documented `test_mudata_alignment.py` exclusion was rejected during
collection because optional `mudata` is absent; it is not reported as a passing gate. Negative coverage includes
closed compiler arguments, P28 nested/type/fingerprint drift, re-signed connected/nonempty graphs, placeholder
scales, authority/data/model/result injection, standalone replay request-binding elevation, secret/path echo and
science/policy/execution elevation. See [ADR-0025](ADR-0025-limited-biological-world-model-contract.md), the
[P29E runbook](runbooks/LIMITED-BIOLOGICAL-WORLD-MODEL-CONTRACT.md), and the
[P29E completion report](../reports/phase29e/PHASE29E_COMPLETION.md).

## Phase 28E `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION` 本地证据

P28E adds six strict public records for role policy, typed handoff, deterministic DAG, trace event, trace,
and authoritative compilation. The compiler accepts an exact same-request P17 compilation/P27 experiment and
separately binds an exact standalone P27 replay-result fingerprint; `ReplayResultV1` has no request/experiment
binding and is not called request-matched. It has no caller role, module, registry, candidate, tool or LLM input.
The authoritative graph and trace are empty, qualifying modules
are `0/3`, and prediction/result/tool output are null. Synthetic advisory records are conformance only and do
not count toward real acceptance. Legacy `AgentMessage`/`MessageBus` and default runtime/API wiring are unchanged.

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_multi_agent_biology.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -rA \
  praxis_virtualcell/tests/test_multi_agent_biology.py \
  praxis_virtualcell/tests/test_virtual_experiment.py \
  praxis_virtualcell/tests/test_experiment_design_replay.py \
  praxis_virtualcell/tests/test_request_v2.py \
  praxis_virtualcell/tests/test_capability_runtime.py \
  praxis_virtualcell/tests/test_benchmark_system.py \
  praxis_virtualcell/tests/test_model_adapter_sdk.py \
  praxis_virtualcell/tests/test_active_learning_agent.py \
  praxis_virtualcell/tests/test_runtime_active_learning.py \
  praxis_virtualcell/tests/test_report_active_learning_request.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_packaging.py \
  praxis_virtualcell/tests/test_versioning.py

python -m ruff check . --extend-exclude old --no-cache
python -m ruff format --check \
  praxis_virtualcell/multi_agent_biology.py \
  praxis_virtualcell/tests/test_multi_agent_biology.py
python -m py_compile \
  praxis_virtualcell/multi_agent_biology.py \
  praxis_virtualcell/tests/test_multi_agent_biology.py

npm --prefix praxis_vc_react run typecheck
npm --prefix praxis_vc_react run lint
npm --prefix praxis_vc_react run build

python -m pip check
git diff --check
~~~

| Gate | Result |
|---|---|
| P28E focused | `38 passed` |
| P28E affected (exact ten-test-file suite above) | `339 passed` |
| safe local suite | `1,883 passed / 49 skipped / 387 deselected / 419.19s` |
| legacy suite | `1,147 passed / 58 skipped / 105 deselected / 51.29s` |
| packaging + versioning | `18 passed` |
| Ruff / targeted format / compile / diff | PASS |
| React typecheck / lint / build / bundle budget | PASS |
| `pip check` | FAIL: missing `python-magic` + pre-existing `vcbench` pin conflicts in shared environment; no environment mutation |
| reproducible local packaging | PASS: two byte-identical wheels; `1,259,255` bytes / `0358bf4d…ec9f` / `377` entries |

Negative coverage includes external schema/fingerprint mismatch, missing internal predecessor, undeclared or
duplicate roles, cycles, budget overflow, payload/value/evidence/policy injection, re-signed foreign trace,
nested type drift, synthetic-module laundering, status elevation, secret/path echo, and closed candidate/module
inputs. See [ADR-0024](ADR-0024-multi-agent-biology-contract.md), the
[P28E runbook](runbooks/MULTI-AGENT-BIOLOGY-CONTRACT.md), and the
[P28E completion report](../reports/phase28e/PHASE28E_COMPLETION.md).

## Phase 27A-E `COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE_ONLY` 本地证据

P27A-E 新增十个 public strict schemas，以及一个仅用于 canonical fingerprint payload 的
`vc.replay-outcome-contract.v1` identity。`vc.virtual-experiment.v1` 由 exact
`VirtualCellRequestV2` 派生，但公开序列化不回显 request metadata、secret、path 或 raw
constraints。当前无 exact-request executable + scientifically validated + production-promoted action
domain，因此 control/replicate/batch/cost/model/Pack/
evidence/policy/action catalog 均为空或 null，human approval 保持 required，不产生 prediction，
`executable`/`execution_performed` 均为 false。

Synthetic replay harness 固定一条 primary `active_heuristic` 和四条 baseline（`random`、
`uncertainty_only`、`diversity`、`expert_rule`），先冻结全部 selection receipts，再 reveal outcome。
selector 不接受 outcome 参数；evaluator 重算 canonical receipts，并闭合 exact catalog、action→group、
endpoint/unit/cost/feasibility 与 ledger action set。failed/unavailable 保留为空，不补零、不删除。
`synthetic_realized_utility` 不是 real information gain、historical replay 或科学 evidence。

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_experiment_design_replay.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -rA \
  praxis_virtualcell/tests/test_experiment_design_replay.py \
  praxis_virtualcell/tests/test_virtual_experiment.py \
  praxis_virtualcell/tests/test_request_v2.py \
  praxis_virtualcell/tests/test_capability_runtime.py \
  praxis_virtualcell/tests/test_benchmark_system.py \
  praxis_virtualcell/tests/test_model_adapter_sdk.py \
  praxis_virtualcell/tests/test_active_learning_agent.py \
  praxis_virtualcell/tests/test_runtime_active_learning.py \
  praxis_virtualcell/tests/test_report_active_learning_request.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -rA praxis_virtualcell/tests \
  --ignore=praxis_virtualcell/tests/test_mudata_alignment.py \
  -k 'not golden and not gem and not norman'

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -rA tests \
  -m 'not (integration or llm or remote)'

python -m ruff check . --extend-exclude old --no-cache
python -m ruff format --check \
  praxis_virtualcell/experiment_design.py \
  praxis_virtualcell/tests/test_experiment_design_replay.py
python -m py_compile \
  praxis_virtualcell/experiment_design.py \
  praxis_virtualcell/tests/test_experiment_design_replay.py

npm --prefix praxis_vc_react run typecheck
npm --prefix praxis_vc_react run lint
npm --prefix praxis_vc_react run build

python -m pip check
git diff --check
~~~

| Gate | Result |
|---|---|
| P27A-E focused | `28 passed` |
| P27A-E affected (exact nine files above) | `301 passed` |
| safe local suite | `1,845 passed / 49 skipped / 387 deselected / 453.03s` |
| legacy suite | `1,147 passed / 58 skipped / 105 deselected / 61.21s` |
| Ruff / targeted format / compile / diff | PASS |
| React typecheck / lint / build / bundle budget | PASS |
| `pip check` | FAIL：known polluted shared environment (`python-magic` missing and vcbench pin conflicts); no environment mutation |
| reproducible local packaging | PASS：two byte-identical wheels; `1,251,560` bytes; SHA-256 `4bd584bdae75888b4e09d8cfb2211e002cb509155ca834adb7d00a6106abec99`; `376` entries |

Wheel contents include 14 React entries, zero tests and zero AppleDouble entries. Source/wheel module
SHA-256 is exactly `ffa647094f117ef45adb726559ee23bcb0bd20427c87681ab6675522fa26f55f`;
test SHA-256 is `99679162bea1d9cd6b5a7432b9694841d1fcd5f4e15e64645227cf3688c4a62b`.
Builds used two independent exact-code Git archives, `npm ci --offline`, and the installed Python toolchain
with `--no-isolation --skip-dependency-check`; this is not a clean dependency closure, publication or release.

Negative coverage includes secret/path non-echo, valid core unit preservation, recursively revalidated exact
request identity, unknown candidate/action rejection, cross-domain comparator drift, missing feasibility or
unknown synthetic units, re-signed receipt changes, wrong action→group and non-exact ledger sets, outcome
structural holdout, deterministic strategy parity, failed/unavailable preservation, and re-signed attempts to
elevate historical/science/policy/P27B/P27C/autonomous/external status. No ActiveLearningAgent, runtime, LLM
candidate, real asset or historical replay was wired. See [ADR-0023](ADR-0023-agentic-experiment-design-contract.md),
the [P27A-E runbook](runbooks/AGENTIC-EXPERIMENT-DESIGN.md) and
[P27A-E completion report](../reports/phase27ae/PHASE27AE_COMPLETION.md).

## Phase 26E `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION` 本地证据

P26E binds one exact host request, one P25E community contract, typed missing interface identities and
the topology-only `community_t0→mediator_t1→host_t2→community_t3` DAG. P22 v1 remains
full-request-binding-insufficient; host/community/matching releases and interface mappings are absent, so
every compilation has empty steps and null prediction/host/community/mediator values.

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_host_microbiome.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra \
  praxis_virtualcell/tests/test_host_microbiome.py \
  praxis_virtualcell/tests/test_virtual_microbiome_contract.py \
  praxis_virtualcell/tests/test_community_packs.py \
  praxis_virtualcell/tests/test_curated_registry.py \
  praxis_virtualcell/tests/test_virtual_experiment.py

python -m ruff check . --extend-exclude old --no-cache
python -m ruff format --check \
  praxis_virtualcell/host_microbiome.py \
  praxis_virtualcell/tests/test_host_microbiome.py

npm --prefix praxis_vc_react run typecheck
npm --prefix praxis_vc_react run lint
npm --prefix praxis_vc_react run build

python -m pip check
git diff --check
~~~

| Gate | Result |
|---|---|
| P26E focused | `8 passed` |
| P26E + P25E/P10 + P22/P17 affected | `144 passed` |
| safe local suite | `1,817 passed / 49 skipped / 387 deselected / 387.09s` |
| legacy suite | `1,147 passed / 58 skipped / 105 deselected` |
| Ruff / targeted format / compile / diff | PASS |
| React typecheck / lint / build / bundle budget | PASS |
| `pip check` | FAIL：pre-existing shared-environment dependency conflicts; no environment mutation performed |
| reproducible local packaging | PASS：two byte-identical wheels; `1,242,422` bytes; SHA-256 `69700bb63445864a457cb651037e69dddd93d5be4b184c55a34c3f9332de265a`; `375` entries |

Wheel contents include 14 React entries, zero tests and zero AppleDouble entries. Source/wheel P26E module
SHA-256 is exactly `94f421afabbc2932f574bd11d0d3b3a7e2a67d5b3c271528dafc52b2ee8b2c54`.
This is exact-local-source/toolchain package evidence, not clean-install, dependency-closure, publication,
release or science evidence.

Negative coverage includes same-P22-context/full-request drift, K562 substitution, missing or stale P22
checkpoint/lifecycle, P25 member-byte drift, nested-model and LLM authority injection, closed candidate API,
and re-signed step/prediction/community-release injection. See
[ADR-0022](ADR-0022-host-microbiome-contract.md), the
[P26E runbook](runbooks/HOST-MICROBIOME-CONTRACT.md) and
[P26E completion report](../reports/phase26e/PHASE26E_COMPLETION.md).

## Phase 25E `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION` 本地证据

P25E adds independent `vc.virtual-microbiome-*.v1` contracts around the byte-preserved P10
CommunityPack surface. It binds exact ordered 2–3 members, Pack/taxonomy/assembly/strain identities,
initial abundance, medium/compartment, time, one primary end-time abundance endpoint, ordered baseline
names and OOD axes. Adapter/model/environment/mapping/benchmark/evidence/policy identities remain
explicitly absent, so every exact request has empty steps and value-free abstention.

~~~bash
pytest -q \
  praxis_virtualcell/tests/test_virtual_microbiome_contract.py \
  praxis_virtualcell/tests/test_community_packs.py

python -m ruff check . --extend-exclude old --no-cache

python -m ruff format --check \
  praxis_virtualcell/community_packs/virtual_microbiome.py \
  praxis_virtualcell/community_packs/__init__.py \
  praxis_virtualcell/tests/test_virtual_microbiome_contract.py \
  praxis_virtualcell/tests/test_community_packs.py

npm --prefix praxis_vc_react run typecheck
npm --prefix praxis_vc_react run lint
npm --prefix praxis_vc_react run build

python -m pip check
git diff --check
~~~

| Gate | Result |
|---|---|
| P25E focused | `21 passed` |
| P25E + P10 adjacent | `60 passed` |
| safe local suite | `1,809 passed / 49 skipped / 387 deselected / 449.43s` |
| legacy suite | `1,147 passed / 58 skipped / 105 deselected / 57.14s` |
| Ruff / targeted format / compile / diff | PASS |
| React typecheck / lint / build / bundle budget | PASS |
| `pip check` | FAIL：pre-existing shared-environment dependency conflicts; no environment mutation performed |
| reproducible packaging | PASS：two byte-identical wheels; `1,234,438` bytes; SHA-256 `c8529477974c6379f75bee05e4b0b589e3a03ed70302617ab46461954915d77e`; `374` entries |

Wheel contents include 14 React entries, zero tests and zero AppleDouble entries. Source/wheel module
SHA-256 is exactly
`747808c002ff36e5ac00076da50c5a07cb8d4716596e18a1fd8665e8c7a26d61`. Builds used two
independent completion-SHA archives, npm offline, and the installed Python toolchain with
`--no-isolation --skip-dependency-check`; they do not prove a pinned dependency closure, clean install,
publication or release.

Negative/adversarial coverage includes bad/stale hashes, re-signed scope drift, Pack byte drift before
freeze and planning, non-microbial relabeling, missing strain semantics, request identity drift, missing
adapter/model/environment/mapping/protocol/evidence/policy, baseline/OOD reorder, in-memory
`model_copy` bypass, prediction/secondary injection and frozen P10 v1 fingerprints. No real asset/model
or scientific run occurred. See [ADR-0021](ADR-0021-virtual-microbiome-contract.md), the
[P25E runbook](runbooks/VIRTUAL-MICROBIOME-CONTRACT.md) and
[P25E completion report](../reports/phase25e/PHASE25E_COMPLETION.md).

## Phase 23A `COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE` 本地证据

P23A 新增一个 strict、local-only、evidence-only P13 adapter contract。它精确绑定两个
P22 release/Pack/context、typed P18 endpoint identity、同实验 donor/sample/well/
condition/dose/time、ligand/receptor/evidence namespace 与 mapping，以及声明但未验证的
P20/P21 scorer identity。公开投影唯一允许
`{"interaction_evidence_score": [x]}`；receiver response、effect size、causal claim、
额外 prediction 字段及 legacy co-culture payload 均 fail closed。

adapter 不读取资产、不计算生物分数、不运行模型、不修改 registry，也不进入 default adapter
registry。`synthetic_conformance` fixture 固定标记 `synthetic_conformance_not_evidence`，其 score 是调用方
提供的 unit-interval contract fixture，不是模型结果；real data/model execution、paired
linkage、baseline comparison、paired CI、calibrated uncertainty 与 sender/receiver registry
state 均明确为 false/not available。缺失 paired evidence、baseline gate 未过、unsupported
scope/OOD、execution 未授权或 registry state 未验证时只能 abstain，且无法投影。

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_cell_interaction_evidence_contract.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra \
  praxis_virtualcell/tests/test_cell_interaction_evidence_contract.py \
  praxis_virtualcell/tests/test_model_adapter_sdk.py \
  praxis_virtualcell/tests/test_multiomics_model_input.py \
  praxis_virtualcell/tests/test_curated_registry.py \
  praxis_virtualcell/tests/test_model_registry_v2.py \
  praxis_virtualcell/tests/test_benchmark_system.py \
  praxis_virtualcell/tests/test_pack_factory.py \
  praxis_virtualcell/tests/test_pack_product.py \
  praxis_virtualcell/tests/test_capability_runtime.py \
  praxis_virtualcell/tests/test_virtual_experiment.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra praxis_virtualcell/tests \
  --ignore=praxis_virtualcell/tests/test_mudata_alignment.py \
  -k 'not golden and not gem and not norman'

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra tests \
  -m 'not (integration or llm or remote)'

python -m ruff check . --extend-exclude old --no-cache

python -m ruff format --check \
  praxis_virtualcell/model_zoo/cell_interaction_evidence_contract.py \
  praxis_virtualcell/tests/test_cell_interaction_evidence_contract.py

python -m py_compile \
  praxis_virtualcell/model_zoo/cell_interaction_evidence_contract.py \
  praxis_virtualcell/tests/test_cell_interaction_evidence_contract.py

git diff --check
~~~

| Gate | 结果 |
|---|---|
| P23A focused | `107 passed / 41.71s` |
| P23A affected regression gate | `495 passed / 1 skipped / 116.55s` |
| safe Python gate | `1,787 passed / 49 skipped / 387 deselected / 367.11s` |
| legacy gate | `1,147 passed / 58 skipped / 105 deselected / 57.38s` |
| Ruff excluding `old` / targeted format / `py_compile` / diff | PASS |
| reproducible packaging / ZIP integrity | PASS；wheel `1,226,514` bytes；SHA-256 `e78f40f0f4fe7354e3c660d6612a8ee60a1b2dd61af2fc606a67d01e67ac601e`；`373` entries |

两次 exact-code wheel byte-identical，React `14`、tests `0`、AppleDouble `0`，ZIP
integrity PASS；source/wheel
`praxis_virtualcell/model_zoo/cell_interaction_evidence_contract.py` SHA-256 均为
`d1ba8d8054bf91c4a54a215c331fef65557df3954dba730998821ea9f70743cd`。工具链为
Python `3.13.12`、build `1.5.0`、setuptools `70.2.0`、packaging `26.0`、Node
`25.8.2`、npm `11.11.1`、Vite `8.1.2`。前端使用 `npm ci --offline`，Python build 使用
`--no-isolation --skip-dependency-check`；因此这只是 exact local source/toolchain
reproducibility，不是 pinned dependency closure、clean-install 证明或 release。

本轮未读任何真实 interaction asset，未运行真实 candidate/baseline/benchmark/CI/OOD，未
联网、使用 GPU、远程执行、作 science/operator-policy 决策、promotion、version bump、
release、push 或 deploy。完整边界见
[ADR-0020](ADR-0020-cell-interaction-evidence-contract.md)、
[P23A runbook](runbooks/CELL-INTERACTION-EVIDENCE.md) 和
[P23A completion report](../reports/phase23a/PHASE23A_COMPLETION.md)。

## Phase 22 `COMPLETE — CONTRACT_ONLY` 本地证据

P22 新增 strict Curated Virtual Cell Registry library contract。v1 release composition
严格只允许一个 `FactoryRegisteredPackV1`、一个已有的 P12 release/evidence/policy closure、
一个 P21B evidence bundle 和所有带 exact wrapper approval 的 adapter。它只消费已有的
positive scientific/policy state，不能创建、升级或重算这些状态。Multi-Pack、direct
P14/P15/P16 和其他 non-P21B evidence route 均留待未来新 schema。

Import 默认进入 quarantined；approve/quarantine/revoke/supersede 只改变 curated lifecycle
metadata，不安装资产、不执行模型，也不改变 science/policy。外置 trust 默认 deny-all，按
exact import/decision fingerprint allowlist 授权；外置 checkpoint 精确绑定
`entry_count + last_entry_fingerprint`，打开时先锚定 prefix，再用当前 trust 重验全部
suffix。`checkpoint()` 不替调用方在 registry root 外持久化锚点；revoke/supersede 后在
外部 checkpoint 推进前，回滚到旧 checkpoint 仍可能。content hash 与 stable
authorization reference 均不是签名或 issuer authentication。

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_curated_registry.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra \
  praxis_virtualcell/tests/test_curated_registry.py \
  praxis_virtualcell/tests/test_model_registry_v2.py \
  praxis_virtualcell/tests/test_benchmark_system.py \
  praxis_virtualcell/tests/test_pack_factory.py \
  praxis_virtualcell/tests/test_pack_product.py \
  praxis_virtualcell/tests/test_capability_runtime.py \
  praxis_virtualcell/tests/test_virtual_experiment.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra praxis_virtualcell/tests \
  --ignore=praxis_virtualcell/tests/test_mudata_alignment.py \
  -k 'not golden and not gem and not norman'

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra tests \
  -m 'not (integration or llm or remote)'

python -m ruff check . --extend-exclude old --no-cache

python -m ruff format --check \
  praxis_virtualcell/model_zoo/curated_registry.py \
  praxis_virtualcell/tests/test_curated_registry.py

python -m py_compile \
  praxis_virtualcell/model_zoo/curated_registry.py \
  praxis_virtualcell/tests/test_curated_registry.py

git diff --check
~~~

| Gate | 结果 |
|---|---|
| P22 focused | `35 passed / 43.55s` |
| P22 affected regression gate | `289 passed / 1 skipped / 64.94s` |
| safe Python gate | `1,680 passed / 49 skipped / 387 deselected / 334.23s` |
| legacy gate | `1,147 passed / 58 skipped / 105 deselected / 60.48s` |
| Ruff excluding `old` / targeted format / `py_compile` / diff | PASS |
| reproducible packaging / ZIP integrity | PASS；wheel `1,217,155` bytes；SHA-256 `3f978e9f3eb06ea17017c1838002762f28ae717ee08d987cfb8ea059162a2485`；`372` entries |

两次 exact-code wheel byte-identical，React `14`、tests `0`、AppleDouble `0`，ZIP
integrity PASS；source/wheel `praxis_virtualcell/model_zoo/curated_registry.py` SHA-256 均为
`9678b2460aff6738935a2728e12abf398985c4475d66be96d37a721a21bf62ff`。工具链为
Python `3.13.12`、build `1.5.0`、setuptools `70.2.0`、packaging `26.0`、Node
`25.8.2`、npm `11.11.1`、Vite `8.1.2`。前端明确 offline，Python build 明确使用
`--no-isolation --skip-dependency-check`；因此这是当前本地 source/toolchain 的可复现性
证据，不是 pinned dependency closure 或 clean-install 证明。

默认没有 checked-in curated registry root 或真实 curated release；公开投影只有 Python
library query，敏感字段脱敏、`executable=false`、installed/compatibility unknown。没有
HTTP/UI/Data Center/chat/runtime planning、asset install/execution、真实 lifecycle、network、
GPU、remote、science、operator policy、promotion、version bump、release、push 或 deploy。
完整边界见 [ADR-0019](ADR-0019-curated-virtual-cell-registry.md)、
[P22 runbook](runbooks/VIRTUALCELL-CURATED-REGISTRY.md) 和
[P22 completion report](../reports/phase22/PHASE22_COMPLETION.md)。

## Phase 21A `COMPLETE — SYSTEM_ONLY` 本地证据

P21A 新增严格的 benchmark scope/dataset/split/baseline/metric/gate、run authorization/
runtime receipt、result/profile/external evaluation、evidence/bundle 与 content-addressed ledger
合同。Primary、paired CI、calibration、selective 和 OOD 结果从嵌入的 exact rows 重算；
P8/P9 compatibility helper 仍是冻结的本地语义，不生成新科学决策。

授权候选的正向证据必须由调用方从独立受信源提供 P21B composite
execution fingerprint，它同时绑定 exact authorization、run 和 result。合同内的签发者字段和
content hash 不是身份认证；默认 self-contained bundle 导出
`p21b_execution_not_verified` 负状态。测试中的受信 synthetic positive 仅验证门逻辑，
不是可发布的 benchmark/science evidence，也不允许写入 negative-only ledger。

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_benchmark_system.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra \
  praxis_virtualcell/tests/test_benchmark_system.py \
  praxis_virtualcell/tests/test_ood_validation.py \
  praxis_virtualcell/tests/test_model_registry_v2.py \
  praxis_virtualcell/tests/test_training_pipeline.py \
  praxis_virtualcell/tests/test_capability_runtime.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra praxis_virtualcell/tests \
  --ignore=praxis_virtualcell/tests/test_mudata_alignment.py \
  -k 'not golden and not gem and not norman'

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra tests \
  -m 'not (integration or llm or remote)'

python -m ruff check . --extend-exclude old --no-cache

python -m ruff format --check \
  praxis_virtualcell/benchmarks/system.py \
  praxis_virtualcell/tests/test_benchmark_system.py

python -m py_compile \
  praxis_virtualcell/benchmarks/system.py \
  praxis_virtualcell/tests/test_benchmark_system.py

git diff --check
~~~

| Gate | 结果 |
|---|---|
| P21A focused | `35 passed` |
| affected P8/P9/P12/P20/P21A | `238 passed` |
| safe Python gate | `1,645 passed / 49 skipped / 387 deselected / 285.21s` |
| legacy gate | `1,147 passed / 58 skipped / 105 deselected / 61.52s` |
| Ruff lint / targeted format / `py_compile` / diff | PASS |
| reproducible packaging / ZIP integrity | PASS；wheel `1,202,180` bytes；SHA-256 `ee98d4b3c6895bb6a91be1c439a0f927050cb813e9f7e5c61a37552a15c326f1`；`371` entries |

两次 exact-code offline wheel byte-identical，React `14`、tests `0`、AppleDouble `0`；
source/wheel `praxis_virtualcell/benchmarks/system.py` SHA-256 均为
`583d14434216c26ddffa170e2c35f24963f03461d4e9f10c3fe105073624c4d0`。前端明确使用
`npm ci --offline`，Python build 明确使用 `--no-isolation --skip-dependency-check`；因此
该证据是当前本地工具链的 source/wheel/ZIP 一致性，不是 pinned dependency closure
或 clean-install 证据。宿主环境存在既有污染，所以 global `pip check` 结果无效，
没有记为 PASS。

Ledger 只接受负证据，使用 hash chain 和 durable head 检查内容篡改与 tail
truncation。如果攻击者同时回滚或删除全部 entries 与 head，没有外部/签名 anchor 时
仍不可检出。本轮没有真实 candidate、benchmark run、test/external data read、network、
GPU、remote、science、operator policy、promotion、version bump、release、push 或 deploy。
完整边界见 [ADR-0018](ADR-0018-virtual-cell-benchmark-system.md)、
[P21A runbook](runbooks/VIRTUALCELL-BENCHMARK-SYSTEM.md) 和
[P21A completion report](../reports/phase21a/PHASE21A_COMPLETION.md)。

## Phase 20 `COMPLETE — CONTRACT_ONLY` 本地证据

P20 新增 exact P19 RegisteredPack→冻结 training job→pre-label leakage audit→固定 tiny
worker→safe JSON checkpoint/result→candidate-only model identity 的同步本地链。成功状态固定为
`candidate_cataloged_contract_only`；job、audit、checkpoint、result、artifact、card 和
candidate model 双向绑定，不写 production registry、benchmark 或 evidence ledger。

runner 在打开 train label 前完成 audit。在 Pack-root asset-byte 边界内，current manifest 与
split metadata 在 audit 前读取，train-consumed feature/label bytes 只在 audit 通过后打开；
stored P19 tree 只是历史 provenance。Test/external、未消费或上传的 code-like asset 从未打开。
Exact P19 store-chain replay 与受信 repository source verification 仍独立执行。固定可信 worker 以隔离的
`python -I -S` subprocess 运行，但不是 OS syscall sandbox。environment 同时记录调用方声明的
lock digest 与实际观察到的 installed-distribution digest，不声称认证调用方声明。

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_training_pipeline.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra \
  praxis_virtualcell/tests/test_training_pipeline.py \
  praxis_virtualcell/tests/test_pack_factory.py \
  praxis_virtualcell/tests/test_pack_product.py

python -m pytest -o addopts='' -q praxis_virtualcell/tests \
  --ignore=praxis_virtualcell/tests/test_mudata_alignment.py \
  -k 'not golden and not gem and not norman'

python -m ruff check \
  praxis_virtualcell/cli.py \
  praxis_virtualcell/data_packs/manifest.py \
  praxis_virtualcell/model_zoo/training \
  praxis_virtualcell/pack_product.py \
  praxis_virtualcell/tests/test_training_pipeline.py

python -m ruff format --check \
  praxis_virtualcell/model_zoo/training/pipeline.py \
  praxis_virtualcell/model_zoo/training/tiny_worker.py \
  praxis_virtualcell/tests/test_training_pipeline.py

python -m py_compile \
  praxis_virtualcell/cli.py \
  praxis_virtualcell/data_packs/manifest.py \
  praxis_virtualcell/model_zoo/training/__init__.py \
  praxis_virtualcell/model_zoo/training/pipeline.py \
  praxis_virtualcell/model_zoo/training/tiny_worker.py \
  praxis_virtualcell/pack_product.py

git diff --check
~~~

| Gate | 结果 |
|---|---|
| P20 focused | `56 passed / 158.74s` |
| P19 + P20 adjacent | `99 passed / 1 skipped / 180.33s` |
| safe Python gate | `1,610 passed / 49 skipped / 387 deselected / 290.17s` |
| legacy gate | `1,147 passed / 58 skipped / 105 deselected / 62.44s` |
| Ruff lint / targeted format / `py_compile` / diff | PASS |
| reproducible packaging / ZIP integrity | PASS；wheel `1,178,805` bytes；SHA-256 `2273ee71fb58fef543eae358d3df2aefccec42e80fe72a23380200718c223d79`；`370` entries |

P19+P20 gate 的一个 skip 是本地未安装 `mudata`；没有联网补装，也没有记为 pass。两个
exact-code offline build byte-identical，React `14`、tests `0`、AppleDouble `0`；
source/wheel `pipeline.py` SHA-256 均为
`dd7dbe480c3f000e5345b35fc6358fe2cc1b4377b035c31809d584ce3c869134`，source/wheel
`tiny_worker.py` SHA-256 均为
`4de1ba3b67a67ea24c16b7664058939ae3a634e06cf11601a528aca4c465f02b`。
构建使用 Node `25.8.2` / npm `11.11.1` 和 Python `3.13.12` / build `1.5.0` /
setuptools `70.2.0`；由于本地没有 exact pinned backend wheels，Python build 明确使用
`--no-isolation --skip-dependency-check`。因此该证据不声称 pinned dependency closure 或 clean install。

所有成功 training-run artifact 和 test output 只位于 pytest `tmp_path`；wheel 仅写入独立
`/tmp` packaging roots。没有授权 manual/external training output root，也没有真实 training、
test/external read、network、GPU、remote、benchmark、science 或 evidence；policy 为
`NO_NEW_DECISION`，promotion 为 false，也没有 version bump、release、push 或 deploy。完整边界见
[ADR-0017](ADR-0017-virtual-cell-training-pipeline.md)、
[P20 runbook](runbooks/VIRTUALCELL-TRAINING-PIPELINE.md) 和
[P20 completion report](../reports/phase20/PHASE20_COMPLETION.md)。

## Phase 19 `CONTRACT_COMPLETE` 本地证据

P19 新增 controlled receipt→candidate→review→validation→decision→registration chain、
content-addressed append-only store、v1-readable/v2-writing Pack index、显式 local CLI
dependencies 和 root-free、reviewer/operator ID/rationale/reason-redacted
`GET /api/pack-factory`。旧 path-only register 已退役；
index 写入到 store registration append 之间的 pending 状态对所有 consumer fail closed。

P7 species 全部只作 routing hint；exact taxon 由 candidate manifest 与 reviewer confirmation
绑定。Coarse bacteria receipt 不推断 *E. coli*。Factory registration 固定
`model_compatible=null`、`executable=false`，不会创建 training/checkpoint/evidence/promotion。

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_pack_factory.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra \
  praxis_virtualcell/tests/test_pack_factory.py \
  praxis_virtualcell/tests/test_pack_product.py \
  praxis_virtualcell/tests/test_data_packs.py \
  praxis_virtualcell/tests/test_virtual_experiment.py

python -m pytest -o addopts='' -q praxis_virtualcell/tests \
  --ignore=praxis_virtualcell/tests/test_mudata_alignment.py \
  -k 'not golden and not gem and not norman'

python -m ruff check \
  praxis_virtualcell/pack_factory.py \
  praxis_virtualcell/pack_product.py \
  praxis_virtualcell/cli.py \
  praxis_vc_api/main.py \
  praxis_vc_api/services/runtime_service.py \
  praxis_virtualcell/tests/test_pack_factory.py

python -m ruff format --check \
  praxis_virtualcell/pack_factory.py \
  praxis_virtualcell/tests/test_pack_factory.py

python -m py_compile \
  praxis_virtualcell/pack_factory.py \
  praxis_virtualcell/pack_product.py \
  praxis_virtualcell/cli.py

npm --prefix praxis_vc_react run typecheck
npm --prefix praxis_vc_react run lint
npm --prefix praxis_vc_react run build
git diff --check
~~~

| Gate | 结果 |
|---|---|
| P19 focused | `23 passed / 1 skipped` |
| combined focused + adjacent four-file gate | `108 passed / 1 skipped` |
| safe Python gate | `1,554 passed / 49 skipped / 387 deselected` |
| legacy gate | `1,143 passed / 58 skipped / 105 deselected` |
| frontend typecheck/lint/build | PASS |
| Ruff check / P19 changed-file format / `py_compile` / diff | PASS |
| reproducible packaging / ZIP integrity | PASS；wheel `1,154,421` bytes；SHA-256 `1231f948e6f519b9cea66e5ab0e7ccb41b3b7f5a7aa73efdd7dbaf885bfa969f`；`368` entries |

Focused/combined 的一个 skip 是本地未安装 `mudata` 的可选 MuData 正向路径；没有联网补装，
也没有记为 pass。两个 exact-code offline clean-archive wheel byte-identical，React `14`、tests
`0`、AppleDouble `0`；source/wheel `pack_factory.py` SHA-256 均为
`06fb5267c47e8fcf8bcc596e18c9d12e3cb429b0670b662eb0b2ae448b560508`。这不另行声称
dependency-closure/clean-install proof。

Git 外 real tiny fixture、exact new write-only output root、真实 operator、science 与 policy
均未运行；test-controlled temporary fixtures 仅证明工程合同。完整边界见
[ADR-0016](ADR-0016-controlled-pack-factory.md)、
[P19 runbook](runbooks/VIRTUALCELLPACK-CONTROLLED-PACK-FACTORY.md) 和
[P19 completion report](../reports/phase19/PHASE19_COMPLETION.md)。

## Phase 18 `CONTRACT_COMPLETE` 本地证据

P18 新增 strict joint multi-omics model-input compiler，绑定 ordered required/optional slots、
exact feature alignment、真实 observation join 或 explicit mask、Pack/view/adapter/matrix
identity。它拒绝补零、插补、静默归一化、single-tensor adapter 授权、tamper/replay 与
non-finite runtime matrix；固定不创建 Broker execution step，并输出 contract-only abstain。

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_multiomics_model_input.py

python -m pytest -o addopts='' -q praxis_virtualcell/tests \
  --ignore=praxis_virtualcell/tests/test_mudata_alignment.py \
  -k 'not golden and not gem and not norman'
~~~

| Gate | 结果 |
|---|---|
| P18 contract | `44 passed` |
| adjacent directed | `259 passed` |
| safe Python gate | `1531 passed / 48 skipped / 387 deselected` |
| authoritative Ruff / format / `py_compile` / `git diff --check` | PASS |

当前解释器缺可选 `mudata`，因此未运行依赖它的 H5MU 测试；global `pip check` 受宿主环境
既有污染影响，不作为依赖完整性证据。两个 clean offline archive 的完整 wheel
byte-identical：`1,132,811` bytes，SHA-256
`015724a90656706c0441e4f4f873ee51f8db87dfaae9de35a3e841e7c70b2b7c`，`367` entries，
其中 React `14`、tests `0`、AppleDouble `0`。

Registry 保持 5 releases / 0 native / 0 promoted；science `NOT_RUN`，policy
`NO_NEW_DECISION`，没有执行、release、push 或 deploy。真实 multi-omics model acceptance
仍 pending。完整边界见 [ADR-0015](ADR-0015-multiomics-model-input.md)、
[P18 runbook](runbooks/VIRTUALCELL-MULTIOMICS-MODEL-INPUT.md)和
[P18 完成报告](../reports/phase18/PHASE18_COMPLETION.md)。

## Phase 17 `CONTRACT_COMPLETE` 本地证据

P17 新增 direct exact `vc.request.v2` + exact Pack 的 plan-only 编译路径。它重用
`CapabilityRegistry`、`ModelBrokerAgent.plan()` 和 `ExecutionPlanV2`，只生成 deterministic
Virtual Experiment DAG、immutable Brain context 与 contract-only abstain decision；不准备
wrapper、不运行预测、不调用 LLM。可选 LLM candidate 只进入独立 review/checksum，不能改变
authoritative fingerprint。JobStore v3 绑定 Brain/DAG，并交叉核验 companions、报告语义、
trace/narrative 与 provenance。

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_virtual_experiment.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_request_v2.py \
  praxis_virtualcell/tests/test_pack_semantics.py \
  praxis_virtualcell/tests/test_data_packs.py \
  praxis_virtualcell/tests/test_pack_product.py \
  praxis_virtualcell/tests/test_model_registry_v2.py \
  praxis_virtualcell/tests/test_capability_runtime.py \
  praxis_virtualcell/tests/test_model_broker_agent.py \
  praxis_virtualcell/tests/test_broker_public_models.py \
  praxis_virtualcell/tests/test_registry_public_models.py \
  praxis_virtualcell/tests/test_api.py \
  praxis_virtualcell/tests/test_packaging.py \
  praxis_virtualcell/tests/test_versioning.py \
  praxis_virtualcell/tests/test_virtual_experiment.py

python -m pytest -o addopts='' -q praxis_virtualcell/tests \
  --ignore=praxis_virtualcell/tests/test_mudata_alignment.py \
  -k 'not golden and not gem and not norman'
~~~

| Gate | 结果 |
|---|---|
| P17 contract | `41 passed` |
| adjacent directed | `377 passed / 1 skipped` |
| safe Python gate | `1487 passed / 48 skipped / 387 deselected` |
| authoritative `ruff check . --extend-exclude old --no-cache` | PASS |
| exact-file format / `py_compile` / `git diff --check` | PASS |

`test_mudata_alignment.py` 未纳入该门，因为当前解释器缺可选 `mudata`；第一次 collection
在导入时 fail closed。Global `pip check` 也因宿主环境既有 invalid distributions 与
`vcbench` 冲突而不是有效通过证据。两个 offline clean archive 完整 wheel byte-identical：
`1,118,410` bytes，SHA-256
`bd3752b90a6d8e4d7a825b2f4925d00eb7e5204021fef3404b67e88f7a0e23bd`，`366` entries，
其中 React `14`、tests `0`、AppleDouble `0`，并包含 Brain module。Official strict build
在离线且缺 locked `packaging==26.2` distribution 时 fail closed；system-site no-deps smoke
只是受污染环境中的有限 import/static/CLI 检查。

当前 registry 是 5 releases / 0 native / 0 promoted；因此 P17 real multi-model acceptance
仍 pending，所有真实 direct-v2 请求 abstain，science `NOT_RUN`，policy
`NO_NEW_DECISION`。测试内 `Danio rerio / NCBITaxon:7955` 只在临时 fixture 中存在，未注册。
其后 P18 已仅在 contract-only multi-omics 边界完成；P17 完整边界见
[ADR-0014](ADR-0014-virtual-cell-brain.md)、
[P17 runbook](runbooks/VIRTUALCELL-VIRTUAL-EXPERIMENT-DAG.md)和
[P17 完成报告](../reports/phase17/PHASE17_COMPLETION.md)。

## Phase 16E `ENGINEERING_COMPLETE` 本地证据

P16E 只冻结 Golden Norman K562 / `CVCL_0004`、`GRCh38` / `GCA_000001405.15`、
`scRNA` / `EFO:0008913`、Ensembl 84 有序 5,045-feature delta-expression 合同。
`K562GoldenPerturbationAdapter` 的唯一任务是
`predict_delta_expression → delta_expression`；single-gene 和 combination 的 exact
condition/ordered targets 分开绑定，不做 symbol/version/ortholog 猜测，不将
absolute expression 静默转成 delta。raw 5,045-vector 只能在 exact prepared
input 下原顺序透传；非 success/OOD 必须 value-free abstain，uncertainty 固定
`not_available`。

该 adapter 复用 native P12 artifact/environment/release identities 并绑定已检入的 P8
Golden contract/Pack/manifest identities，但 P16E compatibility 固定
`assets_verified=false`、`executable=false`、`reason=p16r_not_authorized`。它只能在
explicit local registry 中使用；`DEFAULT_ADAPTER_REGISTRY` 仍只有原 P13 delta
reference adapter。以下命令不读取 H5AD/NPY、不运行 Golden/science benchmark：

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_k562_golden_delta_contract.py \
  -o addopts='' -p no:cacheprovider -q -ra

PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_k562_golden_delta_contract.py \
  praxis_virtualcell/tests/test_yeast_deletion_fitness_contract.py \
  praxis_virtualcell/tests/test_ecoli_growth_contract.py \
  praxis_virtualcell/tests/test_model_adapter_sdk.py \
  praxis_virtualcell/tests/test_model_adapter_output_flow.py \
  praxis_virtualcell/tests/test_capability_runtime.py \
  praxis_virtualcell/tests/test_model_registry_v2.py \
  praxis_virtualcell/tests/test_request_v2.py \
  praxis_virtualcell/tests/test_packaging.py \
  praxis_virtualcell/tests/baseline/test_baseline_offline_report.py \
  praxis_virtualcell/tests/baseline/test_baseline_routing_snapshot.py \
  -o addopts='' -p no:cacheprovider -q -ra
~~~

completion code/tree 上的冻结结果：

| Gate | 结果 |
|---|---|
| P16E contract | `231 passed` |
| safe directed | `689 passed` |
| safe legacy | `1147 passed / 58 skipped / 105 deselected` |
| authoritative `ruff check . --extend-exclude old --no-cache` | PASS |
| format check / `git diff --check` | PASS |

两个 clean archive 的 exact-commit wheel byte-identical：`1,108,165` bytes，SHA-256
`d333180996a4ed91161d364275589e992d0be634582cc83a57e9758b86c03c66`，`365` entries，
其中 `14` 个 React entries。这些本地 build 值不是 release identity，版本仍为 `1.6.0`，
没有 version bump。official strict offline build 因本地 hash cache 缺 `packaging==26.2`
而 fail closed；受污染的 system-site venv 仅完成有限 install/import/CLI smoke，不能作为
clean hash-locked install 或 dependency-integrity 证据。

`Science: NOT_RUN`；`P16R: AUTHORIZATION_REQUIRED / NOT_RUN`；
`P16B: NOT_RUN`；`Policy: NO_NEW_DECISION`。P16E 只证明 contract/conformance，
没有读取或运行真实 checkpoint/data/assets，没有 training、GPU、network、
release、push 或 deploy。因 P14–P16 仍少于两个 production-promoted
capabilities，P17 后续只在 contract-only 边界完成，未宣称真实多模型编排。完整边界见
[ADR-0013](ADR-0013-virtualcell-k562-golden-delta-contract.md)、
[P16E runbook](runbooks/VIRTUALCELL-K562-GOLDEN-DELTA-CONTRACT.md) 和
[P16E 完成报告](../reports/phase16e/PHASE16E_COMPLETION.md)。

## P16R-PREFLIGHT `COMPLETE — IDENTITY_PREFLIGHT_ONLY`

The local preflight code is `4f77255f84e33180d7d73b421fc9737ca3a1121d` / tree
`f7aadb7b76a2aa55691d67d9c2948cc7b1e38e95`. It only compiles strict P16/P12/P21 identity
declarations into a fixed abstention record; it has no asset I/O or execution surface.

~~~bash
PYTHONDONTWRITEBYTECODE=1 python3.13 -m pytest -q -rA \
  praxis_virtualcell/tests/test_k562_p16r_preflight.py

PYTHONDONTWRITEBYTECODE=1 python3.13 -m pytest -q -rA \
  praxis_virtualcell/tests/test_k562_p16r_preflight.py \
  praxis_virtualcell/tests/test_k562_golden_delta_contract.py \
  praxis_virtualcell/tests/test_benchmark_system.py \
  praxis_virtualcell/tests/test_model_registry_v2.py \
  praxis_virtualcell/tests/test_model_adapter_sdk.py

PYTHONDONTWRITEBYTECODE=1 python3.13 -m pytest -q -rA \
  praxis_virtualcell/tests/test_release_candidate.py \
  praxis_virtualcell/tests/test_release_source_archive.py \
  praxis_virtualcell/tests/test_packaging.py \
  praxis_virtualcell/tests/test_release_finalizer.py
~~~

Recorded results are focused `18 passed` and affected `399 passed` (`18 + 231 + 35 + 60 + 55`);
Ruff check/format and `git diff --check` passed. This is neither asset verification, candidate or
comparator execution, leakage audit, benchmark evidence, policy, release, nor a registry/runtime/API/CLI
route. Actual P16R remains `AUTHORIZATION_REQUIRED / NOT_RUN`, science `NOT_RUN`, policy
`NO_NEW_DECISION`. See the
[P16R identity-preflight completion record](../reports/phase16r_preflight/PHASE16R_AUTHORIZATION_PREFLIGHT.md).

The shared interpreter's extra package probe is recorded separately: `test_packaging.py` passed `14`,
but `test_versioning.py` had `4 passed / 1 failed` because installed `praxis-virtualcell` is still
`1.6.0` while this checkout declares `1.7.0`; `pip check` also failed for the pre-existing missing
`python-magic` and incompatible `vcbench` pins. No environment mutation was used to conceal that drift.

## Phase 15E `ENGINEERING_COMPLETE` 本地证据

P15E 只冻结 S. cerevisiae S288C / `GCF_000146045.2`、单个 complete gene
deletion 和 exact SGD systematic mapping。`YeastDeletionFitnessAdapter` 的唯一输出是
`predict_deletion_fitness → fitness`：一个相对于同 condition/platform matched
non-deletion control 的 dimensionless finite scalar。数值原样透传，负数和大于
`1` 的数不会被自动归一化或裁剪。非 success/OOD 输出必须 value-free
abstain，uncertainty 固定为 `not_available`，公开 projection 只能在 exact prepared
input 绑定后生成。

该 adapter 复用 native P12 artifact/environment/release identities，但 P15E compatibility
固定 `assets_verified=false`、`executable=false`、`reason=p15r_not_authorized`。
它不在 `DEFAULT_ADAPTER_REGISTRY`；默认 registry 仍只包含 delta-expression
reference adapter。以下命令只使用 synthetic identities 和 raw dictionaries：

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_yeast_deletion_fitness_contract.py \
  -o addopts='' -p no:cacheprovider -q -ra

PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_yeast_deletion_fitness_contract.py \
  praxis_virtualcell/tests/test_ecoli_growth_contract.py \
  praxis_virtualcell/tests/test_model_adapter_sdk.py \
  praxis_virtualcell/tests/test_model_adapter_output_flow.py \
  praxis_virtualcell/tests/test_capability_runtime.py \
  praxis_virtualcell/tests/test_model_registry_v2.py \
  praxis_virtualcell/tests/test_request_v2.py \
  praxis_virtualcell/tests/test_packaging.py \
  praxis_virtualcell/tests/baseline/test_baseline_offline_report.py \
  praxis_virtualcell/tests/baseline/test_baseline_routing_snapshot.py \
  -o addopts='' -p no:cacheprovider -q -ra
~~~

completion code/tree 上的冻结结果：

| Gate | 结果 |
|---|---|
| P15E contract | `98 passed` |
| safe directed | `458 passed` |
| safe legacy | `1147 passed / 58 skipped / 105 deselected` |
| authoritative `ruff check . --extend-exclude old --no-cache` | PASS |
| format check / `git diff --check` | PASS |

这些 gate 没有读取真实 deletion screen/model/assets，没有运行 yeast GEM、
benchmark、external/OOD science、training、GPU 或 network。从两个 manual clean Git
archive 使用本地 Python 3.13 toolchain，在 offline 且 OS-level network-denied 边界内
构建的 wheel byte-identical，SHA-256 为
`7758c13bd5a53c74618d556b14c6e27e0492381162a9ab3364aee7dde5d2bb8d`。这是未发布的
本地 build identity；版本仍为 `1.6.0`，没有 version bump。

严格安装脚本所用本地 cache 缺 `packaging==26.2`，因此按设计 fail closed，
不能记为新的 lock-integrity 或 clean-install 证据。系统环境的 `pip check` 受
global packages 污染，也不作为 P15E 全局依赖兼容性证据。

`Science: NOT_RUN`；`P15R: AUTHORIZATION_REQUIRED / NOT_RUN`；
`P15B: NOT_RUN`；`Policy: NO_NEW_DECISION`。完整边界见
[ADR-0012](ADR-0012-virtualcell-yeast-deletion-fitness-contract.md)、
[P15E runbook](runbooks/VIRTUALCELL-YEAST-DELETION-FITNESS-CONTRACT.md) 和
[P15E 完成报告](../reports/phase15e/PHASE15E_COMPLETION.md)。

## Phase 14E `ENGINEERING_COMPLETE` 本地证据

P14E 只冻结 E. coli K-12 MG1655 / `GCF_000005845.2`、
`predict_knockout_growth → growth_ratio` 的 strict contract。它要求 exact
GEM/release/artifact/environment/Pack/mapping/medium/condition/objective/solver 和
`NCBIGene` target bindings；compatibility fixture 固定
`assets_verified=false`、`executable=false`、`reason=p14r_not_authorized`。
`EcoliK12KnockoutGrowthAdapter` 只在测试 local registry 中注册，生产默认 registry
仍只有 delta-expression reference adapter。

P14E 不读取或运行 GEM/SBML、Cobra、growth/essentiality data 或真实 solver。以下命令
只使用 synthetic identity 和 wrapper-dictionary fixtures：

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_ecoli_growth_contract.py \
  -o addopts='' -p no:cacheprovider -q -ra

PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_ecoli_growth_contract.py \
  praxis_virtualcell/tests/test_model_adapter_sdk.py \
  praxis_virtualcell/tests/test_model_adapter_output_flow.py \
  -o addopts='' -p no:cacheprovider -q -ra

PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_ecoli_growth_contract.py \
  praxis_virtualcell/tests/test_model_adapter_sdk.py \
  praxis_virtualcell/tests/test_model_adapter_output_flow.py \
  praxis_virtualcell/tests/test_capability_runtime.py \
  praxis_virtualcell/tests/test_model_registry_v2.py \
  praxis_virtualcell/tests/test_request_v2.py \
  praxis_virtualcell/tests/test_packaging.py \
  praxis_virtualcell/tests/baseline/test_baseline_offline_report.py \
  praxis_virtualcell/tests/baseline/test_baseline_routing_snapshot.py \
  -o addopts='' -p no:cacheprovider -q -ra
~~~

completion code/tree 上的冻结结果：

| Gate | 结果 |
|---|---|
| P14E contract | `71 passed` |
| P14E + adjacent SDK/output flow | `148 passed` |
| safe nine-file directed | `360 passed` |
| safe legacy | `1147 passed / 58 skipped / 105 deselected` |
| full active-tree Ruff / `git diff --check` | PASS |
| exact-hash adversarial review | 3 independent reviews；no P1/P2 |

明确没有运行 `test_ecoli_gem_case.py`、`test_gem_wrapper.py`、
`test_medium_shift_case.py`、`test_antibiotic_case.py`、
`test_yeast_gem_case.py` 或 P10 real-GEM paths。

两个 exact-commit clean archives 在 OS 层禁止网络后独立完成 frontend offline build
和完整 wheel build；结果 byte-identical：1,086,768 bytes，SHA-256
`462b89376a5134906e98ea4b1ec573bc24e5f2e53266d5a7104be8d625eb88b3`，包含 14 个
deterministic React assets 和 P14 module，无 AppleDouble/`__MACOSX`。这不是 artifact
publication。

隔离 runtime 的 dependency compatibility、installed-wheel imports、delta-only default
registry、local P14 registration 和 no-Cobra smoke 通过。但本地 uv cache 缺
`cffi==2.1.0`、`rpds-py==2026.6.3`、`PyYAML==6.0.3` 和
`pydantic-core==2.46.4` 的原始 wheel bytes/metadata；重打包 cache 内容的 archive hash
不同。因此本窗口没有重新证明 one-shot `--require-hashes` offline install，不能把受限
smoke 或 P13 的历史 lock evidence 改写为 P14E exact lock-integrity 证据。

`Science: NOT_RUN`；`P14R: AUTHORIZATION_REQUIRED / NOT_RUN`；
`P14B: NOT_RUN`；`production_promoted=false`。完整证据见
[ADR-0011](ADR-0011-virtualcell-ecoli-k12-growth-contract.md)、
[P14E runbook](runbooks/VIRTUALCELL-ECOLI-K12-GROWTH-CONTRACT.md)和
[P14E 完成报告](../reports/phase14e/PHASE14E_COMPLETION.md)。

## Phase 13 `ENGINEERING_COMPLETE` 本地证据

P13 当前字节在 P12 `vc.model-adapter.v1` identity 上新增六个严格 Adapter SDK
schema：`vc.adapter-input-contract.v1`、`vc.adapter-output-contract.v1`、
`vc.prepared-adapter-input.v1`、`vc.adapter-execution-provenance.v1`、
`vc.adapter-output-envelope.v1` 和 `vc.adapter-conformance-report.v1`。默认 registry
只新增 delta-expression reference adapter；growth/fitness adapter 仍只是测试 fixture。
以下三组合同测试可分别运行：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_model_adapter_sdk.py \
  -o addopts='' -p no:cacheprovider -q -ra

PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_model_adapter_output_flow.py \
  -o addopts='' -p no:cacheprovider -q -ra

PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_capability_runtime.py \
  -o addopts='' -p no:cacheprovider -q -ra
```

completion code/tree 上的冻结结果：

| Gate | 结果 |
|---|---|
| Adapter SDK | `48 passed` |
| Adapter output flow | `22 passed` |
| Capability runtime | `75 passed` |
| P13 directed（含相邻 runtime 回归） | `265 passed` |
| VirtualCell core | `1462 passed / 35 skipped / 9 deselected`；2 条已知 MuData deprecation warnings |
| Legacy unit | `1146 passed / 59 skipped / 105 deselected` |
| Packaging | `13 passed` |
| Ruff / isolated `pip check` | PASS |
| Frontend typecheck/lint/build/bundle budget | PASS |

两次从 exact completion code 构建的 wheel byte-identical：均为 1,076,180 bytes，
SHA-256 `3658b6247a909d0351d760295e0bcbb8082eac930d96fdfe39e4377b591b4f23`；clean-wheel
安装以及 SDK/default-registry import 均通过。全部命令均在无网络、无外置资产、无真实
权重、无训练/LLM/GPU/remote 的本地范围运行。`Science: NOT_RUN`，
`Policy: NO_NEW_DECISION`；没有版本 bump、release、真实模型注册或 promotion。
实现边界和操作步骤见 [ADR-0010](ADR-0010-virtualcell-model-adapter-sdk.md)、
[Model Adapter SDK runbook](runbooks/VIRTUALCELL-MODEL-ADAPTER-SDK.md)和
[P13 完成报告](../reports/phase13/PHASE13_COMPLETION.md)。

## Phase 12 `ENGINEERING_COMPLETE` 本地证据

P12 当前字节新增分层 Model Zoo v2 合同、v1 fail-closed 迁移、公开路径脱敏投影和
v2 Pack-aware execution/job identity；负例还覆盖 environment distribution/import
namespace 分离、unsafe legacy `model_version` 公开为 `null`、canonical `plan_id` 与
step/report binding、job request/report/outcome identity。以下命令在无网络、无外置
资产、无权重、无训练/LLM/GPU/remote 的本地工作树运行：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_model_registry_v2.py \
  praxis_virtualcell/tests/test_capability_runtime.py \
  praxis_virtualcell/tests/test_pack_product.py \
  -o addopts='' -p no:cacheprovider -q -ra
```

completion SHA 的当前观察结果：`184 passed / 0 failed`；其中单独运行
`test_model_registry_v2.py` 为 `60 passed / 0 failed`。测试中的 native positive
release 是 synthetic conformance，不是科学 evidence 或 production promotion。

完整 P12 定向口径还包括 v1 registry 和 API 回归：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_model_registry_v2.py \
  praxis_virtualcell/tests/test_model_zoo_registry.py \
  praxis_virtualcell/tests/test_capability_runtime.py \
  praxis_virtualcell/tests/test_pack_product.py \
  praxis_virtualcell/tests/test_api.py \
  -o addopts='' -p no:cacheprovider -q -ra

ruff check \
  praxis_virtualcell/model_zoo \
  praxis_virtualcell/pack_product.py \
  praxis_virtualcell/cli.py \
  praxis_vc_api \
  praxis_virtualcell/tests/test_model_registry_v2.py \
  --no-cache
python -m pip check
git diff --check
```

最终本地门为：core `1388 passed / 35 skipped / 9 deselected`；legacy
`1146 passed / 59 skipped / 105 deselected`；packaging `13 passed`；Ruff、隔离环境
`pip check`、`git diff --check`、frontend typecheck/lint/build 和 bundle budget 均通过。
两次 release wheel 构建 byte-identical（1,064,637 bytes；SHA-256
`d6e431dd5f1f175eaec9b605e25df4e47864194932f86ca9dfa5c8cc4be63543`），clean-wheel
安装验证通过。完整证据与明确未运行项见 [P12 完成报告](../reports/phase12/PHASE12_COMPLETION.md)。

## 最近记录的 P11B / `b02d219...` 本地重建证据

这些结果记录自 DOCS-CLOSURE parent，不自动继承为 docs-only completion commit 的
代码、发行或科学证据：

| 层 | 记录结果 |
|---|---|---|
| dependency install / `pip check` / Ruff | PASS |
| VirtualCell core | `1309 passed / 35 skipped / 9 deselected / 1 failed` |
| 唯一 core 失败 | `test_playwright_python_can_be_overridden_without_editing_config`；packaging/text-contract 回归，未修复前不能声称全绿 |
| Legacy unit | `1146 passed / 59 skipped / 105 deselected` |
| frontend typecheck / lint / build / bundle budget | PASS |
| Cell-first Playwright | `12/12 passed` |
| release wheel / offline CLI / API health/root | PASS |
| wheel identity | 1,043,145 bytes；SHA-256 `0a31bbb4bfc2f5773cda459e6790b6ccd6ff11dab8d386c026ad37bd0c42aa96`；仅标识该次本地构建 |

核心结果与根 `tests/` 不能相加成一个“总通过数”。前者是 VirtualCell 发布权威口径；后者是继承的 PRAXIS-2 unit 范围。Phase 10 的 `912/40/9` 是新增产品版本契约测试之前的冻结证据，不应在原报告中回写成新数字。

P11A/P11B 的 UI 测试只证明产品交互和当时的后端接线，不构成模型科学验证、
`production_promoted`、P12 验证或发布证据。P11A 锚点为
`10f629b...`，P11B 完整代码锚点为
`bf44aac25b993e49d0146ccd52dddad5c2fa14de`。

### P4.3 legacy/MCP 本地收口

P4.3 以 `eaa9a4067518ab80591ffec7f033b248b43ed951` 为唯一起始基线。旧
`test_pool_slow_server_startup_timeout_skipped` 把 1 秒 pool 预算同时施加给 slow
fixture 和正常 FastMCP 冷启动；当前本机正常启动实测约 `3.15–3.34s`，因此两者
都被误判超时。

修复后 `PRAXIS_MCP_SERVERS_JSON` 的每个条目可声明可选
`startup_timeout_s`。未声明时沿用 pool 默认 10 秒；声明值必须是有限正数，否则
启动配置 fail-fast。slow fixture 仍使用 1 秒，good fixture 使用 10 秒，没有
skip 或放宽 slow 断言。

当前实际结果：

```text
MCP 红灯：7 failed / 12 passed
超大整数异常边界红灯：1 failed / 18 passed
MCP 收口：20 passed / 0 failed
锁文件目标顶层版本 mcp 1.28.1 / anyio 4.14.2 定向：37 passed / 0 failed
VirtualCell core：1104 passed / 43 skipped / 9 deselected / 0 failed
legacy：1147 passed / 58 skipped / 105 deselected / 0 failed
ruff check . --no-cache：All checks passed
```

完整 core/legacy 使用当前 Python 3.13 环境；锁版本 MCP 定向使用临时
system-site venv 覆盖顶层 `mcp/anyio`，不冒充完整 fresh hash-lock 安装。

### P5 VirtualCellPack multiomics / feature-alignment 收口

P5 以 `a229699deac1e791252739df71f4e4202cc72bac` 为唯一起始基线，在
`/Volumes/T7/PRAXIS-virtualcell-p0` 的 `codex/p5` 分支实施。测试先行证据分为：

```text
初始缺少 P5 error/API：collection error
首轮完整 P5 红灯：20 failed / 5 passed
canonical ModelFeatureContract + UniProt 边界红灯：5 failed / 0 passed
超大 fill 整数异常边界红灯：1 failed / 0 passed
mapping 必须为 Pack asset 红灯：1 failed / 0 passed
base-only optional omics import 红灯：1 failed / 0 passed
```

最小实现后，在全新 `/private/tmp/praxis-p5-verify` Python 3.13.12 环境中严格
hash-install `build-py313.lock` 与重生成的 `dev-py313.lock`，再以
`--no-build-isolation --no-deps -e .` 安装候选，实际结果：

```text
python -m pip check：
No broken requirements found.

锁版本：
anndata 0.12.19
mudata 0.3.10
scverse-misc 0.1.1

P5 定向：
32 passed / 0 failed

P1–P5 Pack/request/baseline 定向：
187 passed / 0 failed

python -m ruff check . --no-cache：
All checks passed

VirtualCell core：
1144 passed / 35 skipped / 9 deselected / 0 failed

legacy：
1146 passed / 59 skipped / 105 deselected / 0 failed
```

core 相对 P4.3 的总收集量精确增加 32 个 P5 case。完整 dev lock 还使 8 个既有
environment-gated case 从 skip 转为 pass，故不能把 passed 数的全部变化归因于
P5。legacy 总收集量不变；fresh lock 未包含非锁定的 `aiosmtpd`，1 个既有 email
test 从 pass 变为明确 skip。MCP slow/good timeout 测试保持通过。

P5 定向产生 2 条 MuData namespace 注册 API 的上游 DeprecationWarning；没有
`pull_on_update` FutureWarning，生产 loader 与 fixture 均显式使用
`pull_on_update=False`。本阶段没有 opt-in LLM、remote、Docker、前端或 `.53`
执行，不能把普通 skip 写成这些能力通过。

### P6 capability-driven runtime

P6 以 `e97cfa153281fb6c9ad33e39c916e2fed1225df9` 为唯一起始基线，在独立
`/Volumes/T7/PRAXIS-virtualcell-p0` 的 `codex/p6` 分支实施。测试先行证据：

```text
初始缺 CapabilityRegistry API：collection error
首轮契约实现后主链接线：5 failed / 32 passed
request identity/严格类型/重复 output/nested dependency：5 failed
request modality/namespace 与 Pack 关系约束：2 failed
plugin 非 dict 输出：1 failed
runtime task/output adapter 与错误 output shape：2 failed
超大 predictor integer：1 failed
提交前 fail-closed 对抗复审（Windows 路径、probe 异常、资产重验、
嵌套非 JSON plugin 输出）：5 failed / 55 passed
```

当前 P6 定向：

```text
praxis_virtualcell/tests/test_capability_runtime.py：
60 passed / 0 failed

P0 offline baseline + runtime determinism 定向：
29 passed / 0 failed

Model Zoo/Broker/wrapper 兼容定向：
58 passed / 0 failed
```

定向测试证明 strict model card、四因子 fingerprint、三层状态、资产/依赖/
资源/scope/runtime adapter fail-closed、Broker 动态 dummy plugin、无 mock
fallback、显式 legacy adapter 和 P0 报告基线。阶段末使用同一 P5 strict-lock
环境实际结果：

```text
python -m pip check：
No broken requirements found.

ruff check . --no-cache：
All checks passed!

VirtualCell core：
1204 passed / 35 skipped / 9 deselected / 0 failed

legacy：
1146 passed / 59 skipped / 105 deselected / 0 failed
```

core 相对 P5 的 `1144 passed` 精确增加 60 个 P6 case；legacy 结果与 P5 完全
一致。core 仍有 MuData 上游 namespace 注册的 2 条 DeprecationWarning。没有
运行真实 LLM、remote/GPU、Docker、前端或 `.53`；普通 skip 不能冒充这些门通过。

### P7 species data portal / controlled exchange

P7 以 `bcc812eed8a9b1cd162361f8c12fb9e325cdb17c` 为唯一起始基线，在独立
`/Volumes/T7/PRAXIS-virtualcell-p0` 的 `codex/p7` 分支实施。测试先行证据：

```text
初始 backend catalog/download/upload 合同：16 failed
初始 frontend data-library E2E：2 failed
hash 不可读 + upload symlink 逃逸：2 failed
声明 body 预解析上限：1 failed
chunked body 预落盘上限：1 failed
最终 frontend dependency audit：1 high（transitive postcss 8.5.16）
```

最小实现与安全复核后：

```text
python -m pip check：
No broken requirements found.

P7 定向：
20 passed / 0 failed

ruff 定向：
All checks passed!

VirtualCell core：
1224 passed / 35 skipped / 9 deselected / 0 failed

legacy：
1146 passed / 59 skipped / 105 deselected / 0 failed

frontend：
npm audit 0 vulnerabilities
typecheck PASS
lint PASS
build + bundle budget PASS
Playwright 58 passed / 1 skipped / 0 failed（59 collected）
```

core 相对 P6 精确增加 20 个 P7 case；legacy 与 P6 完全一致。Playwright 新增
2 个 P7 case，唯一 skip 仍是需明确授权的真实 LLM 流程。完整 core 的 35 skip
仍是 remote/Docker 外部门；本轮没有运行真实 LLM、GPU、Docker 或远端科学模型。
MuData 的 2 条上游 DeprecationWarning 保持不变。

`.53` 只执行了本阶段明确授权的数据操作：在
`/home/zkyd/data1/mzy/praxis-virtualcell-data/public` 下载并逐文件核验 5 个
清单资产，总计 `27,823,623` bytes。远端代码 HEAD/branch/status 和现有
PRAXIS-2 进程保持不变；这不是部署或远端 runtime 测试。

### P8 Golden Norman/K562 Pack 与简单 baseline

P8 以 `09fb1bb3d02adfceed504cbccd7cf36c54a61b69` 为唯一起始基线，在独立
`/Volumes/T7/PRAXIS-virtualcell-p0` 的 `codex/p8-golden-norman` 分支实施。
测试先行证据：

```text
初始 Golden Norman 模块缺失：collection error
正式 evaluation API 缺失：collection error
真实 source/derived hash mismatch 调试：fail-closed，未产出错误 Pack
篡改 Pack 在 baseline 拟合前未校验：1 failed
冻结 control-assignment hash 未执行：1 failed
metric/baseline 标签可与固定数学不一致：5 failed
```

最小实现后，在全新 `/private/tmp/praxis-p8-verify` Python 3.13 strict-lock
环境中 hash-install `build-py313.lock`、`dev-py313.lock`，再以
`--no-build-isolation --no-deps -e .` 安装候选：

```text
python -m pip check：
No broken requirements found.

锁版本：
anndata 0.12.19
numpy 2.5.1
scipy 1.18.0
mcp 1.28.1

P8 定向：
21 passed / 0 failed

P6 capability + Pack/adapter + P8 合并定向：
172 passed / 0 failed

python -m ruff check . --no-cache：
All checks passed!

VirtualCell core：
1245 passed / 35 skipped / 9 deselected / 0 failed

legacy：
1146 passed / 59 skipped / 105 deselected / 0 failed
```

core 相对 P7 的 `1224 passed` 精确增加 21 个 P8 case；legacy 与 P7 完全一致。
core 的 35 skip 仍是 remote/Docker 外部门，2 条 warning 仍来自 MuData 上游
namespace decorator deprecation。没有运行真实 LLM、GEARS、GPU/checkpoint、
Docker 或 UI/E2E，不能把普通 skip 写成这些能力通过。

真实数据操作另有独立证据：

- Dataverse ZIP 与 H5AD 的 size/hash 全部匹配 frozen contract；
- source 和 derived Pack 的 CSR X/counts dataset hash 精确一致；
- 30 validation + 116 test condition × 3 baseline，共 438 次预测逐个经过正式
  Pack-aware broker/governance/Report；
- `.53` Golden 根 15 个文件逐项重算 size/SHA-256，与 Git
  `artifact-manifest.json` 一致，总计 `4,693,649,813` bytes；
- GEARS `run=false`、`assets_accessed=false`。

这类外置数据/评估成功不等于代码已部署，也不提升
`scientifically_validated=false`。

### P8 产品化收口：三物种 Pack、CLI/API/UI 与历史身份

产品化收口以 Golden 完成提交
`b6cf226382cb841fb50e70875c82d1804ae5681e` 为唯一起始基线，在
`codex/p8-product-closure` 分支实施。测试先行证据：

```text
产品模块尚不存在：
collection error / ModuleNotFoundError

React 尚未展示 Pack capability：
1 failed（找不到 “VirtualCellPack 能力与验证” region）

产品编排误放入 data_packs 基础层：
1 failed / 189 passed
既有架构守卫确认 model-zoo/runtime 反向依赖，模块上移后恢复
```

最小实现后的本地证据：

```text
P8 product 定向：
13 passed / 0 failed

API + Pack manifest/adapter/semantics + P6 capability + P8 product：
191 passed / 0 failed

python -m pip check：
No broken requirements found.

python -m ruff check . --no-cache：
All checks passed!

VirtualCell core：
1258 passed / 35 skipped / 9 deselected / 0 failed

legacy：
1146 passed / 59 skipped / 105 deselected / 0 failed

frontend：
typecheck PASS
lint PASS
build + bundle budget PASS
Playwright 59 passed / 1 skipped / 0 failed（60 collected）
```

core 相对 Golden P8 的 `1245 passed` 精确增加 13 个产品契约 case；legacy
计数不变。唯一 Playwright skip 仍是真实 LLM 显式门。三个约 44 KB 的 H5AD
fixture 连续生成两次得到完全相同 SHA-256；测试用正向 model 是 pytest 内部 dummy，
没有加入生产 model zoo。

从当前源码复制到 `/private/tmp` 的无 AppleDouble 临时源后，wheel content smoke
PASS：三个 manifest/H5AD 全部存在，`praxis_virtualcell/tests` 不在 wheel 中。
该 wheel 来自未提交候选，只证明 package-data 内容，不是可发布或可复现 release
artifact。直接在外置盘构建会被文件系统自动生成的 `._*.dist-info` 污染并由 pip
拒绝；正式 release script 仍须在提交后从 `git archive` 的临时源构建。

普通验收没有访问 `.53`、P7 大数据或 Golden 外置资产，没有运行 GEARS、GPU、
真实 LLM、Docker 或远端服务。35 个 core skip 仍是 remote/Docker 外部门，不能
冒充这些能力通过。

### P9 多轴 OOD、弃权与无适配外部验证

P9 以 `480706fbf58343565532debeca70c4de093b045f` 为唯一起始基线，在
`codex/p9-ood-validation` 分支实施。测试先行证据：

```text
初始 P9 模块缺失：
collection error / ModuleNotFoundError

来源 hash 与 selective 防篡改补强：
2 failed / 10 passed

feature contract / external metadata 防篡改补强：
1 failed / 11 passed
```

最小实现后的本地证据：

```text
P9 定向：
12 passed / 0 failed

python -m pip check：
No broken requirements found.

ruff check . --no-cache：
All checks passed!

VirtualCell core：
1270 passed / 35 skipped / 9 deselected / 0 failed

legacy：
1146 passed / 59 skipped / 105 deselected / 0 failed

frontend：
npm audit 0 vulnerabilities
typecheck PASS
lint PASS
build + bundle budget PASS
Playwright 59 passed / 1 skipped / 0 failed（60 collected）
```

core 相对 P8 product 的 `1258 passed` 精确增加 12 个 P9 合同 case；legacy 与
前端计数不变。首次 Playwright 命令因本轮严格 Python 环境位于 `/private/tmp`
而未找到 checkout `.venv/bin/python`，在测试收集前退出；随后按本指南显式启动
同一 fresh API 环境并复用，60 个 case 得到上述正式结果，没有修改配置或断言。
本机 Node 是 `26.4.0`，不替代 CI 固定的 `24.18.0` 平台证据。

公开输入在 Git 外临时目录重放，生成的
`external-validation.json` 与 checked-in artifact 逐字节一致。主 MSE
candidate `1.0603835779`、no-change `1.0533347059`，paired difference 95% CI
`[-0.9076414928, 0.9749711895]`；因此 `available=false`、
`scientifically_validated=false`。没有运行 GEARS、GPU、真实 LLM、remote
service 或 `.53`。

P9 implementation anchor
`6de2ec1543aada7f4e7b265280a784ce0528c9dc` 的 post-commit 发行证据已完成：

```text
双 clean archive wheel 可复现
wheel SHA-256 97a71283005ec462cd3b91f60efe2bcd95a8d5b2f63b44bd7c7160b5d34149ad
clean-install verifier PASS
Docker exact-HEAD smoke 5 passed / 0 failed
```

P9 release-closure 只修测试入口、AppleDouble bundle 审计和治理文档，不改变
runtime、模型或科学 artifact；其最终 commit、wheel hash 和隔离预览证据仍由
阶段结束报告绑定，因为 Git commit 无法自嵌其最终 SHA。

### P10 CommunityPack 前置接口

P10 以 `b0064fab936f06d09a88eea5292e934410302145` 为唯一起始基线，在独立
APFS 分支 `codex/p10-community-readiness` 实施。测试先行证据：

```text
初始 CommunityPack 模块缺失：
collection error / ModuleNotFoundError

namespace/member-current-bytes/exchange-contract 对抗补测：
4 failed / 27 passed

no-model plan/result 可伪造 execution content 补测：
4 failed / 34 passed
```

最小实现后，在 `/private/tmp/praxis-p10-verify-20260729` Python 3.13.12
严格环境中 hash-install `build-py313.lock` 与 `dev-py313.lock`，再以
`--no-build-isolation --no-deps -e .` 安装当前 checkout：

```text
python -m pip check：
No broken requirements found.

P10 定向：
38 passed / 0 failed

Pack/capability/packaging/P10 合并定向：
192 passed / 0 failed

python -m ruff check . --no-cache：
All checks passed!

VirtualCell core：
1310 passed / 35 skipped / 9 deselected / 0 failed

legacy：
1146 passed / 59 skipped / 105 deselected / 0 failed
```

第一次完整 core 诊断误用了旧 T7 venv；其 distribution metadata 是 `0.0.0`，
因此唯一失败是版本合同要求的 `1.6.0`，其余 `1305 passed`。该运行不作为候选
证据，也没有放宽断言；上面的正式结果来自重新安装当前 checkout 的严格环境。

E. coli 复用 P8 tiny Pack；新增 S. cerevisiae H5AD 为 43,848 bytes，两次生成的
SHA-256 均为
`c675ddee3d96aef9000e48ca7480cd0169eb10d3d4eced0fb08891178c7c46fc`。
P10 不增加真实 community model、权重、API、CLI 或 UI；未运行 frontend、真实
LLM、remote/GPU、Docker 或 `.53` 服务测试。toy exchange 通过只证明精确声明量
守恒，不是实验、通量、热力学或科学有效性证据。

## 本地复现

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: \
  --require-hashes -r requirements/build-py313.lock
.venv/bin/python -m pip install \
  --require-hashes -r requirements/dev-py313.lock
.venv/bin/python -m pip install \
  --no-build-isolation --no-deps -e .
.venv/bin/python -m pip check
.venv/bin/ruff check .

.venv/bin/pytest praxis_virtualcell/tests \
  -m "not llm" -o addopts='' -q -ra

.venv/bin/pytest tests \
  -m "not (integration or llm or remote)" \
  -o addopts='' -q -ra

# 可选的广义 legacy 本地盘点；与上面的 CI isolation 分开记数
.venv/bin/pytest tests \
  -m "not llm" -o addopts='' -q -ra

cd praxis_vc_react
npm ci
npm audit --audit-level=high
npm run typecheck
npm run lint
npm run build
CI=1 npm run e2e
```

CI 配置固定 Python `3.13.14` 和 Node `24.18.0`。完整本地/CI 测试环境使用 `requirements/dev-py313.lock`；frontend Playwright 的 API 也使用该 lock，确保真实 FBA 正例具备 mechanistic/Cobra。`requirements/runtime-py313.lock` 继续服务于精简发行安装和 clean-wheel verifier，不能替代完整测试环境。

依赖/frontend 修复提交 `d6011d8` 已由 GitHub attempt 2 的四个通过 job 验证。唯一 legacy 失败在 native Linux 证明为 BashTool 只 kill 直接 shell、后代继续持有 pipe；提交 `6a81987` 用独立 process group、统一 deadline 和取消清理修复，并在 fresh macOS/Linux 严格锁环境得到 legacy `1139/59/105/0`。没有降格、skip 或放宽原失败断言；最终平台发布结论仍必须由下一候选的 GitHub native x86_64 retry 给出。C4 wheel/clean install 和 Docker 证据仍按固定 commit 冻结；最终文档提交完成后还必须重新绑定 exact candidate 的 release artifact。

## C4 发布复现

完整 wheel 从 committed HEAD 的临时 archive 构建，不复用 checkout 的 `dist/` 或 Python build 目录：

```bash
PYTHON_BIN=python3.13 scripts/build_release_wheel.sh /tmp/release-one
PYTHON_BIN=python3.13 scripts/build_release_wheel.sh /tmp/release-two
cmp /tmp/release-one/praxis_virtualcell-*.whl \
    /tmp/release-two/praxis_virtualcell-*.whl
```

随后在全新 Python 3.13 venv hash-install `requirements/runtime-py313.lock`，以 `--no-deps` 安装 wheel，运行 `pip check`，并从 checkout 外执行安装生成的 `praxis-vc --version` / `praxis-vc run` 与 `scripts/verify_release_install.py`。console entry 和 installed-package verifier 都覆盖 offline run 的四项产物；verifier 还覆盖 API health/job、同源 root/hashed asset、包内 web 入口和测试树排除。不包括完整 Streamlit server 或 `praxis-vc ask`。

Docker smoke 必须同时打开环境变量和 pytest integration 门；缺少任一项时只能得到 skip：

```bash
PRAXIS_RUN_DOCKER_SMOKE=1 .venv/bin/python -m pytest \
  praxis_virtualcell/tests/test_linux_docker_smoke.py \
  --run-integration -o addopts='' -q -ra
```

它从 committed HEAD 构建唯一标记镜像，以 `--network none` 启动，并在容器 loopback 验证 non-root、health/version/SHA、installed CLI、React assets 和 offline API report。本地结果只代表 Docker Desktop 的 Linux/arm64 container，不代表原生 Linux、amd64 或 `.53`。

## Marker 与外部门

pytest 启用 strict markers，并静态注册：

- `integration`：容器、数据库、Redis 或发行环境依赖；需 `--run-integration`。兼容旧流程的 `PRAXIS_INTEGRATION=1` 仍可开启该门。
- `llm`：真实外部 LLM 请求；需 `--run-llm`，测试还会单独检查凭证。
- `remote`：GPU、checkpoint、donor 或私网服务；需 `--run-remote`，测试还会单独检查本地依赖。
- `operational`：活部署健康探针，而非隔离测试依赖。

一个测试拥有多个 marker 时，必须满足全部相关 opt-in。只打开 integration 不会运行同时标记为 `integration + llm + remote` 的真实 LLM 模块。

固定 `.53:7788` 健康不变量标记为 `remote + operational`，普通 legacy 命令不会建立 socket 或 HTTP 连接。只有在授权网络与明确运维窗口中才运行：

```bash
.venv/bin/pytest \
  tests/test_m9_invariants.py::test_inv5_v1_backend_still_healthy \
  --run-remote -m "remote and operational" \
  -o addopts='' -q -ra
```

退出码 0 但全部为 skip 只表示前置条件缺失，不能写成 LLM、integration 或 remote 能力通过。

W4B/Gate A 真 ML 验证必须在用户批准的同一候选 SHA、独立批准的 clean donor Git SHA/remote 和可信六文件 digest 集上，按 [Remote Science Validation](runbooks/REMOTE-SCIENCE-VALIDATION.md) 执行：

```bash
# 非独立入口：必须先在 linked runbook 的同一会话通过 donor 与 digest 信任门。
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_ml_workflow_e2e.py \
  --run-remote -m remote -p no:cacheprovider -o addopts='' -q -ra
```

该门要求先只读发现 donor/code 与 checkpoint 元数据，再由可信负责人批准 donor Git 身份和三组 `.json/.pt` digest；当前 `weights_only=False` PT 在批准前禁止反序列化。批准后仍须满足正确 sidecar class、manifest-matching Norman 数据和可用 torch/donor 环境，且结果为 `2 passed / 0 skipped / 0 failed`。CUDA 只作现场环境盘点；当前实现以 `map_location="cpu"` 加载且未迁移 tensor 到 GPU，所以该门不证明 GPU 推理。普通 `run_query()` 不装载 W4B runtime；测试覆盖的是 `build_runtime_ml(...).run_workflow(...)`。

## 前端覆盖边界

历史 C4 候选的 14 个 Playwright spec 共收集 57 个 case，覆盖本地 S1–S9 与
S11–S13：五阶段/返回/重置、abstain、敌对输入、扰动矩阵、高级字段、预设、六个
结果 tab 与审计产物、主题/历史、离线重复性、响应式语义可达和稳定性，以及两个
Results lazy-loading 路径。S10 是真实 LLM 外部门的 1 条显式 skip；没有运行，不能
写成通过。现行 P11B Cell-first 重建证据是上方单列的 `12/12`，两种 UI scope 不得
混算。

视觉/几何边界：C3 已完成人工浅色/深色验收并自动验证实际 `data-theme`。Results 工具栏在 1280×720 使用 `.card-actions` 与 `getBoundingClientRect()` 做一条窄几何回归，因为它保护已复现的标题/按钮挤压 bug；mobile/tablet 只证明语义可达，不声称逐像素等价。

C4 的 build budget 实测 initial JavaScript aggregate 为 226,046 bytes（gzip 70,320），延迟加载的 Results chunk 为 410,889 bytes（gzip 114,914），八个本地 font assets 合计 214,292 bytes。旧 C3 单主包 `635.51 kB` 已由 lazy boundary 取代；预算脚本会在初始 aggregate、任一 JavaScript chunk 或 font 范围超标时使 build 失败。

## GitHub Actions

`.github/workflows/ci.yml` 配置五个 job：

1. Python lint + VirtualCell core
2. frontend build + Playwright
3. reproducible full release wheel
4. Linux release container smoke
5. legacy unit（外部套件 gated）

首次 D1a 已把 `codex/project-consolidation=6086e6995b1c3c01ec31075ce1164a0165cb8d43` 发布到 GitHub。对应 [run 29894971142](https://github.com/NHNQNHNQ/PRAXIS-Virtualcell/actions/runs/29894971142) 的实际结果为：

| GitHub job | 结果 | 失败边界 |
|---|---|---|
| Python lint and VirtualCell core | FAIL | dev lock 的严格 hash 安装阶段失败，未进入 Ruff/pytest |
| Frontend build and Playwright | FAIL | typecheck、lint、build 通过；Playwright `55 passed / 1 skipped / 1 failed` |
| Reproducible full release wheel | PASS | 只绑定旧 SHA `6086e6995b1c3c01ec31075ce1164a0165cb8d43`，不能继承给新候选 |
| Linux release container smoke | FAIL | hash 依赖安装阶段失败，未进入 smoke |
| Legacy unit tests (external suites gated) | FAIL | dev lock 的严格 hash 安装阶段失败，未进入 pytest |

三个 Python/Linux 失败首先暴露 macOS/arm64 编译的 dev lock 漏掉 Linux marker 依赖 `greenlet`，修复后 Linux 迭代又暴露 `watchdog`；hash mode 因此在环境创建阶段 fail-closed。frontend 使用 lean runtime lock 时没有 Cobra，真实 FBA 正例按设计返回 abstain，从而使旧断言失败。提交 `d6011d8` 通过显式 union `greenlet==3.5.3`、`watchdog==6.0.0`、重生成 dev lock、让 frontend CI 使用 dev lock 并增加 packaging 回归修复这两个环境问题，没有弱化科学断言。

首次修复后的 candidate `ee36d7948047f346f55a02d62ccaac84391e3c20` 经精确授权快进发布。对应 [run 29971566980](https://github.com/NHNQNHNQ/PRAXIS-Virtualcell/actions/runs/29971566980) 的实际结果为 Python core、frontend/Playwright、reproducible wheel、Linux release container **PASS**；legacy **FAIL**，汇总 `1 failed / 1135 passed / 59 skipped / 105 deselected`。唯一失败 `test_huge_output_capped_not_ooming` 是 Linux dash 派生的 `cat` 在直接 shell 被 kill 后仍持有 pipe；详见 [D1a retry report](status/PHASE-D1A-CI-RETRY-2026-07-23.md)。本地修复 `6a81987` 还关闭了 pipe 提前关闭绕过 timeout 与上层取消遗留进程组两个同源缺口。

“存在 run”不等于 CI 全绿，也不证明这些 job 是 branch-protection required checks。
以上 D1a 指令和 SHA 只属于当时的发布窗口，已不构成当前行动授权。当前 P20 窗口未读取
或修改 GitHub `main`/tag、`.53` 或任何远程状态；未来 CI、push、发布和部署仍须以
届时现场 HEAD 获得独立精确授权。
