# ADR-0021：Virtual Microbiome contract-only identity and abstention

- 状态：Accepted（P25E engineering `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`）
- 日期：2026-08-08
- Starting SHA / active baseline：`ae5e93571783cb3cf49a6e0fab531a89e963f7ec`
- Completion code SHA：`039393e6be897b3014bb0b657d0a439d879578b6`
- Completion tree：`b53e542940bf39fd44965fe55416798211ab580b`
- Source date epoch：`1786171049`
- 分支：`codex/p25e-virtual-microbiome`
- 前置：P10 CommunityPack v1 byte/semantic regression；P24 real adapter 仍未授权
- Engineering：`COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`
- Fixture evidence：`SYNTHETIC_CONFORMANCE_ONLY`
- Science：`NOT_RUN`
- Policy：`NO_NEW_DECISION`

## 背景

P24 是 real-only First Community Adapter work unit；没有真实 assets、固定 P20/P21 model、
mapping 和 execution window 时，不能用 synthetic adapter 冒充 P24 完成。当前持续本地授权同时
明确允许 P25E 先完成固定 scope、schema、adapter requirement、endpoint 和 fail-closed software。

因此 P25E 必须表达「未来真实能力需要什么」和「当前缺少什么」，但不能创建一个假 adapter、
预测值、evidence 或 policy。它还必须逐字节保护 P10 `vc.community-*.v1` no-model 语义。

## 决策

### 1. P25 使用独立 v1 schema，不修改 P10 CommunityPack runtime

P25E 在新模块 `community_packs/virtual_microbiome.py` 中定义七个
`vc.virtual-microbiome-*.v1` schema。P10 `contracts.py` 不变，也不新增
`CommunityModelAdapter` subclass 或默认 registration。P10 plan/result 继续固定 no-model
abstention；P25E 不能把 toy exchange balance 当作生物学或 solver evidence。

### 2. Scope 绑定完整 ordered member closure

Scope 只接受两个或三个 ordered unique members，并绑定每个成员的当前 Pack bytes、Pack
fingerprint、NCBI taxonomy、scientific name、assembly 和一个显式 unique strain identity term。
Initial abundance 必须逐成员绑定、为正且精确合计为一。Medium、compartment、time start/end/unit、
time fingerprint 和 `well_mixed` space 都进入 scope identity。

每次 freeze 和 planning 都从当前 Pack bytes 重建 identity。仅重新签一个改变了 time、member、
abundance、medium 或 nested fingerprint 的对象不能绕过 current-scope comparison。Pydantic
in-memory instance 也先经过 JSON-shaped round-trip revalidation，避免 `model_copy` 绕过 strict
边界。

P25E 的 schema 要求 2–3 members，但 synthetic conformance allowlist 当前只有两个已审计的
checked-in bacteria/yeast Pack fingerprints，因此唯一 positive freeze fixture 恰为 2 members。
这些 fingerprints 必须与 exact taxonomy/assembly/strain term 组合。这不是生产 taxonomy allowlist；真实
P25R 必须使用另行授权、独立命名且不声称 contract-only fixture role 的 binding。

### 3. 唯一 primary endpoint 与 science/policy 分层

唯一 endpoint 是 exact end time 的 ordered strain abundance fraction vector。Metric 是 mean
absolute error，方向 lower-is-better；工程 fixture 阈值为 `0.1`。Secondary 不能覆盖 primary，
P25E 结果完全禁止 secondary values。

Scope fingerprint 不包含 mutable science 或 policy status。P25R 的 P21 benchmark evidence 与
P21C operator policy 必须独立引用 immutable scope/endpoint/model/environment/adapter identities，
而不是修改现有 scope bytes。

### 4. Adapter requirement 是 typed negative closure

P25E 要求 adapter 必须来自 independently versioned/fingerprinted P24 real community adapter，
并固定 baselines 和 OOD axes。但当前 adapter、model、environment、metabolite mapping、benchmark
protocol、evidence 和 policy fingerprints 全部为 `null`，`implementation_available=false`。

这不是一套重复的 benchmark protocol。P25R 必须复用 P21A/P21B 的 frozen protocol、split、
metric/CI/OOD 和 execution identity，并在独立授权后提供这些 immutable references。

### 5. 所有 P25E plan/result 必须 value-free abstain

Exact request 仍返回 empty steps、`executable=false`、`prediction=null` 和
`secondary_predictions=null`。Reasons 明确列出缺少 P24 adapter、model、environment、mapping、
benchmark protocol、real execution binding、scientific evidence 和 production policy。

Stale Pack bytes、stale/re-signed community identity 或 request scope drift 会增加对应首因。没有
fallback、zero fill、imputation、LLM 数值、legacy predictor 或 P10 toy solver 路径。

### 6. Identity 与 negative tests 是工程证据，不是 science

Canonical synthetic fixture 的 contract/plan/result fingerprints 和 P10 golden fingerprints
被冻结为 regression evidence。测试覆盖 bad hashes、wrong scope、missing binding、OOD reorder、
stale Pack bytes、in-memory bypass、human-Pack relabel、secondary/prediction injection 和 P10 v1
golden drift。

这些 checks 只证明 deterministic conformance 和 fail-closed 行为。没有真实 mono/co-culture
data、growth/biomass、metabolomics、mapping、model execution、baseline、paired CI、independent
condition/batch、scientific evidence 或 product policy。

## 后果

P25E engineering 可以独立收口，但 P25 scientific capability 仍不存在。P25 umbrella 状态是
`ENGINEERING_COMPLETE_SCIENCE_PENDING`。P24 和 P25R 都需要
exact external asset/run authorization；positive evidence 后仍须独立 P21C operator decision。

P26E 随后已在 code `5bd3e502a7a1f1cb0fd1b79ecfd109eeeaf265c4` 完成
contract/DAG/matching/abstain software；它只把 P25E identity 作为 typed missing community
prerequisite，未把它升级为 release、science 或 policy。只有 exact host/community capabilities
都 scientifically validated、production promoted，且独立 matching release 存在时，真实 P26
execution 才可开始。不得用 K562 替代缺失的 host capability。

操作边界见 [P25E runbook](runbooks/VIRTUAL-MICROBIOME-CONTRACT.md)，完整 frozen evidence 见
[P25E completion report](../reports/phase25e/PHASE25E_COMPLETION.md)。P26E 的后续决策见
[ADR-0022](ADR-0022-host-microbiome-contract.md)与
[P26E completion report](../reports/phase26e/PHASE26E_COMPLETION.md)。
