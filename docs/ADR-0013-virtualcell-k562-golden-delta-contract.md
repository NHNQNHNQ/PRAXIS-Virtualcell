# ADR-0013：K562 Golden Norman perturbation→delta-expression contract

- 状态：Accepted（P16E engineering complete）
- 日期：2026-08-06
- 唯一起始基线：d1e2e37b69784bd2f440cba34f51cfb56dcc00b2
- Completion code SHA：9f6b14ea84cb0884b2bde2ed4c67c73aeb5a37e2
- Completion tree：098cd563e3d865e080a0d121727b987e2d40ed18
- 分支：codex/p16e-k562-perturbation-contract
- 前置：ADR-0006、ADR-0008、ADR-0009、ADR-0010、ADR-0011、ADR-0012
- 范围：P16E；P16R 与 P16B 未运行

## 背景

P8 已冻结 Norman 2019 K562 Golden benchmark 的 source、Pack、feature order、split、
control、metric、bootstrap 和三个简单 baseline identity。P12 已分离 model、artifact、
environment、adapter、evidence 和 operator-policy identity；P13 已实现 strict、
prepared-aware Adapter SDK；P14E/P15E 已证明窄任务合同可以在不读取真实科学资产的
前提下独立收口。

P16E 只把既有 P8 identity 接入一个 exact K562 perturbation→delta-expression 工程
合同。它不打开外置 H5AD、golden_contract.json、NPY、checkpoint 或 model cache，不
导入或运行 Golden benchmark wrapper、GEARS、scGPT 或其他候选模型，不训练、调参、
计算真实 MSE/paired CI/external/OOD 结果，不创建 scientific evidence，也不作 operator
policy 决定。真实资产与科学运行属于 P16R；产品 policy 属于 P16B。

## 决策

### 1. 公开任务是 exact K562 CRISPR-activation delta expression

任务冻结为：

| 项 | 冻结值 |
|---|---|
| task | predict_delta_expression |
| output | delta_expression |
| shape | (5045,) |
| unit | null / None |
| value semantics | condition_mean_X_minus_matched_split_control_mean_X |
| reference | matched_split_control_mean_X |
| species | NCBITaxon:9606 / Homo sapiens |
| cell identity | K562 / CVCL_0004 |
| assembly | GRCh38 / GCA_000001405.15 |
| assay/modality | scRNA / EFO:0008913 |
| feature namespace | EnsemblGene / Ensembl 84 / ensembl_gene |
| perturbation | CRISPR activation；dose 1.0 unit `1`；time 5.0 d / request `5d` |
| evaluation scopes | single_gene 与 combination，分别绑定 |

核心 `CellContext.cell_type_id` 只接受 CL identity，因此 exact request 使用
`cell_type_name=K562`、`cell_type_id=None`，并在 strict attributes 中绑定
`cell_identity_id=CVCL_0004`。不能把 CVCL identity 填入 CL-only 字段，也不能用名称
相似的 human cell 替代 K562。

Output 是 wrapper 已按 exact matched split control 计算的 5,045 个 finite delta 值。
Adapter 原样传递完整有序向量，不执行 normalization、reordering、fill、imputation、
deduplication 或 absolute-expression→delta conversion。负数、大于 1 的数和其他 finite
值都不会被裁剪；bool、NaN、Infinity、unsafe integer、错长度或嵌套向量被拒绝。

### 2. P8 K562 identity 被引用，不被重新解释

P16E data binding 固定：

- Pack `norman-2019-k562-golden` / `1.0.0`，fingerprint
  `42165e430bab3474cdc9e607770ff5e204608c4243f84e492c08e2c6442c55ee`；
- canonical Golden contract
  `f34afa761239abc97033c78bb9d0c29a1c36a4c7d1a106a9cbbaa805a5196ff5`；
- matrix shape `(91205, 5045)`；license `CC0-1.0`；
- exact ordered feature IDs hash
  `ecca6c636629e35ae5f5a0ec6fe84c1a7983e1adb263fbbcaea70a0c5495b2b7`；
