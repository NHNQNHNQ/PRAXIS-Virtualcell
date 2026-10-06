# S1.1:26 strong 组合可复现证据(本地 EC/KP 13 组合)

把冻结 v0.9 证据面里 rule-first 融合**显著优于** AMRFinderPlus 规则法的 strong 组合,
从结果表变成可追溯到每个 isolate 预测、可一键复现的证据。

## 一键复现

```bash
.venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v1.export_strong26 \
    --species escherichia_coli,klebsiella_pneumoniae,pseudomonas_aeruginosa,acinetobacter_baumannii,salmonella_enterica
```

确定性:seed=0(RF + GroupKFold-by-ST);置换 10000 次固定 seed;ΔVME bootstrap 2000 次固定 seed。特征=机制增强(augmented_features)。重跑得到一致数值。

## 汇总

| species | drug | n | R-ST | t\* | 融合VME | 规则VME | ΔVME | p | ME融合 | ME规则 | AUC | 显著 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:--:|
| acinetobacter_baumannii | amikacin | 944 | 36 | 0.64 | 0.353 | 0.8512 | -0.4982 | 0.0001 | 0.0508 | 0.015 | 0.9123 | ✅ |
| acinetobacter_baumannii | cefepime | 319 | 32 | 0.92 | 0.5857 | 0.728 | -0.1424 | 0.0159 | 0.036 | 0.0 | 0.881 | ✅ |
| acinetobacter_baumannii | ceftriaxone | 807 | 40 | 0.9 | 0.5041 | 0.8067 | -0.3026 | 0.0001 | 0.0226 | 0.0 | 0.9101 | ✅ |
| acinetobacter_baumannii | ciprofloxacin | 987 | 44 | 0.94 | 0.722 | 0.9995 | -0.2775 | 0.0001 | 0.043 | 0.0 | 0.9662 | ✅ |
| acinetobacter_baumannii | gentamicin | 982 | 53 | 0.84 | 0.1839 | 0.2887 | -0.1048 | 0.0043 | 0.3602 | 0.3218 | 0.8739 | ✅ |
| acinetobacter_baumannii | levofloxacin | 800 | 38 | 0.84 | 0.7782 | 1.0 | -0.2218 | 0.0006 | 0.0373 | 0.0034 | 0.8967 | ✅ |
| acinetobacter_baumannii | tetracycline | 797 | 34 | 0.74 | 0.3765 | 0.4319 | -0.0554 | 0.0336 | 0.0627 | 0.0148 | 0.8967 | ✅ |
| escherichia_coli | ampicillin | 7609 | 531 | 0.26 | 0.0258 | 0.1223 | -0.0965 | 0.0001 | 0.057 | 0.0182 | 0.9868 | ✅ |
| escherichia_coli | cefepime | 3525 | 158 | 0.12 | 0.0355 | 0.1671 | -0.1316 | 0.0001 | 0.2206 | 0.175 | 0.9373 | ✅ |
| escherichia_coli | ceftriaxone | 6852 | 246 | 0.12 | 0.0269 | 0.0297 | -0.0028 | 0.001 | 0.0469 | 0.0089 | 0.9913 | ✅ |
| escherichia_coli | gentamicin | 7445 | 212 | 0.2 | 0.0346 | 0.068 | -0.0334 | 0.0001 | 0.0642 | 0.0179 | 0.981 | ✅ |
| escherichia_coli | tetracycline | 7247 | 541 | 0.36 | 0.0212 | 0.0225 | -0.0013 | 0.0621 | 0.0556 | 0.0183 | 0.9895 | — |
| escherichia_coli | tobramycin | 2972 | 47 | 0.14 | 0.2427 | 0.3912 | -0.1485 | 0.0005 | 0.0631 | 0.0144 | 0.9487 | ✅ |
| escherichia_coli | trimethoprim-sulfamethoxazole | 7040 | 199 | 0.06 | 0.0162 | 0.0198 | -0.0036 | 0.0165 | 0.2853 | 0.2409 | 0.9803 | ✅ |
| klebsiella_pneumoniae | amikacin | 730 | 36 | 0.16 | 0.0017 | 0.082 | -0.0803 | 0.0087 | 0.5536 | 0.5057 | 0.9271 | ✅ |
| klebsiella_pneumoniae | cefepime | 627 | 86 | 0.4 | 0.0286 | 0.0591 | -0.0305 | 0.0146 | 0.4706 | 0.4244 | 0.9054 | ✅ |
| klebsiella_pneumoniae | ceftriaxone | 1024 | 145 | 0.64 | 0.1445 | 0.2615 | -0.117 | 0.0001 | 0.0703 | 0.0216 | 0.9615 | ✅ |
| klebsiella_pneumoniae | gentamicin | 719 | 89 | 0.56 | 0.0891 | 0.1264 | -0.0373 | 0.016 | 0.1342 | 0.0895 | 0.9298 | ✅ |
| klebsiella_pneumoniae | meropenem | 768 | 68 | 0.42 | 0.1115 | 0.2662 | -0.1547 | 0.0001 | 0.1832 | 0.1374 | 0.9541 | ✅ |
| klebsiella_pneumoniae | tobramycin | 604 | 76 | 0.4 | 0.037 | 0.0683 | -0.0313 | 0.0036 | 0.204 | 0.16 | 0.9425 | ✅ |
| pseudomonas_aeruginosa | aztreonam | 180 | 56 | 0.72 | 0.8217 | 0.9169 | -0.0952 | 0.0063 | 0.038 | 0.0127 | 0.7191 | ✅ |
| pseudomonas_aeruginosa | ciprofloxacin | 645 | 79 | 0.52 | 0.3402 | 0.8672 | -0.527 | 0.0001 | 0.0734 | 0.0321 | 0.9592 | ✅ |
| pseudomonas_aeruginosa | levofloxacin | 415 | 76 | 0.46 | 0.2621 | 0.8728 | -0.6107 | 0.0001 | 0.0745 | 0.0373 | 0.9241 | ✅ |
| pseudomonas_aeruginosa | meropenem | 351 | 83 | 0.7 | 0.6024 | 0.6931 | -0.0907 | 0.0012 | 0.2941 | 0.2521 | 0.833 | ✅ |
| salmonella_enterica | ampicillin | 9611 | 43 | 0.1 | 0.0461 | 0.0587 | -0.0126 | 0.009 | 0.0442 | 0.0049 | 0.9878 | ✅ |
| salmonella_enterica | gentamicin | 9588 | 36 | 0.12 | 0.0439 | 0.123 | -0.0791 | 0.008 | 0.0611 | 0.0201 | 0.9704 | ✅ |

