# ADR-0018：Virtual Cell Benchmark System 合同

- 状态：Accepted（P21A `COMPLETE — SYSTEM_ONLY`）
- 日期：2026-08-07
- 唯一起始基线：`5f3fc2d88c20e8083fb66a4c3399c5fe148241be`
- Completion code SHA：`20ecc12542e5df40c90d1fc367dbe86b563478b8`
- Completion tree：`ffcd261dd7d506d0ad852023afcba0f5c97a2d72`
- Source date epoch：`1786050825`
- 分支：`codex/p21-benchmark-system`
- 前置：ADR-0017
- 工程状态：`COMPLETE — SYSTEM_ONLY`
- Science：`NOT_RUN`
- Policy：`NO_NEW_DECISION`
- P21B / P21C：`AUTHORIZATION_REQUIRED / NOT_RUN`

## 背景

P20 已把 exact factory-registered Pack 绑到 contract-only candidate model identity，但它不能回答
如何在查看 candidate result 前冻结 benchmark protocol，也不能将内部 benchmark、外部
validation、promotion eligibility 和 operator promotion policy 混成一个状态。P21A 因此只建立
repository-local benchmark system contract：冻结 protocol、重验 result bindings、派生分层 evidence，
并保留 fail-closed negative history。

P21A 没有获得任何真实 candidate、test/external data、output root、asset、weight、GPU、
remote 或 network 授权。所有 positive-path 单元测试只是 pytest 临时目录内的 synthetic conformance，
不是 benchmark 或 scientific evidence。

## 决策

### 1. Protocol 在 candidate result 之前全量冻结

`BenchmarkProtocolV1` 使用 strict frozen Pydantic contract 和 canonical JSON SHA-256 identity，绑定
scope、Pack、dataset/platform、feature/output contract、biological-group split、simple baseline、primary
metric、seed、paired CI、validation-only threshold、calibration、OOD、independent external policy 和 promotion
gate。`candidate_result_observed=false`、`frozen=true`、`composite_score=null` 为强制状态；不定义
可被调参的综合分数。

Split 嵌入 exact validation/test/external biological group IDs、counts 和 set fingerprints，并把 train /
validation / test / external 的 donor、condition、replicate、batch 记录 count/fingerprint 绑回 protocol。
`LeakageAuditV1` 必须携带 canonical records，覆盖所有 partition，且在任何 test/external evaluation
前通过。修改记录后单纯重签 audit 不能绕过 frozen protocol。

### 2. Run 必须绑定全部 P20 provenance 和 formal execution receipts

`BenchmarkRunV1` 绑定 training job/result/checkpoint/artifact/card/candidate identity、factory registration、
Pack、feature/output contracts、trainer source、environment、adapter/compatibility receipts、evaluation code 和
environment，并要求路径固定为 `model_adapter_broker_runtime`。Broker/runtime fields 只是严格
typed receipt contract；P21A 没有实际调用 model、Broker 或 runtime，也不直接读取 model asset。

`BenchmarkRunAuthorizationV1` 自包含完整 content hash，绑定 exact run payload、protocol、scope、candidate、
asset manifest 和 output-root identity。这些检查证明 identity/content integrity，**不证明 issuer
authentication**。P21B consumer 必须从独立受信来源 pin exact
`vc.p21b-execution-identity.v1`，其 identity 同时覆盖 authorization fingerprint、完整 run fingerprint 和
result fingerprint。调用者自报、仅绑定 authorization，或在 result 产生前预算的值都不足够。

### 3. Result 从嵌入记录重算，evidence 分层派生

Completed result 必须嵌入 exact group×seed primary rows、paired group differences、validation threshold rows、
test selective rows、calibration bins、OOD group values 和 external evaluation receipt。Canonical means 使用
`math.fsum`；paired CI 按冻结的 P8 `0.95 / 2000 / seed 0` helper 重放；threshold 只能由
validation rows 通过 P9 `select_threshold` 选择，test selective metrics 通过 P9
`selective_metrics` 重算。Summary、CI、calibration、OOD 或 receipt 不一致时 fail closed。

`derive_evidence()` 分别派生 `benchmark_passed`、`scientifically_validated` 和
`promotion_eligible`，但不存在 `production_promoted` 状态或 operator decision。未提供独立受信
P21B composite identity 时，authorized run 也必须保持 negative。

