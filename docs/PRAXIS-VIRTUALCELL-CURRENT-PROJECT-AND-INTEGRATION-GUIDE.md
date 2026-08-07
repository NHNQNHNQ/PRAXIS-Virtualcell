# PRAXIS-VirtualCell 当前项目全景与外部集成说明

> 文档状态：`CURRENT_PROJECT_AND_INTEGRATION_GUIDE`
>
> 核对日期：2026-08-07
>
> 当前本地仓库：`/Volumes/T7/PRAXIS-virtualcell`
>
> 当前完成分支：`codex/p23-cell-interaction`
>
> DOCS-CLOSURE parent：`b02d21985bcde50cf0758d339b05b13bb3e200a2`
>
> DOCS-CLOSURE completion / P12 starting SHA：
> `b19c896202bea56f894d0ad540501331af42a40c`
>
> 已完成 work unit：`Phase 12 — Virtual Cell Model Zoo v2`；completion code SHA
> `1a5464fb0d2d9e105058f6797d92efd69783e5b2`
>
> 已完成 work unit：`Phase 13 — Model Adapter SDK`；starting SHA
> `f83c13db386cb552b3ce7a5643e5ffbead0ff573`；completion code SHA
> `744d0a28d2cfc13d1b10e85b133b6c13b9426174`；tree
> `198e623120688d3704b9312990ddaa93c9a7b0e6`
>
> 已完成 work unit：`P14E — E. coli K-12 knockout→growth contract`；starting SHA
> `0b193310009d6e4d2ebc0fc8abf95da20a56acdb`；SDK trust-boundary prerequisite
> `c3401450fd79f7829c438d6b55c1902ea2f4cf5f`；completion code SHA
> `8778e93c31c2dfe1ef0f77f06e7a80a425633736`；tree
> `fa85e049bb36f3fbd8e6d4a7503e4b5837ed7c78`
>
> 已完成 work unit：`P15E — S. cerevisiae gene-deletion→fitness contract`；starting SHA
> `0ff6870a70a04d71098a16875e633f909e31cc5a`；completion code SHA
> `62480a3951173a2aa7b006403af9b169521db138`；tree
> `64906691c4c989a843df4da97f0a93f32cd65ad2`
>
> 已完成 work unit：`P16E — Human/K562 perturbation→delta-expression contract`；starting SHA
> `d1e2e37b69784bd2f440cba34f51cfb56dcc00b2`；completion code SHA
> `9f6b14ea84cb0884b2bde2ed4c67c73aeb5a37e2`；tree
> `098cd563e3d865e080a0d121727b987e2d40ed18`
>
> 已完成 work unit：`P17 — PRAXIS Virtual Cell Brain contract`；starting SHA
> `ff525a0611901df422161a7143ebfe9d1e051008`；completion code SHA
> `16636f1b2c36e0a0fabb782a662b5b3b934891e0`；tree
> `321a59eed44c45bf2bb8798714352b3303b92e58`；状态
> `P17_CONTRACT_COMPLETE_REAL_MULTI_MODEL_ACCEPTANCE_PENDING_P18_ELIGIBLE`
>
> 已完成 work unit：`P18 — Multi-omics Virtual Cell contract`；starting SHA
> `f253664239e4b1c9665301cf1bdf4e117a3e9c31`；completion code SHA
> `626c71ffd1ce18a5adc200f6a6e376e57b269beb`；tree
> `2b570398caff6cf955d789c3cb4a7a77dc13a082`；状态
> `P18_CONTRACT_COMPLETE_REAL_MULTIOMICS_MODEL_ACCEPTANCE_PENDING`
>
> 已完成 work unit：`P19 — Controlled Pack Factory contract`；starting SHA
> `871c5a8a4265f5b8fe5c2c6e35d418644bf1c4be`；completion code SHA
> `42eabe63ea1a444d8b2ad14cecba6c9d6fa351d5`；tree
> `b4bd63833adc89bd1e30e9595d2cb6b38a3e005f`；状态
> `P19_CONTRACT_COMPLETE_REAL_EXTERNAL_FIXTURE_OPERATOR_SCIENCE_POLICY_NOT_RUN`
>
> 已完成 work unit：`P20 — Virtual Cell Training Pipeline contract`；starting SHA
> `f53e29e5722a8fe48aa2eb6fe63be01f61b5cc9a`；completion code SHA
> `a4003704b70f06eb65297ddd32e0695ae8ee146b`；tree
> `d12d64a7c8d013d8d299272eea88a4ce0431ccab`；source date epoch `1786040663`；状态
> `COMPLETE — CONTRACT_ONLY`；science `NOT_RUN`；policy `NO_NEW_DECISION`
>
> 已完成 work unit：`P21A — Virtual Cell Benchmark System`；starting SHA
> `5f3fc2d88c20e8083fb66a4c3399c5fe148241be`；completion code SHA
> `20ecc12542e5df40c90d1fc367dbe86b563478b8`；tree
> `ffcd261dd7d506d0ad852023afcba0f5c97a2d72`；source date epoch `1786050825`；状态
> `COMPLETE — SYSTEM_ONLY`；science `NOT_RUN`；policy `NO_NEW_DECISION`
>
> 已完成 work unit：`P22 — Curated Virtual Cell Registry`；actual starting docs-closure SHA
> `09792e13e29a76b5e4434507f3334eefb947789c`；P21A prerequisite code SHA
> `20ecc12542e5df40c90d1fc367dbe86b563478b8`；completion code SHA
> `bca5ad661856e8d9aa832c47f23c6ad7179ee0c9`；tree
> `f78476ac1dbe2f865e3c1bcdc71ecc512dbad22a`；source date epoch `1786056220`；branch
> `codex/p22-virtual-cell-registry`；状态 `COMPLETE — CONTRACT_ONLY`；science `NOT_RUN`；
> policy `NO_NEW_DECISION`
>
> 已完成 work unit：`P23A — Cell Interaction Evidence`；starting SHA
> `2b5c28ac152857dfa1109de41ed5d5ddc7ab06a4`；completion code SHA
> `2b894966cd00b2af2fafbf8f009566dd69f393a7`；tree
> `00bd98b0fd14091f4528115dcc66730264d5803a`；source date epoch `1786061504`；branch
> `codex/p23-cell-interaction`；状态 `COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE`；science `NOT_RUN`；policy
> `NO_NEW_DECISION`
>
> 工作树保护清单：不在本文固定；每轮从现场 `git status --short` 动态重建，任何
> 新 staged/modified/deleted/untracked 路径默认受保护
>
> 当前 Cell-first 产品代码锚点：`bf44aac25b993e49d0146ccd52dddad5c2fa14de`
>
> 下一步：没有可用 fake/no-asset scaffold 继续自动推进。可选 P23B 与真实 P24 均为
> `AUTHORIZATION_REQUIRED / NOT_RUN`；P23B 需要 intervention/estimand/assumptions，P24 需要
> exact real community assets、fixed P20/P21 model 和 write-new output window；P21B/P21C 仍为
> `AUTHORIZATION_REQUIRED / NOT_RUN`

本文是一份面向其他项目、开发团队、科研合作者和后续智能体的独立项目说明。它回答四个问题：

1. PRAXIS-VirtualCell 现在究竟是什么；
2. 已经完成了哪些可信数据、模型和运行合同；
3. 其他项目当前可以怎样安全地调用或扩展它；
4. 哪些能力尚未完成，不能被宣传为已经实现。

本文按当前源码、合同和已记录测试证据撰写。历史论文、旧项目总结和过时 UI 指南不能覆盖本文所列的当前事实。

---

## 1. 一句话定位

PRAXIS-VirtualCell 是一个以显式合同、确定性运行、可审计证据和诚实弃权为核心的多物种虚拟细胞基础设施。

它当前能够：

- 接收经过严格验证的结构化科学请求；
- 接入符合 VirtualCellPack 合同的数据；
- 检查请求、Pack、模型和执行环境之间的兼容性；
- 在存在匹配且可执行的模型时生成执行计划；
- 将 direct exact `vc.request.v2` Pack-aware 请求编译为确定性、可重放的
  Virtual Experiment DAG/Brain/decision；
- 将 exact Pack v0.3 multi-omics view 编译为 typed、content-bound、contract-only
  joint model input，同时保持明确 abstention；
- 将 P7 quarantine receipt 经显式 candidate、完整 review、strict validation 和
  registration-only operator decision 登记为可追溯的 factory-registered Pack；
- 将 exact P19 factory registration 冻结为 strict、可重放的 contract-only training job，
  通过固定 `-I -S` tiny worker 生成 safe checkpoint/result/candidate-only model identity；
- 将两个 exact P22/P19 release/Pack closures、typed unverified P18 identities、单一
  same-experiment identity 和 declared P20/P21 scorer references 编译为 P23A evidence-only
  prepared input，并对 synthetic fixture 只投影 `interaction_evidence_score`；
- 保存请求、报告、trace、provenance 和 execution identity；
- 在缺数据、缺模型、不兼容、环境不满足或超出科学范围时明确 abstain；
- 使用可选 LLM 做自然语言解析和文字解释，但不让 LLM 参与数值预测或最终裁决。

它当前**不是**：

- 上传任意原始组学数据后自动训练出预测器的平台；
- 任意物种、任意细胞都已经可预测的世界模型；
- 已经完成科学验证的通用 Virtual Cell；
- 已完成真实多模型科学验收的 Virtual Cell Brain；
- 已完成真实 multi-omics 模型、Broker/Registry resolution 或科学验收的平台；
- 上传任意文件后自动推断 taxon、清洗数据、生成 Pack 或获得模型能力的平台；
- 已运行真实 candidate training、test/external benchmark 或科学验证的平台；
- 已运行真实 sender→receiver evidence model、receiver response 或 causal interaction 的平台；
- 由 LLM 直接生成生物学数值结论的问答系统；
- 已经实现的 Community world model 或 Host–Microbiome digital twin。

当前准确的产品承诺是：

> 任意符合显式合同的数据可以制作成 VirtualCellPack 接入；只有存在匹配、可执行且
> 经过验证并获 product policy 批准的模型时才产生预测，否则明确 abstain。

### 1.1 Phase 12 完成边界

当前实现候选把 model、artifact、environment、adapter、validation evidence 和
operator-policy record 拆为独立 version/fingerprint，并把它们接入 Pack-aware
compatibility、plan 和 job identity。`vc.model-card.v1` 保持兼容，但迁移只生成
`legacy_incomplete` records；无法精确绑定现有 model identity 的 P8/P9 历史结果只
保存为 `binding_status=unbound` 的 migration receipt，不创建 evidence、policy 或
promotion，P9 `available=false` 保持不变。

Registry lifecycle 使用 append-only `cataloged/artifact_ready/revoked/superseded`
events；历史 release、job 和负结果不原地改写。现有 `praxis-vc pack list` 和
`GET /api/packs` 调用链提供 `vc.model-registry-catalog.v2` 白名单、路径脱敏只读投影，
没有新增管理写接口。

Native environment package identity 使用 canonical PEP 503 distribution name 和
显式 version；legacy `python_dependencies` 的 runtime import-module name 则按原始文本
分层保留，不能被 package normalization 合并。Native `model_version` 必须 path-safe；
unsafe legacy raw version 仍进入内部 immutable fingerprint，但所有公开投影返回
`null`，不会改写旧 card bytes 或回显不安全文本。

P12 工程已由 completion code SHA、全部约定本地测试、packaging、post-commit 核验
和完成报告收口。本阶段没有外置资产、真实模型或权重、训练、科学
benchmark/external/OOD run，也没有新的 operator promotion decision；因此工程完成
不能写成新增真实模型能力或 production promotion。

### 1.2 Phase 13 完成边界

P13 以 `f83c13db386cb552b3ce7a5643e5ffbead0ff573` 为实际起始 SHA，在
`codex/p13-model-adapter-sdk` 上以 code SHA
`744d0a28d2cfc13d1b10e85b133b6c13b9426174`、tree
`198e623120688d3704b9312990ddaa93c9a7b0e6` 完成。它新增统一
`VirtualCellModelAdapter`/`AdapterRegistry`、Broker 准备的递归不可变输入、严格输出
envelope、execution provenance 与 deterministic conformance，并复用 P5
`ModelFeatureContract`/`AlignmentReport` 和 P12 exact `AdapterIdentity`。

默认生产 registry 只包含
`predict_delta_expression → delta_expression` reference adapter；growth/fitness adapters
只存在于 conformance tests，不能被外部集成方当作 E. coli 或 yeast 生产能力。SDK
本身不猜 Pack rows、mapping、control 或 split，不补零或静默转换；合同声明
`pack_data_required`/`alignment_required` 时，缺 values+Pack 或 feature/alignment binding
会 fail closed。control/split 等额外要求必须由具体 adapter 显式实现和测试。adapter 也
不能在 prediction metadata 中写入 reserved science/policy 字段，不能签发 evidence 或
promotion。

P13 工程状态为 `COMPLETE`；science 为 `NOT_RUN`；policy 为
`NO_NEW_DECISION`。没有真实模型、数据、权重、训练、科学运行、发布或部署。完整证据见
`reports/phase13/PHASE13_COMPLETION.md`，设计与操作边界见
`docs/ADR-0010-virtualcell-model-adapter-sdk.md` 和
`docs/runbooks/VIRTUALCELL-MODEL-ADAPTER-SDK.md`。

### 1.3 Phase 14E 完成边界

P14E 以 `0b193310009d6e4d2ebc0fc8abf95da20a56acdb` 为实际起始 SHA，在
`codex/p14e-ecoli-growth-contract` 上完成 shared SDK trust-boundary prerequisite
`c3401450fd79f7829c438d6b55c1902ea2f4cf5f`，并以 code SHA
`8778e93c31c2dfe1ef0f77f06e7a80a425633736`、tree
`fa85e049bb36f3fbd8e6d4a7503e4b5837ed7c78` 冻结一个窄合同：exact
`NCBITaxon:562 / NCBITaxon:511145 / GCF_000005845.2`、GEM/medium/condition/
objective/solver/mapping identities 和一个 canonical NCBIGene knockout；task/output 为
`predict_knockout_growth / growth_ratio`，shape/unit 为 `(1,) / dimensionless`，reference
固定为 `wild_type_same_gem_medium_condition`。

P14E 新增九个 strict、frozen、fingerprinted schema：
`vc.ecoli-growth-scope.v1`、`vc.ecoli-growth-validation-protocol.v1`、
`vc.ecoli-growth-data-binding.v1`、`vc.ecoli-growth-execution-binding.v1`、
`vc.ecoli-growth-gene-mapping-binding.v1`、
`vc.ecoli-growth-compatibility-binding.v1`、
`vc.ecoli-growth-adapter-input-contract.v1`、
`vc.ecoli-growth-adapter-output-contract.v1` 和
`vc.ecoli-growth-prepared-model-input.v1`。adapter/input/output contract fingerprints
分别为 `0b26d81c99f3ed216f5dcc6c86814379b6997633c0a6c071109d3ed45918b1a9`、
`6995a1c262367bbd510a488b80b2c01a15e18cd6c32169f3036045869218edfa` 和
`bfda36704cfd82006ec0a3bd1c772d62209eb8c860b7baffae982f150955f13f`。

canonical synthetic fixture 的 component fingerprints 为：

- artifact：`435f2868ed5e86a7ea1cf5ff47463896213b4cef8f515acd731f30c34d50c283`；
- environment：`b572089b347346becb09a2915046b8cd6e55c3ba681124e5275d2250c87fa065`；
- model release：`03db9b219ea47e954a2b89cdd0fa28c6395235cd28a4b938e6aa63ec0de405ba`；
- mapping：`c355339c2450214384300aa966de130f42e64d68fa50138d9fae3d6e3fef1886`；
- execution：`832eb94872fc2ed09fbbc97368287538ca6673424f5e3928c61fc5f0699dc5ac`；
- Pack identity：`5555555555555555555555555555555555555555555555555555555555555555`；
- data binding：`93faa211ed040d378d67c82055c00f96c5af5399cf677ca986692b5c323d74a6`；
- compatibility：`b61c7d6bacf2a2ca2de76d0ced740acef4a548155c9f4e09b7e5fa891ba81878`；
- scope：`bd7bc1cf60877ee8abfeb2e8769cf1cfd6e99e34305487da09fb18e810fc996e`；
- validation protocol：`a4b0bcc46aed1586cc5a466d06422753f944043ca526a2c88ceeeef79f3a88dc`；
- prepared input：`f6b1e7f263fc0b4608fedda71475b66fa0a20e9754dbe27a27d7714730e1f344`；
- output envelope：`c7ea3e0d8d966bed09008425adc81c018be4643566e0fbe3db7fafbe7b1d6cae`；
- conformance report：`608e931a8a2b5199410b15428587ef03b9c5b6bd6b7b8fdf89ab753b1f1a752e`。

这些值只标识 synthetic test fixture，不证明外置 asset 存在、许可通过、可执行或
scientifically validated。

`EcoliK12KnockoutGrowthAdapter` 是源代码中的 local/conformance contract adapter，
不是 P13 的 dummy growth adapter，也没有进入 `DEFAULT_ADAPTER_REGISTRY`。默认 registry
仍只有 `predict_delta_expression → delta_expression`。它也不复用历史 v1
`ecoli_gem` card、`GemWrapper`、route table 或 case dispatch 形成 positive path；legacy
card 的 `available`/迁移状态不能补足 P14E 的 exact assets、environment、evidence 或
policy。

P14E 的 synthetic compatibility 固定为 `assets_verified=false`、`executable=false`、
`reason=p14r_not_authorized`。validation protocol 只是未来 P14R 的预登记合同，不是
scientific evidence。合同测试为 `71 passed`，相邻 SDK/output-flow 为 `148 passed`，
safe nine-file directed gate 为 `360 passed`，safe legacy 为
`1147 passed / 58 skipped / 105 deselected`；Ruff 与 `git diff --check` 通过。测试只使用
synthetic identity/raw dictionary，没有读取或运行 GEM、SBML、growth/essentiality data、
Cobra 或 solver。

因此 P14E 仅为 `ENGINEERING_COMPLETE`，P14 整体状态为
`ENGINEERING_COMPLETE_SCIENCE_PENDING`；P14R 仍是
`AUTHORIZATION_REQUIRED / NOT_RUN`，P14B 仍是 `NOT_RUN`。没有真实 GEM/Pack/model
execution、benchmark、external cohort、scientific evidence、operator policy、release 或
promotion。完整边界见 [ADR-0011](ADR-0011-virtualcell-ecoli-k12-growth-contract.md)、
[P14E runbook](runbooks/VIRTUALCELL-ECOLI-K12-GROWTH-CONTRACT.md) 和
[P14E completion report](../reports/phase14e/PHASE14E_COMPLETION.md)。下一 eligible
本地工程 work unit 是不依赖 P14R/P14B 正结果的 P15E contract-only 工程，
它现已完成。

### 1.4 Phase 15E 完成边界

