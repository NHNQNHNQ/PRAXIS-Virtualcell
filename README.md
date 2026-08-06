# PRAXIS-VirtualCell

可信虚拟细胞扰动预测的可靠性治理系统：离线优先、可审计、可弃权。它的重点不是笼统宣称“更准”，而是在适用范围不足时明确拒绝、降级或弃权，并为结果保留证据与溯源。

用户描述物种、细胞场景和扰动任务后，系统把请求路由到适用的预测器或规则模块，产出包含治理裁决、证据边界和复现信息的 Markdown 报告。默认 `offline`，不需要 API key。

当前阶段事实：Phase 11B Cell-first 产品入口和 DOCS-CLOSURE 已完成；Phase 12
Virtual Cell Model Zoo v2 工程于
`1a5464fb0d2d9e105058f6797d92efd69783e5b2` 完成。Phase 13 Model Adapter SDK
从 `f83c13db386cb552b3ce7a5643e5ffbead0ff573` 开始，在
`744d0a28d2cfc13d1b10e85b133b6c13b9426174`（tree
`198e623120688d3704b9312990ddaa93c9a7b0e6`）完成本地工程，状态为
`P13_ENGINEERING_COMPLETE_P14E_ELIGIBLE`，现作为历史工程证据保留。Phase 14E 从
`0b193310009d6e4d2ebc0fc8abf95da20a56acdb` 开始，在
`8778e93c31c2dfe1ef0f77f06e7a80a425633736`（tree
`fa85e049bb36f3fbd8e6d4a7503e4b5837ed7c78`）完成本地 E. coli K-12
knockout→growth 工程合同，收口状态为
`P14E_ENGINEERING_COMPLETE_P15E_ELIGIBLE`，现作为历史工程证据保留。Phase 15E 从
P14E docs-closure `0ff6870a70a04d71098a16875e633f909e31cc5a` 开始，在
`62480a3951173a2aa7b006403af9b169521db138`（tree
`64906691c4c989a843df4da97f0a93f32cd65ad2`）完成本地 S. cerevisiae S288C
gene-deletion→fitness 工程合同，收口状态为
`P15E_ENGINEERING_COMPLETE_P16E_ELIGIBLE`，现作为历史工程证据保留。Phase 16E 从
P15E docs-closure `d1e2e37b69784bd2f440cba34f51cfb56dcc00b2` 开始，在
`9f6b14ea84cb0884b2bde2ed4c67c73aeb5a37e2`（tree
`098cd563e3d865e080a0d121727b987e2d40ed18`）完成本地 Human/K562 Golden Norman
perturbation→delta-expression 工程合同，当前收口状态为
`P16E_ENGINEERING_COMPLETE`。Phase 17 从 P16E docs-closure
`ff525a0611901df422161a7143ebfe9d1e051008` 开始，在
`16636f1b2c36e0a0fabb782a662b5b3b934891e0`（tree
`321a59eed44c45bf2bb8798714352b3303b92e58`）完成 deterministic Virtual Cell Brain
合同，状态为 `P17_CONTRACT_COMPLETE_REAL_MULTI_MODEL_ACCEPTANCE_PENDING_P18_ELIGIBLE`。
exact 验证与克制的科学/policy 边界见
[P12 完成报告](reports/phase12/PHASE12_COMPLETION.md)、
[P13 完成报告](reports/phase13/PHASE13_COMPLETION.md)和
[P14E 完成报告](reports/phase14e/PHASE14E_COMPLETION.md)及
[P15E 完成报告](reports/phase15e/PHASE15E_COMPLETION.md)和
[P16E 完成报告](reports/phase16e/PHASE16E_COMPLETION.md)及
[P17 完成报告](reports/phase17/PHASE17_COMPLETION.md)。P14R、P15R 与 P16R 的真实
asset/science run 均为 `AUTHORIZATION_REQUIRED / NOT_RUN`，P14B、P15B 与 P16B 均为
`NOT_RUN`。当前 registry 有 5 个 release、0 个 native、0 个 production-promoted
capability，因此 P17 没有真实多模型执行或验收，所有 direct-v2 Virtual Experiment
保持 abstain；下一 eligible 本地 gate 是尚未完成的 contract-only `P18 — Multi-omics`。

准确产品承诺是：任意符合显式合同的数据可以制作成 VirtualCellPack 接入；只有
存在匹配、可执行且经过验证并获 product policy 批准的模型时才产生预测，否则明确
abstain。