- exact feature records hash
  `1cc8b612bef0a0d7daac01bb8cc509346a4a32850f93298f29865bb2328d9747`。

P8 source 的 `cell_type=A549` 是已知 upstream metadata error，必须原样保存为：

~~~text
source_cell_type_value           A549
source_cell_type_interpretation  upstream_metadata_error_preserved
canonical cell identity          K562 / CVCL_0004
~~~

该字段绝不能成为 request cell identity、fallback 或 compatibility 依据。

P16E 测试只读取 checked-in 的 `contract.yaml`、`pack.manifest.yaml` 和
`artifact-manifest.json`，并验证它们的 byte size、SHA-256 与 canonical identity。
H5AD 与 `golden_contract.json` 只作为 manifest 中的 path/media-type/size/hash reference；
P16E 不解析、打开或声明它们当前可用。

### 3. 冻结九个 P16E versioned contracts

| 合同 | schema | 职责 |
|---|---|---|
| K562GoldenDataBinding | vc.k562-golden-data-binding.v1 | 绑定 checked-in P8 manifests、external asset refs、biology、feature、split、control 与 aggregate hashes |
| K562GoldenPerturbationBinding | vc.k562-golden-perturbation-binding.v1 | 绑定一个 ordered condition record proposal；不证明外置 record membership |
| K562GoldenExecutionBinding | vc.k562-golden-execution-binding.v1 | 绑定 native delta semantics、feature order、runner/configuration 与禁止的转换 |
| K562GoldenCompatibilityBinding | vc.k562-golden-compatibility-binding.v1 | P16E typed negative preflight |
| K562GoldenPerturbationScope | vc.k562-golden-perturbation-scope.v1 | 交叉绑定 exact biology、assay、perturbation scope、P12 identities、Pack 与 output semantics |
| K562GoldenValidationProtocol | vc.k562-golden-validation-protocol.v1 | 预登记未来 P16R split、metric、comparator、paired CI、external、seed、OOD 与 scope-separation gates |
| K562GoldenAdapterInputContract | vc.k562-golden-adapter-input-contract.v1 | 冻结 task/input 与全部 required bindings |
| K562GoldenAdapterOutputContract | vc.k562-golden-adapter-output-contract.v1 | 冻结 5,045-feature delta vector、uncertainty、OOD 与 abstain |
| K562GoldenPreparedModelInput | vc.k562-golden-prepared-model-input.v1 | 保存 exact prepared request/scope/protocol/condition/data/execution/compatibility bindings |

合同均 strict、frozen，拒绝 unknown fields、隐式类型漂移、隐藏/excluded/computed
Pydantic fields、声明外 subtype fields 和 nested `model_copy` extras。canonical JSON
bytes 的小写 SHA-256 是 fingerprint；不兼容语义变化必须使用新的 schema/version。

### 4. Single-gene 与 combination 永久分门

Canonical engineering fixtures 为：

| Scope | condition | kind | ordered targets | record SHA-256 |
|---|---|---|---|---|
| single_gene | AHR+ctrl | gene | ENSG00000106546 | e04567ee8d8fb3273d600b3dc8956c3f0dd35d4e4bab1d1a5ba1fb83f483b9c1 |
| combination | AHR+FEV | gene_combination | ENSG00000106546, ENSG00000163497 | 7b77f2c32cde91604fe8182fa38af90a991c1c10f27fdc116d6f94aa6eff2a85 |

Condition binding 支持其他 exact canonical Ensembl record proposal，但 v1 的
`record_membership_verified` 永远为 false，reason 为 `p16r_not_authorized`。Checked-in
Pack 的 aggregate hashes、284 个 perturbation records 与两个 canonical sample 的文本
检查不能证明任意外置 runtime record membership。该事实只能在获授权的 P16R 中由 exact
asset bytes 重新验证。

Single-gene 与 combination 拥有不同 perturbation、scope、protocol、prepared input、
envelope 和 conformance fingerprints。未来 benchmark、paired CI、external gate、
evidence 和 policy 也必须分别记录；任一 scope 不得借用另一 scope 过门。