P15E 以 `0ff6870a70a04d71098a16875e633f909e31cc5a` 为起始 SHA，在
`codex/p15e-yeast-fitness-contract` 上以 code SHA
`62480a3951173a2aa7b006403af9b169521db138`、tree
`64906691c4c989a843df4da97f0a93f32cd65ad2` 完成。它只冻结 exact
S. cerevisiae S288C / `GCF_000146045.2`、单个 complete gene deletion、SGD
systematic exact mapping，以及相对同 condition/platform matched non-deletion
control 的一个 dimensionless `fitness` scalar。

`YeastDeletionFitnessAdapter` 复用 native P12 artifact/environment/release bindings，对 finite
raw scalar 原样透传；负数和大于 `1` 的值不自动归一化或裁剪。非
success/OOD 输出必须 value-free abstain，uncertainty 为 `not_available`，公开
projection 只能在 exact prepared input 绑定后生成。adapter 是 local-only，不在
`DEFAULT_ADAPTER_REGISTRY`；默认 registry 仍只有
`predict_delta_expression → delta_expression`。

P15E compatibility 固定 `assets_verified=false`、`executable=false`、
`reason=p15r_not_authorized`。P15E contract 测试为 `98 passed`，safe directed 为
`458 passed`，safe legacy 为 `1147 passed / 58 skipped / 105 deselected`；
authoritative Ruff、format 和 diff check 通过。两个 offline/network-denied manual clean
archive 的可复现 wheel SHA-256 为
`7758c13bd5a53c74618d556b14c6e27e0492381162a9ab3364aee7dde5d2bb8d`，但它没有发布；
产品版本仍为 `1.6.0`。严格安装脚本的 cache 缺 `packaging==26.2`而 fail
closed，系统 `pip check` 又受 global environment 污染，两者都不构成 P15E 新的
全局依赖或 lock-integrity 证据。

P15R 仍是 `AUTHORIZATION_REQUIRED / NOT_RUN`，P15B/science/real assets/GEM 未运行，
policy 为 `NO_NEW_DECISION`。完整边界见
[ADR-0012](ADR-0012-virtualcell-yeast-deletion-fitness-contract.md)、
[P15E runbook](runbooks/VIRTUALCELL-YEAST-DELETION-FITNESS-CONTRACT.md) 和
[P15E completion report](../reports/phase15e/PHASE15E_COMPLETION.md)。

### 1.5 Phase 16E 完成边界

P16E 以 P15E docs-closure `d1e2e37b69784bd2f440cba34f51cfb56dcc00b2`
为起始 SHA，在 `codex/p16e-k562-perturbation-contract` 上以 code SHA
`9f6b14ea84cb0884b2bde2ed4c67c73aeb5a37e2`、tree
`098cd563e3d865e080a0d121727b987e2d40ed18` 完成。它冻结 exact Human/K562
`CVCL_0004`、GRCh38、scRNA、Ensembl 84 ordered 5,045 features，以及
`predict_delta_expression → delta_expression`。请求仍使用 core-accepted
`cell_type_name=K562`、`cell_type_id=None`，并在 attributes 绑定
`cell_identity_id=CVCL_0004`；P8 source 中的 A549 只作为 upstream metadata error
原样保存，绝不是请求 identity。

`K562GoldenPerturbationAdapter` 将 single-gene 与 ordered combination scope、record、
protocol 和 fingerprint 分开；`record_membership_verified=false`，checked-in aggregate
hash 不能证明任意外置 record membership。adapter 只允许 local registration，不在
`DEFAULT_ADAPTER_REGISTRY`；默认仍是 P13 generic delta reference adapter。raw successful
vector 必须是 5,045 个 finite JSON-safe numbers 并逐项原样透传，禁止 symbol/version
修正、ortholog、normalization、reorder、fill、impute、dedup 和 absolute→delta。非
success/OOD 必须 value-free abstain，uncertainty 固定 `not_available`，公开 projection
只能绑定 exact prepared input。

validation protocol 固定 P8 `train→train / test→validation / ood→test`、137/30/116
non-control conditions、`condition_id` leakage guard、condition-macro full-feature delta MSE、
additive ridge comparator 和 candidate-MSE-minus-additive-MSE paired CI 方向。这只是
`preregistration_not_evidence`；历史 additive result 只作 checked-in comparator reference。
P16E 没有读取 H5AD、运行 candidate/comparator、产生 MSE/CI/external/contamination
result，也没有 evidence、policy、promotion、release 或 deploy。compatibility 固定
`assets_verified=false`、`executable=false`、`reason=p16r_not_authorized`。P16R 为
`AUTHORIZATION_REQUIRED / NOT_RUN`，P16B 为 `NOT_RUN`，policy 为
`NO_NEW_DECISION`。完整边界见 [ADR-0013](ADR-0013-virtualcell-k562-golden-delta-contract.md)、
[P16E runbook](runbooks/VIRTUALCELL-K562-GOLDEN-DELTA-CONTRACT.md) 和
[P16E completion report](../reports/phase16e/PHASE16E_COMPLETION.md)。

### 1.6 Phase 17 完成边界

P17 以 P16E docs-closure `ff525a0611901df422161a7143ebfe9d1e051008` 为起始 SHA，
在 `codex/p17-virtual-cell-brain` 上以 code SHA
`16636f1b2c36e0a0fabb782a662b5b3b934891e0`、tree
`321a59eed44c45bf2bb8798714352b3303b92e58` 完成。direct exact
`vc.request.v2` Pack-aware 入口把 canonical request、cell context、Pack、plan、model、
environment、adapter、evidence、policy、step/edge 和最终 deterministic decision 绑定进
immutable Virtual Experiment DAG 与 Brain identity。Broker 只生成既有
CapabilityRegistry/ExecutionPlan，不实例化 legacy wrapper；legacy 入口仍保留且 v2
marker 不能降级进入它。

LLM 只能提交 schema-bound candidate DAG；candidate review 有独立 checksum，但不进入
权威 DAG/Brain/decision fingerprint，因而 LLM off、timeout 或 injection 不能改写权威
结果。JobStore `vc.job-execution-identity.v3` 绑定 Brain/DAG 并在 reload 时重验 request、
report、provenance、plan、step 和 capability identities。测试临时目录中的第五 taxon
Danio rerio（NCBITaxon:7955）只证明 species-neutral contract compilation，从未注册为生产 Pack/release，也
没有新增物种分支。

当前 registry 精确为 5 releases、0 native、0 promoted。故没有真实多模型 execution，
每个真实 P17 direct-v2 请求均形成 identity 完整的 abstain；science `NOT_RUN`，policy
`NO_NEW_DECISION`，状态是 contract complete、real multi-model acceptance pending。
engineering contracts、tests 与 artifact-ready packaging 均已收口。验证为 P17
`41 passed`、adjacent `377 passed / 1 skipped`、safe gate
`1487 passed / 48 skipped / 387 deselected`，Ruff passed。exact code commit 的两次
clean-archive wheel byte-identical：`1,118,410` bytes、SHA-256
`bd3752b90a6d8e4d7a825b2f4925d00eb7e5204021fef3404b67e88f7a0e23bd`、
`366` entries、`14` React entries、`0` tests、`0` AppleDouble，并包含 Brain 模块；
official strict build 仍因 offline cache 缺 `packaging==26.2` fail closed。未运行
P14R/P15R/P16R/B，未 push、release、deploy 或 version bump。完整边界见
[ADR-0014](ADR-0014-virtual-cell-brain.md)、
[P17 runbook](runbooks/VIRTUALCELL-VIRTUAL-EXPERIMENT-DAG.md) 和
[P17 completion report](../reports/phase17/PHASE17_COMPLETION.md)。

### 1.7 Phase 18 完成边界

P18 以 P17 docs-closure `f253664239e4b1c9665301cf1bdf4e117a3e9c31` 为起始 SHA，
在 `codex/p18-multiomics-cell-state` 上以 code SHA
`626c71ffd1ce18a5adc200f6a6e376e57b269beb`、tree
`2b570398caff6cf955d789c3cb4a7a77dc13a082` 完成。`vc.multiomics-model-input.v1`
把 exact request、Pack v0.3 manifest、ordered required/optional modality slots、逐层
feature contract/alignment report、observation semantics、view/join/missingness identity 与
matrix storage/content fingerprint 绑定为严格合同。paired 输入只接受相同真实行；
partially-paired 只使用真实交集或显式 mask，不补行、补零、fill、impute 或 normalization。

Request target 保留 Pack 源科学身份；只有 identity 或经 Pack JSON mapping asset 证明的
一对一 alias 可进入模型 feature identity。target 被 drop、aggregate、多对一 collapse、
跨 modality/namespace 或未声明时均 fail closed。Prepared input 使用不可变 byte-backed
snapshot，并在消费边界重新核对 shape、storage 和 content fingerprint；矩阵值不序列化进
JSON。嵌入的 request、Pack、contract、adapter marker、observation/view/join/missingness
和 alignment identities 均重新验证。

验证为 focused `44 passed`、adjacent `259 passed`、safe gate
`1531 passed / 48 skipped / 387 deselected`；Ruff、format、py_compile 和 diff checks
通过。两次 offline clean-archive wheel byte-identical：`1,132,811` bytes、SHA-256
`015724a90656706c0441e4f4f873ee51f8db87dfaae9de35a3e841e7c70b2b7c`、`367`
entries、`14` React entries、`0` tests、`0` AppleDouble。可选 `mudata` suite 未安装而
无法 collect；共享环境 `pip check` 冲突不是通过证据。

`adapter_identity` 由调用方声明，`ModelBrokerAgent` 只是
`identity_only_not_registry_evaluated` marker；P18 没有调用 Broker、CapabilityRegistry、
wrapper 或 model。registry 仍为 5 releases / 0 native / 0 promoted，science
`NOT_RUN`、policy `NO_NEW_DECISION`，未运行真实数据/model/benchmark、训练、GPU、
Golden/GEM/Norman、push、release 或 deploy。完整边界见
[ADR-0015](ADR-0015-multiomics-model-input.md)、
[P18 runbook](runbooks/VIRTUALCELL-MULTIOMICS-MODEL-INPUT.md) 和
[P18 completion report](../reports/phase18/PHASE18_COMPLETION.md)。

### 1.8 Phase 19 完成边界

P19 从 P18 docs-closure
`871c5a8a4265f5b8fe5c2c6e35d418644bf1c4be` 开始，在
`codex/p19-controlled-pack-factory` 以 completion code
`42eabe63ea1a444d8b2ad14cecba6c9d6fa351d5` / tree
`b4bd63833adc89bd1e30e9595d2cb6b38a3e005f` 完成 contract-only Controlled Pack Factory。

Factory 把 exact P7 receipt/payload、candidate file tree/manifest/source asset、全部 metadata
claims、versioned mapping summary、review confirmations、full validation report、named
registration-only decision 和 `FactoryRegisteredPackV1` 分别 fingerprint。Actual payload 必须
是 Pack 的 matrix/multi-omics data asset；系统不做 normalization、fill、imputation、
deduplication、reorder、random split 或 identifier conversion。

P7 human/mouse/yeast/bacteria species 全部只是 routing hint。Exact taxon 只来自 candidate
manifest 并由 reviewer 对 exact claim 确认；coarse bacteria receipt 不推断 *E. coli*。
`taxon_review_binding` 不把 receipt 升级为 taxonomy authority。

Registration 强制显式 absolute index 和由 `PackFactoryStore.create()` write-new 初始化、
带 exact `.factory-store.json` bytes `{"schema_version":"vc.pack-factory-store.v1"}\n` 的
append-only store；普通既存目录拒绝。
`vc.pack-index.v2`
兼容读取 v1；legacy v1 entry 保持 readable、factory provenance 为 null，且不会被追认为
factory-approved。旧 path-only register 已退役。Index 写入 registration expectation 后、store
registration append 前是 pending：consumer 回查不到完整 store chain 时一律 invalid/fail
closed，双向一致后才 committed。

公共面只有 root-free、reviewer/operator raw ID/rationale/reason-redacted
`GET /api/pack-factory`，没有 HTTP 管理写 route；UI 分开
Quarantine、Candidate、Factory-registered、Model-compatible 和 Executable。Factory record
固定 `model_compatible=null`、`executable=false`，具名 registration decision 也不是 model
operator policy。

Git 外 real tiny fixture、exact new output root、真实 operator/science/policy 均未运行。
P19 没有 training、checkpoint、model card、benchmark、evidence 或 promotion。完整边界见
[ADR-0016](ADR-0016-controlled-pack-factory.md)、
[P19 runbook](runbooks/VIRTUALCELLPACK-CONTROLLED-PACK-FACTORY.md) 和
[P19 completion report](../reports/phase19/PHASE19_COMPLETION.md)。

### 1.9 Phase 20 完成边界

P20 从 P19 docs-closure `f53e29e5722a8fe48aa2eb6fe63be01f61b5cc9a`
开始，在 `codex/p20-training-pipeline` 以 completion code
`a4003704b70f06eb65297ddd32e0695ae8ee146b` / tree
`d12d64a7c8d013d8d299272eea88a4ce0431ccab`（source date epoch `1786040663`）完成
contract-only Virtual Cell Training Pipeline。

入口只接受 explicit absolute `vc.pack-index.v2` 所引用、可由 P19 append-only store 完整
重放的 committed registration。Stored P19 full candidate tree 是历史 provenance；live
open/validation 只覆盖 exact manifest、split，以及 leakage audit 通过后 job 冻结且实际
消费的 train feature/label bytes。Validation/test/external、uploaded code 和其他未消费
assets 从不打开。

训练 job 双向绑定 Pack、feature/alignment、split/leakage、trainer/code/environment、seed、
hyperparameters、resource limits 和 candidate model identity。固定 trusted tiny worker 从私有
临时副本以 Python `-I -S` 运行；这是依赖/导入隔离和 source-hash 边界，不是 OS sandbox
声明。Checkpoint 是 canonical safe JSON，经 write-new staging、size/hash/cross-binding 重验和
atomic no-replace commit 后才成为 candidate-only bundle；失败、cancel、timeout 和发布竞态均
fail closed。

P20 只运行 repository tiny fixtures，没有真实 candidate training、test/external read、GPU、
network、benchmark/evidence、registry promotion、release 或 deploy。Science `NOT_RUN`，policy
`NO_NEW_DECISION`；candidate/cataloged 不等于 scientifically validated、promotion eligible 或
production promoted。完整边界见 [ADR-0017](ADR-0017-virtual-cell-training-pipeline.md)、
[P20 runbook](runbooks/VIRTUALCELL-TRAINING-PIPELINE.md) 和
[P20 completion report](../reports/phase20/PHASE20_COMPLETION.md)。

### 1.10 代码与外部资产许可

仓库源码在 `pyproject.toml` 中声明为 MIT License。公共数据集、数据库下载、模型权重、checkpoint 和其他外置科研资产保留各自的许可、引用和使用限制；不能因为仓库代码使用 MIT，就推定这些外部资产也可按 MIT 再分发。

其他项目在发布 Pack、模型或复现实验时，应分别保存：

- 源代码许可；
- dataset terms 和 citation；
- model/weight license；
- Pack manifest 中的 provenance；
- 不能进入发行物的受限资产清单。

---

## 2. 为什么建立这个项目

多数虚拟细胞演示把一次自然语言问答直接连接到一个固定模型。这样可以快速展示结果，但很难回答以下科研问题：

- 输入数据来自哪里，是否被修改过；
- 模型是否真正适用于这个物种、细胞、组学和任务；
- 模型权重、软件环境和特征顺序是否与验证时一致；
- 输出是模型预测、规则建议、历史证据，还是 LLM 生成的文字；
- 当条件不满足时，系统是否会停止，而不是生成看似合理的答案；
- 多个项目是否能在不修改核心 runtime 的情况下接入新数据和新模型。

PRAXIS-VirtualCell 把这些问题视为系统的第一等对象。项目的核心贡献不是宣称“所有细胞都能预测”，而是建立一个可插拔、可验证、可追踪、可拒绝的运行基座。

---

## 3. 核心可信原则

### 3.1 合同优先

数据、请求、特征映射、模型能力、执行环境、兼容性报告、执行计划和运行结果都有显式版本化合同。未知字段和不支持的版本在关键边界上 fail closed。

### 3.2 数据字节不被静默改写

数据适配层不擅自：

- 归一化；
- 补零；
- 去重；
- 改写 feature ID；
- 改变源顺序；
- 把缺失 modality 伪造成存在；
- 生成随机 split；
- 执行未声明的同源基因转换。

如果模型需要这些操作，必须由显式、版本化并带 provenance 的转换合同表达。

### 3.3 兼容不等于有效

系统严格区分：

```text
数据存在
≠ Pack 存在
≠ Pack 有效
≠ 模型兼容
≠ 环境兼容
≠ 可以执行
≠ benchmark 通过
≠ 科学验证通过
≠ 正式推广
```

### 3.4 默认诚实弃权

在 Pack-aware 可信路径中，没有匹配模型、缺权重、缺依赖、缺输出 adapter、超出 OOD 边界或科学门槛未通过时，正确结果是空执行计划或 abstain，而不是 mock prediction。当前 legacy demo 路径的差异在第 4.6 节单独说明。

### 3.5 LLM 不拥有科学真相

LLM 可以：

- 把自然语言解析为候选请求；
- 提示缺失字段；
- 在确定性结果之后生成文字解释；
- 帮助用户阅读 trace 和 provenance。

LLM 不可以：

- 决定 Pack 是否有效；
- 修改真实数据；
- 生成或覆盖模型数值预测；
- 判断模型是否兼容；
- 决定可靠性和 abstain；
- 改写 fingerprint、provenance 或 execution identity；
- 决定科学模型是否 promotion。

所有运行结果都固定记录：

```json
{
  "llm_used_for_prediction": false
}
```

---

## 4. 当前产品形态：Cell-first 科研入口

当前网页已经从传统的流程配置界面改为白色、Cell-first、ChatGPT 类科研入口。

实际可见流程是：

```text
进入网站
  ↓
选择 Cell Context preset
  ↓
输入自然语言科学问题
  ↓
解析并校验结构化请求
  ↓
确定性 runtime 自动路由和运行
  ↓
直接显示报告或 abstain
  ↓
查看 execution identity、证据、trace 和 provenance
```

### 4.1 首页

首页先展示四个常用 Cell Context：

- Human K562；
- Human PBMC；
- Mouse T cell；
- E. coli。

它们是用户提问时的上下文预设，不是持久化 Virtual Cell，也不代表已经绑定了数据 Pack 或经过验证的模型。

### 4.2 Data Center

Data Center 当前是可搜索的 Cell Context 背景库，支持：

- human；
- mouse；
- yeast；
- bacteria；
- 物种筛选；
- 12 个后端维护的 cell presets；
- 同物种 dataset 和 Pack 状态的只读展示。

Data Center 中显示的 dataset 数量和 Pack 数量只是背景信息。当前 UI 明确标注这些对象没有自动绑定到所选 cell。

### 4.3 对话区

选择 cell 后显示单一聊天框和该 cell 的示例问题。点击示例只会填入输入框，不会自动执行。

前端会把所选 species 和 cell type 作为显式结构化上下文交给后端解析。LLM 解析成功时可以继续运行；确定性 fallback 解析需要用户确认结构化解释后再执行。

### 4.4 报告区

当前报告界面包含七类信息：

1. 报告；
2. 预测；
3. 模块路由；
4. 数据与执行身份；
5. 证据；
6. 运行轨迹；
7. 溯源。