当前安装包版本来自 `pyproject.toml`，可用 `praxis-vc --version` 查询。GitHub、当前本地候选和 `.53` 的发布状态并不由版本字符串推断，请以 [三端同步台账](docs/status/SYNC-STATE.md) 为准。

## 安装与本地页面

要求 Python 3.11+（项目 CI 使用 3.13）以及 Linux 或 macOS。以下命令在源码仓库根目录执行：

```bash
git clone https://github.com/NHNQNHNQ/PRAXIS-Virtualcell.git
cd PRAXIS-Virtualcell
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[api]"
praxis-vc --version
```

源码可编辑安装的 `praxis-vc serve` 可以启动 API；若要让源码 checkout 在 `/` 同源托管 React 页面，先构建前端：

```bash
cd praxis_vc_react
npm ci
npm run build
cd ..
praxis-vc serve
```

浏览器打开 `http://127.0.0.1:8000`。安装自检脚本 `bash deploy/vc/check_install.sh` 仍是源码 checkout 专用；独立 wheel 与容器路径见 [安装指南](docs/INSTALL.md)。

完整 release wheel 由 `scripts/build_release_wheel.sh` 构建，内含 React 静态资源、CLI/API 代码、`praxis_vc_web/app.py` 和经过许可审查的默认 gene-set 数据；从 wheel 启动 `praxis-vc serve` 不依赖源码 checkout 或外置 `dist/`。`praxis-vc web` 的入口文件已打包，但运行 Streamlit 仍需安装 `web` extra；当前发行门只验证其打包和绝对路径接线，不声称完整 Streamlit server smoke。

发布容器从同一完整 wheel 安装，不复制源码到最终镜像。构建时必须注入候选 commit 和 epoch：

```bash
scripts/build_release_container.sh praxis-virtualcell:local
docker run --rm -p 127.0.0.1:8000:8000 \
  -v praxis-vc-runs:/var/lib/praxis-vc/runs \
  praxis-virtualcell:local
```

构建脚本拒绝把未提交的 tracked 内容或未知 untracked 文件标成当前 HEAD；受保护且已被 Docker context 排除的 `.claude/` 与 `string.jpeg` 不影响候选身份。容器以 UID/GID 10001 非 root 运行，在 `/api/health` 暴露产品版本与注入的 Git SHA，并同源提供打包后的 React 页面。完整构建首次仍需网络取得 npm 与 hash-locked Python wheels；最终安装阶段和运行时不访问包索引。

## 快速开始

```bash
# 结构化请求：离线确定性执行
praxis-vc run \
  --request examples/ahr_k562.json \
  --mode offline \
  --out runs/ahr

# 自然语言解析后确认执行
praxis-vc ask \
  --text "在 human K562 里敲掉 AHR 会怎么样" \
  --mode offline \
  --yes \
  --out runs/ahr
```

每次运行会生成 `runs/<job>/report.md`，包含 Question、Cell Context、Routing、Result、Governance Verdict、Evidence & Provenance、Biological Interpretation、Limitations 和 Reproducibility 九个确定性章节。

## 治理裁决

| verdict | 含义 |
|---|---|
| `accept` | 请求适用且证据足够，可以给出预测 |
| `caution` | 可以使用，但必须携带明确告警 |
| `downgrade` | 引擎存在，但数据或证据不足，只能降级解读 |
| `abstain` | 没有适用引擎，系统拒绝伪造预测 |

所有预测和治理终决由后端确定性 runtime 完成。LLM 只可参与自然语言解析、路由建议、critic 复核和报告润色，不能修改 prediction、hard rule、learned reliability、provenance 或最终 verdict。`llm_assisted` 需要 `DEEPSEEK_API_KEY`；缺少凭证或调用失败时回退到离线路径。

上述 `accept/caution/downgrade/abstain` 是现有 runtime verdict，不等于
`production_promoted`。P12 已把 artifact、environment、adapter、validation evidence
和 operator-policy 拆成独立 identity；工程完成不表示存在真实 evidence、具名
operator 决定或 production promotion。

## VirtualCellPack 与模型输入

可选 `omics` extra 提供严格、只读的数据合同：`vc.pack.v0.1/v0.2` 使用 H5AD，
`vc.pack.v0.3` 使用 H5MU，并显式区分完全配对和部分配对 observation。部分配对
不会为缺失 modality 造行或补零。

