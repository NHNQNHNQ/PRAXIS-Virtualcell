# ADR-0011：E. coli K-12 knockout→growth contract

- 状态：Accepted（P14E engineering complete）
- 日期：2026-08-06
- 唯一起始基线：0b193310009d6e4d2ebc0fc8abf95da20a56acdb
- SDK trust-boundary prerequisite：c3401450fd79f7829c438d6b55c1902ea2f4cf5f
- Completion code SHA：8778e93c31c2dfe1ef0f77f06e7a80a425633736
- Completion tree：fa85e049bb36f3fbd8e6d4a7503e4b5837ed7c78
- 分支：codex/p14e-ecoli-growth-contract
- 前置：ADR-0009、ADR-0010
- 范围：P14E；P14R 与 P14B 未运行

## 背景

P12 已分离 model、artifact、environment、adapter、evidence 和 operator-policy
identity，P13 已实现严格 Adapter SDK。此前 growth 只在通用 SDK 测试中作为 dummy
合同出现，没有冻结可供真实 E. coli 工作复用的物种、菌株、GEM、medium、condition、
gene mapping、solver 和 output 语义。

P14E 只补齐该工程合同。它不读取、下载或运行 GEM、SBML、growth/essentiality data
或真实模型，不调用 Cobra，不运行 benchmark，也不创建 scientific evidence 或
operator policy。真实资产和科学运行属于 P14R；产品 policy 属于 P14B。

## 决策

### 1. 唯一公开任务是单基因 knockout 的相对 growth

任务冻结为：

| 项 | 冻结值 |
|---|---|
| task | predict_knockout_growth |
| output | growth_ratio |
| shape | (1,) |
| unit | dimensionless |
| reference | wild_type_same_gem_medium_condition |
| species | NCBITaxon:562 / Escherichia coli |
| strain | NCBITaxon:511145 / E. coli K-12 MG1655 |
| assembly | GCF_000005845.2 |
| request gene namespace | NCBIGene |
| request ID format | canonical NCBIGene CURIE |
| perturbation | exactly one gene knockout |

公开值只允许 knockout objective 除以同一 GEM、medium、condition 和 objective 下的
wild-type objective。绝对 growth、essentiality、resistance、gene expression 和 flux
都不是 P14E 产品输出。调用方不得用 symbol、大小写、ortholog、assembly stripping 或
隐式单位换算替代 exact NCBIGene identity。

### 2. 冻结九个 P14E versioned contracts

| 合同 | schema | 职责 |
|---|---|---|
| EcoliGrowthScope | vc.ecoli-growth-scope.v1 | 绑定完整物种、模型、资产、环境、Pack、mapping、medium、condition、objective 和 solver scope |
| EcoliGrowthValidationProtocol | vc.ecoli-growth-validation-protocol.v1 | 预登记未来 P14R split、baseline、metric、CI、external 和 OOD 门 |
| EcoliGrowthDataBinding | vc.ecoli-growth-data-binding.v1 | 绑定未来 growth-condition Pack identity |
| EcoliGrowthExecutionBinding | vc.ecoli-growth-execution-binding.v1 | 绑定 medium、condition、objective 与 deterministic solver configuration |
| EcoliGrowthGeneMappingBinding | vc.ecoli-growth-gene-mapping-binding.v1 | 绑定 exact NCBIGene→GEM mapping asset |
| EcoliGrowthCompatibilityBinding | vc.ecoli-growth-compatibility-binding.v1 | P14E 的 typed negative preflight |
| EcoliGrowthAdapterInputContract | vc.ecoli-growth-adapter-input-contract.v1 | 冻结 task/input 及全部 required bindings |
| EcoliGrowthAdapterOutputContract | vc.ecoli-growth-adapter-output-contract.v1 | 冻结 scalar ratio、unit、uncertainty、OOD、abstain 与 trace-only flux |
| EcoliK12KnockoutGrowthInput | vc.ecoli-growth-prepared-model-input.v1 | 保存 exact prepared model input 与全部交叉 fingerprint |

这些合同均 strict、frozen、拒绝 unknown fields、隐式类型转换、隐藏 Pydantic fields、
声明外 subtype fields、dataclass type drift 和 nested model_copy extras。canonical JSON
bytes 的小写 SHA-256 是其 fingerprint。任何不兼容语义变化都需要新 schema/version，
不能在 v1 下静默放宽。

Validation protocol 只是未来科学运行的预登记合同，不是
vc.model-validation-evidence.v1，不包含 benchmark result、scientifically_validated、
promotion_eligible 或 production_promoted。

### 3. P14E compatibility 必须是明确负状态

P14E 的 EcoliGrowthCompatibilityBinding 固定：

- assets_verified=false；
- executable=false；
- reason=p14r_not_authorized。

Adapter 使用 synthetic、identity-only ArtifactIdentity、EnvironmentIdentity、
ModelReleaseRecord、Pack/data、mapping 和 execution bindings 验证交叉约束。这些 fixture
不代表资产存在、许可已审查、环境可执行或真实模型已运行。release fixture 不带
evidence 或 policy。

EcoliK12KnockoutGrowthAdapter 只可由测试或未来获得授权的集成代码显式放入本地
AdapterRegistry。DEFAULT_ADAPTER_REGISTRY 继续只包含
predict_delta_expression→delta_expression；P14E 不修改 registry.yaml、model card、
wrapper、route table、case dispatch 或核心 runtime。

### 4. 输入必须在准备阶段绑定完整 scope

prepare_input 同时核对：

- request 的 task/output/unit、species、strain、assembly、medium、condition 和单一
  NCBIGene target；
