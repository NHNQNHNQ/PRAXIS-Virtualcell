# ADR-0012：S. cerevisiae deletion→fitness contract

- 状态：Accepted（P15E engineering complete）
- 日期：2026-08-06
- 唯一起始基线：0ff6870a70a04d71098a16875e633f909e31cc5a
- Completion code SHA：62480a3951173a2aa7b006403af9b169521db138
- Completion tree：64906691c4c989a843df4da97f0a93f32cd65ad2
- 分支：codex/p15e-yeast-fitness-contract
- 前置：ADR-0009、ADR-0010、ADR-0011
- 范围：P15E；P15R 与 P15B 未运行

## 背景

P12 已分离 model、artifact、environment、adapter、evidence 和 operator-policy
identity，P13 已实现 strict、prepared-aware Adapter SDK，P14E 已证明窄任务可以在
不运行真实科学资产的前提下冻结 exact contract。此前 yeast_deletion_fitness 仍只是
planned legacy card；P10 yeast tiny Pack 是 synthetic scRNA contract fixture，不能
代表 deletion screen、模型、验证证据或产品能力。

P15E 只补齐 S. cerevisiae S288C gene-deletion→fitness 工程合同。它不读取、下载或
运行真实 deletion screen、H5AD、模型 artifact、GEM 或 Cobra path，不训练或评估模型，
不创建 scientific evidence，也不作 operator policy 决定。真实资产与科学运行属于
P15R；产品 policy 属于 P15B。

## 决策

### 1. 公开任务是 exact S288C 单基因 deletion 的 assay-defined fitness

任务冻结为：

| 项 | 冻结值 |
|---|---|
| task | predict_deletion_fitness |
| output | fitness |
| shape | (1,) |
| unit | dimensionless |
| reference | matched_non_deletion_control_same_condition_platform |
| species | NCBITaxon:4932 / Saccharomyces cerevisiae |
| strain | NCBITaxon:559292 / Saccharomyces cerevisiae S288C |
| assembly | R64 / GCF_000146045.2 |
| request gene namespace | SGD，版本与 fingerprint 由 exact scope 绑定 |
| request ID format | sgd_systematic |
| target grammar | `^Y[A-P][LR][0-9]{3}[CW](?:-[A-Z])?$` |
| perturbation | exactly one complete gene deletion |
| value semantics | prepared_scope_assay_defined_scalar |

公开值是 wrapper 已按 exact assay/condition/control/platform 语义定义的一个 finite
fitness scalar。Adapter 原样传递该值，不执行 ratio、normalization、clipping 或
range cap；因此负 finite fitness 也是合法合同值。该合同不允许 symbol、大小写修复、
ortholog、NCBIGene、assembly fallback 或隐式单位转换代替 canonical SGD systematic
identity。

### 2. 冻结九个 P15E versioned contracts

| 合同 | schema | 职责 |
|---|---|---|
| YeastDeletionFitnessScope | vc.yeast-deletion-fitness-scope.v1 | 绑定物种、S288C、R64、模型、artifact、环境、Pack、mapping、condition、control、assay、platform、fitness semantics、target universe 与 inference scope |
| YeastFitnessValidationProtocol | vc.yeast-deletion-fitness-validation-protocol.v1 | 预登记未来 P15R split、baseline、metric、paired CI、independent condition/platform、seed、zero-adaptation 与 OOD 门 |
| YeastFitnessDataBinding | vc.yeast-deletion-fitness-data-binding.v1 | 绑定未来 deletion-fitness screen Pack identity 与 assay semantics |
| YeastFitnessExecutionBinding | vc.yeast-deletion-fitness-execution-binding.v1 | 绑定 condition、control、assay、platform、target universe、runner 与 inference configuration |
| YeastFitnessGeneMappingBinding | vc.yeast-deletion-fitness-gene-mapping-binding.v1 | 绑定 exact SGD systematic ID→model target-universe mapping asset |
| YeastFitnessCompatibilityBinding | vc.yeast-deletion-fitness-compatibility-binding.v1 | P15E typed negative preflight |
| YeastDeletionFitnessAdapterInputContract | vc.yeast-deletion-fitness-adapter-input-contract.v1 | 冻结 task/input 及全部 required bindings |
| YeastDeletionFitnessAdapterOutputContract | vc.yeast-deletion-fitness-adapter-output-contract.v1 | 冻结 scalar fitness、unit、reference、uncertainty、OOD 与 abstain |
| YeastDeletionFitnessPreparedModelInput | vc.yeast-deletion-fitness-prepared-model-input.v1 | 保存 exact prepared model input 与全部交叉 fingerprint |