`vc.model-feature-contract.v1` 把模型要求的物种、assembly、modality、feature
namespace/version 和有序 feature ID 固定下来。默认必须逐字匹配；alias、
aggregate、drop、fill、reorder 只有被合同或 hash/version 绑定的 mapping asset
明确授权时才能执行，并写入 `vc.alignment-report.v1`。不存在自动 symbol
替换、Ensembl version 剥离、ortholog/同源转换或 mock fallback。

以下五层不能混用，也不是自动递进状态链：

- Pack：`pack_valid`；
- Registry：`cataloged / artifact_ready / revoked / superseded`；
- 每次请求计算：`model_compatible / environment_compatible / executable`；
- Scientific evidence：`benchmark_passed / scientifically_validated /
  promotion_eligible`；
- Product policy：`production_promoted`。

P12 以 `vc.model-registry.v2` 分层保存 `vc.model-artifact.v1`、
`vc.model-environment.v1`、`vc.model-adapter.v1`、
`vc.model-validation-evidence.v1`、`vc.model-operator-policy.v1` 和
`vc.model-release.v1`，并从 append-only lifecycle event 归约
`cataloged / artifact_ready / revoked / superseded`。旧 `vc.model-card.v1` 字节和
fingerprint 保持兼容；迁移只生成 `legacy_incomplete` release 和结构化
`legacy_status`，不生成 evidence/policy，不把 `planned/available/missing` 升级为
可执行、科学有效或 production promoted。Native `model_version` 必须是 path-safe
identifier；legacy raw 值只保留在内部 identity/fingerprint，若不安全，公开 catalog
中的 `model_version` 为 `null`，不会重写原值。

Pack-aware 产品路径生成 `vc.environment.v2`、`vc.compatibility-report.v2` 和
`vc.execution-plan.v2`，逐次核对 exact
request×Pack×release×artifact×environment×adapter×evidence×policy 及 lifecycle。
`model_compatible` 只表示 request×Pack×model；`adapter_compatible`、
`environment_compatible` 和 `executable` 分开计算。任一引用、hash、scope、环境、
adapter、evidence、policy 或 lifecycle 门缺失即产生空计划并弃权，不会 fallback 到
mock。`vc.compatibility-report.v1`、`vc.execution-plan.v1` 和无 Pack legacy adapter
仍可解析，但不是 P12 产品执行授权。

v2 compatibility/step 的 canonical identity 排除 runtime path 和公开 display-only
`model_version`；raw version 仍由 `model_fingerprint` 与 release fingerprint 约束，
因此 unsafe legacy version 脱敏为 `null` 不会改变 `plan_id`。`ExecutionPlanV2`
反序列化时重算 canonical `plan_id`，并核对 report、wrapper 和 agent 的 step binding。

当前 in-process 实例化只接受声明为 `safe_load_policy=data_only` 的 artifact，并在
计划和实例化时重复检查；`restricted_deserializer`、`isolated_runtime` 和
`unavailable` 均弃权。`data_only` 目前仍是 registry 声明，尚无类型级 wrapper loader
证明，因此不能把该字段当成任意权重安全加载证明。P12 没有下载或运行真实权重，也
没有新增任何真实 promoted release。

`EnvironmentIdentity.packages` 使用 PEP 503 distribution name+version；当次
`EnvironmentSnapshot.python_dependencies` 记录 import-module availability。两组名称
不是同一 namespace，不按字符串强行等同；exact environment 由 environment
fingerprint 及 lockfile/image digest 绑定。

P13 在 P12 `vc.model-adapter.v1` identity 上实现严格的本地 Adapter SDK：
`vc.adapter-input-contract.v1`、`vc.adapter-output-contract.v1`、
`vc.prepared-adapter-input.v1`、`vc.adapter-execution-provenance.v1`、
`vc.adapter-output-envelope.v1` 和 `vc.adapter-conformance-report.v1`。Broker/
CapabilityRegistry 准备 exact input，wrapper/ensemble 核验 output envelope，
reliability/critic 消费已验证状态，provenance/report 条件携带 envelope，governance
abstain 清除公开 output 并保留审计 provenance。其 provenance 绑定 exact request、
Pack、compatibility 和 adapter/input/output contract fingerprint。非法 shape/unit/type、
非有限值、漂移的 feature
alignment/provenance、未注册或混合 adapter 输出均 fail-closed。默认 registry 只注册
delta-expression reference adapter；P13 的 growth/fitness dummy 仅存在于通用 SDK
合同测试，不是生产 registry、真实模型或科学 evidence。P13 没有运行科学评估
（`Science: NOT_RUN`），没有
新增 operator policy（`Policy: NO_NEW_DECISION`），也没有 release、版本 bump、真实权重、
训练、下载或 production promotion。设计与操作边界见
[P13 ADR](docs/ADR-0010-virtualcell-model-adapter-sdk.md)和
[P13 runbook](docs/runbooks/VIRTUALCELL-MODEL-ADAPTER-SDK.md)。