可下载的内容包括结构化报告、文字解释和 Markdown 报告。

### 4.5 旧五阶段 Workspace 的真实状态

旧的 `Ask → Review → Route → Run → Results` 组件仍保留在前端源码中，但当前 `App.tsx` 没有挂载它。当前产品入口只编排：

```text
chat
data-center
```

因此其他项目不应根据过时的用户指南声称“五阶段 Workspace 是当前可见 UI”。

### 4.6 当前 UI 的关键限制

当前 Chat 前端创建 job 时没有传入 `pack_id + pack_version`。因此：

- Cell preset 只提供 context；
- 当前聊天走 legacy adapter 路径；
- 它不会因为 Data Center 中存在同物种 Pack 就自动绑定该 Pack；
- 后端 API 虽已支持显式 Pack identity，但当前主 UI 尚未使用这一能力。

legacy 路径仍可能枚举明确标记的 `MockLinear`、`MockCPA`、`MockGEARS` 或窄域 case runner。它与 P6 Pack-aware 路径的语义不同：

```text
legacy direct chat
  可以产生明确标记为 mock/advisory 的演示报告

Pack-aware runtime
  没有可执行模型时不得回退到 mock，必须 abstain
```

因此 UI 中的“Report generated”只表示后端完成了一次可审计运行并生成报告，不等于真实模型已经完成科学预测。

这也是下一阶段真实模型闭环必须解决的关键接缝。

---

## 5. 系统架构

```mermaid
flowchart TD
    U["用户或外部项目"] --> REST["FastAPI / vc.api.v1"]
    U --> CLI["praxis-vc CLI"]
    U --> PY["Python 接口"]

    UI["Cell-first React UI"] --> REST
    DC["Data Catalog / Quarantine Upload"] --> REST

    REST --> PARSE["自然语言解析与请求校验"]
    CLI --> PARSE
    PY --> PARSE

    PARSE --> REQ["版本化 Request Contract"]
    REQ --> BROKER["Capability Registry + Model Broker"]
    PACK["VirtualCellPack + Feature Contract"] --> BROKER
    MODEL["ModelCard + P12 Registry v2 identity candidate"] --> BROKER
    ENV["Environment Snapshot"] --> BROKER

    BROKER --> COMP["Compatibility Report"]
    COMP --> PLAN["Deterministic Execution Plan"]
    PLAN -->|executable| RT["Deterministic Runtime"]
    PLAN -->|not executable| ABS["Abstain"]

    RT --> JOB["Immutable Job Artifacts"]
    ABS --> JOB
    JOB --> REPORT["Report / Evidence / Trace / Provenance"]

    LLM["Optional LLM"] -. "parse / narrative only" .-> PARSE
    LLM -. "post-hoc interpretation only" .-> REPORT
```

### 5.1 信任边界

```text
数据真实性       → Pack validator / hash / schema
模型适用性       → CapabilityRegistry / ModelBroker
执行可能性       → environment / asset / dependency / adapter checks
数值预测         → model or mechanism adapter
可靠性与 abstain → deterministic governance
文字解释         → deterministic template or optional LLM
```

LLM 位于科学执行链之外。

---

## 6. 核心对象模型

| 对象 | 含义 | 当前状态 |
|---|---|---|
| Cell Context preset | 物种和 cell type 的提问入口 | 已实现，只读展示上下文 |
| Dataset catalog record | 公共组学资源的元数据和文件身份 | 已实现 |
| Upload receipt | 用户上传原始字节的 quarantine 收据 | 已实现，不是 Pack |
| Pack candidate/review/validation | receipt-bound authoring、逐项确认与完整 strict report | P19 contract-only 已实现；不是 registration 或 science |
| Factory registration | exact receipt→decision chain 和 append-only store/index provenance | P19 contract-only 已实现；不是模型兼容或执行 |
| VirtualCellPack | 数据、语义、资产和 provenance 的版本化包 | 已实现 v0.1–v0.3 |
| Feature contract | 模型期望的 feature namespace、顺序和映射要求 | 已实现 |
| ModelCard | 模型能力、输入、输出、资源、OOD 和 wrapper 合同 | v1 保持兼容 |
| Model Registry v2 identities | model release、artifact、environment、adapter、evidence、operator policy | P12 工程完成；不代表科学验证或 promotion |
| Environment snapshot | 依赖、资源、adapter 和运行环境状态 | v1 保留；Pack-aware v2 绑定 exact environment identity |
| Compatibility report | Pack × request × model × environment × adapter × evidence × policy 检查结果 | v1 保留；Pack-aware v2 工程完成 |
| Execution plan | 可执行步骤及其 fingerprint | v1 保留；Pack-aware v2 工程完成 |
| Job execution identity | 本次运行绑定的 Pack、release、artifact、environment、adapter、evidence、policy 和 compatibility identity | v1 保留；v2 工程完成 |
| Training job/result/checkpoint | exact P19 registration、split/leakage、feature、code/environment 和 candidate artifact 的 contract-only identity | P20 工程完成；只验证 tiny deterministic runner，不是 science evidence |
| Persistent Virtual Cell | cell + dataset + Pack + model 的持久化产品对象 | 尚未实现 |
| Community model runtime | 多成员动态和交换预测 | 只有抽象合同，尚无真实模型 |

---

## 7. 状态语义：其他项目必须保持的区分

P19 数据接入的五层必须单独展示：

| 层 | 唯一含义 | 不能推出 |
|---|---|---|
| Quarantine | 原始上传 bytes/receipt identity | Pack 或 exact taxon truth |
| Candidate | operator-authored manifest/mapping/metadata proposal | review、validation 或 registration |
| Factory-registered | exact review/report/registration decision 已双向提交到 store/index | model compatibility、science 或 policy |
| Model-compatible | exact request×Pack×model 当次兼容裁决 | environment/adapter ready 或 execution |
| Executable | exact request 的完整运行门满足 | benchmark quality、scientific validity 或 promotion |

前三级属于 P19 ingestion，后两级仍由既有 request/model/environment/adapter runtime 逐次
裁决；Factory catalog 固定后两级为 `null/not evaluated` 与 `false`。

以下五层不是自动递进的状态链：

| 层 | 状态 | 唯一含义 |
|---|---|---|
| Pack | `pack_valid` | manifest、bytes、hash 和科学语义合同通过 |
| Registry | `cataloged / artifact_ready / revoked / superseded` | 身份登记、资产可取用或未来执行 policy；不创建科学结论 |
| 每次请求计算 | `model_compatible / environment_compatible / executable` | exact request×Pack×model×environment×adapter 当次满足 |
| Scientific evidence | `benchmark_passed / scientifically_validated / promotion_eligible` | exact protocol/scope 的不可变科学结果 |
| Product policy | `production_promoted` | 具名 operator 引用 exact evidence 作出的窄域产品决定 |

`available=true`、Pack/model card 存在、兼容成功、代码路径、smoke、UI 或 LLM 评价
都不能推导科学或产品状态。operator decision 不能把
`scientifically_validated=false` 改成 true；registry 也不能创建 evidence。
撤销只影响未来运行，不改写历史 job。

P12 已补入独立 artifact、environment、adapter、evidence 和 operator-policy record
identity，并让 Pack-aware runtime 对 exact 完整绑定 fail closed；P13 已在其上完成
严格 Adapter SDK 和 delta reference path；P14E/P15E/P16E 分别冻结了 local-only
E. coli growth、S288C deletion-fitness 和 K562 Golden delta-expression 合同。这些
work units 均已有 completion code SHA，但仍只是本地 engineering-complete、未发布状态；
P14E/P15E/P16E 都明确
`executable=false`。P6-era v1 合同继续
兼容，不能与 v2 完整治理混称；软件发布、科学 evidence 与 product policy 仍分别治理。
P17 在这些边界之上完成 deterministic DAG/Brain contract，但没有把 0 promoted
capabilities 改写成真实多模型能力；所有真实 P17 direct-v2 请求继续 abstain。
P18 继续复用 Pack v0.3、feature alignment 和 Adapter identity，完成 typed joint input
合同；它没有把 caller-declared marker 改写成 Broker/Registry compatibility 或真实模型能力。
P19 在更早的数据接入边界增加受控 registration provenance；registration-only operator
decision 不是 P12 model operator policy，也不能生成 evidence/promotion。
P20 在该 committed registration 上冻结 contract-only training job/checkpoint/result/candidate
identities；candidate/cataloged 仍不是 benchmark、science evidence 或 production policy。
P21A 在其上冻结 benchmark/evidence contract；P22 再把既有 P19/P12/P21B/P21C identities
组合为独立 curated release closure。P22 `cataloged` 只表示 curator lifecycle，绝不等于
installed、compatible、executable、validated 或 promoted；默认 P22 registry absent/empty，
而 P12 registry 仍是 5 legacy / 0 native / 0 promoted，两者不可混称。
P23A 又在这一边界上冻结 directed interaction evidence contract：它可重验 synthetic P22/P19
release/Pack content closure 和 typed P18/P20/P21 declared identities，但所有 registry、asset、linkage、
execution、science 与 policy flags 固定为 false。唯一 projection 是 supplied synthetic fixture 的
`interaction_evidence_score`；它不是 receiver response、effect size、因果结论或真实 model output。

---

## 8. P0–P23A 已完成工程工作

### Phase 0：可信边界和确定性基线

- 审计 request、runtime、SpeciesBrain、route、case、model zoo、Report 和 ActiveLearning；
- 定义 Pack 有效、模型兼容和科学验证的分层状态；
- 修复 Report request 丢失；
- 修复 ActiveLearning `genetic_hub@:unspecified`；
- 冻结确定性报告和测试基线。

### Phase 1：严格请求合同

- 建立版本化 species、cell、modality、dataset、perturbation 和 task 域；
- nested JSON 通过验证后不可变；
- 未知字段 fail closed；
- 保留 legacy request 到严格请求合同的显式转换。

### Phase 2：VirtualCellPack 基础合同

- 建立 `vc.pack.v0.1`；
- 绑定 root-relative path、size 和 SHA-256；
- 验证 license 和 taxon；
- 拒绝 traversal、绝对路径、逃逸 symlink 和坏 hash。

### Phase 3：H5AD / AnnData 适配

- backed、只读访问；
- 保持 observations、features 和稀疏矩阵的源顺序；
- 不静默归一化、补零、去重、改 ID 或随机 split。

### Phase 4：标准科学语义

- 建立 `vc.pack.v0.2`；
- 增加 taxon、assembly、cell identity/state/context；
- 增加 condition、control、unit、split 和 leakage 语义；
- 支持 Cellosaurus/local CURIE 和 canonical key；
- 收紧 legacy 和 MCP fail-closed 边界。

### Phase 5：多组学和特征对齐

- 建立 `vc.pack.v0.3`；
- 支持 H5MU；
- 支持完全配对和部分配对多组学；
- 不为缺失 modality 造行或 impute；
- 建立 `vc.model-feature-contract.v1`；
- 记录显式 mapping 和 alignment provenance。

### Phase 6：模型能力运行时

- 严格 ModelCard；
- CapabilityRegistry；
- ModelBroker；
- compatibility report；
- deterministic execution plan；
- 检查 Pack × request × model × environment；
- 缺模型、资产、依赖或 adapter 时生成空 plan 或 abstain。

当前通用 plugin output adapter 只支持：

```text
predict_delta_expression → delta_expression
```

### Phase 7：数据门户

- 建立 human、mouse、yeast、bacteria 数据目录；
- 当前固定为 4 个 dataset、5 个文件、总计 27,823,623 bytes；
- allowlisted 下载；
- 每次下载前重验路径、大小和 hash；
- bearer token、单文件限额和总 quota；
- byte-preserving quarantine upload；
- 上传收据不是 Pack，也不会自动注册或预测。

### Phase 8：产品 Pack 和 Golden Norman

- 三个内置 tiny Pack：human、mouse、bacteria；
- Pack inspect、validate、register、list、compatibility、run CLI；
- Pack 只读 API；
- job 绑定不可变 Pack/model fingerprint；
- Golden Norman/K562 Pack：91,205 × 5,045；
- 三个简单 baseline 和冻结评估；
- 没有运行 GEARS；
- `scientifically_validated=false`。

### Phase 9：OOD 和外部验证

- IID；
- perturbation；
- combination；
- cell type；
- donor；
- dataset/platform；
- species；
- dose/time；
- grouped biological-unit/replicate leakage audit；
- GSE67402 → GSE94117 无适配外部验证。

关键负结果：

```text
candidate MSE  = 1.0603835779
no-change MSE  = 1.0533347059
```

candidate 没有胜过预声明 no-change baseline，因此：

```text
available = false
scientifically_validated = false
```

该负结果被保留，不能用后续 UI 或模型卡状态覆盖。

### Phase 10：CommunityPack 合同

- 建立 `vc.community-pack.v1`；
- E. coli 和 S. cerevisiae tiny member Packs；
- abundance、medium、compartment、time、well-mixed 和 metabolite namespace；
- citation、ID、单位冲突检查；
- 单成员等价检查；
- toy exchange 的声明量精确守恒；
- `CommunityModelAdapter` 抽象合同。

当前没有真实 Community model。正确结果固定为：

```json
{
  "prediction": null,
  "abstain": true,
  "reason": "community_model_unavailable"
}
```

### Phase 11A：数据中心化产品骨架

Phase 11A 曾建立 Dashboard、Organisms、Datasets、VirtualCellPacks、Virtual Cells
和 Agent Runs 的数据中心化前端骨架。它是当前 Git 历史的一部分，产品叙事随后在
同一 Phase 的 UI 收口中改为 Cell-first。

### Phase 11B：Cell-first 正式入口

- 白色产品风格；
- 首页先选择 Cell；
- 常用 Cell presets；
- Data Center 作为 Cell Context 背景库；
- ChatGPT 类单一聊天框；
- 每个 cell 的示例问题；
- 自动解析和运行；
- 直接生成报告或 abstain；
- 展示 execution identity、证据、trace 和 provenance。

Phase 11B 完成的是可信入口，不是“cell 与数据、Pack、模型已经形成可执行绑定”。
该边界没有被 P12 改写。

### Phase 12：Virtual Cell Model Zoo v2（`COMPLETE`）

P12 从 `b19c896202bea56f894d0ad540501331af42a40c` 开始，在
`codex/p12-model-registry-v2` 上以
`1a5464fb0d2d9e105058f6797d92efd69783e5b2` 完成：

- model artifact、environment、adapter、validation evidence、operator policy、
  release 和 lifecycle event 的独立不可变身份；
- Pack-aware v2 compatibility、execution plan 和 job execution identity；
- `vc.model-card.v1` 到 `legacy_incomplete` v2 records 的保守迁移；
- P8/P9 无法 exact model-bind 的 evidence 只作为 `unbound` migration receipt；
- append-only catalog/readiness/revoke/supersede history；
- 现有 Pack list/API 的路径脱敏、字段白名单 Model Registry v2 投影。

P12 没有新增、下载或运行真实权重，没有训练或科学验证，没有新的 operator promotion
decision，也没有管理写 API。这里的 `COMPLETE` 只表示工程合同完成。

### Phase 13：Model Adapter SDK（`COMPLETE`）

P13 从 P12 completion docs SHA
`f83c13db386cb552b3ce7a5643e5ffbead0ff573` 开始，以
`744d0a28d2cfc13d1b10e85b133b6c13b9426174` 完成：

- 六个 versioned schema：input/output contracts、prepared input、output envelope、
  execution provenance 和 conformance report；
- 按 exact task/output 注册、按 P12 identity fingerprint 绑定的 adapter registry；
- Broker-only prepared input 与 wrapper-only consumption；
- strict finite/shape/unit/uncertainty/OOD/abstain/provenance 校验；
- delta-expression reference adapter 与 P0/v1/legacy compatibility；
- growth/fitness test-only conformance，不进入默认生产 registry。

P13 没有运行真实 science，也没有作 operator decision。

### Phase 14E：E. coli K-12 knockout→growth contract（`COMPLETE`）

P14E 从 P13 docs-closure SHA
`0b193310009d6e4d2ebc0fc8abf95da20a56acdb` 开始，在 shared SDK prerequisite
`c3401450fd79f7829c438d6b55c1902ea2f4cf5f` 之后，以
`8778e93c31c2dfe1ef0f77f06e7a80a425633736`、tree
`fa85e049bb36f3fbd8e6d4a7503e4b5837ed7c78` 完成：

- exact K-12 MG1655 strain/assembly、GEM、medium、condition、objective、solver、Pack 和
  NCBIGene→GEM mapping identity contracts；
- 一个 canonical NCBIGene knockout 到一个 dimensionless `growth_ratio` 的 strict input/
  output contract；
- typed-negative compatibility：`assets_verified=false`、`executable=false`、
  `reason=p14r_not_authorized`；
- prepared-bound envelope/projection、OOD/value-free abstain 和 deterministic synthetic
  conformance；
- local `EcoliK12KnockoutGrowthAdapter`，明确不加入默认 adapter registry；
- flux 只允许作为未来独立 solver trace，不是公开产品输出。

这里的 adapter 不是 P13 测试 dummy，也不是历史 `ecoli_gem`/`GemWrapper` 的生产接线。
P14E 没有读取或执行真实 GEM/SBML/data，没有运行 Cobra、solver、benchmark 或 external
science，没有生成 evidence/policy，也没有 release 或 promotion。P14R 与 P14B 保持
未授权/未运行。P15E 不依赖这些正结果，且已作为独立 contract-only
work unit 完成。

### Phase 15E：S. cerevisiae deletion→fitness contract（`COMPLETE`）

P15E 从 P14E docs-closure SHA
`0ff6870a70a04d71098a16875e633f909e31cc5a` 开始，以
`62480a3951173a2aa7b006403af9b169521db138`、tree
`64906691c4c989a843df4da97f0a93f32cd65ad2` 完成：

- exact S288C strain/assembly、condition/control/assay/platform、target universe 和 SGD
  systematic mapping contracts；
- single complete gene deletion 到一个 dimensionless `fitness` scalar，reference 为同
  condition/platform matched non-deletion control；
- native P12 artifact/environment/release bindings 和 typed-negative compatibility：
  `assets_verified=false`、`executable=false`、`reason=p15r_not_authorized`；
- finite scalar 原样透传，不对负数或 >1 数值做静默处理；
- `not_available` uncertainty、OOD/non-success value-free abstain 和 prepared-only
  public projection；
- local `YeastDeletionFitnessAdapter`，不加入默认 adapter registry。

P15E 没有读取或运行真实 deletion screen/model/GEM，没有 science run、
evidence/policy、release 或 promotion。P15R 与 P15B 保持未授权/未运行。
P16E 不依赖这些正结果，且已作为独立 contract-only work unit 完成。

### Phase 16E：Human/K562 Golden perturbation→delta-expression contract（`COMPLETE`）

P16E 从 P15E docs-closure SHA
`d1e2e37b69784bd2f440cba34f51cfb56dcc00b2` 开始，以
`9f6b14ea84cb0884b2bde2ed4c67c73aeb5a37e2`、tree
`098cd563e3d865e080a0d121727b987e2d40ed18` 完成：