### 5. Split、control 与 validation protocol 是预登记，不是 evidence

P8 source role 映射固定为：

~~~text
source train  -> train       137 non-control conditions
source test   -> validation   30 non-control conditions
source ood    -> test        116 non-control conditions
leakage guard -> condition_id
~~~

Source control condition 是 `ctrl`；派生 control condition 与 guide 固定为：

| Split | condition ID | guide |
|---|---|---|
| train | norman.control.train | NegCtrl0_NegCtrl0__NegCtrl0_NegCtrl0 |
| validation | norman.control.validation | NegCtrl10_NegCtrl0__NegCtrl10_NegCtrl0 |
| test | norman.control.test | NegCtrl11_NegCtrl0__NegCtrl11_NegCtrl0 |

K562GoldenValidationProtocol 还固定：

- primary metric `condition_macro_full_feature_delta_mse`，lower is better；
- primary comparator `condition_level_additive_ridge`；
- historical additive result
  `b82dc7ab26c6f6fdef4414f6b05c51edb32b2a35e4c00f45824cc839ab9cf1a9`，
  historical test MSE `0.0032570634320908554`；
- historical no-change/global-mean/evaluation hashes分别为
  `38182a3fdb24666b8d76d9b118d2de4fd8cfd998ae025a54d7fecc42e09f7b5e`、
  `2b757d3e2d4e657f9bdc3aa890ee6d84ae5096661246ff4f881045676bb98d3a`、
  `1cc1110a75183f1b271a8caf34db9998046f93bd42abda278f725879d38eb79c`；
- historical comparator role 是 `checked_in_historical_reference_only`；
- candidate 与 additive 必须走同一 runtime，并先通过 contamination audit；
- paired difference 是 `candidate_mse_minus_additive_ridge_mse`；
- held-out condition paired-percentile bootstrap，`numpy.PCG64`、seed 0、2,000 次、
  interval `(0.025, 0.975)`；
- superiority 要求 `paired_difference_ci_upper_below_zero`；
- stochastic candidate seeds `(11, 23, 37)`；tuning 只用 validation；
- external 必须是独立且语义兼容的 K562 dataset/platform，adaptation steps 为 0；
- donor 或非 K562 external 只能作为 OOD，不能替代 K562 external gate；
- OOD order 为 iid、perturbation、combination、cell_type、donor、dataset_platform、
  species、dose_time；
- `record_role=preregistration_not_evidence`。

历史 P8 baseline score 不是 P16 candidate result。P16E 未运行 candidate、baseline、
paired CI、contamination audit、external 或 OOD science，不得创建
`vc.model-validation-evidence.v1`。

### 6. P16E compatibility 必须是明确负状态

K562GoldenCompatibilityBinding 固定：

- assets_verified=false；
- executable=false；
- reason=p16r_not_authorized。

测试使用 synthetic、identity-only ArtifactIdentity、EnvironmentIdentity、
ModelReleaseRecord、data、perturbation 和 execution bindings 检查交叉约束。Synthetic
artifact 是不存在文件的 `application/json` / `data_only` identity；release 不带
evidence 或 policy。它们不证明外置 H5AD、candidate checkpoint、environment 或 runner
存在、获许可、可加载、可执行或科学正确。

K562GoldenPerturbationAdapter 只能由测试或未来明确获授权的集成代码放入本地
AdapterRegistry。`DEFAULT_ADAPTER_REGISTRY` 继续只包含通用
`predict_delta_expression→delta_expression` reference adapter；相同 task/output 不足以
证明 P16 scope。P16E 不修改 registry.yaml、model card、wrapper、routing、case dispatch
或核心 runtime。

### 7. Prepared input 与 output 必须绑定完整 exact scope

`prepare_input` 同时核对：

