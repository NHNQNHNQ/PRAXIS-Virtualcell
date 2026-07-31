# PRAXIS-VirtualCell P0–P10 总结与剩余工作

> 文档角色：`FROZEN P0–P10 HISTORICAL SNAPSHOT — NOT CURRENT PHASE AUTHORITY`
>
> 状态日期：2026-07-29
>
> P10 完成 SHA：`5f2eb940c07f2cae5b664f35a57c407026d66587`
>
> GitHub 候选分支：`codex/p10-community-readiness`
>
> `.53` 部署分支：`codex/deploy-v1.6.0`
>
> 当时产品版本字符串：`1.6.0`
>
> 后续状态：P11B 已在
> `bf44aac25b993e49d0146ccd52dddad5c2fa14de` 完成；P12 尚未开始。当前接手以
> [项目与集成指南](PRAXIS-VIRTUALCELL-CURRENT-PROJECT-AND-INTEGRATION-GUIDE.md)
> 和 [顺序总提示词](PHASE12-30-SEQUENTIAL-MASTER-PROMPT.md) 为准。
>
> 规范工作树：`/Volumes/T7/PRAXIS-virtualcell`；Git metadata：
> `/Users/mzy/Projects/.PRAXIS-virtualcell-gitdir`

## 1. 项目目标与当前结论

PRAXIS-VirtualCell 的目标是建立一个可信、可审计、可扩展的虚拟细胞智能体基座：

1. 不修改核心 runtime，即可接入不同物种、细胞和组学数据；
2. 通过显式 Pack、模型和 feature contract 判断数据与模型是否兼容；
3. 有适用模型时执行预测，没有适用模型时诚实弃权；
4. LLM 只参与自然语言解析和结果解释，不掌握数据真相、数值预测或最终裁决；
5. 所有数据、模型、执行和报告都具有可复现 fingerprint 与 provenance。

截至 P10，**可信、可插拔的软件基座已经建立**，但
**“上传任意细胞数据后立即得到经过科学验证的虚拟细胞预测器”尚未实现**。

当前已经成立的准确表述是：

> 任意符合显式合同的物种和细胞组学数据都可以制作成
> VirtualCellPack 接入；只有存在匹配、可执行且经过验证并获 product policy
> 批准的模型时才产生预测，否则系统明确 abstain。

当前不能成立的表述是：

> 任意原始组学文件上传后都会自动转换成 Pack，且任意物种、任意细胞都已有
> 可泛化、科学有效的预测模型。

## 2. P0–P10 总览

| Phase | 核心交付 | 解决的问题 | 仍保留的边界 |
|---|---|---|---|
| P0 | 基座审计、三层状态、ADR、能力矩阵、Report/ActiveLearning 兼容修复 | 冻结科学边界和确定性基线 | 没有 Pack loader 或新模型 |
| P1 | 严格、版本化 request domain | 物种、细胞、模态、数据、扰动和任务不再依靠模糊字典猜测 | request valid 不代表数据或模型有效 |
| P2 | Pack manifest、资产路径、大小和 hash 严格验证 | Pack 可审计且不能通过路径逃逸或缺失资产伪造有效 | 只证明文件合同，不读取科学语义 |
| P3 | backed、只读 AnnData/H5AD adapter | 确定性加载和选择单组学数据 | 不做归一化、补零或隐式转换 |
| P4 | `vc.pack.v0.2` 标准科学语义和 legacy/MCP 收口 | 冻结物种、assembly、细胞角色、单位、条件、对照、split 和 leakage | 不提供模型兼容性 |
| P5 | `vc.pack.v0.3` H5MU 多组学与显式 feature alignment | 支持配对/部分配对多组学和可审计特征映射 | 不自动推断 alias、ortholog 或缺失模态 |
| P6 | strict ModelCard、CapabilityRegistry、ModelBroker、ExecutionPlan | Pack×request×model×environment 的 fail-closed 决策 | 默认 plugin runtime 只执行 `delta_expression` |
| P7 | 四物种数据资源库、受控下载、quarantine 上传和数据 UI | 用户可选择物种、下载公开数据或上传原始数据 | 上传不会自动制作或注册 Pack |
| P8 | 三物种 tiny Pack、Pack CLI/API/UI、历史 fingerprint；Golden Norman | 证明 Pack 产品面可插拔且 job 身份不可变 | tiny Pack 是 fixture；Golden baseline 不能泛化 |
| P9 | 八轴 OOD 合同、泄漏审计、选择性预测、无适配外部验证 | 证明负结果和跨数据集失败也会被诚实保留 | 外部候选未胜 no-change baseline |
| P10 | CommunityPack 前置合同、E. coli/yeast tiny Pack、质量守恒和无模型弃权 | 为多成员系统冻结引用、单位和执行边界 | 没有真实 CommunityModelAdapter 或 community world model |