- exact Human/K562 `CVCL_0004`、GRCh38、scRNA、Ensembl 84、P8 Pack/manifests、
  split controls 和 5,045 ordered feature identities；
- generic single-gene / ordered two-gene combination record contract，两个 scope 独立；
- native P12 release/artifact/environment binding 和 typed-negative compatibility：
  `assets_verified=false`、`executable=false`、`reason=p16r_not_authorized`；
- native delta-expression vector 原样透传，禁止任何隐式 ID 或数值转换；
- additive ridge comparator、paired CI sign、validation-only tuning、external/OOD 和
  leakage 的 evidence-neutral preregistration；
- `not_available` uncertainty、OOD/non-success value-free abstain 和 prepared-only
  public projection；
- local `K562GoldenPerturbationAdapter`，不加入默认 adapter registry。

P16E 只读取小型 checked-in YAML/JSON manifests，没有打开 H5AD 或运行 Golden
benchmark/candidate/additive ridge，没有产生 scientific evidence 或 policy，也没有
release、promotion 或 deploy。P16R 为 `AUTHORIZATION_REQUIRED / NOT_RUN`，P16B 为
`NOT_RUN`。

### Phase 17：PRAXIS Virtual Cell Brain contract（`CONTRACT_COMPLETE`）

P17 从 P16E docs-closure SHA `ff525a0611901df422161a7143ebfe9d1e051008`
开始，以 `16636f1b2c36e0a0fabb782a662b5b3b934891e0`、tree
`321a59eed44c45bf2bb8798714352b3303b92e58` 完成：

- direct exact request-v2 Pack-aware contract path，legacy 路径保留；
- immutable Brain、deterministic DAG/decision、step/edge 与 plan identity；
- 复用 CapabilityRegistry、plan-only ModelBroker 和 ExecutionPlan；
- non-authoritative LLM candidate review，不影响权威 fingerprint/verdict；
- conflict/partial/abstain/final-verdict governance 与 JobStore v3 cross-binding；
- test-only Danio rerio fifth taxon fixture，不进入生产注册。

当前 registry 为 5 releases / 0 native / 0 promoted，因此 real multi-model acceptance
pending，所有真实 P17 direct-v2 请求 abstain；science `NOT_RUN`、policy `NO_NEW_DECISION`。

### Phase 18：Multi-omics model input contract（`CONTRACT_COMPLETE`）

P18 从 P17 docs-closure SHA `f253664239e4b1c9665301cf1bdf4e117a3e9c31`
开始，以 `626c71ffd1ce18a5adc200f6a6e376e57b269beb`、tree
`2b570398caff6cf955d789c3cb4a7a77dc13a082` 完成：

- exact Pack v0.3 + exact request + ordered required/optional slots；
- 每层独立 feature alignment/report 与 identity/alias-only target proof；
- paired/partially-paired real-row join 和 explicit missingness mask；
- observation/view/join/missingness 与 matrix storage/content identities；
- defensive runtime snapshots 和 contract-only abstention；
- Broker/Registry/wrapper/model 未调用，真实 multi-omics acceptance pending。

### Phase 19：Controlled Pack Factory（`CONTRACT_COMPLETE`）

P19 从 P18 docs-closure SHA
`871c5a8a4265f5b8fe5c2c6e35d418644bf1c4be` 开始，完成：

- receipt/candidate/review/validation/decision/registration/supersession 独立 identities；
- actual source payload、完整 metadata confirmation、identity-only mapping 与 full report；
- explicit append-only store + absolute `vc.pack-index.v2`，兼容读 v1；
- path-only register retirement 与 pending→committed consumer fail-closed；
- root-free、reviewer/operator ID/rationale/reason-redacted read-only API 和五层 UI projection；
- 全部 science/training/checkpoint/evidence/promotion flags 保持 false。

Final code/tree 是 `42eabe63ea1a444d8b2ad14cecba6c9d6fa351d5` /
`b4bd63833adc89bd1e30e9595d2cb6b38a3e005f`；focused `23 passed / 1 skipped`，combined
focused+adjacent `108 passed / 1 skipped`，safe `1,554/49/387`，legacy `1,143/58/105`；
reproducible wheel `1,154,421` bytes / `1231f948e6f5...` / `368` entries。Real external
fixture/output root/operator/science/policy 未运行。

### Phase 20：Virtual Cell Training Pipeline（`COMPLETE — CONTRACT_ONLY`）

P20 从 P19 docs-closure SHA `f53e29e5722a8fe48aa2eb6fe63be01f61b5cc9a`
开始，以 `a4003704b70f06eb65297ddd32e0695ae8ee146b`、tree
`d12d64a7c8d013d8d299272eea88a4ce0431ccab` 完成：

- exact P19 registration → frozen strict training job 与 pre-label leakage audit；
- live read 只限 manifest/split/audit 后实际 train-consumed bytes，其他 Pack assets 不打开；
- fixed hash-bound `python -I -S` worker，不执行 uploaded code，也不声称 OS sandbox；
- canonical safe-JSON checkpoint/result 与双向绑定 candidate artifact/card/model identity；
- write-new staging、atomic no-replace publish、race/cancel/failure/timeout cleanup；
- 所有 benchmark/science/promotion booleans 保持 false，product policy 为 `NO_NEW_DECISION`。

Focused `56 passed`；P19+P20 `99 passed / 1 skipped`；safe `1,610/49/387`；legacy
`1,147/58/105`；static clean。Wheel `1,178,805` bytes / SHA-256
`2273ee71fb58fef543eae358d3df2aefccec42e80fe72a23380200718c223d79` / `370` entries /
`14` React / `0` tests / `0` AppleDouble。Real candidate training、test/external、science
均 `NOT_RUN`，policy `NO_NEW_DECISION`。该 wheel 只证明 exact local source/toolchain 可复现，
不是 pinned dependency closure 或 clean-install evidence。P21A 随后从 P20 docs-closure
`5f3fc2d88c20e8083fb66a4c3399c5fe148241be` 开始。

### Phase 21A：Virtual Cell Benchmark System（`COMPLETE — SYSTEM_ONLY`）

P21A 以 code SHA `20ecc12542e5df40c90d1fc367dbe86b563478b8`、tree
`ffcd261dd7d506d0ad852023afcba0f5c97a2d72`、source date epoch `1786050825`
冻结 strict benchmark protocol/run/result/evidence、validation-only threshold、paired CI、
calibration/OOD/selective gates 和只接受负结果的 content-addressed ledger。formal
adapter/Broker/runtime 只形成 typed receipt 合同，未执行真实模型。

本阶段没有真实 candidate run、test/external、资产、权重、训练、GPU、network、operator、
promotion、release 或 deploy；science `NOT_RUN`，policy `NO_NEW_DECISION`。synthetic
positive fixtures 只验证合同，不是 evidence；只读兼容重放保持 P8 historical
null/unbound 和 P9 exact negative/unbound。任何 P21B 执行都必须由外部可信边界独立固定
composite execution identity；content fingerprint 只证明内容身份，不构成 issuer
authentication。P21B/P21C 仍 `AUTHORIZATION_REQUIRED / NOT_RUN`。P22 contract-only
随后完成，但没有制造 executable、validated 或 promoted release。

### Phase 22：Curated Virtual Cell Registry（`COMPLETE — CONTRACT_ONLY`）

P22 以 P21A code `20ecc12542e5df40c90d1fc367dbe86b563478b8` 为 prerequisite，
从实际 P21A docs-closure `09792e13e29a76b5e4434507f3334eefb947789c` 开始，以
code SHA `bca5ad661856e8d9aa832c47f23c6ad7179ee0c9`、tree
`f78476ac1dbe2f865e3c1bcdc71ecc512dbad22a`、source date epoch `1786056220`
完成以下本地合同：

- exact One-Pack/P19 registration + P12 native one-release graph + P21B evidence/execution +
  P21C policy 的 immutable `vc.virtual-cell-release.v1` closure；
- reviewed wrapper approval，但 registry 从不 import/执行 entrypoint；
- operator-owned default-deny import/decision allowlists、stable authorization references、
  approve_catalog/quarantine/revoke/supersede append-only log；
- independently persisted monotonic checkpoint，且 checkpoint 后的 suffix 每次读取重新做
  authorization provenance 核对；
- path-redacted、nonexecuting、read-only Python catalog/query/dependency projection；
  installed/model/environment/adapter compatibility 为 unknown/null，`executable=false`。

Focused `35 passed`；affected `289 passed / 1 skipped`；safe `1,680/49/387`；legacy
`1,147/58/105`；static PASS。Wheel `1,217,155` bytes / SHA-256
`3f978e9f3eb06ea17017c1838002762f28ae717ee08d987cfb8ea059162a2485` / `372`
entries / React `14` / tests `0` / AppleDouble `0`；source/wheel module SHA-256 均为
`9678b2460aff6738935a2728e12abf398985c4475d66be96d37a721a21bf62ff`。

没有真实 imported/cataloged/quarantined/revoked/superseded release；默认 P22 registry
未配置/不存在或为空。Synthetic positive fixtures 只验证合同，不能成为 evidence/policy。
Science `NOT_RUN`，policy `NO_NEW_DECISION`；P21B/P21C 仍未运行。Content hash 不认证
issuer；external checkpoint 未推进时，registry/head 一起回退到最近受信 checkpoint 仍可能
无法检出。HTTP API、Data Center、chat/job identity、UI、asset install、runtime plan/execution、
multi-Pack 和 non-P21B/direct P14–P16 import 均未实现。

完整边界见 [ADR-0019](ADR-0019-curated-virtual-cell-registry.md)、
[P22 runbook](runbooks/VIRTUALCELL-CURATED-REGISTRY.md) 和
[P22 completion report](../reports/phase22/PHASE22_COMPLETION.md)。

### Phase 23A：Cell Interaction Evidence（`COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE`）

P23A 从 P22 docs-closure `2b5c28ac152857dfa1109de41ed5d5ddc7ab06a4` 开始，以 code SHA
`2b894966cd00b2af2fafbf8f009566dd69f393a7`、tree
`00bd98b0fd14091f4528115dcc66730264d5803a`、source date epoch `1786061504` 完成：

- exact sender/receiver P22 release、P19 registration、Pack/context closure；registry state 未验证；
- typed P18 model-input/view/observation identity；P18 contract 和 membership 未验证；
- 单一 dataset/platform/experiment/donor/sample/well/condition/dose/time identity，以及 exact
  ligand/receptor/evidence namespaces 和 mapping fingerprint；asset/linkage 未验证；
- declared P20/P21 model/benchmark/execution references；trust、artifact 和 execution 全部未验证；
- canonical `no_interaction`、`receiver_only`、`lr_coexpression` baselines 和 sender/receiver/
  ligand/donor/dataset/platform/dose-time OOD axes；
- P13-shaped prepared input/envelope/provenance/conformance，只有 synthetic fixture 可投影一个
  `[0,1]` dimensionless `interaction_evidence_score`。

Projection exact key set 只有 `interaction_evidence_score`；receiver response、effect size、causal
claim 和 legacy co-culture fields 在所有层级 fail closed。Missing evidence、baseline gate、OOD、
execution authorization 或 registry verification 失败时 values/shape 为 null 且不能 projection。
模块没有 filesystem/network/model I/O、registry mutation、runtime/API/UI wiring、aggregation 或默认
adapter registration。

Focused `107 passed`；affected `495 passed / 1 skipped`；safe `1,787/49/387`；legacy
`1,147/58/105`。Wheel `1,226,514` bytes / SHA-256
`e78f40f0f4fe7354e3c660d6612a8ee60a1b2dd61af2fc606a67d01e67ac601e` / `373`
entries / React `14` / tests `0` / AppleDouble `0`；两次独立 build byte-identical；module
source/wheel SHA-256 都是
`d1ba8d8054bf91c4a54a215c331fef65557df3954dba730998821ea9f70743cd`。

没有真实 release/Pack/data/mapping/model read 或 execution、baseline/CI/OOD science、receiver
response、scientific evidence、operator policy、release 或 deploy。Science `NOT_RUN`，policy
`NO_NEW_DECISION`。P23B 可选且需独立授权；P24 是 First Real Community Adapter，同样必须先获得
exact real assets/model/output window，不能用 fake/no-asset contract-only scaffold 替代。

完整边界见 [ADR-0020](ADR-0020-cell-interaction-evidence-contract.md)、
[P23A runbook](runbooks/CELL-INTERACTION-EVIDENCE.md) 和
[P23A completion report](../reports/phase23a/PHASE23A_COMPLETION.md)。

---

## 9. 当前合同与协议版本

### 9.1 服务协议

| 合同 | 当前值 |
|---|---|
| API protocol | `vc.api.v1` |
| Runtime protocol | `vc.runtime.v1` |
| Legacy runtime label | `v0.3` |
| Python package version string | `1.6.0` |

版本注意事项：

- GitHub 已经存在历史 annotated `v1.6.0` tag；
- 当前 Phase 11 产品代码在该历史发布之后继续沿用了 `1.6.0` 字符串；
- DOCS-CLOSURE parent `b02d219...` 及后续本地 docs commit 都不能被描述为现有
  GitHub `v1.6.0` tag 的内容；
- 这是待下一正式版本修复的版本漂移；
- 旧 tag 不得移动、覆盖或重建。

跨项目集成时应同时记录：

```text
product_version
api_protocol_version
runtime_protocol_version
git_sha
artifact SHA-256
```

不能只记录 `1.6.0`。

### 9.2 主要 schema

当前主要版本化合同包括：

- `vc.request.v2`
- `vc.species-ref.v1`
- `vc.cell-context.v1`
- `vc.modality.v1`
- `vc.dataset-ref.v1`
- `vc.perturbation.v1`
- `vc.task.v1`
- `vc.model-input.v1`
- `vc.prediction.v1`
- `vc.pack.v0.1`
- `vc.pack.v0.2`
- `vc.pack.v0.3`
- `vc.model-feature-contract.v1`
- `vc.feature-mapping.v1`
- `vc.alignment-report.v1`
- `vc.model-card.v1`
- `vc.environment.v1`
- `vc.compatibility-report.v1`
- `vc.execution-plan.v1`
- `vc.pack-record.v1`
- `vc.pack-index.v1`（legacy read）
- `vc.pack-index.v2`（P19 writes；factory registration/store provenance）
- `vc.pack-catalog.v1`
- `vc.job-execution-identity.v1`
- `vc.model-artifact.v1`（P12 candidate）
- `vc.model-environment.v1`（P12 immutable identity；不同于 runtime snapshot）
- `vc.model-adapter.v1`（P12 identity；不是 P13 Adapter SDK）
- `vc.model-validation-evidence.v1`
- `vc.model-operator-policy.v1`
- `vc.model-release.v1`
- `vc.model-registry-event.v1`
- `vc.model-registry-state.v1`
- `vc.model-registry.v2`
- `vc.model-registry-catalog.v2`
- `vc.model-registry-legacy-receipt.v1`
- `vc.model-registry-legacy-migration-report.v1`
- `vc.environment.v2`
- `vc.compatibility-report.v2`
- `vc.execution-step.v2`
- `vc.execution-plan.v2`
- `vc.job-execution-identity.v2`
- `vc.adapter-input-contract.v1`
- `vc.prepared-adapter-input.v1`
- `vc.adapter-output-contract.v1`
- `vc.adapter-output-envelope.v1`
- `vc.adapter-execution-provenance.v1`
- `vc.adapter-conformance-report.v1`
- `vc.ecoli-growth-scope.v1`
- `vc.ecoli-growth-validation-protocol.v1`
- `vc.ecoli-growth-data-binding.v1`
- `vc.ecoli-growth-execution-binding.v1`
- `vc.ecoli-growth-gene-mapping-binding.v1`
- `vc.ecoli-growth-compatibility-binding.v1`
- `vc.ecoli-growth-adapter-input-contract.v1`
- `vc.ecoli-growth-adapter-output-contract.v1`
- `vc.ecoli-growth-prepared-model-input.v1`
- `vc.yeast-deletion-fitness-scope.v1`
- `vc.yeast-deletion-fitness-validation-protocol.v1`
- `vc.yeast-deletion-fitness-data-binding.v1`
- `vc.yeast-deletion-fitness-execution-binding.v1`
- `vc.yeast-deletion-fitness-gene-mapping-binding.v1`
- `vc.yeast-deletion-fitness-compatibility-binding.v1`
- `vc.yeast-deletion-fitness-adapter-input-contract.v1`
- `vc.yeast-deletion-fitness-adapter-output-contract.v1`
- `vc.yeast-deletion-fitness-prepared-model-input.v1`
- `vc.k562-golden-perturbation-scope.v1`
- `vc.k562-golden-validation-protocol.v1`
- `vc.k562-golden-data-binding.v1`
- `vc.k562-golden-perturbation-binding.v1`
- `vc.k562-golden-execution-binding.v1`
- `vc.k562-golden-compatibility-binding.v1`
- `vc.k562-golden-adapter-input-contract.v1`
- `vc.k562-golden-adapter-output-contract.v1`
- `vc.k562-golden-prepared-model-input.v1`
- `vc.virtual-experiment-node.v1`
- `vc.virtual-experiment-edge.v1`
- `vc.virtual-experiment-dag.v1`
- `vc.virtual-cell-brain-context.v1`
- `vc.virtual-experiment-decision.v1`
- `vc.candidate-virtual-experiment-dag.v1`
- `vc.candidate-dag-review.v1`
- `vc.virtual-experiment-compilation.v1`
- `vc.job-execution-identity.v3`
- `vc.multiomics-modality-slot.v1`
- `vc.multiomics-input-contract.v1`
- `vc.multiomics-layer-input.v1`
- `vc.multiomics-observation-semantics.v1`
- `vc.multiomics-model-input.v1`
- `vc.multiomics-matrix.v1`（fingerprint payload）
- `vc.multiomics-observation-join.v1`（fingerprint payload）
- `vc.multiomics-missingness.v1`（fingerprint payload）
- `vc.multiomics-view-identity.v1`（fingerprint payload）
- `vc.data-catalog.v1`
- `vc.upload-receipt.v1`
- `vc.pack-candidate.v1`
- `vc.pack-metadata-review.v1`
- `vc.pack-validation-report.v1`
- `vc.pack-operator-decision.v1`
- `vc.factory-registered-pack.v1`
- `vc.pack-supersession.v1`
- `vc.pack-factory-store.v1`（exact `.factory-store.json` bytes：`{"schema_version":"vc.pack-factory-store.v1"}\n`）
- `vc.pack-factory-catalog.v1`
- `vc.training-environment.v1`
- `vc.training-resource-limits.v1`
- `vc.training-resource-observation.v1`
- `vc.training-asset-binding.v1`
- `vc.training-split.v1`
- `vc.training-leakage-overlap.v1`
- `vc.training-leakage-audit.v1`
- `vc.training-hyperparameter.v1`
- `vc.training-job.v1`
- `vc.candidate-checkpoint.v1`
- `vc.training-metric.v1`
- `vc.training-result.v1`
- `vc.candidate-model-artifact.v1`
- `vc.candidate-model-card.v1`
- `vc.training-candidate-model.v1`
- `vc.training-model-identity.v1`（fingerprint payload）
- `vc.tiny-json-checkpoint.v1`（safe data-only checkpoint payload）
- `vc.training-candidate-bundle.v1`
- `vc.training-run-bundle.v1`
- `vc.benchmark-scope.v1`
- `vc.benchmark-dataset-binding.v1`
- `vc.benchmark-split.v1`
- `vc.benchmark-baseline.v1`
- `vc.benchmark-metric.v1`
- `vc.benchmark-ci-policy.v1`
- `vc.benchmark-threshold-policy.v1`
- `vc.benchmark-ood-gate.v1`
- `vc.benchmark-calibration-policy.v1`
- `vc.benchmark-external-policy.v1`
- `vc.benchmark-promotion-gate.v1`
- `vc.benchmark-protocol.v1`
- `vc.benchmark-run-authorization.v1`
- `vc.benchmark-run.v1`
- `vc.benchmark-group-identity.v1`
- `vc.benchmark-leakage-audit.v1`
- `vc.benchmark-reliability-row.v1`
- `vc.benchmark-threshold-receipt.v1`
- `vc.benchmark-seed-result.v1`
- `vc.benchmark-group-metric-value.v1`
- `vc.benchmark-primary-measurement-row.v1`
- `vc.benchmark-paired-ci.v1`
- `vc.benchmark-primary-result.v1`
- `vc.benchmark-calibration-bin.v1`
- `vc.benchmark-scalar-capability.v1`
- `vc.benchmark-ood-result.v1`
- `vc.benchmark-capability-profile.v1`
- `vc.benchmark-external-result.v1`
- `vc.benchmark-result.v1`
- `vc.benchmark-promotion-evidence.v1`
- `vc.benchmark-evidence-bundle.v1`
- `vc.p21b-execution-identity.v1`（fingerprint payload）
- `vc.benchmark-evidence-ledger-entry.v1`
- `vc.benchmark-evidence-ledger-head.v1`
- `vc.benchmark-evidence-ledger.v1`（exact ledger marker）
- `vc.virtual-cell-context.v1`
- `vc.virtual-cell-wrapper-approval.v1`
- `vc.virtual-cell-release.v1`
- `vc.curated-virtual-cell-import-identity.v1`（fingerprint payload）
- `vc.curated-registry-decision.v1`
- `vc.curated-registry-entry.v1`
- `vc.curated-registry-head.v1`
- `vc.curated-registry-trust.v1`
- `vc.curated-registry-authorization-reference.v1`（fingerprint payload）
- `vc.curated-release-state.v1`
- `vc.curated-virtual-cell-registry.v1`（exact `.curated-registry.json` marker）
- `vc.curated-virtual-cell-catalog.v1`
- `vc.curated-release-dependency-graph.v1`
- `vc.p23-p18-endpoint-identity.v1`
- `vc.interaction-endpoint.v1`
- `vc.same-experiment-interaction-evidence.v1`
- `vc.interaction-scorer-fixture.v1`
- `vc.cell-interaction-evidence-input.v1`
- `vc.interaction-evidence-adapter-input-contract.v1`
- `vc.interaction-evidence-adapter-output-contract.v1`
- `vc.community-pack.v1`