- exact human/K562/GRCh38/scRNA/Ensembl 84 request；
- `cell_type_id=None` 与 `attributes.cell_identity_id=CVCL_0004`；
- exact ordered target、dose/time、condition、matched split control 与 evaluation scope；
- model release、data-only artifact、environment 与 adapter identities；
- P8 Pack/data、perturbation record proposal、execution、typed negative compatibility；
- scope-specific validation protocol；
- feature order、value semantics、reference 与禁止的转换。

缺任一 binding、fingerprint/type 漂移、unsafe load policy、错 media type、跨 scope/replay
prepared input、把 A549 当 canonical cell、把 symbol/versioned ID/ortholog 当 EnsemblGene，
或从 P8 legacy wrapper/model name 猜 fallback 时一律 fail closed。SDK 不打开 identity
指向的路径。

成功 raw output 只允许 exact prediction metadata 与 5,045 个 finite values。Uncertainty
固定为 `available=false`、`calibrated=false`、value/sigma 为空、
`method=not_available`、`reason=no_calibrated_uncertainty_declared`。授权状态不得编码进
uncertainty。

`target_not_found`、`unsupported_scope` 和 `error` 必须 value-free abstain；
`unsupported_scope` 必须同时声明 detected OOD。任意 detected OOD 都必须 abstain，并按
canonical axis order 给出 dimension/reason。Standalone `validate_envelope`、
`project_output` 与 `aggregate` 被拒绝；公开 projection 只有在 exact prepared-bound
validation 后才可为 `{"delta_expression": [...]}`。

### 8. Conformance 只是 synthetic engineering evidence

Canonical fixtures 使用测试内 identities 和 deterministic 5,045-value vector，分别
证明 single-gene 与 combination 的 prepared input、envelope、projection 和 conformance
fingerprints 可重复。它们不加载数据或模型，不测 MSE，不执行 baseline、paired CI、
independent K562 external 或 OOD science gate。

Adapter-global fingerprints：

| Identity | SHA-256 |
|---|---|
| adapter | 873c4e441619da1eeeac8da3522b5c919dac0ab49b3a16cc36a74e020f55997e |
| input contract | 46dc96360506b7ec7b25609c619960e97ae613e9d05277c26fc09a21d96d1fe3 |
| output contract | 10a211d99f2a2b8170e2fc9b0fb7030009849ff5e7d2968510e49c9375b21854 |

Shared synthetic fingerprints：

| Identity | SHA-256 |
|---|---|
| artifact | 38f21e38edcd2876095c29a342c8dc4f04c52f8afcb914079a69721211a30714 |
| environment | e4764936dabfdc36bb011190a8d4b3846fa5cc73bc5d58978dffef7f4ffe0572 |
| model release | a2b61b216dae1547429435b1bcc7351c7d63b4a0ec61f28338a5342bb249bb9b |
| data binding | 080f140a48eed4b2a8a072b262132c64cd376d5418cf1edca0a4c3ed58a7c167 |
| execution binding | c11517270bc132ca6581019cc6449fa94e69298aae6fc0f4b9f706967c090ecb |

Scope-specific fingerprints：

| Identity | single_gene | combination |
|---|---|---|
| perturbation binding | 454a851530484b4993e9a1a07ccef6f724684e65b21171d32c37545c8959b6b2 | 01eb25c45e844e22a15f85b5fe4c1fc9b55c4350532450a700d86a1cc0f8f573 |
| compatibility | 5ccdeffe1cfb2188cf8dc4232aba8bc02e97be45b2bb742ec71baecd246c0f6f | 414d64b93a398080fd3172f51d76513250349f39b71ef0fe478d27f2a2f7c170 |
| scope | 14393395712f70d4e05bfa220933548695d3d619162d9a8e23f082f96b3a7f24 | 579b2eee8fd32a410443086983c224ad83ea18226c6d696332c5a8b01da0926f |
| validation protocol | 5322aa8261d786482c4d24a92e7f40bbf55fef8cecfd3819ca9bb778b274d73b | a6700ae44273cb3f788724be10239b40c89217c378c9bd2f0aedd14a6776f229 |
| prepared input | d54d10582bd5abe3a16848d1fa3fb2ad48dd16fab6b0cfb4756c4bffcb985322 | 94b541ee7a4500a33ff862d6f531ebd5a4cc6e7633c2f7db64c48057d268290a |
| output envelope | 69f948b0282a0cc1be59d8c6a5a3efa2f32848b3d4ab0bc21223e9993769b73b | add96cc86478db890a594512afe92a97c0380d79893992de01596ecef51bd1eb |
| conformance report | e3083e73df38a045e707d2117309ddf5f0fef824fc26f521f97fa4f1aba0f4c5 | 42f9612a6eb5e433a826c5b21e6a20c622df2a7dba2369c347cb01c9192ce203 |