## 3. 各阶段完成内容

### P0：冻结基座和科学边界

P0 审计了 request、runtime、SpeciesBrain、route table、case dispatch、
model zoo、Report、ActiveLearning 和测试口径，并完成：

- 定义并强制分离 `pack_valid`、`model_compatible`、
  `scientifically_validated`；
- 写入基座 ADR、能力矩阵和 P0 baseline；
- 修复 ReportAgent 丢失原始 request；
- 修复 ActiveLearning 产生 `genetic_hub@:unspecified`；
- 冻结代表性 structured report 和 9 段 Markdown hash；
- 保留确定性 runtime、governance 和 LLM 外层边界。

P0 没有实现 Pack loader、增加模型或修改 UI。

### P1：严格版本化请求

P1 把请求拆成显式、版本化且验证后不可变的 domain：

- species/taxon；
- cell identity、state 和 context；
- modality/assay；
- dataset reference；
- perturbation；
- task/output；
- model input/prediction bundle。

未知字段、缺失必填字段、错误嵌套结构和不完整 Pack identity 均在执行前拒绝。
系统不猜测 target、cell domain 或输出。

### P2：VirtualCellPack 文件合同

P2 建立 `vc.pack.v0.1`：

- manifest schema；
- taxon、license 和来源元数据；
- root-bound 相对路径；
- 文件大小和 SHA-256；
- manifest canonical fingerprint；
- traversal、绝对路径、逃逸 symlink、缺失资产和坏 hash 拒绝。

这一阶段证明的是 Pack 文件完整性，不等于模型兼容或科学验证。

### P3：AnnData/H5AD 确定性适配

P3 实现 backed、只读 H5AD adapter：

- 读取前保持 backed；
- 按源 observation/feature 顺序确定性选择；
- 保持 CSR/CSC 稀疏结构；
- canonical metadata 验证后不可变；
- 未知、重复或乱序 selection fail-closed；
- 不修改源文件。

它不做隐式归一化、补零、去重、ID 改写或随机 split。

### P4：标准数据语义与 legacy/MCP 收口

P4 建立 `vc.pack.v0.2` 的科学语义门：

- NCBITaxon 与 versioned assembly；
- canonical feature ID 和 namespace；
- cell identity/state/context 角色分离；
- condition、perturbation、target 和 control 外键；
- dose/time value 与 unit；
- named split 和 leakage guard；
- Cellosaurus accession 与 local CURIE 约束；
- 完整科学语义进入 canonical key；
- YAML、symlink 和验证快照保持 Pack 异常边界。

P4.1–P4.3 还完成 legacy 回归修复，并解决坏 MCP server 一秒握手超时与正常
FastMCP server 启动较慢之间的冲突，没有取消 fail-closed 超时。

### P5：多组学与显式 feature alignment

P5 建立 `vc.pack.v0.3` 和 H5MU adapter：

- 多 modality 声明和顺序；
- 完全配对与部分配对 observation；
- 全局 observation 为真实 modality observation 并集；
- 选择时只保留真实行；
- 不为缺失 modality 造行、补零或 impute。

同时建立 `vc.model-feature-contract.v1`：

- taxon、assembly、modality、namespace/version、ID format；
- 有序 feature ID；
- 显式 mapping asset 的版本和 hash；
- alias、aggregate、drop、fill、reorder 逐项 provenance；
- 生成 `vc.alignment-report.v1`。

默认是逐字严格匹配；只有合同显式授权时才执行转换。

### P6：Capability-driven runtime

P6 把 Pack-aware 主链连接到：

- strict `vc.model-card.v1`；
- `CapabilityRegistry`；
- `vc.compatibility-report.v1`；
- `ModelBrokerAgent`；
- `vc.execution-plan.v1`；
- plugin wrapper 实例化和输出治理。

兼容性逐项检查：

- request 与 Pack 的 taxon、modality、assay、cell domain；
- perturbation、task 和 output；
- feature namespace 和 representation；
- 模型 status、wrapper、asset、dependency 和 resource；
- runtime task/output adapter；
- uncertainty 和 OOD。

