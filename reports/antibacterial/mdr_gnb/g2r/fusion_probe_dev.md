# G2R 探针:rule-first 融合(dev 级信号,2026-07-07)

> **定级:dev 级探针,非 locked-test 终判。** 单 seed、全数据(未做 dev/locked 双层划分)。
> 目的:验证 (1) G2 harness 可复现;(2) rule-first 融合能否救 EC 锚点。
> 脚本:`praxis_virtualcell/mdr_gnb/workflows/g2r_fusion_probe.py`。harness=`run_combo_eval` 同源
> (ST 分组 5 折、每折重训 RF、操作点对齐、per-ST VME、置换检验 n_perm=10000)。
> 融合定义:rule-first = `rule==R ? R : ML`(规则判 R 直接 R,否则用 ML)。

## 结果

| 锚点 | n | n_ST(R) | 规则 per-ST VME | ML 单独 | ML Δ (p) | **融合** | **融合 Δ (p)** | ME 规则→融合 |
|---|---|---|---|---|---|---|---|---|
| KP × meropenem | 768 | 68 | 0.266 | 0.102 | −0.164 (0.0001) | **0.096** | **−0.170 (0.0001)** | 0.137→0.374 |
| EC × ceftriaxone | 6852 | 246 | 0.030 | 0.046 | +0.017 (0.967) FAIL | **0.024** | **−0.005 (0.0006)** | 0.009→0.045 |

## 结论(校准后,不夸大)

1. **G2 harness 精确复现**:KP ML per-ST VME=0.102 与冻结门报告完全一致;EC ML Δ=+0.017 复现冻结的 +0.020 FAIL。科学门可重复、可回归 ✅(Milestone 1 实质达成)。
2. **rule-first 融合把两锚点都推到 VME ≤ 规则**:
   - KP:融合 −0.170(比 ML 单独还好一点),STRONG。
   - EC:融合 −0.005, p=0.0006 —— **从 ML 单独失败翻成显著优于规则**。原始 G2 唯一 blocker(EC ceftriaxone)被解掉。
3. **代价 = ME 升高**(VME 换 ME):EC 0.009→0.045、KP 0.137→0.374。融合多判 R → 少漏耐药(VME↓)但多误报敏感为耐药(ME↑)。对安全筛选工具 VME-first 通常划算,但 ME 增幅需正式认可(计划 dev_selection 的 `max_ME_increase: acceptable` 约束)。

## 重要保留(为何这不是终判)

- **单 seed**:未验 seed 稳定性(应多 seed)。
- **全数据非 dev/locked**:阈值/融合方式的选择应只看 dev,locked 只跑一次。本探针在全数据上算,有轻微乐观偏差。
- **EC Δ=−0.005 幅度极小**:统计显著但绝对安全增益很小 → EC 更接近 practical-pass,strong-pass 是"字面达标(p<0.05, Δ<0)但实际温和"。
- **特征仍与规则同源**(AMRFinderPlus 基因调用):融合的收益来自"规则兜底 + ML 补漏",不是新生物学信息。真正拉开 EC VME 仍需 k-mer/porin/CARD 新特征(依赖真实工具链)。

## 下一步(据此)

- Milestone 2:失败归因 atlas(EC ceftriaxone ML 在哪些 ST/基因上漏判 → 融合补了多少)。
- 建 dev/locked 双层划分,把融合 + conservative-threshold + abstain 正式训练/选择,locked 只跑一次出终判。
- 把 rule-first 融合作为 `combo_gate` 的第三个预测路径纳入 harness,per-ST VME 与置换检验复用。