`BenchmarkEvidenceBundleV1` 是自包含但不受信的交换格式；它不序列化、传播或存储信任
bit，重载时必须默认派生 negative evidence。Synthetic positive gate tests 仅短暂调用 out-of-band
composite verifier，不将 positive bundle 当作 evidence 写盘。

### 4. P8/P9 只作 exact compatibility replay

`replay_checked_in_benchmarks()` 只读已检入的 exact-size/exact-SHA 历史文件。P8 保持
historical inventory：available/benchmark/promotion 不绑定，science 为 false；P9 必须精确重放为
negative/unbound，包括原 reason codes 和 exact receipt fingerprint。这是 in-memory/测试身份重验，
不是重新发布、新 scientific result 或对历史 output root 的补授权。

### 5. Ledger 只保存 negative evidence

`BenchmarkEvidenceLedger` 要求 explicit absolute canonical write-new root。初始化在 parent 下创建随机
`0700` sibling staging，持有 dirfd/inode，fsync marker/head/lock/entries，再以 no-replace atomic rename
发布。追加记录使用 canonical content-addressed filename、exclusive staging/link、稳定 lock、
predecessor hash chain 和 durable head；单次已发布但 head 未更新的 crash tail 可在 lock 内恢复。

Ledger 只接受 authorized-candidate negative bundle 或 exact P9 negative receipt；拒绝 contract fixture、
promotion-eligible bundle、重复 result/run、冲突 logical identity 和重用 authorization。P8 保持 null/unbound，
不写入 negative ledger。

Durable head 可发现 tail/all-entry truncation，但 hash chain + head 无法发现攻击者同时回滚整个 ledger
和 head；完整 anti-rollback 仍需外部或签名 anchor。初始化失败时不通过路径递归删除，
因此可保留随机 `0700` staging 供安全人工恢复；处理前必须停止 writers，并重验 inode、
owner、mode 和完整 content。

## 验证与完成身份

| Evidence | Frozen value |
|---|---|
| completion code SHA / tree / epoch | `20ecc12542e5df40c90d1fc367dbe86b563478b8` / `ffcd261dd7d506d0ad852023afcba0f5c97a2d72` / `1786050825` |
| focused / affected matrix | `35 passed` / `238 passed` |
| safe / legacy | `1,645 passed, 49 skipped, 387 deselected` / `1,147 passed, 58 skipped, 105 deselected` |
| static checks | full Ruff lint / targeted format check、`py_compile`、`git diff --check` passed |
| reproducible wheel | `1,202,180` bytes；SHA-256 `ee98d4b3c6895bb6a91be1c439a0f927050cb813e9f7e5c61a37552a15c326f1`；`371` entries / React `14` / tests `0` / AppleDouble `0`；ZIP passed |
| `system.py` source / wheel | SHA-256 `583d14434216c26ddffa170e2c35f24963f03461d4e9f10c3fe105073624c4d0`；exact match |
| two independent builds | byte-identical；explicit npm offline and Python no-isolation/skip-dependency-check |

Global `pip check` 因宿主环境已有污染、缺失 `python-magic` 和 `vcbench` conflicts 而失败，
不是 P21A gate，也未被误报为通过。两次打包均从 completion commit 的独立 `git archive`
执行，只使用本机已安装 toolchain/cache；没有 download 或 network fallback。这只证明 exact local
source/toolchain 边界下的字节可复现性，不是 clean-install、dependency-closure、release 或部署证明。

## 后果与下一 gate

P21A 完成只证明 benchmark system contract 可在 tiny synthetic fixtures 上 fail closed 和确定性重验。
真实 candidate run、data/test/external read、asset/weight、training、GPU、remote、network、scientific
validation、operator decision、promotion、`production_promoted`、push、release 和 deploy 均保持 `NOT_RUN`/false。

P21B real execution 和 P21C independent operator policy 仍为 `AUTHORIZATION_REQUIRED / NOT_RUN`。下一个
eligible local work unit 是 P22 contract-only curated model registry；它不得借 P21A completion 导入任何
executable release 或 promotion decision。

详细操作边界见 [P21A runbook](runbooks/VIRTUALCELL-BENCHMARK-SYSTEM.md)、
[P21A completion report](../reports/phase21a/PHASE21A_COMPLETION.md) 和
[Phase 12–30 execution plan](PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md)。