缺任一条件都会得到空 plan 或拒绝结果，不会 fallback 到 Mock。无 Pack 请求继续
走显式 legacy adapter。

当前通用 plugin output gate 只实现：

```text
predict_delta_expression → delta_expression
```

growth、fitness、embedding 和其他任务仍需要各自 execution adapter。

### P7：物种数据资源库和上传/下载

P7 实现独立于 Pack/runtime 的数据交换层：

- strict `vc.data-catalog.v1`；
- human、mouse、yeast、bacteria 四物种筛选；
- 4 个公开数据集、5 个文件；
- 总计 `27,823,623` bytes；
- 下载前重验 path、普通文件、size 和 SHA-256；
- bearer token、单文件上限、总 quota 和扩展名限制；
- 上传原字节保存到 quarantine；
- 原子生成 `vc.upload-receipt.v1`；
- React 数据资源页展示物种、资源状态、下载和上传。

P7 exact-SHA 部署历史实测：

```text
species          human, mouse, yeast, bacteria
datasets         4
files            5
all_available    true
upload_enabled   true
quarantine_only  true
```

上传成功只证明字节已被安全接收，不会自动解包、归一化、映射、注册 Pack 或参与预测。

### P8：Golden Pack 与 Pack 产品面

P8 包含两部分。

#### Golden Norman/K562

- 冻结 Norman/K562 公开 source、X/counts、obs/var 和 split；
- Pack 为 `91,205 × 5,045`；
- 原始数据和派生 Pack 放在 `.53` 外置数据根，不进入 Git；
- 无随机 split、补零、去重、symbol 或 ortholog 转换；
- 三个简单 baseline 各自使用严格模型卡和正式 runtime；
- 30 个 validation condition 和 116 个 test condition；
- no-change MSE `0.00620609`；
- global-mean MSE `0.00458205`；
- additive-ridge MSE `0.00325706`；
- 所有结果仍为 `scientifically_validated=false`；
- 没有运行 GEARS。

#### Pack 产品化

- 内置 `p8-human-tiny`、`p8-mouse-tiny`、`p8-bacteria-tiny`；
- human/mouse 使用 `EnsemblGene`，bacteria 使用 `NCBIGene`；
- CLI：`inspect/validate/register/list/compatibility/run`；
- 只读 API：list、inspect、validate、compatibility；
- React 只展示后端 validation/capability；
- HTTP 不提供 register；
- `vc.job-execution-identity.v1` 锁定 Pack 与 model/card fingerprint；
- 同名历史 job 不可覆盖；
- 无模型、错误 modality、cell domain、taxon 或非法跨物种输入均 abstain。

### P9：OOD 与外部验证

P9 冻结八类 OOD 轴：

1. IID；
2. perturbation；
3. combination；
4. cell type；
5. donor；
6. dataset/platform；
7. species；
8. dose/time。

grouped leakage audit 要求 biological unit 和 replicate identity 不能跨 partition，
不使用随机 cell split。

真实无适配外部验证为：

```text
source       GSE67402
external     GSE94117:glycerol_time_course
features     4,484 个原始 ID 精确交集
adaptation   0
```

主结果：

```text
candidate condition-macro MSE  1.0603835779
no-change condition-macro MSE  1.0533347059
paired difference 95% CI       跨 0
available                       false
scientifically_validated        false
```

候选未胜简单 baseline，因此不能进入产品预测。该负结果是 fail-closed 验收成功，
不是应被隐藏的执行异常。

### P10：CommunityPack 前置接口

P10 建立 `vc.community-pack.v1`：

- 成员 Pack ID/version/fingerprint；
- abundance 和精确 `fraction` sum；
- medium、compartment、time 和 `well_mixed` space；
- shared metabolite namespace；
- interaction evidence；
- E. coli 与 S. cerevisiae tiny member Pack；
- ID、单位、成员、compartment 和引用完整性；
- 单成员与原 RegisteredPack 等价；
- toy exchange 使用精确有理数质量收支；
- `CommunityModelAdapter` 抽象边界。

P10 没有实现真实 adapter。无模型时：

```text
execution_plan.executable = false
steps                     = []
prediction                = null
abstain                   = true
reason                    = community_model_unavailable
scientifically_validated  = false
```

## 4. P10 exact-SHA 代码、部署和验证历史

### Git 与部署