其他项目应按 `schema_version` 路由解析器，不能依靠字段形状猜测版本。
以上 P12/P13/P14E/P15E/P16E/P17/P18/P19/P20/P21A/P22/P23A 新增 schema 属于本地
engineering-complete work units；
它们尚未发布，外部项目不应仅凭本地 completion 把它们当作已发布协议或
真实科学能力。P14E/P15E/P16E 的 validation protocols、synthetic fixtures、P17
contract-only DAG、P18 joint input、P19 factory registration、P20 candidate bundle 与 P22
synthetic curated release 尤其不能
被解析为 P12 validation evidence、真实多模型验收、真实 multi-omics 模型能力、科学训练结果
或 product promotion。P22 schema 只支持 exact One-Pack/P21B closure；multi-Pack、direct
P14–P16/non-P21B route 和 runtime integration 均未完成。P23A schema 只接受 synthetic
conformance score，并将真实 registry/P18/asset/linkage/P20/P21/execution/science/policy gates 固定为
false；不得把它解析成真实 interaction model、receiver response 或 causal capability。

---

## 10. 当前数据、Pack 和模型实况

### 10.1 数据目录

当前数据门户包含四个物种：

- human；
- mouse；
- yeast；
- bacteria。

固定目录状态：

```text
datasets       4
files          5
total bytes    27,823,623
usage status   download_only
```

公共文件只有在以下条件全部满足时才标记为 available：

- 位于配置数据根目录的 `public/` 下；
- 路径是 catalog 声明的路径；
- 文件大小匹配；
- SHA-256 匹配。

### 10.2 上传

上传只执行：

```text
认证
→ 大小和 quota 检查
→ 保留原始字节
→ 计算 SHA-256
→ 写入 quarantine
→ 返回 receipt
```

上传不会执行：

- 解包；
- schema mapping；
- QC；
- feature ID 映射；
- Pack authoring；
- Pack 注册；
- 模型训练；
- 模型预测。

### 10.3 内置产品 Pack

当前默认产品 catalog 只有：

- `p8-human-tiny`
- `p8-mouse-tiny`
- `p8-bacteria-tiny`

P10 yeast tiny Pack 存在于 CommunityPack fixture/release 资产中，但不在默认产品 Pack catalog。

### 10.4 默认模型卡

默认 registry 中有五类卡片：

- `ecoli_gem`：标记 available；
- `gears`：planned；
- `scgpt`：planned；
- `norman_mean_baseline`：planned；
- `yeast_deletion_fitness`：planned。

`ecoli_gem` 的 available 只表示 registry 中的资产/能力状态。当前通用 Pack runtime 缺少 growth output adapter，因此不能把它宣传为可对任意 bacteria Pack 执行的通用生长模型。

P12 的保守迁移不会把这五张卡的 `planned/available/missing` 提升为 v2
`artifact_ready`、`executable`、scientifically validated 或 promoted。每张旧卡只
形成 `migration_status=legacy_incomplete` 的 release 和结构化 `legacy_status`；其
不完整 artifact/environment/adapter records 不能进入 v2 可执行计划。P8/P9 历史
receipt 若缺 exact model binding 也只进入 unbound migration report。若旧卡的 raw
`model_version` 不是 canonical path-safe identifier，内部 identity 仍绑定原值，而
公开 catalog/capability/job projection 的 version 显示 `null`。

对 human/K562 Pack 的历史实测曾出现：

```text
pack_valid                   true
norman_mean model_compatible true
scgpt model_compatible       true
environment_compatible       false
execution_plan.executable    false
steps                        0
```

这说明数据验证和兼容性规划已经工作，同时也说明当前环境不能执行这些模型。

### 10.5 Golden Norman/K562

Golden Pack 和冻结评估已建立，但三个简单 baseline 都没有获得科学 promotion。

历史冻结简单 baseline MSE：

```text
no-change       0.00620609
global mean     0.00458205
additive ridge  0.00325706
```

这些值只属于冻结 Norman/K562 benchmark，不是跨数据集、跨细胞或跨物种性能声明。

### 10.6 Community

当前 CommunityPack 验证的是合同、单位、ID、质量守恒和 fail-closed 行为。它没有：

- 真实 CommunityModelAdapter 实现；
- 真实多成员动态模型；
- metabolite exchange 预测模型；
- 实验验证；
- scientifically promoted capability。

---

## 11. 外部项目推荐接入方式

优先级建议：

1. REST API：最清晰、最适合跨语言和跨项目；
2. CLI：适合 shell、批处理和 CI；
3. Python import：适合同一 Python 环境，但稳定性低于版本化 HTTP/schema；
4. 直接读取内部文件：只适合审计，不建议作为运行集成。

---

## 12. REST API

FastAPI 应用位于 `praxis_vc_api/main.py`。默认提供：

- OpenAPI：`/openapi.json`
- Swagger UI：`/docs`

### 12.1 系统和解析

| 方法 | 路径 | 用途 | 是否产生预测 |
|---|---|---|---|
| GET | `/api/health` | 服务、LLM、协议、版本和 Git SHA | 否 |
| POST | `/api/parse` | 自然语言转候选请求并校验 | 否 |
| GET | `/api/options` | 物种、扰动、任务枚举和 cell presets | 否 |
| GET | `/api/modules` | M1–M8 模块目录 | 否 |

### 12.2 Pack

| 方法 | 路径 | 用途 | 是否执行模型 |
|---|---|---|---|
| GET | `/api/packs` | 列出并重新验证 Pack records；P12 candidate 同时投影路径脱敏的 `model_registry` | 否 |
| GET | `/api/packs/{id}/{version}` | 获取单个 Pack record | 否 |
| GET | `/api/packs/{id}/{version}/validate` | 重新验证注册 Pack | 否 |
| POST | `/api/packs/compatibility` | 计算兼容性和计划 | 否 |
| GET | `/api/pack-factory` | root-free、reviewer/operator ID/rationale/reason-redacted receipt→registration lifecycle catalog | 否 |

当前没有远程 Pack register API。Pack 注册是本地 operator CLI/Python 操作。
`/api/pack-factory` 没有 POST/PUT/PATCH/DELETE route，且固定
`write_api_enabled=false`；未配置 store 时返回空的 `configured=false` catalog，不创建目录。
P12 没有增加 model-registry 管理写 API；`model_registry` 只包含显式白名单字段，不能
返回 asset cache path、URI、wrapper/implementation locator 或本地路径。

### 12.3 数据门户

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/data-catalog` | 获取严格公共数据目录 |
| GET | `/api/data-catalog?species=human` | 按物种筛选 |
| GET | `/api/data-catalog/{dataset_id}/files/{file_id}/download` | hash 重验后下载 |
| POST | `/api/data-uploads` | bearer 认证后上传到 quarantine |

### 12.4 Job 和报告

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/api/jobs` | 同步执行已验证请求并保存 job |
| GET | `/api/jobs` | 列出本地历史 job |
| GET | `/api/jobs/{job_id}` | 获取状态 |
| GET | `/api/reports/{job_id}` | 获取结构化和 narrative 报告 |
| GET | `/api/reports/{job_id}/trace` | 获取完整消息 trace |
| GET | `/api/reports/{job_id}/provenance` | 获取 provenance、LLM metadata 和 execution identity |
| GET | `/api/reports/{job_id}/module-plan` | 获取该次运行实际保存的模块计划 |
| GET | `/api/reports/{job_id}/markdown` | 获取确定性 Markdown 报告 |

### 12.5 Health 示例

```bash
curl -s http://127.0.0.1:8000/api/health
```

调用方至少应检查：

```json
{
  "status": "ok",
  "api_protocol_version": "vc.api.v1",
  "runtime_protocol_version": "vc.runtime.v1",
  "git_sha": "<exact-sha>"
}
```

### 12.6 解析示例

```bash
curl -s \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "在人 K562 细胞中敲除 AHR 后预测表达变化",
    "mode": "offline"
  }' \
  http://127.0.0.1:8000/api/parse
```

只有在以下条件满足时才应创建 job：

```text
schema_valid = true
clarification_required = false
```

### 12.7 Pack compatibility 示例

```bash
curl -s \
  -H 'Content-Type: application/json' \
  -d @- \
  http://127.0.0.1:8000/api/packs/compatibility <<'JSON'
{
  "pack_id": "p8-human-tiny",
  "pack_version": "1.0.0",
  "request": {
    "request_id": "external-k562-001",
    "species": "human",
    "cell_type": "K562",
    "perturbation_type": "gene",
    "perturbation_targets": ["AHR"],
    "input_modality": "scRNA",
    "output_modality": "delta_expression",
    "task_type": "predict_delta_expression"
  }
}
JSON
```

这是只读规划请求。调用成功不代表模型已运行。

### 12.8 显式 Pack job 示例

```bash
curl -s \
  -H 'Content-Type: application/json' \
  -d @- \
  http://127.0.0.1:8000/api/jobs <<'JSON'
{
  "mode": "offline",
  "enable_llm_report": false,
  "pack_id": "p8-human-tiny",
  "pack_version": "1.0.0",
  "request": {
    "request_id": "external-k562-001",
    "species": "human",
    "cell_type": "K562",
    "perturbation_type": "gene",
    "perturbation_targets": ["AHR"],
    "input_modality": "scRNA",
    "output_modality": "delta_expression",
    "task_type": "predict_delta_expression"
  }
}
JSON
```

`pack_id` 和 `pack_version` 必须同时提供或同时省略。

### 12.9 API 安全边界

当前 VirtualCell API：

- 上传端点有独立 bearer token；
- 其他端点没有通用用户认证、租户隔离或权限系统；
- job 使用本地文件系统持久化；
- 不适合直接裸露在公网；
- 对外部署应由反向代理、TLS、认证、网络 ACL、quota 和审计层保护。

---

## 13. CLI

命令入口：

```text
praxis-vc
```

### 13.1 普通运行

```bash
praxis-vc run \
  --request examples/ahr_k562.json \
  --mode offline \
  --out runs/external-k562
```

### 13.2 自然语言解析和确认

```bash
praxis-vc ask \
  --text "在人 K562 细胞中敲除 AHR 后会怎样" \
  --mode offline
```

默认只显示解析结果。加 `--yes` 才执行：

```bash
praxis-vc ask \
  --text "在人 K562 细胞中敲除 AHR 后会怎样" \
  --mode offline \
  --yes \
  --out runs/external-k562
```

### 13.3 启动 API 和当前 React 网站

```bash
praxis-vc serve --host 127.0.0.1 --port 8000
```

### 13.4 Pack 操作

```bash
praxis-vc pack inspect /path/to/pack
praxis-vc pack validate /path/to/pack
praxis-vc pack list
```

P19 已退役 `praxis-vc pack register /path/to/pack`。受控 register 必须显式提交完整 chain：

```bash
praxis-vc pack register \
  --upload-directory /absolute/quarantine/<upload-id> \
  --pack-root /absolute/operator-authored-pack \
  --candidate /absolute/contracts/candidate.json \
  --review /absolute/contracts/review.json \
  --validation /absolute/contracts/validation.json \
  --decision /absolute/contracts/decision.json \
  --index /absolute/existing-parent/pack-index.json \
  --store /absolute/initialized-factory-store
```

`--index` 和 `--store` 都是 required，CLI 不会代写 metadata/review/decision，也不会回退到
default path-only write。`--store` 必须先通过 `PackFactoryStore.create()` 的 supported
write-new 初始化流程生成并通过 exact marker 校验。完整操作边界见 P19 runbook。

`inspect` 只解析 manifest，不读取全部资产，也不声明 Pack 有效。
在 P12 candidate 中，`pack list` 复用同一个 Pack catalog payload，额外返回
`vc.model-registry-catalog.v2` 只读白名单投影；它不执行 lifecycle 写操作，也不把
cataloged 或 legacy available 解释为可预测。

兼容性规划：

```bash
praxis-vc pack compatibility \
  --request examples/ahr_k562.json \
  --pack-id p8-human-tiny \
  --pack-version 1.0.0
```

显式 Pack 运行：

```bash
praxis-vc pack run \
  --request examples/ahr_k562.json \
  --pack-id p8-human-tiny \
  --pack-version 1.0.0 \
  --mode offline \
  --out runs/pack-k562
```

如果没有可执行模型，命令应诚实返回 abstain，而不是生成 mock 结果。

### 13.5 P20 contract-only training dry-run

```bash
praxis-vc training dry-run \
  --job /absolute/training-job.json \
  --index /absolute/pack-index.json \
  --output-root /absolute/write-new-output
```

该命令只接受 exact P19 factory registration-bound job、explicit absolute index 和当时不存在的
canonical output root。它不自动选数据、训练真实 candidate、读取 test/external、运行 benchmark
或生成 evidence/promotion；任何手工 output root 仍需独立 exact 授权。P20 完成证据只使用
pytest `tmp_path`，不能据此推导一个可复用的外部 output root。

---

## 14. Python 集成

Python 可直接导入，但外部项目应把它视为比 REST schema 更容易变化的程序接口。

主要 workflow：

```python
from praxis_virtualcell.workflows.run_virtualcell_query import (
    parse_query,
    run_full_query,
    run_query,
)
```

Pack 数据合同公开接口：

```python
from praxis_virtualcell.data_packs import (
    AlignmentReport,
    ModelFeatureContract,
    PackManifest,
    PackRegistry,
    RegisteredPack,
    align_features,
    load_anndata_view,
    load_mudata_view,
    validate_pack,
)
```

Community 合同：

```python
from praxis_virtualcell.community_packs import CommunityModelAdapter
```

注意：`CommunityModelAdapter` 当前是抽象接口，不存在可直接执行的默认模型。

---

## 15. 当前普通请求格式

当前普通 `/api/parse` 和 `/api/jobs` 路径使用经过验证的 flat request：

```json
{
  "request_id": "ahr_k562_demo",
  "species": "human",
  "cell_type": "K562",
  "perturbation_type": "gene",
  "perturbation_targets": ["AHR"],
  "input_modality": "scRNA",
  "output_modality": "delta_expression",
  "task_type": "predict_delta_expression"
}
```

当前 validator 支持的主要枚举：

```text
species:
  human
  mouse
  yeast
  bacteria

perturbation_type:
  gene
  gene_combination
  drug
  medium
  ligand

task_type:
  predict_delta_expression
```

严格 nested `vc.request.v2` 已经实现。Pack 路径可以显式处理 v2 或把 legacy request 转换为 v2。外部项目如果需要长期稳定合同，应优先围绕 `schema_version` 和 v2 域对象设计，而不是扩展 legacy flat request 的任意字段。

---

## 16. Job 产物和可复现身份

当前 JobStore 使用本地文件系统，不使用数据库。典型目录：

```text
runs/<job_id>/
├── request.json
├── report.json
├── trace.json
├── provenance.json
├── execution_identity.json
├── report.md
├── narrative_report.md      # 启用且实际生成时
├── llm_meta.json
└── status
```

同名 job 目录拒绝覆盖。

### 16.1 Execution identity

Pack-aware job 记录：

- Pack ID；
- Pack version；
- Pack fingerprint；
- 模型 name/version；
- 模型 fingerprint；
- compatibility fingerprint；
- executable 状态；
- 整体 execution fingerprint。

P12 candidate 对 `vc.execution-plan.v2` 生成
`vc.job-execution-identity.v2`，进一步冻结 submitted/normalized request、plan、
environment snapshot、model release、capability、artifact、environment、adapter、
evidence、operator policy、lifecycle snapshot、science/policy snapshot verdict 和
compatibility fingerprints；`plan_id` 使用 canonical plan identity，并单列每个
execution-step fingerprint。JobStore 要求 submitted request 的 normalized fingerprint
与 plan 相等，也要求 structured report 与 provenance 保存同一 plan；该 identity 只
从该次已保存 plan/report 生成，不查询 live registry 来改写历史状态。落盘 structured
report 与 provenance 中的 execution plan 均替换为同一个字段白名单/路径脱敏 public
plan。历史 `vc.job-execution-identity.v1` bytes 和 legacy adapter 标记保持兼容。

Legacy job 明确记录：

```json
{
  "legacy_adapter": true
}
```

其他项目保存结果时应把 `execution_identity.json` 与报告放在一起。只保存 narrative 或截图不足以复现运行身份。