合同均 strict、frozen、拒绝 unknown fields、隐式类型漂移、隐藏/excluded/computed
Pydantic fields、声明外 subtype fields、dataclass/MappingAssetRef drift 和 nested
model_copy extras。canonical JSON bytes 的小写 SHA-256 是 fingerprint；不兼容语义
变化必须使用新的 schema/version。

### 3. Validation protocol 是预登记，不是 evidence

YeastFitnessValidationProtocol 固定：

- split_unit=held_out_biological_group；
- biological_group_keys=(target_gene_id, condition_id, replicate_group_id)；
- baseline=training_mean_fitness_same_condition；
- primary_metric=mean_squared_error_fitness，lower_is_better；
- paired_ci_required=true；
- independent_condition_required=true；
- independent_platform_required=true；
- external_adaptation_steps=0；
- validation_only_tuning=true；
- stochastic_seeds=(11, 23, 37)，且任意 v1 record 至少三个不重复、非负、
  JSON-safe integer seeds；
- OOD axes 依次为 strain、assembly、assay、condition、control、platform、
  gene_namespace、target_universe、target；
- record_role=preregistration_not_evidence。

输出 reference 与评估 baseline 故意不同：前者定义单个 assay fitness 值的 matched
non-deletion control，后者定义未来模型比较器。Protocol 不包含 benchmark result、
scientifically_validated、promotion_eligible 或 production_promoted；P15E conformance
不能代替 P15R scientific evidence。

### 4. P15E compatibility 必须是明确负状态

YeastFitnessCompatibilityBinding 固定：

- assets_verified=false；
- executable=false；
- reason=p15r_not_authorized。

测试使用 synthetic、identity-only ArtifactIdentity、EnvironmentIdentity、
ModelReleaseRecord、Pack/data、mapping 和 execution bindings 检查交叉约束。模型
artifact 仅声明为 application/json 与 data_only；fixture 没有对应真实文件，不证明
许可、可加载性、执行能力或科学正确性。synthetic release 不带 evidence 或 policy。

YeastDeletionFitnessAdapter 只能由测试或未来明确获授权的集成代码放入本地
AdapterRegistry。DEFAULT_ADAPTER_REGISTRY 继续只包含
predict_delta_expression→delta_expression；P15E 不修改 registry.yaml、planned legacy
card、wrapper、routing、case dispatch 或核心 runtime。

### 5. Prepared input 必须绑定完整 exact scope

prepare_input 同时核对：

- request task/output/unit、taxon、strain、assembly、single SGD target 与 complete
  deletion semantics；
- exact condition、matched control、assay、platform、fitness semantics 和 target
  universe IDs/fingerprints；
- model release、application/json data-only artifact、environment 与 adapter identities；
- deletion-screen Pack/data binding；
- SGD namespace version/fingerprint 与 exact mapping asset；
- runner/inference configuration binding；
- typed negative compatibility；
- validation protocol 与 exact scope。

缺任一 binding、fingerprint/type 漂移、unsafe load policy、错 media type、错
namespace/target、跨 request prepared input，或把 P10 yeast tiny scRNA/NCBIGene
fixture 重新贴标签冒充 fitness data 时一律 fail closed。SDK 不打开 identity 指向的
路径，也不从目录、legacy card、GEM 或模型名字猜 fallback。

### 6. Output 只允许 prepared-bound finite scalar

Wrapper raw output 必须精确包含 prediction、prediction_status、scope_fingerprint、
uncertainty、ood、abstain 和 abstain_reasons。成功路径要求：

- prediction_status=success；
- prediction 只含 fitness、fitness_semantics_id、reference、unit；
- fitness 为 finite JSON-safe number，原样保留，不施加正值或区间限制；
- semantics/reference/unit 与 prepared scope exact 相等；
- uncertainty available=false、calibrated=false、value/sigma 均为空，
  method=not_available，reason=no_calibrated_uncertainty_declared；
- OOD 未检测。

target_not_found、unsupported_scope 或 error 都必须 value-free abstain 并给出原因。
unsupported_scope 必须同时声明 detected OOD、canonical dimension 与 reason；任何 OOD
都必须 value-free abstain。Envelope 和 projection 必须携带 exact prepared binding。
Adapter 故意拒绝 standalone validate_envelope、project_output 和 aggregate；公开
projection 只能是 fitness。

