# S4:高价值稀有组合 — colistin high-risk demonstration 决策

## 定位(诚实核心)

colistin 是对抗泛耐药 GNB 的**最后一线**药,临床极高价值。但规则表**未收录** colistin(RuleBaselineSIR 抛 KeyError)→ **no_baseline**,无规则基线可对照。故 colistin 定位为**high-risk demonstration**:诚实表征「能预测到什么程度」,**不声称优于规则、不做 ΔVME/规则对照、不硬求 strong-pass**。

## 方法

纯 ML 的 ST 分组 5 折 OOF(不融合规则):augmented_features + RF(seed=0),OOF 概率固定 0.5 阈值出预测;报 per-ST VME、ME、AUC_R、ECE。无规则基线故无 ΔVME。

## 结果(每 colistin 组合)

| species | n | n_R | n_R_ST | VME(ml) | ME(ml) | AUC_R | ECE | 可靠? |
|---|--:|--:|--:|--:|--:|--:|--:|:--:|
| klebsiella_pneumoniae | 238 | 71 | 26 | 0.6125 | 0.0769 | 0.7826 | 0.0644 | ✅ reliable |
| escherichia_coli | 541 | 16 | 15 | 1.0 | 0.0 | 0.9605 | 0.024 | ✅ reliable |
| pseudomonas_aeruginosa | 144 | 13 | 10 | 1.0 | 0.0 | 0.5044 | 0.0768 | ⚠️ underpowered |
| acinetobacter_baumannii | 303 | 24 | 8 | 0.875 | 0.0036 | 0.7063 | 0.0537 | ⚠️ underpowered |

## 汇总结论

- **colistin = no_baseline high-risk demo**:无规则基线,只做 ML-only 表征,不声称优于规则。
- **可评估(R-ST≥12,reliable=True)**:klebsiella_pneumoniae, escherichia_coli——KP/EC 为主案例,展示「能预测到什么程度」(看 AUC_R/VME),但受 colistin 标签噪声与机制盲区限制,不外推为临床错误率。
- **underpowered(R-ST<12,reliable=False)**:pseudomonas_aeruginosa, acinetobacter_baumannii——R-ST 太少,指标不稳,评估但明确标注不可靠。
- **失败模式**见 rare_combo_failure_modes.yaml(breakpoint 变异 / 表型噪声 / mcr 阴性机制 / 无规则基线)。

> 数据位点:colistin 表型/ST **只在 53**。本产物由协调方在 53 跑 `python -m ...rare_combos` 生成;本地无 colistin 数据,gate 待 53 跑完 rsync 回后转 pass。

