# ADR-0006：Norman/K562 Golden VirtualCellPack 与固定 baseline

- 状态：Accepted（Phase 8 local candidate）
- 日期：2026-07-28
- 唯一起始基线：`09fb1bb3d02adfceed504cbccd7cf36c54a61b69`
- 决策范围：Golden Pack、固定 benchmark、简单 baseline、正式 runtime 证据

## 背景

P2–P6 已分别提供 Pack schema、标准语义、多组学对齐和 capability-driven
runtime；P7 提供独立的数据交换层。此前仍缺一个以公开真实数据为依据、从数据
身份一直走到治理报告的端到端 Golden 参考。

Phase 8 选择 Norman et al. 2019 K562 CRISPRa Perturb-seq 数据：

- 论文：[Norman et al., Science 2019](https://doi.org/10.1126/science.aax4438)；
- GEO：[GSE133344](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE133344)；
- 公开归档：[Harvard Dataverse DOI 10.7910/DVN/Q2ZV3E](https://doi.org/10.7910/DVN/Q2ZV3E)；
- CPA preprocessing notebook 固定在 commit
  [`50e283a7`](https://github.com/facebookresearch/CPA/blob/50e283a7a1b3d43470d8adc5e11d3be4c10a534c/preprocessing/Norman19.ipynb)。

本 ADR 冻结 benchmark，不把一次基线结果扩写成普遍生物学结论。

## 决策

### 1. 数据和 feature 身份

事实源是 Dataverse datafile `6881912`：

| 对象 | Bytes | SHA-256 |
|---|---:|---|
| ZIP | 166,988,031 | `64af382a6af9d129042577a651691d0bdbbdeef2ad973bef77f012b4b209c41f` |
| `Norman2019_simulation_cpa.h5ad` | 2,235,954,082 | `de50bb456ea344ae934878def8339e8b7050baf934a69bda2c7196bcb3a0e6cd` |

H5AD 固定为 `91,205 × 5,045`。有序 observation、feature、symbol、source
condition/split/guide，以及 CSR `X/{data,indices,indptr}` 和 dense
`layers/counts` 都有独立 hash，见
[`contract.yaml`](../data/golden/norman_2019/contract.yaml)。

`X` 是上游已执行 normalize-total/log1p 后的表达矩阵；PRAXIS 原样使用，不再
归一化、补零、过滤、重排或抽样。`layers/counts` 也原样保留。派生过程复制 H5AD
后只替换 `obs` group；派生文件中的 X/counts hash 必须仍与源一致。

feature ID 是 source `var_names` 中的 Ensembl gene ID，固定 assembly
`GRCh38 / GCA_000001405.15`、namespace `EnsemblGene / Ensembl 84`；`gene_name`
只用于从冻结 source condition 构造 Pack perturbation 外键。runtime 请求只接受
canonical Ensembl ID，不执行 symbol、version、ortholog 或同源转换。

### 2. K562 与上游 A549 字段

论文/GEO 的实验细胞是 K562，Pack 的 canonical identity 固定为
`CVCL_0004`。CPA 派生文件中的 `cell_type=A549` 是已知上游元数据错误，但它仍是
源字节事实：派生 Pack 保留该列和值，并另加 `cell_identity_id=CVCL_0004`。
系统不得静默覆写 source 字段。

状态和实验 context 使用有定义的本地 term：

- `VCSTATE:unspecified`：来源没有更细的标准状态注释；
- `VCCONTEXT:in_vitro`：Norman 体外实验 context。

扰动为 CRISPR activation。Pack v0.2 的 `kind` 只能表达 `genetic`，更具体的
action 保存在 Golden contract。dose 使用显式 dimensionless intervention
indicator：control `0`、perturbation `1`、unit `1`；不是浓度声明。time 固定
`5 d`，对应来源协议的收集区间。

### 3. split 与 control

非 control condition 逐字映射：

```text
source train → Golden train
source test  → Golden validation
source ood   → Golden test
```

control 不随机划分。三个非靶向 guide 唯一决定 partition：

```text
NegCtrl0_NegCtrl0__NegCtrl0_NegCtrl0   → train
NegCtrl10_NegCtrl0__NegCtrl10_NegCtrl0 → validation
NegCtrl11_NegCtrl0__NegCtrl11_NegCtrl0 → test
```

对应 condition 是 `norman.control.{train,validation,test}`。每个 control cell
只进入一个 partition；每个 perturbation condition 只能出现在一个 partition。
leakage guard 固定为 `condition_id`。最终行数为
`45,989 / 10,944 / 34,272`，其中 control 为 `2,059 / 2,920 / 2,374`；
非 control condition 为 `137 / 30 / 116`。不存在随机 split、去重、fallback
或结果后调整。

### 4. primary metric 与 bootstrap

每个非 control condition 的 truth 使用该 condition 全部 cell 的 source X 均值，
减去同 partition matched control 的全部 cell 均值。primary metric 是：

1. 在完整、原顺序的 5,045 个 feature 上计算每个 condition 的 delta MSE；
2. 对 116 个 test condition 等权平均。

bootstrap unit 是 held-out perturbation condition，不是 cell。使用 NumPy
`PCG64`、seed `0`、2,000 次 paired percentile bootstrap、`[2.5%, 97.5%]`；
evaluation artifact 额外记录 NumPy 的线性 quantile 方法。split、metric、
bootstrap 和 baseline 参数在看到结果前冻结，结果后不调参。

### 5. 三个简单 baseline

- `no_change`：delta 定义为零；这是明确模型定义，不是 missing-data 补零。
- `global_mean`：137 个 train 非 control condition delta 的等权均值，不按 cell
  数加权。
- `additive_linear`：condition×105 canonical target 的 binary design，对完整
  5,045-feature delta 拟合 ridge。固定 `alpha=1.0`，不缩放，intercept 不惩罚：

```text
B = (XcᵀXc + I)⁻¹ XcᵀYc
intercept = mean(Y) - mean(X)B
```

35 个 train 未见 target 的 coefficient 因固定数学为零；输出显式列出请求中的
unseen target，不 fallback。重复或未知 target 直接失败。

每个 baseline 使用独立的一卡 registry，经
`PackRegistry → CapabilityRegistry/ModelBroker → GoldenBaselineWrapper →
Ensemble → Reliability/Critic/Provenance → Report` 执行。单模型预测只透传固定
白名单元数据；旧 predictor 未提供这些字段时，报告字节保持原状。缺失或篡改任一
asset 时 execution plan 不实例化 wrapper，runtime 弃权且不转 mock。

### 6. 结果和状态

冻结 test primary MSE：

| Baseline | MSE | condition-bootstrap 95% interval |
|---|---:|---:|
| no-change | 0.0062060923 | [0.0052718065, 0.0071798953] |
| global mean | 0.0045820474 | [0.0038500613, 0.0053562761] |
| additive ridge | 0.0032570634 | [0.0027929521, 0.0037390137] |

这些结果只证明：在冻结 Norman split/metric 上，三个简单 baseline 以当前 artifact
得到上述分数。它们不授予广泛泛化、因果正确性、临床用途或 SOTA 声明。

三层状态保持：

```text
pack_valid=true
model_compatible=true
scientifically_validated=false
```

`scientifically_validated` 不会因 Pack 注册、runtime 成功、分数更低或 bootstrap
区间而自动提升。

### 7. 外置资产与 GEARS 边界

大文件、source H5AD、`.npy` 参数和完整 evaluation artifact 位于：

```text
/home/zkyd/data1/mzy/praxis-virtualcell-data/golden/norman-2019
```

Git 只保存 contract、Pack manifest、model card、hash/score inventory、测试和
runbook。完整远端 bytes/hash 见
[`artifact-manifest.json`](../data/golden/norman_2019/artifact-manifest.json)。

本阶段没有运行 GEARS，没有访问或修改 GEARS checkpoint/模型资产。LLM 未参与
数据真相、split、数值预测、metric、bootstrap 或最终裁决。

## 后果与限制

- 这是单一 K562 CRISPRa 数据集内的冻结 benchmark，不是跨数据集外部验证。
- source X 已由上游预处理，baseline 分数不能与 counts/raw 或不同 feature 集的
  指标直接比较。
- 三个 baseline 都是 point estimate，没有 calibrated predictive uncertainty。
- additive 模型只表达固定的 target 可加效应，不声称恢复高阶机制。
- control guide 分配是审计固定规则，不是随机代表性估计。
- source 许可、Dataverse/GEO 条款与再分发责任仍需部署者持续复核；hash 不证明
  许可或科学质量。
- 任何数据、split、feature、metric、bootstrap、baseline 参数或 artifact bytes
  变化都必须新建 contract/version；不得原地改 hash 迎合现有文件。
