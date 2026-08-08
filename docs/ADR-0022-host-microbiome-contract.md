# ADR-0022：Host–Microbiome contract-only DAG and abstention

- 状态：Accepted（P26E engineering `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`）
- 日期：2026-08-08
- Starting SHA / active baseline：`6bd02231449b6969e22aeb5bea6798fd334daef6`
- Completion code SHA：`5bd3e502a7a1f1cb0fd1b79ecfd109eeeaf265c4`
- Completion tree：`b3d7303cafb5b874c8b5a441b53e32ff77ef2c54`
- Source date epoch：`1786176771`
- 分支：`codex/p25e-virtual-microbiome`
- Engineering：`COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`
- Fixture evidence：`SYNTHETIC_CONFORMANCE_ONLY`
- Science：`NOT_RUN`
- Policy：`NO_NEW_DECISION`
- P26R：`BLOCKED_EXTERNAL / NOT_RUN`

## 背景

P26 真实执行要求 exact-scope host 与 community capabilities 都已有 immutable positive science、
具名 operator 的 production policy、active releases，以及一个绑定双方和跨域 interface 的 matching
release。当前 P22 v1 只组合 one Pack，并只暴露 organism/cell type/intervention/endpoint 级 context；
它不能证明完整 `VirtualCellRequestV2`。P25E 也只是 community contract，不是 multi-Pack release。

因此 P26E 只能冻结未来执行所需 identity、确定性拓扑和明确缺失项。它不能创建 host/community
prediction、mediator value、interface mapping、science evidence、operator policy 或 fake release。

## 决策

### 1. 五个 public records 与一个 joint-scope payload

`praxis_virtualcell/host_microbiome.py` 定义：

- `vc.host-microbiome-interface-requirement.v1`；
- `vc.host-microbiome-dag.v1`；
- `vc.host-microbiome-contract.v1`；
- `vc.host-release-audit-snapshot.v1`；
- `vc.host-microbiome-compilation.v1`。

`vc.host-microbiome-joint-scope.v1` 只是 canonical fingerprint payload，不是第六个 public model。
P26E 不提供 request/plan/candidate schema，也不接受 LLM 或 candidate DAG 作为 authority。

### 2. Exact host request 与 P25E identity 分别绑定

Contract 绑定完整 host request fingerprint、由该 request 确定性派生的 P22-shaped context、P25E
community contract/scope、typed interface requirement、DAG 与 joint scope。P25 member bytes 在 freeze
和 compile 时重验；漂移只能得到 unsupported scope/abstention，不能刷新 fingerprint 或 fallback。

可选 host Pack/release fingerprints 必须成对出现，但 `required_host_request_binding_fingerprint`
固定为 `null`。Community release schema/fingerprint 与 matching release fingerprint 也固定为 `null`。
这些 null 是当前可信状态，不是 caller 待填写字段。

### 3. P22 audit 永远不能升级完整 request

Audit 可以区分 registry absent、verification/checkpoint failure、release missing/mismatch/inactive/non-positive
以及 context matched。但即使 transient synthetic P22 fixture 的 context、lifecycle、science 和 policy 字段
均为 positive，结果仍只能是 `p22_context_matched_request_binding_insufficient`：完整 request match
固定 false，full-request science/policy 固定 `null`。

K562 release 与 intestinal host request 必须 mismatch。这个负例只证明 no-substitution，不证明存在
intestinal epithelial、organoid 或其他真实 host capability。

### 4. Interface 是 typed missing requirement

Interface 绑定 P25 medium、compartment、time、metabolite/cytokine/receptor kinds、identity dimensions 和
两个方向。Mapping、source-output contract 和 target-input contract fingerprints 固定 `null`；implementation、
implicit unit conversion、imputation 和 causal claim 全部 false。列出 entity kinds 不证明 mediator、单位、
dose、receptor binding 或因果机制已建立。

### 5. DAG 只声明时间前向拓扑

唯一拓扑是：

```text
community_state_t0
→ mediator_state_t1
→ host_state_t2
→ community_state_t3
```

它绑定 request/community/interface identities，但没有 execution steps。节点名称和 `time_unrolled=true`
不是动力学、机制、收敛 co-simulation、observed time series 或 causal evidence。

### 6. Compilation 永远 value-free abstain

Compilation 固定 empty steps，`executable=false`、`abstain=true`，prediction、host result、community
result 和 mediator trace 全部 `null`。Mandatory reasons 按序为：

```text
matching_host_release_unavailable
matching_community_release_unavailable
matching_release_unavailable
cross_domain_interface_unavailable
p26_real_execution_not_authorized
```

P25 bytes/scope 漂移时在首位增加 `unsupported_host_microbiome_scope`。Compilation 内固定 false 的
science/promotion/policy guards 不是 benchmark 结果或 operator 决定；canonical ledgers 仍分别是
science `NOT_RUN` 与 policy `NO_NEW_DECISION`。

## 后果

P26E engineering 独立收口，P26 umbrella 状态为
`ENGINEERING_COMPLETE_SCIENCE_PENDING`。P26R 保持 `BLOCKED_EXTERNAL / NOT_RUN`，直到 exact host
release、community release、完整 request bindings、matching release、cross-domain interface 和独立授权
全部存在。P26E 没有运行真实数据、模型、baseline、CI、OOD、privacy/consent 或 co-simulation。

在 P26E 收口时，standing local authorization 下下一 eligible work unit 是 P27A-E；该 follow-on
随后已从 P26E docs closure `a12cf4f4b71efb653f8128afcb1f468211fdb837` 开始，并在 code
`5875571bf9d8b518dc7a857feb935206f756de59` 完成 strict experiment-design contracts 与
rank-then-reveal synthetic harness。P27A-R historical replay 仍为
`REPLAY_NOT_RUN / ASSET_PENDING`；P27B 为 `AUTHORIZATION_REQUIRED / SHADOW_NOT_RUN`，P27C 为
`AUTHORIZATION_REQUIRED / PILOT_NOT_RUN`。当前下一本地 work unit 是 P28E contract-only
orchestrator/typed handoff/trace/abstention，真实 P28 acceptance 为 `0/3`。

操作边界见 [P26E runbook](runbooks/HOST-MICROBIOME-CONTRACT.md)，完整 frozen evidence 见
[P26E completion report](../reports/phase26e/PHASE26E_COMPLETION.md)。