P14E 只冻结 E. coli K-12 MG1655 单基因 knockout→`growth_ratio` 的严格工程
合同与合成 conformance。`EcoliK12KnockoutGrowthAdapter` 是 local contract-only
adapter，必须由测试或未来获授权的集成代码显式放入本地 `AdapterRegistry`；
它不在 `DEFAULT_ADAPTER_REGISTRY` 中，也没有修改 runtime route、wrapper 或 product
surface。P14E 没有读取或运行真实 GEM/SBML/data，没有 Cobra/solver 科学运行、
benchmark/evidence、operator promotion 或 release/deploy。设计、操作和完成边界见
[P14E ADR](docs/ADR-0011-virtualcell-ecoli-k12-growth-contract.md)、
[P14E runbook](docs/runbooks/VIRTUALCELL-ECOLI-K12-GROWTH-CONTRACT.md)和
[P14E 完成报告](reports/phase14e/PHASE14E_COMPLETION.md)。

P15E 只冻结 S. cerevisiae S288C（`NCBITaxon:559292`、R64、
`GCF_000146045.2`）单基因 deletion→`fitness` 的 strict、prepared-bound 工程合同。
`YeastDeletionFitnessAdapter` 只允许显式本地注册，negative compatibility 固定为
`assets_verified=false`、`executable=false`、`reason=p15r_not_authorized`；它不在
默认 registry、runtime route 或产品 surface 中。实现与测试分别位于
`praxis_virtualcell/model_zoo/yeast_deletion_fitness_contract.py` 和
`praxis_virtualcell/tests/test_yeast_deletion_fitness_contract.py`。P15E 只使用合成
identity/contract fixtures，没有读取或运行真实 deletion screen、model、GEM 或科学
benchmark，没有生成 evidence/policy、release、版本 bump、push 或 deploy。设计、操作
和完成边界见 [P15E ADR](docs/ADR-0012-virtualcell-yeast-deletion-fitness-contract.md)、
[P15E runbook](docs/runbooks/VIRTUALCELL-YEAST-DELETION-FITNESS-CONTRACT.md)和
[P15E 完成报告](reports/phase15e/PHASE15E_COMPLETION.md)。

P16E 只冻结 Human/K562（`NCBITaxon:9606`、`CVCL_0004`、GRCh38、Ensembl 84）
Golden Norman perturbation→`delta_expression` 的 strict、prepared-bound 工程合同。
`K562GoldenPerturbationAdapter` 分开绑定 single-gene 与 ordered combination scope，
只允许显式本地注册；negative compatibility 固定为 `assets_verified=false`、
`executable=false`、`reason=p16r_not_authorized`。A549 只作为 upstream metadata error
原样保留，不是请求 cell identity。实现与测试分别位于
`praxis_virtualcell/model_zoo/k562_golden_delta_contract.py` 和
`praxis_virtualcell/tests/test_k562_golden_delta_contract.py`。P16E 只读取 checked-in
小型 YAML/JSON identity manifests 并使用合成 5,045 维向量，没有读取 H5AD、运行
candidate/additive ridge、生成 MSE/CI/external evidence、修改 policy、release、版本、
push 或 deploy。设计、操作和完成边界见
[P16E ADR](docs/ADR-0013-virtualcell-k562-golden-delta-contract.md)、
[P16E runbook](docs/runbooks/VIRTUALCELL-K562-GOLDEN-DELTA-CONTRACT.md)和
[P16E 完成报告](reports/phase16e/PHASE16E_COMPLETION.md)。

