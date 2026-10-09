# ADR-0008：VirtualCellPack P9 多轴 OOD、弃权与外部验证

- 状态：Accepted
- 日期：2026-07-29
- 唯一起始基线：`480706fbf58343565532debeca70c4de093b045f`
- 范围：Phase 9；不实施 Phase 10

## 背景

P8 已证明 Pack、模型卡和运行路径可以插件化，但这些事实都不等于模型在分布外
条件下可靠。P9 需要把 OOD 切分、泄漏检查、阈值选择、选择性预测和外部数据验证
变成可审计合同，并阻止“模型能运行”被误写成“模型有科学效力”。

旧的 151 行 evaluation ledger 含 mock predictor 和历史 index-modulo CV，可继续
作为旧治理数学测试，但不能作为 P9 科学证据。P9 不重解释或升级该 ledger。

## 决策

### 1. 八个 OOD 轴与证据等级

`vc.ood-manifest.v1` 按固定顺序声明：

1. IID；
2. perturbation；
3. combination；
4. cell type；
5. donor；
6. dataset/platform；
7. species；
8. dose/time。

每个轴都必须显式给出 train、validation、test 的生物独立 group；缺失、重复或跨
partition 重叠均拒绝。随 Git 提交的 `group-fixture.json` 只证明合同和泄漏审计
机制，`evidence_kind` 永远是 `contract_fixture`，不得被解释为八轴科学性能。

当前真实外部证据只覆盖 dataset/platform、carbon-source condition 和 time
extrapolation 的组合。其余轴保持“合同已冻结、科学证据未提供”。

### 2. 生物独立分组优先于样本行

模型拟合、阈值选择、测试和外部验证都先按 biological condition 分组；技术或
生物重复不能跨 partition。泄漏审计必须在任何指标计算前通过，同时检查
`biological_unit_id` 与 `replicate_id`。

所有切分均预先声明，不随机划分。feature 字段和 label 字段必须不相交；fit 只用
train，阈值只用 validation，test/external 只用于冻结后的评估。

### 3. 无适配外部验证

外部验证固定为：

- source：GEO `GSE67402`，REL606 glucose time course 中 27 个
  rRNA-depleted RNA-seq 样本；
- external：GEO `GSE94117` 的 `glycerol_time_course`，25 个样本；
- 明确排除 `GSE94117:glucose_time_course`，因为它与 source 存在样本同源风险；
- external adaptation steps：`0`。

四个公开输入文件的 filename、size、SHA-256 和 URL 都进入 manifest。输入 bytes
不匹配即停止，不使用替代下载、不 fallback 到 fixture/mock。

feature 合同是按原始 ID 的精确交集：

- source 4,486 个唯一 ID；
- shared 4,484 个有序 ID；
- source-only 丢弃项仅 `RF01769.1`、`RF01771.1`；
- 只显式排除外部文件中两种已观察到的 HTSeq summary-row 命名；
- 不转换 symbol/version/ortholog，不补零，不聚合重复 ID。

变换被完整声明为
`log1p(1e6 * exact_shared_feature_count / sample_exact_shared_feature_count_sum)`；
这不是静默归一化。

### 4. 候选、简单 baseline 与不可后调参

候选 `source-log-time-feature-trend-v1` 仅在 source train time
`[3, 4, 6, 24, 168] h` 拟合每个 feature 的 log-time 线性 slope。source
validation 是 `[5, 8, 48] h`，source test 是 `[336] h`。

简单 baseline 是每个 feature 的 zero delta（no-change）。候选参数只提交
SHA-256，不提交 4,484 维数组或任何模型权重。

reliability score 是到 source train log2-time coordinate 的负最近距离。阈值只在
source validation 上按“最小 candidate risk、至少 2/3 coverage”选择；test 和
external 的 label、loss 或结果均不能改变阈值。三个登记 seed
`[11, 23, 37]` 对确定性模型产生相同结果，必须如实报告零运行差异，不能伪造随机
波动。

### 5. 指标、置信区间与弃权

主指标是 4,484 个 shared feature 上的 condition-macro delta MSE。次指标是
condition-macro MAE 和 Pearson；no-change 为常量向量，其 Pearson 保持 `null`，
不得填 0。

95% CI 使用 biological condition 为配对 bootstrap 单元、NumPy PCG64 seed 0、
2,000 次 percentile resample。选择性指标同时报告：

- risk-coverage；
- coverage；
- wrong accept：候选不优于 baseline 的 condition 中仍被接受的比例；
- unnecessary abstain：候选优于 baseline 的 condition 中被拒绝的比例。

分母为零时结果必须是 `null`，不得制造 0。

### 6. 科学状态门禁

以下条件必须同时成立，模型才可标记 `available=true` 和
`scientifically_validated=true`：

- 泄漏审计通过；
- external adaptation steps 为 0；
- 至少三个登记 seed；
- candidate 主指标严格优于简单 baseline；
- paired difference 95% CI 上界严格小于 0。

本次真实结果是 candidate MSE `1.0603835779`、no-change MSE
`1.0533347059`、difference `+0.0070488720`，95% CI
`[-0.9076414928, 0.9749711895]`。因此两层状态均为 false。MAE 略好不能覆盖主
指标和 CI 失败。

### 7. LLM 与产品边界

LLM 可以解释 artifact，不参与 split、feature truth、数值预测、阈值选择、
bootstrap 或最终状态裁决。P9 不修改 Pack loader、核心 runtime、模型 zoo、
API、UI 或历史 job；P8 的 immutable Pack/model fingerprint 规则保持不变。

## 后果

- 八轴 OOD 合同可被机器严格检查，但当前不虚构八轴完整性能。
- 外部验证可由公开文件重放，Git 只保存 manifest、小 fixture、结果、hash 和
  runbook。
- 简单候选被科学门禁拒绝，证明 fail-closed 路径能够拒绝“能运行但不胜 baseline”
  的模型。
- 条件数只有 8，CI 很宽；这是一项真实但有限的外部验证，不是临床、跨物种或通用
  Virtual Cell 有效性声明。