Raw、metadata 或 projection 中出现额外 prediction、normalization、GEM、expression、
evidence、policy 或 promotion 字段都被拒绝。Uncertainty 的 neutral unavailable
语义不编码 P15R 授权状态；授权状态只存在于 typed compatibility record。

### 7. Conformance 只是 synthetic engineering evidence

Canonical fixture 使用测试内 identities、fitness=-0.25 和 deterministic raw
dictionary，证明 prepared input、envelope、projection 与 conformance fingerprint
可重复。它不加载数据或模型，不测 MSE，不执行 baseline/paired CI/independent
condition/platform/OOD science gate。

冻结 fingerprints：

| Identity | SHA-256 |
|---|---|
| adapter | b1aa00416fd851b3b340bf54fcfc702bb3406e6b7007d5f80c3e46616a5e357f |
| input contract | f17599d4c40142d5b07628e1d14142d05535eab23deccb8d61f40ed040262597 |
| output contract | adbf56f663b072483680fdce3bb7faa4109639b3663d35332db1e8f7ad9303ea |
| synthetic artifact | 5ae9b7ae69ba01c34cd7ddeb307dfbf69458fd369290e97ac286a24e1e755dcf |
| synthetic environment | 34a38273d839f1a2eddabc5ba3cbbc5e00fa8521198e403a60f8e013a019f291 |
| synthetic model release | c0f476559c7d586b254e0a15126e29a684a549a2a855b64d6e5e57d85fb6e5d7 |
| synthetic mapping | 71375cb49f543f9d5600b983738c87b1ef9d27489bc9f80779838ea7fb00cd83 |
| synthetic execution | 5a1e7dafaa619b1a15b95029aa26b2a1ebcf4bfd8b8dcb56096f0c443cdc4e29 |
| synthetic Pack/data binding record | f3dfbfe59d6f9277ba6d6b6255e45f4f45ab915d55d27a565535e94233535097 |
| synthetic compatibility | b63327a28621ed05de6884fa4d9b701f7540570b9fed97e40346aa73c7a9f574 |
| synthetic scope | b0260216a68850faad4d45469d2e649f2e0fb61ec326bf60279309af08e07e1b |
| synthetic protocol | 279c5aa53f58b55d0bc62e23eaafb08ecf6263ed20a405a426eb9738928645ea |
| synthetic prepared input | 1fc11d4129c7df92d1e5f5caba9c0934161b3b747398410ebd1ec485e88dd90d |
| synthetic envelope | 03f83e286066530e9daa38b0428f3283c8bc2f05cbd23dd2f8d70adf774812ee |
| synthetic conformance report | 80b43f37340f3c073a0fd479ca071718fce53dc99c2a7d69cd7c39aeebed75c3 |

## 被拒绝的方案

- 在 P15E 读取真实 deletion screen、H5AD、weights、GEM 或 Cobra path；
- 把 P10 yeast tiny scRNA fixture 或 planned legacy card 当作 fitness data/model/evidence；
- 在 DEFAULT_ADAPTER_REGISTRY、registry.yaml 或 runtime 注册 contract-only adapter；
- 从 gene symbol、NCBIGene、ortholog、大小写或 assembly 默认值猜 SGD mapping；
- 在 Adapter 内把 assay fitness 重算为 ratio、normalize、clip 或拒绝合法负值；
- 把 deterministic conformance、import success 或 wheel build 当作 scientific validation；
- 用 uncertainty 字段编码授权状态；
- 在没有正 P15R evidence 与具名 operator 的情况下创建 P15B promotion。

## 后果与限制

P15E 工程状态为 COMPLETE，但 P15 scientific capability 不是 complete。P15R 保持
AUTHORIZATION_REQUIRED / NOT_RUN，P15B 保持 NOT_RUN；science、real assets、GEM、
benchmark、external validation、evidence 与 operator policy 均未运行或创建。

两次 exact code clean-archive 完整 wheel build 字节相同，但严格官方离线依赖脚本因
本地 cache 缺 packaging==26.2 且网络被拒绝而 fail closed。该 limitation 不影响
contract test 结论，也不能被改写成 isolated dependency proof 或 release evidence。
P15E 没有 version bump、tag、push、artifact publication、release 或 deploy。

P9 negative result 保持 available=false、scientifically_validated=false，result SHA
abd1145c434fd4e48ac9d72e94e8e19d14a5b4011f03d05db4823dd91760da6e
不变。下一 eligible 本地工程 work unit 是 P16E exact K562
perturbation→delta_expression contract；P15R 与 P15B 保持独立授权窗口。