P17 在不实例化 wrapper、不运行模型、不调用 LLM 的 direct exact `vc.request.v2` + exact
Pack 路径上编译 deterministic `vc.virtual-experiment-dag.v1`、immutable
`vc.virtual-cell-brain-context.v1` 与 contract-only abstain decision。Broker 的公开
plan-only 入口只生成既有 `ExecutionPlanV2`；LLM 只能提供严格候选 DAG，候选审计及其
独立 checksum 不进入 authoritative DAG/Brain/decision fingerprint。
`vc.job-execution-identity.v3` 绑定 Brain/DAG，并在有 companion 文件时拒绝降级、分裂
provenance、报告语义、trace/narrative 或重签篡改。测试内第五 taxon
`Danio rerio / NCBITaxon:7955` 只存在于临时 tiny fixture，未写入生产 registry 或
species route。当前 0 promoted capabilities，所以真实请求仍是空 DAG/abstain；该工程
完成不构成真实 multi-model acceptance、scientific evidence、policy、release 或 deploy。
设计、操作和完成边界见 [P17 ADR](docs/ADR-0014-virtual-cell-brain.md)、
[P17 runbook](docs/runbooks/VIRTUALCELL-VIRTUAL-EXPERIMENT-DAG.md)和
[P17 完成报告](reports/phase17/PHASE17_COMPLETION.md)。

P8 产品化收口随发行物提供三个合成、微型、可审计 Pack：
`p8-human-tiny`、`p8-mouse-tiny`、`p8-bacteria-tiny`。它们覆盖
`EnsemblGene` 与 `NCBIGene` 两种 feature namespace，均通过同一个既有
`PackRegistry` 完整验证；没有复制或转换 P7 大数据，也没有新增生产模型。

```bash
praxis-vc pack inspect /absolute/path/to/pack
praxis-vc pack validate /absolute/path/to/pack
praxis-vc pack register /absolute/path/to/pack
praxis-vc pack list
praxis-vc pack compatibility \
  --request request.json --pack-id p8-human-tiny --pack-version 1.0.0
praxis-vc pack run \
  --request request.json --pack-id p8-human-tiny --pack-version 1.0.0 \
  --mode offline --out runs/p8-example
```

`inspect` 明确返回未校验状态；`validate/register/list/compatibility/run` 均按当前
bytes 重验。只读 API 位于 `/api/packs`、`/api/packs/{id}/{version}`、
`/validate` 和 `/api/packs/compatibility`；服务器不提供 Pack register API。
`vc.pack-catalog.v1` 保持外层兼容，同时在 top-level `model_registry` 暴露路径脱敏的
`vc.model-registry-catalog.v2`，并在每个
`model_capabilities[*].registry_releases` 中只列该模型的 release 投影。React“数据
资源”页只显示后端验证/capability 字段，不复制科学路由。v2 Pack-aware job 使用
`vc.job-execution-identity.v2` 锁定 request、Pack、environment snapshot、release、
component、evidence、policy、structured report fingerprint 和 outcome；历史 v1 job
identity 仍可解析，`JobStore.load` 只做只读投影、不改旧 bytes，同名 job 仍不能覆盖。
P17 compilation-backed direct-v2 job 使用 `vc.job-execution-identity.v3`，在上述字段外绑定
Brain 与 DAG fingerprint；v1/v2/v3 只要存在 request/report/provenance/trace companions
就会重算并交叉核验，真正无 companions 的 historical identity-only 记录继续只读兼容。

P7 的“数据资源”页面提供独立的公开下载和隔离上传通道。公开目录使用 strict
`vc.data-catalog.v1`，只对外置数据根中 path、size、SHA-256 全部匹配的文件开放
下载；缺失或篡改文件保持不可用。上传需部署者配置至少 32 字符 bearer token，
成功后只生成 `vc.upload-receipt.v1` 并原样保存在 quarantine：

```bash
export PRAXIS_VC_DATA_ROOT=/absolute/path/praxis-virtualcell-data
export PRAXIS_VC_UPLOAD_TOKEN='<at-least-32-random-characters>'
praxis-vc serve
```

目录有效、文件可下载或上传成功都不等于 `pack_valid`、`model_compatible` 或
`scientifically_validated`。上传不会自动解包、归一化、补零、转换 feature、
注册 Pack 或参与预测；大数据仍不进入 Git。