### 16.2 结果消费原则

读取方应优先消费：

1. structured report；
2. reliability decision；
3. execution identity；
4. provenance；
5. evidence；
6. trace；
7. narrative。

narrative 是解释层，不是数值真相源。

---

## 17. VirtualCellPack 接入

### 17.1 Pack 的作用

VirtualCellPack 负责把以下内容绑定成不可模糊的版本化对象：

- 数据文件；
- 文件 size 和 SHA-256；
- taxon 和 assembly；
- cell identity、state 和 context；
- modality 和 assay；
- feature namespace 和 ID 语义；
- condition、control 和 unit；
- split 和 leakage 边界；
- 数据来源、引用和 license；
- 多组学 pairing；
- feature mapping provenance。

### 17.2 Pack 不是模型

Pack 有效只表示数据合同成立。模型能力必须由 ModelCard 单独声明并由 Broker 匹配。

### 17.3 本地注册

Legacy read-only discovery 仍可使用默认 Pack index：

```text
~/.local/share/praxis-virtualcell/pack-index.json
```

可通过以下环境变量覆盖：

```text
PRAXIS_VC_PACK_INDEX
```

每次读取注册记录时都会重新验证 Pack bytes。Pack 路径或内容改变会导致 identity mismatch 或 invalid，而不是继续信任旧记录。

P19 controlled write 不使用该隐式 default：必须显式 absolute index 与由
`PackFactoryStore.create()` 初始化、marker-verified 的 factory store；普通
目录不能直接打开。Index v2 兼容读 v1，但所有新写使用 v2；v1 records 不带 factory provenance。
`PackIndex.register(pack_root)` 已禁用。Index 与 store 只有双向匹配、完整 registration chain
可重验后才 committed；中间 pending 或 store drift 一律不可消费。

### 17.4 新 Pack 接入检查清单

其他项目提供 Pack 时至少应确认：

- manifest schema 是受支持版本；
- 所有路径都是 Pack root 内相对路径；
- 没有 symlink escape；
- size 和 SHA-256 完全匹配；
- license 和 citation 明确；
- taxon/assembly 与数据一致；
- cell/context/condition/control/unit 明确；
- feature namespace 和 ID format 明确；
- split 以 biological group 为单位；
- 没有静默数据转换；
- Pack 验证通过后仍不自动宣称有预测能力。

---

## 18. 模型接入和当前 Adapter 边界

ModelCard 描述：

- species/taxon；
- modality/assay；
- cell domain；
- perturbation；
- task；
- output；
- feature namespace；
- 资产和 hash；
- 资源需求；
- uncertainty；
- OOD domain；
- wrapper/adapter。

Compatibility report 分开记录：

```text
pack_valid
model_compatible
environment_compatible
assets_available
wrapper_available
executable
scientifically_validated
```

P12 的 `vc.compatibility-report.v2` 还逐项绑定 model release、capability、
artifact、environment identity、adapter、evidence、operator policy 和 lifecycle
snapshot。只有 native exact-Pack release、经 hash/size 复验的安全 artifact、
`vc.environment.v2` exact identity、exact adapter、promotion-eligible evidence、
production-promoted policy，以及未 revoked/superseded 的 active state 同时成立，
`vc.execution-plan.v2` 才包含 step；否则保存稳定拒因并空 plan/abstain。

产品 Pack CLI/API 路径显式启用 v2 gate。为保持 P8/legacy 低层回归，直接构造自定义
`ModelZooRegistry(custom_path)` 的库调用仍可处于 v1 compatibility mode；该路径不是
v2 fully governed 产品执行面，不能用来绕过 product Pack 路径或声称 P12 完整治理。

P13 已建立通用 `VirtualCellModelAdapter` SDK。生产默认 registry 当前只注册：

```text
predict_delta_expression → delta_expression
```

该 reference adapter 通过 Broker-prepared immutable input 和 strict output envelope 接入
现有 runtime、provenance、report 与 governance。每次输出必须通过 task/output、shape、
unit、finite value、uncertainty、OOD、abstain 和 exact execution provenance 校验；
unexpected adapter/runtime faults 也 fail closed。

P13 的通用 growth/fitness adapters 仍只存在于 tests。P14E 另新增了一个明确版本化的
`predict_knockout_growth → growth_ratio` local contract adapter，但它只可在显式本地
`AdapterRegistry` 中用于 synthetic conformance，未进入默认 registry，且其 compatibility
固定 `executable=false`。它不是测试 dummy，也不是生产 adapter。

P15E 以同样的 local-only 边界新增
`predict_deletion_fitness → fitness` contract adapter。它只支持 exact S288C、单个
complete deletion 和 SGD systematic mapping，公开输出是 matched-control-relative
dimensionless finite scalar；它未进入默认 registry，且 compatibility 同样固定
`executable=false`。

历史 v1 `ecoli_gem` card/`GemWrapper`/legacy route 的存在或 `available` 状态不能把 P14E
升级为真实 GEM capability，不能补足 exact asset、environment、Pack、mapping、evidence
或 policy。要接入 growth、fitness、absolute expression、metabolic flux、drug response
等生产输出，仍需明确的 executable adapter、exact model/assets、独立科学测试、evidence
与 operator policy。不能只修改模型卡的 `status`/`outputs`，引用 P13 dummy，或引用
P14E/P15E/P16E contract adapter，就宣称模型可运行。

模型权重和大型资产必须外置，并通过 hash、模型卡和环境身份绑定，不能直接提交进 Git。

---

## 19. 数据门户接入和治理

关键环境变量：

| 变量 | 用途 |
|---|---|
| `PRAXIS_VC_DATA_ROOT` | 公共数据和 quarantine 的绝对根目录 |
| `PRAXIS_VC_DATA_CATALOG` | 覆盖默认 catalog |
| `PRAXIS_VC_UPLOAD_TOKEN` | 至少 32 字符的上传 bearer token |
| `PRAXIS_VC_UPLOAD_MAX_BYTES` | 单文件上限 |
| `PRAXIS_VC_UPLOAD_TOTAL_BYTES` | 总 quota |

上传示例：

```bash
curl -s \
  -H "Authorization: Bearer ${UPLOAD_TOKEN}" \
  -F species=human \
  -F file=@matrix.h5ad \
  http://127.0.0.1:8000/api/data-uploads
```

返回 receipt 后，外部系统必须把它标记为：

```text
quarantined upload
```

不能标记为：

```text
validated dataset
registered Pack
buildable Virtual Cell
prediction-ready data
```

---

## 20. 安装与运行

### 20.1 Python

要求：

```text
Python >= 3.11
推荐复现版本：Python 3.13
```

源码开发安装：

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[api]"
```

严格复现应使用 `requirements/` 下的 Python 3.13 hash-lock 文件，而不是重新自由解析依赖。

### 20.2 React

```bash
cd praxis_vc_react
npm ci
npm run build
cd ..
praxis-vc serve --host 127.0.0.1 --port 8000
```

浏览：

```text
http://127.0.0.1:8000
```

Vite 开发服务器默认在 5173，并把 `/api` 代理到后端。可通过 `VITE_DEV_API` 调整开发代理，通过 `VITE_API_BASE` 覆盖生产 API base。

### 20.3 可选 extras

| Extra | 作用 |
|---|---|
| `api` | FastAPI + Uvicorn |
| `web` | 旧 Streamlit UI |
| `omics` | AnnData + MuData |
| `mechanistic` | COBRA/GEM |
| `dev` | 测试、lint 和开发工具 |

### 20.4 Wheel

完整 release wheel 的构建入口：

```bash
PYTHON_BIN=python3.13 \
  scripts/build_release_wheel.sh /tmp/praxis-dist