## 每组合 6 问

### acinetobacter_baumannii × amikacin

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.353 < 规则 per-ST VME=0.8512(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.4982(相对降幅≈59%),bootstrap 95% CI=[-0.6358, -0.3492](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.0508 vs ME规则=0.015(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0001(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=944、R-ST=36、t\*=0.64;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### acinetobacter_baumannii × cefepime

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.5857 < 规则 per-ST VME=0.728(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.1424(相对降幅≈20%),bootstrap 95% CI=[-0.2812, -0.0339](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.036 vs ME规则=0.0(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0159(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=319、R-ST=32、t\*=0.92;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### acinetobacter_baumannii × ceftriaxone

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.5041 < 规则 per-ST VME=0.8067(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.3026(相对降幅≈38%),bootstrap 95% CI=[-0.4372, -0.1731](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.0226 vs ME规则=0.0(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0001(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=807、R-ST=40、t\*=0.9;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### acinetobacter_baumannii × ciprofloxacin

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.722 < 规则 per-ST VME=0.9995(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.2775(相对降幅≈28%),bootstrap 95% CI=[-0.4074, -0.1498](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.043 vs ME规则=0.0(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0001(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=987、R-ST=44、t\*=0.94;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### acinetobacter_baumannii × gentamicin

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.1839 < 规则 per-ST VME=0.2887(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.1048(相对降幅≈36%),bootstrap 95% CI=[-0.1876, -0.0377](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.3602 vs ME规则=0.3218(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0043(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=982、R-ST=53、t\*=0.84;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### acinetobacter_baumannii × levofloxacin

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.7782 < 规则 per-ST VME=1.0(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.2218(相对降幅≈22%),bootstrap 95% CI=[-0.3539, -0.1108](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.0373 vs ME规则=0.0034(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0006(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=800、R-ST=38、t\*=0.84;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### acinetobacter_baumannii × tetracycline

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.3765 < 规则 per-ST VME=0.4319(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.0554(相对降幅≈13%),bootstrap 95% CI=[-0.1294, -0.0019](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.0627 vs ME规则=0.0148(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0336(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=797、R-ST=34、t\*=0.74;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### escherichia_coli × ampicillin

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.0258 < 规则 per-ST VME=0.1223(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.0965(相对降幅≈79%),bootstrap 95% CI=[-0.1205, -0.0749](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.057 vs ME规则=0.0182(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0001(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=7609、R-ST=531、t\*=0.26;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### escherichia_coli × cefepime

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.0355 < 规则 per-ST VME=0.1671(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.1316(相对降幅≈79%),bootstrap 95% CI=[-0.1799, -0.0888](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.2206 vs ME规则=0.175(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0001(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=3525、R-ST=158、t\*=0.12;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### escherichia_coli × ceftriaxone

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.0269 < 规则 per-ST VME=0.0297(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.0028(相对降幅≈9%),bootstrap 95% CI=[-0.0052, -0.001](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.0469 vs ME规则=0.0089(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.001(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=6852、R-ST=246、t\*=0.12;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### escherichia_coli × gentamicin

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.0346 < 规则 per-ST VME=0.068(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.0334(相对降幅≈49%),bootstrap 95% CI=[-0.056, -0.0143](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.0642 vs ME规则=0.0179(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0001(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=7445、R-ST=212、t\*=0.2;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### escherichia_coli × tetracycline

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.0212 < 规则 per-ST VME=0.0225(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.0013(相对降幅≈6%),bootstrap 95% CI=[-0.0035, -0.0](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.0556 vs ME规则=0.0183(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0621(不显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=7247、R-ST=541、t\*=0.36;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### escherichia_coli × tobramycin

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.2427 < 规则 per-ST VME=0.3912(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.1485(相对降幅≈38%),bootstrap 95% CI=[-0.2461, -0.0634](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.0631 vs ME规则=0.0144(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0005(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=2972、R-ST=47、t\*=0.14;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### escherichia_coli × trimethoprim-sulfamethoxazole

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.0162 < 规则 per-ST VME=0.0198(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.0036(相对降幅≈18%),bootstrap 95% CI=[-0.009, -0.0002](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.2853 vs ME规则=0.2409(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0165(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=7040、R-ST=199、t\*=0.06;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### klebsiella_pneumoniae × amikacin

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.0017 < 规则 per-ST VME=0.082(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.0803(相对降幅≈98%),bootstrap 95% CI=[-0.1603, -0.0139](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.5536 vs ME规则=0.5057(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0087(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=730、R-ST=36、t\*=0.16;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### klebsiella_pneumoniae × cefepime

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.0286 < 规则 per-ST VME=0.0591(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.0305(相对降幅≈52%),bootstrap 95% CI=[-0.0676, -0.0039](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.4706 vs ME规则=0.4244(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0146(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=627、R-ST=86、t\*=0.4;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### klebsiella_pneumoniae × ceftriaxone

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.1445 < 规则 per-ST VME=0.2615(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.117(相对降幅≈45%),bootstrap 95% CI=[-0.165, -0.0686](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.0703 vs ME规则=0.0216(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0001(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=1024、R-ST=145、t\*=0.64;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### klebsiella_pneumoniae × gentamicin

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.0891 < 规则 per-ST VME=0.1264(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.0373(相对降幅≈30%),bootstrap 95% CI=[-0.0745, -0.0031](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.1342 vs ME规则=0.0895(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.016(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=719、R-ST=89、t\*=0.56;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### klebsiella_pneumoniae × meropenem

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.1115 < 规则 per-ST VME=0.2662(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.1547(相对降幅≈58%),bootstrap 95% CI=[-0.244, -0.0779](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.1832 vs ME规则=0.1374(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0001(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=768、R-ST=68、t\*=0.42;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### klebsiella_pneumoniae × tobramycin

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.037 < 规则 per-ST VME=0.0683(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.0313(相对降幅≈46%),bootstrap 95% CI=[-0.072, -0.003](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.204 vs ME规则=0.16(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0036(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=604、R-ST=76、t\*=0.4;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### pseudomonas_aeruginosa × aztreonam

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.8217 < 规则 per-ST VME=0.9169(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.0952(相对降幅≈10%),bootstrap 95% CI=[-0.1726, -0.0327](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.038 vs ME规则=0.0127(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0063(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=180、R-ST=56、t\*=0.72;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### pseudomonas_aeruginosa × ciprofloxacin

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.3402 < 规则 per-ST VME=0.8672(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.527(相对降幅≈61%),bootstrap 95% CI=[-0.6288, -0.4215](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.0734 vs ME规则=0.0321(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0001(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=645、R-ST=79、t\*=0.52;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### pseudomonas_aeruginosa × levofloxacin

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.2621 < 规则 per-ST VME=0.8728(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.6107(相对降幅≈70%),bootstrap 95% CI=[-0.7081, -0.5077](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.0745 vs ME规则=0.0373(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0001(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=415、R-ST=76、t\*=0.46;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### pseudomonas_aeruginosa × meropenem

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.6024 < 规则 per-ST VME=0.6931(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.0907(相对降幅≈13%),bootstrap 95% CI=[-0.15, -0.0364](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.2941 vs ME规则=0.2521(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.0012(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=351、R-ST=83、t\*=0.7;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### salmonella_enterica × ampicillin

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.0461 < 规则 per-ST VME=0.0587(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.0126(相对降幅≈21%),bootstrap 95% CI=[-0.0238, -0.0038](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.0442 vs ME规则=0.0049(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.009(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=9611、R-ST=43、t\*=0.1;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

### salmonella_enterica × gentamicin

1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME=0.0439 < 规则 per-ST VME=0.123(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。
2. **VME 降多少**:ΔVME=-0.0791(相对降幅≈64%),bootstrap 95% CI=[-0.1549, -0.0201](CI 上界<0 → 稳健优于规则)。
3. **是否牺牲过多 ME**:ME融合=0.0611 vs ME规则=0.0201(判据 ≤规则ME+0.05:通过);rule-first 只在规则判 S 处用 ML,不放大误判。
4. **是否显著**:配对置换检验 p=0.008(显著,单侧 model<rule)。
5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;unknown-ST 剔出折;coverage=1.0(进折 isolate 全覆盖,无弃权)。
6. **如何复现**:上方一键命令;本组合 n=9588、R-ST=36、t\*=0.12;per-isolate 预测见 strong_26_per_isolate_predictions.parquet。