| 端点 | P10 记录状态 |
|---|---|
| 本地候选 | `codex/p10-community-readiness` at `5f2eb940...` |
| GitHub 候选 | `codex/p10-community-readiness` at `5f2eb940...` |
| GitHub `main` | `8e0d0634...`，尚未合入 P0–P10 |
| GitHub `v1.6.0` | peeled 到 `8e0d0634...`，未移动 |
| `.53` 部署仓 | `codex/deploy-v1.6.0` at `5f2eb940...` |
| `.53` 工作树 | 仅保留原有 `?? vc_api.log` |
| 网站 | `http://10.102.106.53:18080` |

当前 wheel SHA-256：

```text
a50c3295f9a01de592db4631fe7f06a267e906f6a7e38c83665830f10938025a
```

GitHub Actions
[run 30434482562](https://github.com/NHNQNHNQ/PRAXIS-Virtualcell/actions/runs/30434482562)
在精确 P10 SHA 上五项全绿：

1. Python lint and VirtualCell core；
2. Linux release container smoke；
3. Reproducible full release wheel；
4. Frontend build and Playwright；
5. Legacy unit tests。

### 测试证据

```text
P10 CommunityPack 定向             38 passed / 0 failed
Pack/capability/packaging/P10      192 passed / 0 failed
VirtualCell core                   1310 passed / 35 skipped /
                                   9 deselected / 0 failed
legacy                             1146 passed / 59 skipped /
                                   105 deselected / 0 failed
Ruff                               PASS
pip check                          PASS
```

skip/deselect 不能解释成外部模型、LLM、GPU 或远端科学能力通过。

### P10 产品面历史实测

部署 API 当前列出：

- 3 个内置产品 Pack：human、mouse、bacteria；
- P10 yeast Pack 已随发行物提供，但没有加入 P8 产品 catalog；
- 5 张默认模型卡；
- `ecoli_gem` 标记为 available；
- GEARS、scGPT、Norman mean baseline 和 yeast deletion fitness 均为 planned。

对部署中的 human/K562 Pack 实际运行 compatibility：

```text
pack_valid                 true
norman_mean model_compatible  true
scgpt model_compatible        true
environment_compatible       false
execution_plan.executable    false
steps                        0
```

这证明数据接入和兼容性判断已工作，但当前部署缺少可执行的人类模型资产/环境，
因此不会伪造预测。

`ecoli_gem` 虽有 available card，但当前 P6 通用 plugin runtime 没有 growth output
adapter；它不能被描述成任意 bacteria Pack 的通用预测模型。

## 5. 已经实现的用户目标

以下目标已经完成：

- 数据和模型合同与核心 runtime 解耦；
- 新 Pack 可通过 registry 接入，不要求增加物种专用 route 分支；
- 支持不同 taxon、assembly、cell domain、modality 和 feature namespace；
- 支持 H5AD 和 H5MU；
- 支持严格、显式、可追溯的 feature mapping；
- 支持物种数据浏览、下载和受控上传；
- 支持 Pack CLI、只读 API 和 React capability 展示；
- 支持 Pack×request×model×environment 的兼容性规划；
- 支持 plugin wrapper；
- 支持不可变 job/Pack/model fingerprint；
- 支持无模型、坏资产、错误物种/模态/cell domain 时诚实 abstain；
- LLM 不能改变数据真相、数值预测和最终裁决。

## 6. 尚未实现的最终目标

### 6.1 上传数据不能直接成为 Pack

当前上传通道只保存原字节和 receipt。仍缺：

- 文件结构识别；
- manifest authoring；
- taxon/assembly/cell ontology/feature namespace 向导；
- 单位和 value semantics 声明；
- condition/control/split 配置；
- 显式 mapping asset；
- 预览验证报告；
- 人工确认；
- 受控 Pack register。

这些步骤不能通过静默归一化或猜测来替代。

### 6.2 产品端缺少完整 Pack 管理闭环

当前 HTTP API 是只读的，没有：

- 管理员 Pack register/unregister；
- 审批状态；
- 版本升级与 supersede；
- 多用户/租户隔离；
- Pack storage lifecycle；
- 数据、Pack 和模型之间的产品化关联页。

P10 yeast Pack 也尚未进入用户可见产品 catalog。

### 6.3 模型插件能力不足

当前通用 output adapter 只支持 `delta_expression`。仍需：

- growth；
- fitness；
- absolute expression；
- embedding/state；
- protein abundance；
- chromatin accessibility；
- spatial output；
- phenotype 和其他任务 adapter。

每种 adapter 都必须有严格输入、输出、不确定性和 OOD 合同，不能用一个宽松
`dict` 代理所有任务。

### 6.4 缺少可用模型和权重

大部分默认模型仍为 planned。需要：

- 合法来源和许可；
- 外置权重存储；
- SHA-256 与模型卡绑定；
- 可重建 runtime 环境；
- 资源声明；
- 模型加载和 output adapter；
- calibration、uncertainty 和 OOD；
- 独立 benchmark。

模型卡存在、wrapper import 成功或 asset 可下载都不等于模型科学有效。

### 6.5 缺少“用户数据训练/适配模型”的通道

要让新物种或新细胞真正变成预测型虚拟细胞，需要：

- 从 RegisteredPack 生成训练输入；
- 预声明 train/validation/test biological groups；
- 防止 donor/cell/replicate 泄漏；
- baseline；
- 训练和 fine-tuning；
- checkpoint、环境和随机性 provenance；
- 指标、置信区间和失败门；
- 模型卡与 Pack fingerprint 双向绑定；
- checkpoint/model、科学 evidence、`promotion_eligible` 和 operator
  `production_promoted` 分别形成不可变 identity；
- registry 不创建科学 evidence 或 product policy；只有 exact request×Pack×model×
  environment×adapter×evidence×policy 全部满足时才可执行。

### 6.6 缺少足够的真实多物种科学验证

当前：

- human Golden 只覆盖 Norman/K562 冻结 benchmark；
- mouse 只有 tiny Pack 与公共数据资源，没有真实预测验证；
- bacteria 的 P9 外部候选未胜 no-change；
- yeast 只有数据资源和 tiny contract Pack；
- community 只有合同和 toy mass balance。

仍需在多个真实物种、cell type、donor、dataset/platform 和实验条件上，按预注册
protocol 验证，并与简单 baseline 比较。

### 6.7 “任意细胞”不能作为无边界科学承诺

任何有限模型都不能证明对所有物种和所有细胞有效。最终产品应声明：

- 已支持的 taxon；
- 已支持的 cell domain；
- 已支持的 modality/assay；
- 已支持的 perturbation/task/output；
- 模型训练域；
- OOD 与 abstain 规则；
- 验证证据等级。

目标应是“任意合规数据可接入、已验证范围可预测、其余诚实弃权”，而不是无条件
承诺任意细胞都能可靠预测。

### 6.8 Community world model 尚未开始

P10 只冻结接口。仍缺：

- 真实 monoculture/co-culture 数据；
- uptake/secretion 和 extracellular metabolomics；
- growth、biomass 和 abundance time series；
- metabolite ontology/mapping；
- community GEM/dFBA、ODE、生态、图或其他真实模型；
- spatial、diffusion、migration 和 time integration；
- `CommunityModelAdapter` 实现；
- 真实 benchmark、calibration、OOD 和实验验证。

### 6.9 部署和发布仍需正式收口

当前服务可用，但仍是独立 uvicorn 部署。仍缺：

- systemd/supervisor；
- TLS 和反向代理；
- 正式域名；
- 用户认证和权限；
- token rotation；
- object storage；
- quota、备份和恢复演练；
- metrics、日志轮转、告警和 SLA；
- GitHub `main`/tag 的独立审批发布；
- 部署版本和发布版本的长期一致性流程。

## 7. 建议的剩余工作优先级

> 本节是 P10 当时的 backlog，已被
> [Phase 12–30 权威执行路线](PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md)取代。
> 不得据此选择、跳过或授权当前 work unit。

### 优先级 A：实现最小真实闭环

1. 建立 Pack Factory：upload → author → validate → review → register；
2. 用一个仓库外的新物种或新 cell dataset 做完整 Pack；
3. 全程不修改核心 runtime；
4. 在 UI 中显示其 Pack、validation 和 compatibility；
5. 绑定一个真实模型或训练一个最小模型；
6. 在 held-out biological groups 上比较 no-change/mean baseline；
7. 通过后运行预测，不通过时保持 abstain。

这是判断基座是否真正实现用户目标的最关键闭环。

### 优先级 B：模型和任务插件 SDK

1. 固定 ModelAdapter 开发模板；
2. 增加 growth、fitness 等 output adapter；
3. 建立权重/环境外置 artifact registry；
4. 建立 training/fine-tuning job contract；
5. 建立模型 promotion gate；
6. 先支持少量明确任务，不宣称通用世界模型。

### 优先级 C：多物种真实验证

建议至少形成：

- human：多个 cell line/primary cell/donor；
- mouse：至少一个真实扰动或状态迁移任务；
- bacteria：growth/condition response 并胜简单 baseline；
- yeast：deletion fitness 或 condition response；
- 每类都包含独立 dataset/platform OOD；
- 所有失败结果原样保留。

### 优先级 D：产品和运维

1. Pack 管理员 API 和审批；
2. 用户/租户、权限和审计；
3. 大文件/object storage；
4. systemd、TLS、域名、监控和备份；
5. GitHub main/tag 正式发布；
6. 之后再考虑 community world model 和更多 UI。

## 8. 最终目标验收标准

只有以下闭环全部通过，才能说“虚拟细胞智能体基座真正实现了用户目的”：

1. 选择一个仓库外、此前未知的物种或细胞数据；
2. 用户通过受控界面上传；
3. 系统生成候选 Pack，但不静默转换数据；
4. 用户明确确认 taxon、assembly、cell domain、modality、feature、单位和 split；
5. Pack 完整验证并注册，不修改核心 runtime；
6. Pack 在 CLI/API/UI 中可见；
7. 系统生成具体 request 的 compatibility report；
8. 只有存在匹配、可执行、经过验证并获 product policy 批准的模型时执行，否则
   abstain；
9. 模型在 held-out biological groups 上胜过预声明 baseline；
10. 所有 Pack、mapping、model、environment、job 和 report fingerprint 被锁定；
11. 错误物种、modality、cell domain、feature namespace 和非法跨物种迁移全部拒绝；
12. 在至少三个真实物种和多个 cell domain 上重复该流程。

通过这些标准后，可以声称：

> PRAXIS-VirtualCell 是一个数据和模型均可插拔、对已验证范围可执行、对未知范围
> 会诚实弃权的虚拟细胞智能体基座。

即使通过，也不应声称：

> 系统已经对自然界所有物种、所有细胞和所有扰动具有统一、无限制的科学预测能力。

## 9. 后续阶段必须保持的不变量

- Pack：`pack_valid`；
- Registry：`cataloged / artifact_ready / revoked / superseded`；
- 每次请求计算：`model_compatible / environment_compatible / executable`；
- Scientific evidence：`benchmark_passed / scientifically_validated /
  promotion_eligible`；
- Product policy：`production_promoted`；
- 上述五层永不合并，也不自动递进；
- LLM 只解析和解释，不参与数据真相、数值预测或最终裁决；
- 不静默归一化、补零、去重、随机 split 或同源转换；
- 不 fallback 到 mock；
- 大数据和模型权重不进入 Git；
- Pack、feature、mapping、model、adapter、environment、evidence 和 policy 必须
  version/hash/fingerprint 绑定；
- runtime 和 governance 保持确定性；
- 失败、负结果和 abstain 是有效结果，不得隐藏；
- 历史 job 的 Pack/model fingerprint 不得重写；
- 新能力必须使用新 identity 和独立验证证据。

## 10. 权威资料

- [当前项目与集成指南](PRAXIS-VIRTUALCELL-CURRENT-PROJECT-AND-INTEGRATION-GUIDE.md)
- [Phase 12–30 顺序总提示词](PHASE12-30-SEQUENTIAL-MASTER-PROMPT.md)
- [Phase 12–30 执行路线](PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md)
- [Phase 12–30 详细完成清单](PHASE12-30-DETAILED-COMPLETION-CHECKLIST.md)
- [Phase 12–30 协调提示词](PHASE12-30-MASTER-PROMPT.md)
- [能力矩阵](VIRTUALCELLPACK-CAPABILITY-MATRIX.md)
- [测试口径](TESTING.md)
- [版本合同](VERSIONING.md)
- [P0 基线](P0-BASELINE.md)
- [P8 Golden ADR](ADR-0006-virtualcellpack-p8-golden-norman.md)
- [P8 产品面 ADR](ADR-0007-virtualcellpack-p8-product-surfaces.md)
- [P9 OOD ADR](ADR-0008-virtualcellpack-p9-ood-validation.md)
- [Community readiness checklist](COMMUNITY-READINESS-CHECKLIST.md)
- [数据资源库 runbook](runbooks/VIRTUALCELLPACK-DATA-PORTAL.md)
- [Pack 产品面 runbook](runbooks/VIRTUALCELLPACK-PRODUCT-SURFACES.md)
- [P9 OOD runbook](runbooks/VIRTUALCELLPACK-P9-OOD-VALIDATION.md)