```

目标 wheel 包含：

- Python runtime；
- CLI；
- FastAPI；
- 构建后的 React 静态文件；
- 旧 Streamlit 入口；
- 包内小型合同和资产。

### 20.5 Docker

```bash
scripts/build_release_container.sh praxis-virtualcell:local
```

运行时应把 `runs` 和所需外部数据作为显式 volume，并把密钥通过进程环境或 secret manager 注入。

---

## 21. 主要环境变量

| 变量 | 用途 |
|---|---|
| `PRAXIS_VIRTUALCELL_MODE` | `offline` 或 `llm_assisted` |
| `DEEPSEEK_API_KEY` | 可选 DeepSeek key |
| `PRAXIS_VC_LLM_BASE_URL` | LLM endpoint |
| `PRAXIS_VC_LLM_MODEL` | LLM model name |
| `PRAXIS_VC_RUNS` | job 产物目录 |
| `PRAXIS_VC_STATIC_ROOT` | React 静态文件根目录 |
| `PRAXIS_VC_PACK_INDEX` | Pack index |
| `PRAXIS_VC_MODEL_REGISTRY` | Model registry |
| `PRAXIS_VC_MODEL_CACHE` | 外置模型缓存 |
| `PRAXIS_VC_DATA_ROOT` | 外置数据根目录 |
| `PRAXIS_VC_DATA_CATALOG` | 数据 catalog |
| `PRAXIS_VC_UPLOAD_TOKEN` | 上传认证 token |
| `PRAXIS_VC_UPLOAD_MAX_BYTES` | 上传单文件限额 |
| `PRAXIS_VC_UPLOAD_TOTAL_BYTES` | 上传总 quota |
| `GEARS_DATA_ROOT` | 外部 GEARS 数据根目录 |
| `GEARS_DATA_NAME` | GEARS dataset name |
| `VITE_DEV_API` | React 开发代理地址 |
| `VITE_API_BASE` | React API base |

`.env`、API key、外部数据、模型权重和部署 secret 都不是仓库内容，不应被复制或提交。

---

## 22. 仓库目录

| 路径 | 责任 |
|---|---|
| `praxis_virtualcell/` | VirtualCell runtime、agents、contracts、Pack、model zoo、governance、workflow |
| `praxis2/` | 继承的 PRAXIS-2 兼容层和底层基础设施 |
| `praxis_vc_api/` | FastAPI 薄适配；不拥有科学判断 |
| `praxis_vc_react/` | 当前 Cell-first React 主 UI |
| `praxis_vc_web/` | 旧 Streamlit UI |
| `examples/` | 可运行请求示例 |
| `data/` | 小型合同 fixture 和 benchmark evidence；大型数据外置 |
| `reports/` | 版本化测试和审计证据 |
| `requirements/` | Python 3.13 hash locks |
| `scripts/` | 构建、验证、审计和运行脚本 |
| `deploy/vc/` | release container 和服务入口 |
| `docs/` | ADR、runbook、状态、测试和路线图 |
| `runs/` | 本地生成的 job 产物，不是源代码 |
| `old/` | 迁移后的历史工作树和恢复资产，不参与当前运行 |

---

## 23. 当前仓库和存储布局

当前规范开发目录：

```text
/Volumes/T7/PRAXIS-virtualcell
```

T7 使用 ExFAT。为了避免 AppleDouble 文件损坏 Git pack index，Git metadata 位于 APFS：

```text
/Users/mzy/Projects/.PRAXIS-virtualcell-gitdir
```

工作树根目录中的 `.git` 文件指向该外置 Git dir。

历史目录已经归档到：

```text
/Volumes/T7/PRAXIS-virtualcell/old
```

`old/` 不属于当前代码，不应被构建、测试、批量清理或提交。

该仓库包含运行离线 CLI、API 和 React 产品所需的源码和小型资产，但不自带：

- 当前 Python virtualenv；
- 生产 `.env`；
- DeepSeek key；
- P7/Golden 的全部外置大数据；
- 模型权重和 checkpoints；
- GPU 环境；
- 远程服务器配置；
- 公网 TLS、域名和通用权限系统。

因此“源码足够重建产品”不等于“源码包含所有数据、凭据和科学模型”。

---

## 24. 测试和证据

### 24.1 P10 历史 exact-SHA 证据

在 P10 SHA `5f2eb940c07f2cae5b664f35a57c407026d66587`：

```text
P10 CommunityPack 定向             38 passed
Pack/capability/packaging/P10      192 passed
VirtualCell core                   1310 passed, 35 skipped, 9 deselected
legacy                             1146 passed, 59 skipped, 105 deselected
Ruff                               PASS
pip check                          PASS
```

GitHub Actions run `30434482562` 的五个 job 全部成功。该证据只属于该 exact SHA。

### 24.2 记录的 `b02d219...` 本地重建证据

迁移后使用新建 Python 3.13 hash-lock 环境完成。它只绑定 DOCS-CLOSURE parent，
不能自动继承给 docs-only completion commit：

```text
依赖安装                           PASS
pip check                          PASS
Ruff                               PASS
legacy                             1146 passed, 59 skipped, 105 deselected
frontend typecheck                 PASS
frontend lint                      PASS
frontend build                     PASS
frontend bundle budget             PASS
Playwright                         12/12 passed
release wheel build                PASS
offline CLI smoke                  PASS
API health/root                    PASS
```

该次 core 测试结果不是全绿：

```text
1309 passed
35 skipped
9 deselected
1 failed
```

唯一失败：

```text
test_playwright_python_can_be_overridden_without_editing_config
```

原因是 `playwright.config.ts` 中环境变量表达式包含转义的 `\${...}`，而 packaging
文本合同测试要求未转义源码字符串。这是只绑定 `b02d219...` 的当时
packaging/text-contract 回归，不是 runtime 执行失败；该 exact SHA 不能写成全绿。
后续 P12/P13 已分别在其 completion code SHA 重验通过，不能用后续结果回写这条历史。

该次 `b02d219...` 本地 wheel 证据：

```text
size     1,043,145 bytes
SHA-256  0a31bbb4bfc2f5773cda459e6790b6ccd6ff11dab8d386c026ad37bd0c42aa96
```

该 hash 只标识该次本地构建，不代表已经发布到 GitHub。本次 DOCS-CLOSURE 不修改
代码，也不重跑 core、legacy、frontend 或发行物；只报告实际文档检查。

### 24.3 P12 完成状态

P12 completion code SHA 为 `1a5464fb0d2d9e105058f6797d92efd69783e5b2`。Model
Registry v2、cache、capability runtime、Pack product 和 job identity 的 fail-closed
门，以及 core、legacy、frontend 静态门、Ruff、隔离 `pip check`、packaging、wheel
reproducibility、`git diff --check` 和 post-commit 核验，均记录在
`reports/phase12/PHASE12_COMPLETION.md`。P10 或更早历史测试没有被继承为 P12 证据。

### 24.4 P13 完成状态

P13 从 `f83c13db386cb552b3ce7a5643e5ffbead0ff573` 开始，completion code SHA 为
`744d0a28d2cfc13d1b10e85b133b6c13b9426174`，tree 为
`198e623120688d3704b9312990ddaa93c9a7b0e6`。Adapter SDK、output flow 与 capability
runtime 分别为 `48/22/75 passed`；7-file directed gate 为 `265 passed`；core 为
`1462 passed, 35 skipped, 9 deselected`（2 条已知 MuData deprecation warnings）；
legacy 为 `1146 passed, 59 skipped, 105 deselected`；packaging `13 passed`。Ruff、隔离
`pip check`、frontend typecheck/lint/build/bundle budget、两次 byte-identical wheel 与
clean install 均通过。wheel 为 1,076,180 bytes，SHA-256
`3658b6247a909d0351d760295e0bcbb8082eac930d96fdfe39e4377b591b4f23`。完整 scope 和
未运行项见 `reports/phase13/PHASE13_COMPLETION.md`。

### 24.5 P14E 完成状态

P14E starting SHA 为 `0b193310009d6e4d2ebc0fc8abf95da20a56acdb`，SDK prerequisite
为 `c3401450fd79f7829c438d6b55c1902ea2f4cf5f`，completion code SHA 为
`8778e93c31c2dfe1ef0f77f06e7a80a425633736`，tree 为
`fa85e049bb36f3fbd8e6d4a7503e4b5837ed7c78`。P14E contract file 为 `71 passed`；
P14E + adjacent SDK/output-flow 为 `148 passed`；safe nine-file directed gate 为
`360 passed`；safe legacy 为 `1147 passed, 58 skipped, 105 deselected`。full active-tree
Ruff 与 `git diff --check` 通过，三次 exact-hash adversarial review 无 P1/P2 finding。

这些 gate 没有运行 `test_ecoli_gem_case.py`、`test_gem_wrapper.py`、medium/antibiotic/
yeast GEM tests 或其他真实 GEM/Cobra science path。两次 clean archive 构建的完整 wheel
byte-identical：1,086,768 bytes，SHA-256
`462b89376a5134906e98ea4b1ec573bc24e5f2e53266d5a7104be8d625eb88b3`；这只是未发布的本地
构建 identity。由于本地 cache 缺四个 dependency 的原始 wheel bytes，本窗口没有刷新
严格 one-shot offline `--require-hashes` install 证明；受限 compatibility smoke 不能冒充
lockfile hash-integrity evidence。完整记录见
`reports/phase14e/PHASE14E_COMPLETION.md`。

### 24.6 P15E 完成状态

P15E starting SHA 为 `0ff6870a70a04d71098a16875e633f909e31cc5a`，completion
code SHA 为 `62480a3951173a2aa7b006403af9b169521db138`，tree 为
`64906691c4c989a843df4da97f0a93f32cd65ad2`。P15E contract 为 `98 passed`，
safe directed 为 `458 passed`，safe legacy 为
`1147 passed, 58 skipped, 105 deselected`。authoritative
`ruff check . --extend-exclude old --no-cache`、format 和 `git diff --check` 通过。

这些 gate 只用 synthetic identities/raw dictionaries，没有运行真实 deletion
screen/model/GEM 或 science。两个 manual clean archive 在 offline/network-denied
Python 3.13 本地 toolchain 上构建出 byte-identical wheel，SHA-256
`7758c13bd5a53c74618d556b14c6e27e0492381162a9ab3364aee7dde5d2bb8d`；该 wheel
未发布。严格安装脚本的 cache 缺 `packaging==26.2` 而 fail closed，系统
`pip check` 受 global environment 污染，因此都不记为新的全局依赖证据。
版本仍为 `1.6.0`，没有 release/version bump。完整记录见
`reports/phase15e/PHASE15E_COMPLETION.md`。

### 24.7 P16E 完成状态

P16E starting SHA 为 `d1e2e37b69784bd2f440cba34f51cfb56dcc00b2`，completion
code SHA 为 `9f6b14ea84cb0884b2bde2ed4c67c73aeb5a37e2`，tree 为
`098cd563e3d865e080a0d121727b987e2d40ed18`。P16E contract 为 `231 passed`，
safe directed 为 `689 passed`，safe legacy 为
`1147 passed, 58 skipped, 105 deselected`。authoritative
`ruff check . --extend-exclude old --no-cache`、format 和 `git diff --check` 通过，
最终 adversarial verification 无剩余 P1/P2 finding。

这些 gate 只读取 checked-in 小型 Golden YAML/JSON manifests，并用 synthetic
5,045-value vectors；没有读取 H5AD、运行 candidate/additive ridge/Golden science、
training、GPU 或 network。两个 clean archive 的 exact wheel byte-identical：
`1,108,165` bytes，SHA-256
`d333180996a4ed91161d364275589e992d0be634582cc83a57e9758b86c03c66`，`365` entries，
其中 `14` 个 React static entries；该 wheel 未发布。
严格 offline install、全局 `pip check` 与 limited installed-wheel smoke 的真实边界见
completion report，不能把受污染或非 hash-locked 环境改写成 release evidence。
版本仍为 `1.6.0`，没有 release/version bump。完整记录见
`reports/phase16e/PHASE16E_COMPLETION.md`。

### 24.8 P20 完成状态

P20 starting SHA 为 `f53e29e5722a8fe48aa2eb6fe63be01f61b5cc9a`，completion code
SHA 为 `a4003704b70f06eb65297ddd32e0695ae8ee146b`，tree 为
`d12d64a7c8d013d8d299272eea88a4ce0431ccab`，source date epoch 为 `1786040663`。
Focused P20 为 `56 passed`；P19+P20 为 `99 passed, 1 skipped`；safe gate 为
`1610 passed, 49 skipped, 387 deselected`；legacy 为
`1147 passed, 58 skipped, 105 deselected`；static checks clean。

Reproducible wheel 为 `1,178,805` bytes，SHA-256
`2273ee71fb58fef543eae358d3df2aefccec42e80fe72a23380200718c223d79`，包含 `370`
entries、`14` React entries、`0` test entries、`0` AppleDouble。Training pipeline source/wheel
SHA-256 都是 `dd7dbe480c3f000e5345b35fc6358fe2cc1b4377b035c31809d584ce3c869134`；fixed
worker source/wheel SHA-256 都是
`4de1ba3b67a67ea24c16b7664058939ae3a634e06cf11601a528aca4c465f02b`。
这些 bytes 只证明 exact local source/toolchain 可复现，不是 pinned dependency closure 或
clean-install evidence。

这些 gate 只使用 repository tiny fixtures 和 pytest `tmp_path`。它们没有运行真实 candidate、
读取 test/external、访问 network/GPU、生成 benchmark/scientific evidence 或作出 product
policy；science `NOT_RUN`，policy `NO_NEW_DECISION`。完整记录见
`reports/phase20/PHASE20_COMPLETION.md`。

### 24.9 P22 完成状态

P22 actual starting docs-closure SHA 为
`09792e13e29a76b5e4434507f3334eefb947789c`，P21A prerequisite code 为
`20ecc12542e5df40c90d1fc367dbe86b563478b8`；completion code/tree 为
`bca5ad661856e8d9aa832c47f23c6ad7179ee0c9` /
`f78476ac1dbe2f865e3c1bcdc71ecc512dbad22a`，epoch `1786056220`。

Focused 为 `35 passed`；affected 为 `289 passed, 1 skipped`；safe 为
`1,680 passed, 49 skipped, 387 deselected`；legacy 为
`1,147 passed, 58 skipped, 105 deselected`；static checks PASS。Reproducible wheel 为
`1,217,155` bytes，SHA-256
`3f978e9f3eb06ea17017c1838002762f28ae717ee08d987cfb8ea059162a2485`，包含
`372` entries、`14` React、`0` tests、`0` AppleDouble；source/wheel curated-registry
module SHA-256 都是
`9678b2460aff6738935a2728e12abf398985c4475d66be96d37a721a21bf62ff`。

这些结果只证明 contract/store/trust/public-projection 在 synthetic fixtures 上 fail closed。
没有真实 release、evidence/policy import 或 lifecycle decision，默认 registry absent/empty；
HTTP/UI/Data Center/chat/job/runtime 均未接线。Science `NOT_RUN`，policy
`NO_NEW_DECISION`。完整记录见 `reports/phase22/PHASE22_COMPLETION.md`。

### 24.10 P23A 完成状态

P23A starting SHA 为 `2b5c28ac152857dfa1109de41ed5d5ddc7ab06a4`；completion code/tree 为
`2b894966cd00b2af2fafbf8f009566dd69f393a7` /
`00bd98b0fd14091f4528115dcc66730264d5803a`，epoch `1786061504`。

Focused 为 `107 passed`；affected 为 `495 passed, 1 skipped`；safe 为
`1,787 passed, 49 skipped, 387 deselected`；legacy 为
`1,147 passed, 58 skipped, 105 deselected`。Reproducible wheel 为 `1,226,514` bytes，
SHA-256 `e78f40f0f4fe7354e3c660d6612a8ee60a1b2dd61af2fc606a67d01e67ac601e`，包含
`373` entries、`14` React、`0` tests、`0` AppleDouble；两次独立 build byte-identical。
Source/wheel module SHA-256 均为
`d1ba8d8054bf91c4a54a215c331fef65557df3954dba730998821ea9f70743cd`。

这些结果只证明 exact content binding、synthetic score validation、abstention、projection 和
provenance fail closed。所有真实 registry/P18/asset/linkage/P20/P21/execution/science/policy metadata
均为 false；没有真实 I/O/runtime/default registration。Science `NOT_RUN`，policy
`NO_NEW_DECISION`。完整记录见 `reports/phase23a/PHASE23A_COMPLETION.md`。

### 24.11 Skip 和 deselect 的含义

skip/deselect 不能写成：

- 外部模型通过；
- LLM 真实调用通过；
- GPU 训练通过；
- 远程科学验证通过；
- Community model 通过。

它们只表示相应测试没有在该次本地 scope 中执行。

---

## 25. 当前已知限制

### 产品限制

- Cell preset 不是持久化 Virtual Cell；
- 当前 React Chat 不绑定 Pack identity；
- Pack Factory 只有本地 contract-only CLI/library 和只读 API/UI；没有公共 authoring/write UI；
- Training Pipeline 只有本地 synchronous contract-only CLI/library；没有真实 candidate service、
  scheduler、GPU queue 或 benchmark UI；
- 没有 operator approval UI；
- 没有持久化 VirtualCell registry；
- 没有服务器数据安装工作流；
- 没有用户/租户/通用权限系统；
- Data Center 只展示真实 catalog/Pack 背景状态。

### 数据限制

- 不支持任意原始测序文件的自动处理；
- 上传先只进入 quarantine；只有显式 P19 chain 才可成为 factory-registered Pack；
- 没有自动 schema mapping 和 QC；
- 没有自动 Pack authoring；candidate manifest/mapping 和所有 claims 必须显式审核；
- 大型公共数据外置。

### 模型限制

- P13 SDK 支持严格注册多种 task/output 合同，但默认生产 registry 仍只包含 delta
  expression reference adapter；P13 growth/fitness adapters 仅为测试 dummy；
- P14E growth adapter 是 local、non-default、typed-negative 的 contract adapter，不是
  production adapter；它没有真实 GEM/Pack/model release、evidence 或 policy；
- P15E fitness adapter 同样是 local、non-default、typed-negative contract adapter；它没有
  真实 deletion screen/model/Pack evidence 或 policy，不能与 planned card 合并宣传；
- P16E K562 adapter 同样是 local、non-default、typed-negative contract adapter；它没有
  真实 candidate/model execution/evidence 或 policy，历史 P8 additive result 不能冒充候选证据；
- 历史 `ecoli_gem` card、legacy `GemWrapper`/route 和 P14E contract adapter 是不同边界，
  不能相互补足或合并宣传为可执行 E. coli growth capability；
- P12 adapter identity 与 P13 executable adapter SDK 已完成接线，但没有新增生产
  growth/fitness adapter、真实模型或 task-scoped science evidence；
- P12 v2 identities 和 Pack-aware gate 工程完成，但没有新增真实科学 evidence/policy；
- P20 candidate checkpoint/card/model 只证明 exact tiny contract replay，不是训练质量、真实模型
  capability、scientific evidence 或 production registry entry；
- P23A adapter 是 local、non-default、synthetic pass-through contract；它不计算 score，不读取
  sender/receiver data/model，不验证 P22 registry 或 P18 membership，也不提供 receiver response；
- custom-path 低层 ModelZooRegistry 保留显式 v1 compatibility mode，不能称 v2 fully
  governed 产品路径；
- 当前部署/本地默认环境没有完整真实权重生态；
- 模型卡 available 不等于 runtime 可执行；
- Golden baselines 没有科学 promotion；
- P9 外部验证是负结果。

### 科学限制

- 没有“任意细胞预测器”；
- P14E 没有读取/运行真实 GEM、growth/essentiality data 或 solver，没有 E. coli
  benchmark、paired CI、independent cohort、real OOD 或 scientific validation；
- P15E 没有读取/运行真实 deletion-fitness data/model/GEM，没有 benchmark、
  paired CI、independent condition/platform、real OOD 或 scientific validation；
- P16E 没有读取 H5AD 或运行 candidate/additive ridge，没有新的 MSE、paired CI、
  contamination、external K562/platform、real OOD 或 scientific validation；
- 没有多物种科学能力同时通过的证据；
- P20 没有真实 candidate training、test/external evaluation、benchmark、external replication
  或 scientific validation；
- P23A 没有真实 paired/co-culture/spatial evidence、baseline comparison、paired CI 或 OOD science；
  supplied fixture score 不是 scientific evidence；
- 少于两个 capability 拥有 exact positive evidence 与 named-operator
  `production_promoted`；P17 contract 已完成，但不能声称真实多模型执行或科学验收；
- 没有真实 Community model；
- 没有 Host–Microbiome model；
- 没有 biological world model；
- 不能把 routing、规则建议或 LLM narrative 当作预测。

### 工程限制

- 当前版本字符串存在发布漂移；
- P13 Adapter SDK、P14E/P15E/P16E narrow contracts、P17 Brain/DAG、P18/P19/P20/P23A contracts
  仅在本地工程完成，尚未发布；
- P14E 尚无任意未来 GEM loader 为 `data_only` 的类型级证明；
- JobStore 是本地文件系统；
- API 除上传外没有通用认证；
- `docs/USER-GUIDE.md` 的五阶段网页描述已过时；
- 旧编号 `docs/PHASE13-30-MASTER-PROMPT.md` 已从现行树删除；原 bytes 保留在 Git
  历史中，当前不得作为接手或授权入口；
- 多份历史状态文档只对其原始 SHA/日期有效。

---

## 26. 其他项目的安全集成模板

### 26.1 只读能力发现

适合需要知道 PRAXIS 当前支持什么的项目：

```text
GET /api/health
GET /api/options
GET /api/modules
GET /api/data-catalog
GET /api/packs
```

调用方只显示服务返回的状态，不自行把 `available` 升级为 `validated`。

### 26.2 请求解析服务

适合已有前端或 Agent 的项目：

```text
POST /api/parse
→ 检查 schema_valid
→ 需要澄清则停止
→ 用户或上游系统确认
→ POST /api/jobs
```

不要绕过解析结果的校验字段。

### 26.3 Pack-aware 运行

适合已经制作 VirtualCellPack 的项目：

```text
本地 validate/register
→ POST /api/packs/compatibility
→ 检查 execution_plan.executable
→ POST /api/jobs，显式传 pack_id + pack_version
→ 保存 execution identity
```

### 26.4 结果归档

至少保存：

```text
request
structured report
reliability decision
execution identity
provenance
trace
software git SHA
artifact hash
```

### 26.5 失败处理

调用方必须把以下结果当作正常、可预期的科学输出：

- clarification required；
- pack invalid；
- model incompatible；
- environment incompatible；
- asset unavailable；
- output adapter missing；
- OOD；
- benchmark failed；
- community model unavailable；
- abstain。

不能在这些状态下调用 LLM 生成替代数值。

---

## 27. 外部项目接入检查清单

### 身份

- [ ] 记录 `/api/health` 的协议版本和 exact `git_sha`
- [ ] 记录 wheel/container SHA 或 image digest
- [ ] 不只依赖产品版本字符串

### 请求

- [ ] 使用受支持 schema
- [ ] 校验未知字段和枚举
- [ ] 需要澄清时停止
- [ ] 不让 LLM 绕过 validator

### 数据接入

- [ ] 记录 dataset/Pack fingerprint
- [ ] 验证路径、size 和 SHA-256
- [ ] 记录 license、citation、taxon 和 assembly
- [ ] 不做未声明转换
- [ ] 上传 receipt 不冒充 Pack

### 模型接入

- [ ] 使用严格 ModelCard
- [ ] 权重外置且 hash-bound
- [ ] adapter 支持任务和输出
- [ ] 环境依赖可验证
- [ ] 区分 available、executable 和 scientifically validated

### 评估

- [ ] 预声明 biological-group split
- [ ] 审计 leakage
- [ ] 预声明 baseline 和 metric
- [ ] 单独处理 OOD
- [ ] 负结果原样保留
- [ ] 未通过时 abstain

### 结果

- [ ] 保存 execution identity
- [ ] 保存 provenance 和 trace
- [ ] 把 narrative 标为解释层
- [ ] 不把 smoke test 写成科学验证

### 安全

- [ ] API 不裸露公网
- [ ] 上传使用强 bearer token
- [ ] secret 不进入 Git
- [ ] 数据根目录最小权限
- [ ] 外置数据和模型有独立备份与审计

---

## 28. 后续路线图 P12–P30

P12/P13/P14E/P15E/P16E/P17/P18/P19/P20/P21A/P22/P23A 行记录已完成的工程 work units；
P14R/P14B、P15R/P15B 与 P16R/P16B 仍未运行。P21B/P21C 未授权、未运行，真实科学或
policy 窗口不能当作当前能力。P23A contract-only 已完成；真实 sender/receiver curated release、
Pack/context 与 interaction evidence/data/execution 仍未提供。P23B 可选且需独立授权；P24 是
First Real Community Adapter，也需 exact real assets/model/output window，不能用 fake scaffold 推进。

| 阶段 | 目标 |
|---|---|
| P12 | `COMPLETE`：Model Registry v2 artifact、environment、adapter、evidence、policy 身份分层 |
| P13 | `COMPLETE`：统一 VirtualCellModelAdapter SDK、delta reference 与 conformance harness |
| P14E | `COMPLETE`：E. coli K-12 knockout→growth-ratio local contract；`executable=false` |
| P14R | `AUTHORIZATION_REQUIRED / NOT_RUN`：exact GEM/data/assets 的科学运行 |
| P14B | `NOT_RUN`：正科学 evidence 后的独立 operator decision |
| P15E | `COMPLETE`：exact S. cerevisiae strain/condition gene-deletion→fitness local contract；`executable=false` |
| P15R | `AUTHORIZATION_REQUIRED / NOT_RUN`：exact deletion screen/model/assets 的科学运行 |
| P15B | `NOT_RUN`：正科学 evidence 后的独立 operator decision |
| P16E | `COMPLETE`：exact Human/K562 Golden perturbation→delta-expression local contract；`executable=false` |
| P16R | `AUTHORIZATION_REQUIRED / NOT_RUN`：exact candidate/model/assets 的科学运行 |
| P16B | `NOT_RUN`：正科学 evidence 后的独立 operator decision |
| P17 | `COMPLETE / CONTRACT_ONLY`：deterministic Virtual Cell Brain DAG/Brain/decision；real multi-model acceptance pending |
| P18 | `COMPLETE / CONTRACT_ONLY`：typed multi-omics model input；real model acceptance pending |
| P19 | `COMPLETE / CONTRACT_ONLY`：受控 receipt→RegisteredPack；real fixture/operator/science/policy NOT_RUN |
| P20 | `COMPLETE / CONTRACT_ONLY`：exact P19-bound training job/result、safe checkpoint/model identity 和 tiny dry-run；science `NOT_RUN`；policy `NO_NEW_DECISION` |
| P21A | `COMPLETE / SYSTEM_ONLY`：从 `5f3fc2d88c20e8083fb66a4c3399c5fe148241be` 冻结 Benchmark System、typed runtime receipts 和 negative ledger；completion `20ecc12542e5df40c90d1fc367dbe86b563478b8`；science `NOT_RUN`；policy `NO_NEW_DECISION` |
| P21B | `AUTHORIZATION_REQUIRED / NOT_RUN`：每个 candidate 的独立 run-only evidence 窗口 |
| P21C | `AUTHORIZATION_REQUIRED / NOT_RUN`：每个 exact scope 的独立 operator-only policy 窗口 |
| P22 | `COMPLETE / CONTRACT_ONLY`：start `09792e13e29a76b5e4434507f3334eefb947789c`；completion `bca5ad661856e8d9aa832c47f23c6ad7179ee0c9`；One-Pack/P21B release closure、default-deny trust、append-only lifecycle/checkpoint、redacted Python projection；默认 registry empty；science `NOT_RUN`；policy `NO_NEW_DECISION` |
| P23A | `COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE`：start `2b5c28ac152857dfa1109de41ed5d5ddc7ab06a4`；completion `2b894966cd00b2af2fafbf8f009566dd69f393a7`；evidence-only synthetic conformance；real release/data/execution `NOT_RUN`；禁止 receiver response/causal claim |
| P23B | `OPTIONAL / AUTHORIZATION_REQUIRED / NOT_RUN`：receiver response；需 intervention data、estimand、assumptions 和 exact P21B identity |
| P24 | `AUTHORIZATION_REQUIRED / NOT_RUN`：First Real Community Adapter；需 exact real assets、fixed P20/P21 model 和 write-new output window；无 fake contract-only scaffold |
| P25 | Virtual Microbiome prototype |
| P26 | Host–Microbiome coupled system |
| P27A | Experiment Design historical offline replay |
| P27B | 可选具名专家 shadow review |
| P27C | 可选 prospective pilot |
| P28 | Multi-agent virtual biology |
| P29 | 有限域、typed biological world-model candidate |
| P30A | Local RC |
| P30B1 | Push + exact-SHA CI |
| P30B2 | Main/tag/artifact release |
| P30B3 | Immutable staging |
| P30B4 | Production + real rollback |

路线顺序必须保持：

```text
先冻结模型身份和 Adapter 合同
→ 再建立三个窄任务的真实模型与科学验证
→ 再做多模型 Agent
→ 再做多组学、Pack Factory、训练合同和 benchmark
→ 再做细胞交互和 community
→ 最后讨论 world model
```

不能因为路线图中出现某个名称，就把它写成当前能力。

---

## 29. 当前推荐的下一技术闭环

P14E E. coli K-12 knockout→growth-ratio contract 已在不读取或运行真实 GEM/data 的边界内
完成。P14R 仍须逐资产、exact output root 和 run window 授权，P14B 仍须等待正科学结果
与具名 operator 决定；P14E completion 不改变这两个状态。

P15E S. cerevisiae gene-deletion→fitness contract 已在 synthetic、local-only 边界内
完成。P15R/P15B 分别保持独立授权窗口，P10 yeast tiny Pack、历史
yeast GEM 和 planned model card 仍不能冒充真实 deletion-fitness evidence。

P16E Human/K562 Golden perturbation→delta-expression contract 也已在 local-only、
typed-negative 边界内完成。P16R/P16B 分别保持独立授权窗口，P8 historical baseline
结果不是 P16 candidate evidence。

P17 deterministic Virtual Cell Brain DAG/Brain contract 已完成。当前 registry 为
5 releases / 0 native / 0 promoted，所以真实多模型 acceptance 仍 pending，所有真实
P17 direct-v2 请求必须 fail closed 或 abstain。P18 contract-only typed multi-omics
model input 也已完成，但 caller-declared adapter marker 未经 Broker/Registry 解析，真实
数据/模型/science 仍未运行。P19 controlled Pack Factory 已完成本地受控 registration
合同；真实 external fixture/output root/operator/science/policy 仍未运行。P20 Training
Pipeline 也已在 exact P19-bound、repository tiny、contract-only 边界完成；真实 candidate、
test/external、benchmark/science 均未运行，policy 为 `NO_NEW_DECISION`。P21A 随后从
P20 文档闭包提交 `5f3fc2d88c20e8083fb66a4c3399c5fe148241be` 开始，以
`20ecc12542e5df40c90d1fc367dbe86b563478b8`（tree
`ffcd261dd7d506d0ad852023afcba0f5c97a2d72`）完成 system-only benchmark contracts
与 negative ledger；science `NOT_RUN`，policy `NO_NEW_DECISION`。P21B/P21C 未授权、
未运行。P22 随后从 P21A docs-closure
`09792e13e29a76b5e4434507f3334eefb947789c` 开始，以
`bca5ad661856e8d9aa832c47f23c6ad7179ee0c9`（tree
`f78476ac1dbe2f865e3c1bcdc71ecc512dbad22a`）完成 contract-only curated registry；
默认 registry empty，没有真实 import/lifecycle、science 或 policy。P23A 随后从 P22 docs-closure
`2b5c28ac152857dfa1109de41ed5d5ddc7ab06a4` 开始，以
`2b894966cd00b2af2fafbf8f009566dd69f393a7`（tree
`00bd98b0fd14091f4528115dcc66730264d5803a`）完成 evidence-only synthetic contract；真实
sender/receiver release、Pack/context、interaction evidence/data 或执行仍须满足 exact gate。
P23B 与 P24 都需要独立授权，当前没有 eligible fake/no-asset scaffold。

在进入更大世界模型之前，最重要的闭环仍然是：

```text
新数据
→ 明确 metadata 和 feature mapping
→ strict Pack validate
→ operator-approved register
→ 冻结 P20 training job/checkpoint/candidate identity
→ P21A 先冻结 benchmark protocol
→ 仅在独立授权的 P21B 窗口训练/评估 exact candidate
→ 绑定真实 ModelCard、权重和 adapter
→ 在 held-out biological groups 上比较预声明 baseline
→ 通过后形成 scientific evidence
→ 再由独立 operator policy 决定是否 production_promoted
→ 由独立 registry authority allowlist/checkpoint 导入 exact curated release
→ 未通过继续 abstain
```

该闭环应先在一个窄任务上完成，例如：

- E. coli condition → growth；
- Yeast deletion → fitness；
- K562 perturbation → delta expression。

每项能力都必须独立声明其适用物种、cell context、任务、输出、数据、模型、OOD 和证据。

---

## 30. 权威文件入口

建议其他项目按以下顺序阅读：

1. [README](../README.md)
2. [Testing Guide](TESTING.md)
3. [Versioning Contract](VERSIONING.md)
4. [P0–P10 Summary](PHASE0-10-SUMMARY-AND-REMAINING-WORK.md)
5. [VirtualCellPack Capability Matrix](VIRTUALCELLPACK-CAPABILITY-MATRIX.md)
6. [Community Readiness Checklist](COMMUNITY-READINESS-CHECKLIST.md)
7. [P11A Historical Design](PHASE11A-DATA-CENTRIC-UI-DESIGN.md)
8. [P12–P30 Execution Plan](PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md)
9. [P12–P30 Detailed Checklist](PHASE12-30-DETAILED-COMPLETION-CHECKLIST.md)
10. [P12–P30 Master Prompt](PHASE12-30-MASTER-PROMPT.md)
11. [P12–P30 Sequential Master Prompt](PHASE12-30-SEQUENTIAL-MASTER-PROMPT.md)
12. [P13 Completion Report](../reports/phase13/PHASE13_COMPLETION.md)
13. [P14E Completion Report](../reports/phase14e/PHASE14E_COMPLETION.md)
14. [P15E Completion Report](../reports/phase15e/PHASE15E_COMPLETION.md)
15. [P16E Completion Report](../reports/phase16e/PHASE16E_COMPLETION.md)
16. [P17 Completion Report](../reports/phase17/PHASE17_COMPLETION.md)
17. [P18 Completion Report](../reports/phase18/PHASE18_COMPLETION.md)
18. [P19 Completion Report](../reports/phase19/PHASE19_COMPLETION.md)
19. [P20 Completion Report](../reports/phase20/PHASE20_COMPLETION.md)
20. 本当前项目与集成指南
21. [Repository Layout](REPOSITORY-LAYOUT.md)
22. [Installation Guide](INSTALL.md)
23. 当前 work unit 的 ADR、runbook、contracts、代码和测试

关键 ADR：

- [P0 Foundation](ADR-0001-virtualcellpack-p0-foundation.md)
- [P4 Standard Semantics](ADR-0002-virtualcellpack-p4-standard-semantics.md)
- [P5 Multiomics Alignment](ADR-0003-virtualcellpack-p5-multiomics-alignment.md)
- [P6 Capability Runtime](ADR-0004-virtualcellpack-p6-capability-runtime.md)
- [P7 Data Portal](ADR-0005-virtualcellpack-p7-data-portal.md)
- [P8 Golden Norman](ADR-0006-virtualcellpack-p8-golden-norman.md)
- [P8 Product Surfaces](ADR-0007-virtualcellpack-p8-product-surfaces.md)
- [P9 OOD Validation](ADR-0008-virtualcellpack-p9-ood-validation.md)
- [P12 Model Zoo v2](ADR-0009-virtualcell-model-zoo-v2.md)
- [P13 Model Adapter SDK](ADR-0010-virtualcell-model-adapter-sdk.md)
- [P14E E. coli K-12 Growth Contract](ADR-0011-virtualcell-ecoli-k12-growth-contract.md)
- [P15E S. cerevisiae Deletion-Fitness Contract](ADR-0012-virtualcell-yeast-deletion-fitness-contract.md)
- [P16E K562 Golden Delta Contract](ADR-0013-virtualcell-k562-golden-delta-contract.md)
- [P17 Virtual Cell Brain](ADR-0014-virtual-cell-brain.md)
- [P18 Multi-omics Model Input](ADR-0015-multiomics-model-input.md)
- [P19 Controlled Pack Factory](ADR-0016-controlled-pack-factory.md)
- [P20 Virtual Cell Training Pipeline](ADR-0017-virtual-cell-training-pipeline.md)

关键 runbook：

- [Capability Runtime](runbooks/VIRTUALCELLPACK-CAPABILITY-RUNTIME.md)
- [Data Portal](runbooks/VIRTUALCELLPACK-DATA-PORTAL.md)
- [Multiomics](runbooks/VIRTUALCELLPACK-MULTIOMICS.md)
- [Golden Norman](runbooks/VIRTUALCELLPACK-GOLDEN-NORMAN.md)
- [Pack Product Surfaces](runbooks/VIRTUALCELLPACK-PRODUCT-SURFACES.md)
- [P9 OOD Validation](runbooks/VIRTUALCELLPACK-P9-OOD-VALIDATION.md)
- [P12 Model Zoo v2](runbooks/VIRTUALCELL-MODEL-ZOO-V2.md)（validation runbook）
- [P13 Model Adapter SDK](runbooks/VIRTUALCELL-MODEL-ADAPTER-SDK.md)
- [P14E E. coli K-12 Growth Contract](runbooks/VIRTUALCELL-ECOLI-K12-GROWTH-CONTRACT.md)
- [P15E S. cerevisiae Deletion-Fitness Contract](runbooks/VIRTUALCELL-YEAST-DELETION-FITNESS-CONTRACT.md)
- [P16E K562 Golden Delta Contract](runbooks/VIRTUALCELL-K562-GOLDEN-DELTA-CONTRACT.md)
- [P17 Virtual Experiment DAG](runbooks/VIRTUALCELL-VIRTUAL-EXPERIMENT-DAG.md)
- [P18 Multi-omics Model Input](runbooks/VIRTUALCELL-MULTIOMICS-MODEL-INPUT.md)
- [P19 Controlled Pack Factory](runbooks/VIRTUALCELLPACK-CONTROLLED-PACK-FACTORY.md)
- [P20 Virtual Cell Training Pipeline](runbooks/VIRTUALCELL-TRAINING-PIPELINE.md)
- [External Disk Git Maintenance](runbooks/EXTERNAL-DISK-GIT-MAINTENANCE.md)

---

## 31. 给其他项目或后续智能体的最短交接摘要

```text
PRAXIS-VirtualCell 当前是一个合同驱动、确定性运行、可审计且会诚实
abstain 的多物种虚拟细胞基础设施。