P8 的 Norman/K562 Golden Pack 把一个公开真实数据集固定为可审计参考：source
H5AD、上游预处理 X/counts、有序 feature、三个 control guide、预定义
train/validation/test、condition-macro MSE、condition 级 bootstrap 和三个简单
baseline 全部 hash/版本绑定。每个 baseline 使用独立的一卡 registry 走正式
Pack→broker→governance→Report，不经 mock shortcut；未知/重复 canonical target
或篡改资产均 fail-closed。当前 test MSE 是 no-change `0.00620609`、global mean
`0.00458205`、additive ridge `0.00325706`，只适用于该冻结 benchmark。
`pack_valid=true` 与 `model_compatible=true` 仍保持
`scientifically_validated=false`；本阶段没有运行或访问 GEARS。

P9 进一步冻结 IID、perturbation、combination、cell type、donor、
dataset/platform、species、dose/time 八类 OOD 分组合同，并要求 biological unit
和 replicate 在评估前通过泄漏审计。随仓库提交的八轴 fixture 只证明合同，不是
八轴性能证据。真实的无适配外部验证固定为
`GSE67402 → GSE94117:glycerol_time_course`：4,484 个 feature 仅取原始 ID
精确交集，不补零、不做 symbol/ortholog 转换；阈值只在 source validation 选择。
候选主 MSE `1.06038358` 未胜 no-change `1.05333471`，paired 95% CI 跨 0，
因此 `available=false` 且 `scientifically_validated=false`。该失败结论是 P9
fail-closed 验收结果，不是待隐藏的异常。

P10 增加独立、无模型的 `vc.community-pack.v1` 前置接口：成员只按已经完整验证的
VirtualCellPack ID/version/fingerprint 引用，abundance、medium、compartment、
time、`well_mixed` space、共享代谢物 namespace 和 interaction evidence 全部显式
声明。E. coli 与合成 S. cerevisiae tiny Pack 只验证引用和合同可插拔性；toy
exchange 只做精确质量收支检查。当前没有真实 `CommunityModelAdapter`，因此
community plan 固定不可执行，run 只能 `prediction=null` 并诚实 abstain；不存在
单位/ID 转换、自动丰度归一或 mock fallback。完成项与尚缺实验验证见
[Community readiness checklist](docs/COMMUNITY-READINESS-CHECKLIST.md)。

架构和复现边界见 [ADR-0003](docs/ADR-0003-virtualcellpack-p5-multiomics-alignment.md)、
[ADR-0004](docs/ADR-0004-virtualcellpack-p6-capability-runtime.md)、
[ADR-0005](docs/ADR-0005-virtualcellpack-p7-data-portal.md)、
[ADR-0006](docs/ADR-0006-virtualcellpack-p8-golden-norman.md)、
[ADR-0007](docs/ADR-0007-virtualcellpack-p8-product-surfaces.md)、
[ADR-0008](docs/ADR-0008-virtualcellpack-p9-ood-validation.md)、
[ADR-0009](docs/ADR-0009-virtualcell-model-zoo-v2.md)、
[多组学 runbook](docs/runbooks/VIRTUALCELLPACK-MULTIOMICS.md) 与
[能力 runtime runbook](docs/runbooks/VIRTUALCELLPACK-CAPABILITY-RUNTIME.md)、
[数据资源库 runbook](docs/runbooks/VIRTUALCELLPACK-DATA-PORTAL.md) 和
[Golden Norman runbook](docs/runbooks/VIRTUALCELLPACK-GOLDEN-NORMAN.md)、
[Pack 产品面 runbook](docs/runbooks/VIRTUALCELLPACK-PRODUCT-SURFACES.md)、
[P9 OOD 验证 runbook](docs/runbooks/VIRTUALCELLPACK-P9-OOD-VALIDATION.md) 和
[Model Zoo v2 runbook](docs/runbooks/VIRTUALCELL-MODEL-ZOO-V2.md)、
[Community readiness checklist](docs/COMMUNITY-READINESS-CHECKLIST.md)。

## 能力边界

PRAXIS-VirtualCell 是带可靠性治理的操作层，不是通用或 SOTA 预测模型。历史
Phase 10 Gate 的可复现证据只支持以下克制表述；它不构成 P12
`ValidationEvidence`、operator policy 或 promotion：

- 当时记录的引擎级覆盖为四类：M2（真实 donor 证据来自 `.53` 历史亲验）、M3、M4
  和 M7。
- M1、M5、M8 属于 rule-based advisory；M6 以及 EMT、fate、spatial、communication 等路径存在明确 limitation。
- 历史本地 offline 流程中的 mock 只用于测试或演示 conformance，不构成生产预测、
  科学 evidence 或 product policy。
