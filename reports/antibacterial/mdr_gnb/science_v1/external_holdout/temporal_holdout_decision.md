# S3.2:时间外推 holdout(train≤2021 / test≥2022)

现有 strong/practical 结果都是 5 折 ST-grouped OOF(同一数据生态内)。审稿人会问:**换年份还行吗?是不是只拟合了某个采样时期?** S3.2 做**时间外推**——用 **2021 及之前**的 isolate 训练,在 **2022+ 近年**的 isolate 上测,看模型是否随年份漂移。

## 方法(frozen-consistent,同 S3.1 lineage)

每 anchor:按 BioSample 采样年份切 train(≤2021)/ test(>2021)。特征 augmented_features + build_X/fit_vocab;ML=GenotypeToSIR(rf, seed=0);**t\* 只在 train(≤2021)上选**(select_tstar,防泄漏),test 只评估不选阈;融合 = rule-first(rule 判 R 兜底,否则 ML≥t\*)。test 上算 per-ST VME(融合 vs 规则)与 ΔVME。

## 一键复现

```bash
.venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v1.holdout \
    --species escherichia_coli,klebsiella_pneumoniae --mode temporal
```

确定性:seed=0;切分/训练均确定性,重跑字节一致。

## 评估结果(test≥2022 上融合 vs 规则)

| species | drug | train_n | test_n | test_R_ST | 融合VME | 规则VME | ΔVME | t\* | 年份覆盖 |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| escherichia_coli | ceftriaxone | 6464 | 337 | 68 | 0.0000 | 0.0223 | -0.0223 | 0.040 | 0.993 |
| escherichia_coli | ciprofloxacin | 6423 | 336 | 41 | 0.0000 | 0.0079 | -0.0079 | 0.100 | 0.871 |
| klebsiella_pneumoniae | meropenem | 392 | 210 | 24 | 0.0480 | 0.1010 | -0.0530 | 0.160 | 0.784 |
| klebsiella_pneumoniae | cefepime | 248 | 230 | 31 | 0.0000 | 0.0312 | -0.0312 | 0.240 | 0.762 |
| klebsiella_pneumoniae | ceftriaxone | 792 | 138 | 44 | 0.0044 | 0.0819 | -0.0774 | 0.240 | 0.908 |

## 主案例 EC×ceftriaxone(ESBL 近年扩散场景)

- train≤2021: n=6464;**test≥2022: n=337**(test 侧 R-ST=68,近年样本高度耐药,ESBL 扩散)。
- 融合 VME=0.0000 vs 规则 VME=0.0223(ΔVME=-0.0223,容差 0.05)→ **不劣于规则 ✅**。
- 结论:模型在未见过的近年 isolate 上,VME 不劣于规则——**不是只拟合某个采样时期**。

## 数据 vintage 分布 + CUTOFF 依据(诚实)

- CUTOFF=2021:train/test 以 2021/2022 分界——2022+ 为「近年现代 isolate」,足够近以检验时间漂移,又能在多数 anchor 上留出 ≥20 test 与 ≥5 R-ST。

  - escherichia_coli×ceftriaxone:年份覆盖 99.3%(train 6464 / test 337)。
  - escherichia_coli×ciprofloxacin:年份覆盖 87.1%(train 6423 / test 336)。
  - klebsiella_pneumoniae×meropenem:年份覆盖 78.4%(train 392 / test 210)。
  - klebsiella_pneumoniae×cefepime:年份覆盖 76.2%(train 248 / test 230)。
  - klebsiella_pneumoniae×ceftriaxone:年份覆盖 90.8%(train 792 / test 138)。

## 跳过的组合(诚实标注)

以下组合因无年份缓存 / 样本不足 / test 侧 R-ST 不足而跳过,不硬跑出噪声数字:

- **escherichia_coli × meropenem**:test≥2022 R-ST 不足(=2<5),不硬跑噪声 VME,年份覆盖 89.3%。

> 说明:年份缓存按**物种**存(biosample_acc→year),同一 isolate 跨药共享 BioSample,故仅富集了 ceftriaxone 的 EC 年份也惠及 EC×ciprofloxacin/meropenem 等——覆盖率取决于各组合 isolate 的 BioSample 是否落在缓存内,而非严格按药富集。

## 更正记录:早期探针误判

早期探针(前 150 条 BioSample)曾误判「数据止于 2016」;**全量富集后确认数据延伸到 2025**(EC/KP 均有 2022+ isolate),故现代 ≥2022 temporal holdout 可行。早期结论作废,以全量富集分布为准。

## 待办(本任务范围外)

- **PA/AB/SA temporal**:待 53 数据管线 + 年份富集。
- **source holdout(S3.3)**:按数据来源/地域留出外推。