## 被拒绝的方案

- 在 P16E 打开 H5AD、golden_contract.json、NPY、checkpoint、model cache 或 external data；
- 把 source `A549` metadata error 当作 canonical cell identity；
- 把 P8 aggregate hashes 或两个 checked-in sample records 当作任意 runtime record
  membership proof；
- 用 gene symbol、version stripping、ortholog、reorder、fill、imputation 或 deduplication
  改写 exact Ensembl feature/target identity；
- 在 Adapter 内把 absolute expression、normalized expression 或其他 output 宽松转换为
  delta expression；
- 把 single-gene 与 combination 的 metric、CI、external result、evidence 或 policy 合并；
- 把历史 additive score、deterministic conformance、import success 或 wheel build 当作
  P16 candidate scientific validation；
- 在 `DEFAULT_ADAPTER_REGISTRY`、registry.yaml 或 runtime 注册 contract-only adapter；
- 用 uncertainty 字段编码 P16R 授权状态；
- 在没有正 P16R evidence 与具名 operator 的情况下创建 P16B promotion。

## 后果与限制

P16E 工程状态为 COMPLETE，但 P16 scientific capability 不是 complete。P16R 保持
AUTHORIZATION_REQUIRED / NOT_RUN，P16B 保持 NOT_RUN；real assets、candidate model、
benchmark、contamination audit、external validation、evidence 与 operator policy 均未
运行或创建。

P16E 没有 product/API/runtime version bump、tag、push、PR、artifact publication、
release、deploy 或 `.53` 操作。Packaging identity、strict offline build failure 和有限
system-site install smoke 的边界由 P16E completion report 单独记录；本地可复现 wheel
不能被解释为 clean hash-locked install、科学或发布证据。

P9 negative result 保持 available=false、scientifically_validated=false，result SHA
`abd1145c434fd4e48ac9d72e94e8e19d14a5b4011f03d05db4823dd91760da6e`
不变。在 P16E closure 时，下一 eligible 本地 work unit 是 P17 Virtual Cell Brain contract-only engineering；
由于当前少于两个 P14–P16 production-promoted capabilities，P17 不得宣称真实多模型
执行已通过。P16R 与 P16B 保持独立授权窗口。

## P16R-PREFLIGHT follow-on（2026-08-10）

在 P30A-E2b 后，P16R local authorization-preflight identity bridge 于
`4f77255f84e33180d7d73b421fc9737ca3a1121d`（tree
`f7aadb7b76a2aa55691d67d9c2948cc7b1e38e95`）完成
`COMPLETE — IDENTITY_PREFLIGHT_ONLY`。它新增
`vc.k562-p16r-external-scope-declaration.v1` 与
`vc.k562-p16r-authorization-preflight.v1`，只在内存中交叉绑定 P16 scope、P12 component 和
P21 protocol/group declarations，并固定 `assets_verified=false`、`executable=false`、
`prediction=null` 和 abstain。

这不是 P16R authorization、asset verification、candidate/comparator execution、leakage audit、
benchmark evidence、operator policy、registry/runtime/API/CLI route、release 或 promotion。actual
P16R 仍 `AUTHORIZATION_REQUIRED / NOT_RUN`，science `NOT_RUN`，policy `NO_NEW_DECISION`。
详见 [P16R identity-preflight completion record](../reports/phase16r_preflight/PHASE16R_AUTHORIZATION_PREFLIGHT.md)。
