# S6 升级组合(v0.9 → v1,共 17 个 E 级别上升)

聚合 S2 abstain 复评 + S3 lineage holdout 后,17 个组合证据级别上升。升级只来自
**真做过的评估**(holdout 外推 / abstain-aware 复评),不凭空拔高。

## strong(E4) → E5 external-supported(5 个)

冻结面已 strong-pass 的组合,S3 lineage holdout(留出整组稀有谱系群)上融合仍不劣于规则
(该 anchor 全部 held cluster ΔVME 均值 ≤0),获外推支撑升 E5。

| species | drug | v0.9 | v1 | ΔVME(ST-CV) |
|---|---|:--:|:--:|--:|
| escherichia_coli | ceftriaxone | E4 | E5 | -0.0028 |
| klebsiella_pneumoniae | cefepime | E4 | E5 | -0.0305 |
| klebsiella_pneumoniae | meropenem | E4 | E5 | -0.1598 |
| pseudomonas_aeruginosa | levofloxacin | E4 | E5 | -0.6107 |
| pseudomonas_aeruginosa | meropenem | E4 | E5 | -0.0907 |

## practical(E3) → E5 external-supported(5 个,跨 2 级最大跳)

冻结面仅 practical(不劣于规则但未显著)的组合,在 holdout 外推上依然不劣于规则,直接升
E5。其中 escherichia_coli×meropenem、salmonella_enterica×ceftriaxone 同时也过 S2 safety-pass。

| species | drug | v0.9 | v1 | ΔVME(ST-CV) |
|---|---|:--:|:--:|--:|
| acinetobacter_baumannii | meropenem | E3 | E5 | -0.0007 |
| escherichia_coli | ciprofloxacin | E3 | E5 | -0.0097 |
| escherichia_coli | meropenem | E3 | E5 | -0.0182 |
| klebsiella_pneumoniae | ciprofloxacin | E3 | E5 | 0.0 |
| salmonella_enterica | ceftriaxone | E3 | E5 | -0.0385 |

## practical(E3) → E4 strong-pass(2 个,S2 abstain 升 strong)

S2 abstain-aware 复评:在 c=1.0 满覆盖下 per-ST VME 显著优于规则(ΔVME<0 且 p<0.05),
从 practical 实升 strong-pass。

| species | drug | v0.9 | v1 | ΔVME(ST-CV) |
|---|---|:--:|:--:|--:|
| acinetobacter_baumannii | ampicillin | E3 | E4 | -0.2966 |
| acinetobacter_baumannii | aztreonam | E3 | E4 | -0.5289 |

## practical(E3) → E4 safety-pass(5 个,S2 abstain 高覆盖安全收益)

S2 abstain-aware 复评:在覆盖率 ≥0.8 下,对 covered 子集把危险漏判 VME 压到 ≤规则且 ME 受控
(fail-closed + abstain 叙事核心),升 safety-pass。这些**未过 holdout**(不在 anchor panel),
故止步 E4 不升 E5。

| species | drug | v0.9 | v1 | ΔVME(ST-CV) |
|---|---|:--:|:--:|--:|
| escherichia_coli | aztreonam | E3 | E4 | -0.0285 |
| escherichia_coli | chloramphenicol | E3 | E4 | -0.0064 |
| klebsiella_pneumoniae | tetracycline | E3 | E4 | -0.004 |
| pseudomonas_aeruginosa | cefepime | E3 | E4 | 0.0 |
| salmonella_enterica | tetracycline | E3 | E4 | 0.0 |