- 多模块结果表示路由计划中的多个 entry 与 advisory，不表示多个预测器已经完成证据融合。
- 更完整的 met / narrowed / unsupported / pending 边界以 [Phase 10 Gate](reports/phase10/PHASE10_GATE.md) 为准。

## 开发与测试

```bash
python -m pip install -e ".[dev,api,mechanistic,omics]"
python -m pip check
ruff check .

# VirtualCell 核心权威口径；真实 LLM 不在普通门中
pytest praxis_virtualcell/tests -m "not llm" -o addopts='' -q -ra

# 继承测试口径；排除容器、真实 LLM、GPU/checkpoint 和私网服务
pytest tests -m "not (integration or llm or remote)" -o addopts='' -q -ra

cd praxis_vc_react
npm ci
npm run typecheck
npm run lint
npm run build
CI=1 npm run e2e
```

当前精确结果、skip/deselect 含义、显式外部门和 GitHub CI 状态见 [测试指南](docs/TESTING.md)。普通测试默认不访问固定私网服务；`integration`、`llm`、`remote` 分别需要 `--run-integration`、`--run-llm`、`--run-remote`，一个测试拥有多个 marker 时必须同时满足对应门。

## 文档入口

| 文档 | 内容 |
|---|---|
| [当前项目与集成指南](docs/PRAXIS-VIRTUALCELL-CURRENT-PROJECT-AND-INTEGRATION-GUIDE.md) | 当前产品事实、P11–P17 边界和跨项目集成 |
| [P17 完成报告](reports/phase17/PHASE17_COMPLETION.md) | exact code/tree、deterministic contract 验证、reproducible wheel 与真实多模型验收未完成边界 |
| [P17 Virtual Cell Brain ADR](docs/ADR-0014-virtual-cell-brain.md) | authoritative DAG/Brain/decision、candidate isolation 与 JobStore v3 identity |
| [P17 Virtual Experiment DAG runbook](docs/runbooks/VIRTUALCELL-VIRTUAL-EXPERIMENT-DAG.md) | direct-v2 contract 审计、tamper/downgrade 检查与 fail-closed 解读 |
| [P16E 完成报告](reports/phase16e/PHASE16E_COMPLETION.md) | exact code/tree、本地 contract-only 验证、reproducible wheel 与 P16R/P16B 非运行边界 |
| [P16E K562 Golden delta ADR](docs/ADR-0013-virtualcell-k562-golden-delta-contract.md) | exact K562/P8 scope、ordered perturbation binding、prepared-bound 输出与 local-only adapter |
| [P16E K562 Golden delta runbook](docs/runbooks/VIRTUALCELL-K562-GOLDEN-DELTA-CONTRACT.md) | 本地 manifest/合同审计、定向验证、P16R 授权门和 fail-closed 解读 |
| [P15E 完成报告](reports/phase15e/PHASE15E_COMPLETION.md) | exact code/tree、本地 contract-only 验证、reproducible wheel 与 P15R/P15B 非运行边界 |
| [P15E S. cerevisiae deletion-fitness ADR](docs/ADR-0012-virtualcell-yeast-deletion-fitness-contract.md) | exact S288C scope、strict binding、prepared-bound 输出与 local-only adapter |
| [P15E S. cerevisiae deletion-fitness runbook](docs/runbooks/VIRTUALCELL-YEAST-DELETION-FITNESS-CONTRACT.md) | 本地合同审计、定向验证、P15R 授权门和 fail-closed 解读 |
| [P14E 完成报告](reports/phase14e/PHASE14E_COMPLETION.md) | exact start/code/tree、本地 contract-only 验证、P14R/P14B 非运行边界 |
| [P14E E. coli K-12 growth ADR](docs/ADR-0011-virtualcell-ecoli-k12-growth-contract.md) | exact scope、九个合同、prepared-bound 输出与 default-registry 隔离 |
| [P14E E. coli K-12 growth runbook](docs/runbooks/VIRTUALCELL-ECOLI-K12-GROWTH-CONTRACT.md) | 本地合同审计、定向验证、P14R 授权门和 fail-closed 解读 |
| [P13 完成报告](reports/phase13/PHASE13_COMPLETION.md) | 历史 exact code/tree、Adapter SDK 验证和 science/policy 非声明 |
| [P13 Model Adapter SDK ADR](docs/ADR-0010-virtualcell-model-adapter-sdk.md) | 六个严格 schema、identity binding、fail-closed 输出与兼容边界 |
| [P13 Model Adapter SDK runbook](docs/runbooks/VIRTUALCELL-MODEL-ADAPTER-SDK.md) | adapter 注册、conformance、运行时审计和定向验证 |
| [P12 Model Zoo v2 ADR](docs/ADR-0009-virtualcell-model-zoo-v2.md) | 当前分层 identity、迁移、fail-closed 和安全加载边界 |
| [P12 Model Zoo v2 runbook](docs/runbooks/VIRTUALCELL-MODEL-ZOO-V2.md) | 当前只读操作、验证命令和状态解释 |
| [P12–P30 顺序总提示词](docs/PHASE12-30-SEQUENTIAL-MASTER-PROMPT.md) | 当前状态机、动态 work-unit 选择和授权纪律 |
| [P12–P30 执行路线](docs/PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md) | 详细 scope、硬门和条件式授权模板 |
| [P12–P30 完成清单](docs/PHASE12-30-DETAILED-COMPLETION-CHECKLIST.md) | 工程、科学和 policy 分离的验收台账 |
| [P12–P30 协调提示词](docs/PHASE12-30-MASTER-PROMPT.md) | 长期协调边界；不得替代现场 Git 证据 |
| [P11A 设计](docs/PHASE11A-DATA-CENTRIC-UI-DESIGN.md) | P11A 历史实现说明；现行产品以 P11B 为准 |
| [文档地图](docs/INDEX.md) | 当前权威入口与历史材料分层索引 |
| [2026-07-18 项目状态](docs/status/PROJECT-STATE-2026-07-18.md) | 历史快照，不是当前阶段台账 |
| [三端同步台账](docs/status/SYNC-STATE.md) | 历史远程观测；使用前必须在获准窗口现场刷新 |
| [安装指南](docs/INSTALL.md) | pip、前端、Docker 现状和可选依赖 |
| [用户指南](docs/USER-GUIDE.md) | 历史 CLI/五阶段界面说明；Cell-first 现状以上述集成指南为准 |
| [版本契约](docs/VERSIONING.md) | 产品、协议、schema、artifact 和模型版本边界 |
| [Phase 10 Gate](reports/phase10/PHASE10_GATE.md) | 科学能力与远端证据边界 |