已完成产品阶段是 Phase 11，DOCS-CLOSURE completion 是
b19c896202bea56f894d0ad540501331af42a40c。Phase 12 Model Registry v2 以该 SHA 起步，
completion code SHA 是 1a5464fb0d2d9e105058f6797d92efd69783e5b2；工程完成不代表
真实科学验证或 promotion。P13 Model Adapter SDK 以
f83c13db386cb552b3ce7a5643e5ffbead0ff573 起步，completion code SHA 是
744d0a28d2cfc13d1b10e85b133b6c13b9426174；工程 COMPLETE，science NOT_RUN，policy
NO_NEW_DECISION。P14E 从 0b193310009d6e4d2ebc0fc8abf95da20a56acdb 起步，经 SDK
prerequisite c3401450fd79f7829c438d6b55c1902ea2f4cf5f，以
8778e93c31c2dfe1ef0f77f06e7a80a425633736（tree
fa85e049bb36f3fbd8e6d4a7503e4b5837ed7c78）完成 local E. coli K-12
knockout→growth-ratio 合同；工程 COMPLETE，science NOT_RUN，policy NO_NEW_DECISION，
executable=false。P14R/P14B 未授权、未运行。P15E 以
62480a3951173a2aa7b006403af9b169521db138（tree
64906691c4c989a843df4da97f0a93f32cd65ad2）完成 local S288C
single-deletion→fitness contract；工程 COMPLETE，executable=false，P15R/P15B/science/policy
未运行。P16E 从 d1e2e37b69784bd2f440cba34f51cfb56dcc00b2 起步，以
9f6b14ea84cb0884b2bde2ed4c67c73aeb5a37e2（tree
098cd563e3d865e080a0d121727b987e2d40ed18）完成 local K562 Golden
perturbation→delta-expression contract；工程 COMPLETE，executable=false，
P16R/P16B/science/policy 未运行。P17 从
ff525a0611901df422161a7143ebfe9d1e051008 起步，以
16636f1b2c36e0a0fabb782a662b5b3b934891e0（tree
321a59eed44c45bf2bb8798714352b3303b92e58）完成 deterministic direct-v2
Virtual Experiment DAG/Brain/decision 与 JobStore v3 contract。registry 为
5 releases / 0 native / 0 promoted，故所有真实 P17 direct-v2 请求 abstain；science NOT_RUN，policy
NO_NEW_DECISION，real multi-model acceptance pending。P18 从
f253664239e4b1c9665301cf1bdf4e117a3e9c31 起步，以
626c71ffd1ce18a5adc200f6a6e376e57b269beb（tree
2b570398caff6cf955d789c3cb4a7a77dc13a082）完成 exact Pack v0.3 typed
multi-omics model-input contract；工程 COMPLETE，science NOT_RUN，policy
NO_NEW_DECISION，真实 Broker/Registry/model acceptance pending。P19 随后从 P18 docs-closure
871c5a8a4265f5b8fe5c2c6e35d418644bf1c4be 起步，完成 receipt→candidate→review→
validation→registration contract、v2 index、explicit store/index 和 read-only projection；
completion code/tree 是 42eabe63ea1a444d8b2ad14cecba6c9d6fa351d5 /
b4bd63833adc89bd1e30e9595d2cb6b38a3e005f。真实 external fixture/output
root/operator/science/policy 未运行。P20 从
f53e29e5722a8fe48aa2eb6fe63be01f61b5cc9a 起步，以
a4003704b70f06eb65297ddd32e0695ae8ee146b（tree
d12d64a7c8d013d8d299272eea88a4ce0431ccab）完成 exact P19-bound Training Pipeline
contract；engineering COMPLETE — CONTRACT_ONLY，science NOT_RUN，policy NO_NEW_DECISION。
P21A 从 5f3fc2d88c20e8083fb66a4c3399c5fe148241be 起步，以
20ecc12542e5df40c90d1fc367dbe86b563478b8（tree
ffcd261dd7d506d0ad852023afcba0f5c97a2d72；epoch 1786050825）完成 frozen benchmark
system 和 negative ledger；engineering COMPLETE — SYSTEM_ONLY，science NOT_RUN，policy
NO_NEW_DECISION。P21B/P21C 未授权、未运行。P22 从 P21A docs-closure
09792e13e29a76b5e4434507f3334eefb947789c 起步，以
bca5ad661856e8d9aa832c47f23c6ad7179ee0c9（tree
f78476ac1dbe2f865e3c1bcdc71ecc512dbad22a；epoch 1786056220）完成 One-Pack/P21B
curated registry contract、default-deny trust、append-only lifecycle/checkpoint 与 redacted
Python projection；engineering COMPLETE — CONTRACT_ONLY，science NOT_RUN，policy
NO_NEW_DECISION。没有真实 release import/lifecycle，默认 P22 registry empty。P23A 从
2b5c28ac152857dfa1109de41ed5d5ddc7ab06a4 起步，以
2b894966cd00b2af2fafbf8f009566dd69f393a7（tree
00bd98b0fd14091f4528115dcc66730264d5803a；epoch 1786061504）完成 local evidence-only
synthetic conformance；它只投影 interaction evidence score，真实 release/data/execution 未运行，
receiver response/causal claim 被禁止。P23B 与 P24 均需独立授权，不能自动进入 fake scaffold。

当前 UI 是：
选择 Cell Context → Chat → 自动解析/运行 → Report/Abstain，
另有 Data Center 供搜索 12 个 cell presets，并只读展示同物种数据和 Pack
背景。Preset 不是持久化 Virtual Cell，当前 Chat 也没有绑定 Pack identity；P22 的
Python-only curated registry 与 P23A local/non-default interaction contract 均未接入 Data Center、
Chat、JobStore 或 runtime plan。

数据层已经支持 strict VirtualCellPack v0.1–v0.3、H5AD/H5MU、feature
contract、hash 和 provenance。模型层已有严格 ModelCard；P12 candidate 进一步
分离 artifact/environment/adapter/evidence/policy identity，并让 Pack-aware
compatibility/plan/job 对 exact bindings fail closed。P13 已提供严格 input/output、
prepared input、execution provenance 和 conformance contracts；v1 仍兼容，默认生产
registry 当前只注册 predict_delta_expression → delta_expression。P13 growth/fitness
adapters 仅在测试中；P14E 另有 local、non-default、typed-negative 的
predict_knockout_growth → growth_ratio contract adapter。后者不是 dummy，也不是生产
capability，更不能与 legacy ecoli_gem/GemWrapper 合并为真实执行能力。
P15E 另有 local、non-default、typed-negative 的 predict_deletion_fitness → fitness
contract adapter，同样不是 runtime-ready 或科学能力。
P16E 另有 local、non-default、typed-negative 的 K562 Golden
predict_delta_expression → delta_expression contract adapter；它与默认 generic delta
reference adapter 不同，也不进入默认 registry。
P17 复用这些 registry/adapter boundaries 形成 plan-only deterministic Brain/DAG；它
没有创建新生产能力，LLM candidate 不进入权威 decision 或 fingerprint。
P18 复用 Pack v0.3 和 alignment contracts 形成 typed joint input；adapter/Broker 字段
只是未解析 identity marker，不代表 registry compatibility 或 model execution。
P19 把 P7 receipt 与 exact reviewed/validated candidate chain 绑定到 factory registration；
P7 species 仍只作 routing hint，factory registration 也不代表 model compatibility/execution。
P20 把 exact committed registration 绑定到 frozen training job、pre-label leakage audit、fixed
-I -S worker、safe checkpoint/result 和 candidate-only model identity；stored P19 full tree 只作
历史 provenance；exact P19 store-chain 与 trusted repository source 另行重验。Pack-root live bytes
只包括 audit 前的 manifest/split 和 audit 后实际 train-consumed feature/label，且不声明 OS sandbox。
P21A 冻结 benchmark/evidence system，P22 冻结 curated release/store/trust/projection；两者均未运行
真实 P21B/P21C 或创建真实 release。P23A 复用 P13 envelope/provenance，绑定 synthetic P22/P19/P18/
P20/P21 references，只允许 supplied fixture 的 `interaction_evidence_score`；它不进入默认 registry，
也不执行真实 interaction model。

P12 legacy migration 不创建 evidence/policy/promotion；无法精确绑定的 P8/P9
结果保持 unbound/incomplete。registry lifecycle 是 append-only，Pack list/API 只
返回路径脱敏白名单投影。P12 没有真实 science run 或新 operator decision。
P13 同样没有真实模型、数据、权重、science run 或新 operator decision。P14E 也没有
读取/运行真实 GEM、SBML、growth data 或 solver，没有 benchmark/evidence/policy、release
或 promotion；P15E 也没有读取/运行真实 deletion screen/model/GEM 或生成
evidence/policy；P16E 也没有读取 H5AD、运行 candidate/additive comparator 或生成
MSE/CI/external evidence/policy。P17 同样没有运行真实多模型 science、P14R/P15R/P16R/B
或生成 promotion；P18 也没有读取外置 multi-omics assets、调用 model/Broker/Registry、
运行训练/benchmark 或生成 evidence/policy；P20 也没有真实 candidate、test/external、
benchmark/science evidence；P21A/P22/P23A 也没有真实 benchmark run、curated import、paired evidence、
model execution、receiver response 或 causal claim。Policy 保持 `NO_NEW_DECISION`；contract
conformance 只证明工程确定性。

数据存在不等于 Pack；Pack、registry、per-request compatibility/executable、
scientific evidence 和 product policy 是五个独立层次。只有 exact
request×Pack×model×environment×adapter×evidence×policy 全部满足时才执行；缺模型、
缺资产、缺 adapter、OOD、evidence 或 policy 不足时必须 abstain。LLM 只能解析和
解释，永远不能参与数值预测或最终裁决。

跨项目优先使用 vc.api.v1 REST API，并保存 exact git_sha、Pack/model
fingerprints、execution identity、provenance 和 trace。上传 API 只进入
quarantine，不会自动 QC、生成 Pack、训练模型或预测。

当前还没有任意细胞预测器、自动/公共写 Pack Factory、持久化 Virtual Cell、真实
Community model、Virtual Microbiome 或 biological world model。
```

---

## 32. 最终边界

PRAXIS-VirtualCell 的可信度不来自展示了多少物种、多少 cell card 或多少模型名称，而来自每次运行都能回答：

```text
使用了什么数据？
数据字节和语义是否验证？
使用了哪个模型和环境？
模型为什么兼容？
执行了哪些步骤？
证据来自哪个 benchmark？
当前是否 OOD？
为什么预测，或者为什么 abstain？
结果能否由相同 identity 重放？
```

只有这些问题都有可审计答案时，系统才产生其合同允许的结果。否则，诚实 abstain 就是正确的产品行为。