- model release、GEM artifact、environment 与 adapter identities；
- growth-condition Pack/data binding；
- exact NCBIGene→GEM mapping asset；
- medium、condition、objective、objective unit 和 solver configuration；
- typed negative compatibility；
- validation protocol 与 exact scope。

缺任一 binding、fingerprint 漂移、unsafe load policy、错 media type、错 namespace、
错 target、错 condition、跨 request prepared input 或把 p8-bacteria-tiny scRNA fixture
冒充 growth Pack 时一律 fail closed。SDK 不读取这些 identity 指向的资产，也不从目录、
环境或 legacy card 猜测 fallback。

### 5. 输出只允许 prepared-bound growth ratio

Wrapper raw output 必须具有 exact prediction、solver_status、scope fingerprint、
uncertainty、OOD、abstain 和 reasons 字段，且不得含其他字段。成功输出要求：

- solver_status=optimal；
- knockout objective 非负，wild-type objective 严格为正；
- objective unit 与 prepared scope exact 相等；
- uncertainty method 为 deterministic_fba，但 available=false、
  calibrated=false，且没有 value/sigma；
- OOD 未检测；
- ratio 为 finite、非负 scalar。

非 optimal solver、OOD、target_not_found 或 error 必须 value-free abstain 并给出原因。
OOD axes 只允许 strain、assembly、gem、medium、condition、gene_namespace 和 target。
deterministic 只描述同一输入的求解器行为，不证明结果正确，也不能伪造 calibrated
uncertainty。

Envelope、projection 和 conformance 都必须携带 exact prepared input。该 adapter
故意拒绝 standalone validate_envelope、project_output 和 aggregate；公开 projection
只允许 growth_ratio。generic SDK 的 prepared-aware project_prepared_output 由
conformance harness 使用，以防合法 envelope 被跨请求、跨 Pack 或跨 scope 重放。

Flux 即使由未来 solver 产生，也只能留在独立 solver trace。raw output、
projection metadata 和公开 projection 中出现 flux、essentiality、evidence、policy 或
promotion 字段都会被拒绝。

### 6. Conformance 是合成工程证据

P14E 的 canonical fixture 只使用测试内 identity、ratio 0.25 和 deterministic raw
dictionary，证明同一 prepared input/output 可重复得到相同 envelope、projection 和
conformance report。它不加载 GEM，不运行 FBA，不测准确率，不建立 baseline 比较或
external/OOD science evidence。

冻结 fingerprints 为：

| Identity | SHA-256 |
|---|---|
| adapter | 0b26d81c99f3ed216f5dcc6c86814379b6997633c0a6c071109d3ed45918b1a9 |
| input contract | 6995a1c262367bbd510a488b80b2c01a15e18cd6c32169f3036045869218edfa |
| output contract | bfda36704cfd82006ec0a3bd1c772d62209eb8c860b7baffae982f150955f13f |
| synthetic scope | bd7bc1cf60877ee8abfeb2e8769cf1cfd6e99e34305487da09fb18e810fc996e |
| synthetic protocol | a4b0bcc46aed1586cc5a466d06422753f944043ca526a2c88ceeeef79f3a88dc |
| synthetic compatibility | b61c7d6bacf2a2ca2de76d0ced740acef4a548155c9f4e09b7e5fa891ba81878 |
| synthetic prepared input | f6b1e7f263fc0b4608fedda71475b66fa0a20e9754dbe27a27d7714730e1f344 |
| synthetic envelope | c7ea3e0d8d966bed09008425adc81c018be4643566e0fbe3db7fafbe7b1d6cae |
| synthetic conformance report | 608e931a8a2b5199410b15428587ef03b9c5b6bd6b7b8fdf89ab753b1f1a752e |

### 7. SDK prerequisite hardening 不改变 P13 identity

P14E 前置提交 c3401450fd79f7829c438d6b55c1902ea2f4cf5f 加固了 generic SDK 的
递归 exact-type 和隐藏字段边界，并增加 prepared-aware projection。它不改变 delta
reference adapter 的 canonical identity。P13 的 adapter/input/output、prepared、
envelope 和 conformance 六个 fingerprints 均保持不变。

## 被拒绝的方案

- 在 P14E 读取 textbook GEM、SBML 或 Cobra 并返回真实数值；
- 把 p8-bacteria-tiny synthetic scRNA Pack 当作 growth-condition data；
- 在 DEFAULT_ADAPTER_REGISTRY 或 registry.yaml 注册 contract-only adapter；
- 复用 legacy ecoli_gem card、GemWrapper 或 case dispatch 形成隐式 positive path；
- 从 gene symbol、ortholog、名称相似或 assembly 默认值猜 mapping；
- 把 absolute objective、flux 或 essentiality 暴露为已验证产品输出；
- 用 deterministic、runtime success 或 conformance 代替科学 evidence；
- 在没有 P14R 正 evidence 与具名 operator 的情况下创建 P14B promotion。

## 后果与限制

P14E 工程状态为 COMPLETE，但 P14 整体科学能力不是 complete。P14R 保持
AUTHORIZATION_REQUIRED / NOT_RUN，P14B 保持 NOT_RUN；没有真实 Pack、GEM、
environment execution、benchmark、external cohort、evidence 或 policy。

P9 negative result 保持 available=false、scientifically_validated=false，result SHA
abd1145c434fd4e48ac9d72e94e8e19d14a5b4011f03d05db4823dd91760da6e
不变。下一 eligible 本地工程 work unit 是 P15E：S. cerevisiae deletion→fitness
contract；它不依赖 P14R 或 P14B 的正结果。