## 版本与同步流程

唯一允许的流向是：本地 feature branch → GitHub branch/CI → 审批合入 GitHub `main` → 本地 `main` fast-forward → `.53` 从同一 GitHub SHA fast-forward → 三端 SHA 核对。不要在 `.53` 直接开发，也不要把本地 tag 当成已发布 tag。

本轮 P17 contract/docs closure 窗口未刷新 GitHub 或 `.53`。规范工作树是
`/Volumes/T7/PRAXIS-virtualcell`，Git metadata 是
`/Users/mzy/Projects/.PRAXIS-virtualcell-gitdir`；任何远程数字只有带日期和 exact
identity 的只读记录意义。

历史整理分支曾按两次精确 D1a 授权把 GitHub `codex/project-consolidation` 快进到 `ee36d7948047f346f55a02d62ccaac84391e3c20`。对应的 [GitHub Actions run 29971566980](https://github.com/NHNQNHNQ/PRAXIS-Virtualcell/actions/runs/29971566980) 为 `4/5`：Python core、frontend/Playwright、reproducible wheel 和 Linux release container 通过，legacy 唯一失败是 Linux shell 子进程未随直接 shell 终止。修复提交 `6a8198771581d0897a13457e93e50cfec172d59a` 已把输出截断、timeout、pipe 异常和上层取消统一为进程组清理，并在 macOS/Python 3.13.12 与 Linux/Python 3.13.14 严格锁环境得到 legacy `1139 passed / 0 failed`。这些都是绑定旧 SHA 的历史证据，不授权当前工作单元 push、CI、release 或 deploy；GitHub `main`/tag、本地 `main` 和 `.53` 当前状态必须在未来获准窗口重新只读核对。

## 派生关系

本项目由 PRAXIS-2 commit `b124d66` 复制改造，继承 agent runtime、长期大脑、规则系统与反幻觉基础，并扩展 VirtualCell 大脑、预测器注册表和生物 benchmark。兼容运行时代码位于 `praxis2/`，产品代码位于 `praxis_virtualcell/`，本地 API/React 界面位于 `praxis_vc_api/` 与 `praxis_vc_react/`。详见 [PROVENANCE.md](PROVENANCE.md)。
