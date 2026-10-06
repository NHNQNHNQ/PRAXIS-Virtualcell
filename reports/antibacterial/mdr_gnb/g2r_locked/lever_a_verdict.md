# G2R 杠杆 A 决定性终判:OOF ST-CV 全功效 + 机制特征 ±弃权(2026-07-07)

> **零下载、本地。** OOF ST 分组 5 折 CV(每折 held out,operating point 只从 train 定 → 无 test 泄漏),
> 全部 R-ST 进 per-ST 置换检验(恢复 25% holdout 损失的功效)。harness=`workflows/run_g2r_lever_a.py`。
> 融合=rule-first;判据(严格)=ΔVME<0 ∧ p<0.05 ∧ ME<0.10 → strong;数据=`lever_a_nested_cv.json`。

## EC × ceftriaxone —— 真 G2R-strong-pass ✅（全 246 R-ST）

| 配置 | 融合 VME | 规则 VME | ΔVME | p | ME | 判定 |
|---|---|---|---|---|---|---|
| 基线特征 | 0.024 | 0.030 | −0.005 | **0.0006** | 0.045 | **STRONG** |
| +机制特征 | 0.028 | 0.030 | −0.002 | 0.0040 | 0.018 | **STRONG** |
| +机制+弃权(87%) | 0.011 | 0.013 | −0.001 | 0.0089 | 0.014 | **STRONG** |

- **rule-ML 融合在全功效下统计显著优于冻结版 AMRFinderPlus**(ΔVME<0,p<0.01,ME 受控)。
- 之前 practical-pass 是 25% holdout 只有 69 R-ST 欠功效;全 246 R-ST 下显著性成立。**无需 53。**
- 诚实:ΔVME 绝对量级小(0.024 vs 0.030),是"统计显著、绝对温和"的安全增益;机制特征把 ME 从 0.045 降到 0.018。

## KP × meropenem —— VME 决定性胜出,ME 卡关(全 68 R-ST)

| 配置 | 融合 VME | 规则 VME | ΔVME | p | ME | 严格判定 |
|---|---|---|---|---|---|---|
| 基线特征 | 0.096 | 0.266 | **−0.170** | **0.0001** | 0.374 | FAIL(ME) |
| +机制特征 | 0.066 | 0.266 | **−0.200** | **0.0001** | 0.282 | FAIL(ME) |
| +机制+弃权(87%) | 0.023 | 0.229 | **−0.206** | **0.0001** | 0.300 | FAIL(ME) |

- **VME 上是碾压性、铁一般显著的胜出**(ΔVME −0.17~−0.21,p=0.0001,复现并强于原始门)。机制特征把 VME 再压(0.096→0.066)。
- **卡在 ME=0.28~0.37**(30%+ 敏感株被判耐药)。abstain 压不下(操作点激进判 R,弃权移除的是正确的 S 判)。
- **这不是功效/特征问题,是 VME↔ME 的真实临床权衡**:
  - 按**原始 G2 判据(仅 VME、无 ME 约束)**→ KP 是**决定性 strong-pass**(与冻结门一致)。
  - 按**本 G2R 严格判据(ME<0.10)**→ FAIL on ME。
  - **判定取决于可接受的 ME 上限——这是临床决策,不是统计问题。** 对末线美罗培南,漏判耐药(VME)vs 误判耐药挤占用药(ME),孰轻孰重需用户/临床定。

## 结论

1. **EC × ceftriaxone:G2R-strong-pass 达成(本地、全功效、无需 53)。** 可对外诚实声称"在 EC ceftriaxone 上 rule-ML 融合统计显著优于冻结 AMRFinderPlus 的 VME"。
2. **KP × meropenem:VME strong-pass 成立(p=0.0001),但需拍定 ME 上限。** 若接受 ME≈0.30 → strong-pass;若守 ME<0.10 → 现有手段无解(fundamental tradeoff)。
3. **杠杆 A 成功:功效在本地就能恢复,两锚点都不需要 53 下载。** 53 的定向下载(runbook)仅对真稀有组合(EC×mero 32 R-ST、KP×colistin 26 R-ST)才有必要。

## 保留
- 单 seed;融合固定 rule-first;t* 对齐规则 ME(未扫 t* 的 VME-ME 全操作曲线——KP 若要在 ME 与 VME 间找折中点,可扫 t*)。
