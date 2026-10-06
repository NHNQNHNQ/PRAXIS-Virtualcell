# S3.1:外推验证 — anchor panel + ST-cluster(prevalence 分箱)lineage holdout

现有 strong/practical 结果都是 5 折 **ST-grouped OOF**(每个 ST 整体不跨 train/test)。审稿人会问:换谱系还行吗?S3.1 做**更强的外推**——留出**整组谱系**(lineage cluster)而非随机 ST 折。

## 方法(写死)

对每个 anchor 组合:取全部 isolate(剔除 unknown-ST),按唯一 ST 的 **isolate 频次降序**切 **K=4 个连续分箱**(按累计 isolate 数均分):bin0=最常见谱系群,bin3=最稀有谱系群。**leave-one-cluster-out**:留出 1 箱作 held cluster(test),其余 3 箱作 train。特征 frozen-consistent(augmented_features + build_X/fit_vocab);**t\* 只在 train 上选**(select_tstar,防泄漏),held cluster 只评估不选阈;融合 = rule-first(rule 判 R 兜底,否则 ML≥t\*)。held cluster 上算 per-ST VME(融合 vs 规则)与 ΔVME。**测「从常见谱系泛化到稀有谱系」**——比随机 ST 折更强的泛化考验。

## 一键复现

```bash
.venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v1.holdout \
    --species acinetobacter_baumannii,escherichia_coli,klebsiella_pneumoniae,pseudomonas_aeruginosa,salmonella_enterica --mode lineage
```

确定性:seed=0;prevalence 分箱与训练均确定性,重跑字节一致。

## 核心锚点(EC×ceftriaxone / KP×meropenem):holdout 是否保持不劣于规则

| species | drug | held cluster | n | n_R | 融合VME | 规则VME | ΔVME | t\* |
|---|---|:--:|--:|--:|--:|--:|--:|--:|
| escherichia_coli | ceftriaxone | 0 | 1845 | 499 | 0.0143 | 0.0729 | -0.0586 | 0.0400 |
| escherichia_coli | ceftriaxone | 1 | 1580 | 317 | 0.0362 | 0.0534 | -0.0172 | 0.0400 |
| escherichia_coli | ceftriaxone | 2 | 1678 | 302 | 0.0269 | 0.0485 | -0.0216 | 0.0400 |
| escherichia_coli | ceftriaxone | 3 | 1689 | 253 | 0.0199 | 0.0208 | -0.0009 | 0.0400 |
| klebsiella_pneumoniae | meropenem | 0 | 183 | 142 | 0.0000 | 0.0341 | -0.0341 | 0.1200 |
| klebsiella_pneumoniae | meropenem | 1 | 177 | 85 | 0.0000 | 0.1421 | -0.1421 | 0.1400 |
| klebsiella_pneumoniae | meropenem | 2 | 180 | 62 | 0.0238 | 0.2468 | -0.2230 | 0.1600 |
| klebsiella_pneumoniae | meropenem | 3 | 177 | 35 | 0.1176 | 0.3382 | -0.2206 | 0.1800 |

- **escherichia_coli × ceftriaxone**:4 个有效 held cluster,融合 VME 均值 0.0243 vs 规则 0.0489(容差 0.05)→ **不劣于规则 ✅**。

- **klebsiella_pneumoniae × meropenem**:4 个有效 held cluster,融合 VME 均值 0.0354 vs 规则 0.1903(容差 0.05)→ **不劣于规则 ✅**。

## 泛化失败 held cluster(诚实记录)

无 held cluster 上融合明显劣于规则(ΔVME>0.05):所有可评估谱系群外推稳健。

## 无真 R 的 held cluster(无法评 VME,诚实标注)

所有 held cluster 均含真 R 样本,VME 可评估。

## 不在冻结证据面 132、跳过评估的 anchor(诚实标注)

以下 anchor 虽在名单内,但未收录进冻结证据面 132(或收录但 tier=unevaluated、n 空),无冻结基线可对齐,故本次跳过 lineage holdout,manifest 记 status=pending:

- **acinetobacter_baumannii × tigecycline**:不在冻结证据面 132 的可评估集,跳过(53 上或有原始数据,待收录进面后再评)。
- **salmonella_enterica × ciprofloxacin**:不在冻结证据面 132 的可评估集,跳过(53 上或有原始数据,待收录进面后再评)。

## 待办(本任务范围外)

- **PA/AB/SA anchor(6 个,data_locus=53)**:lineage holdout 待 53 数据管线(status=pending,见 manifest)。
- **temporal holdout(S3.2)**:按年份/批次留出时间段外推。
- **source holdout(S3.3)**:按数据来源/地域留出外推。

