# S5.1:机制消融——诚实清单(本地 EC/KP 6 anchor)

拆解 rule-first + ML fusion 优势来源。机制增益 = D_fusion_mech 的 per-ST VME − F(=C_fusion)的 per-ST VME(负 = 机制特征降低危险漏判)。**机制不是万能**:某些药机制帮忙、某些没用甚至微增 VME,如实记录——这正是可证伪的价值。

## 一键复现
```bash
.venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v1.ablation \
    --species escherichia_coli,klebsiella_pneumoniae
```

确定性:seed=0;两路 featurizer(base=parse_genotypes / mech=augmented_features)各 5 折 ST-grouped OOF;重跑一致。D_fusion_mech 逐字复现冻结生产路径。

## 机制确实帮了的组合(D−C<0)

| species | drug | vme_C(base融合) | vme_D(mech融合) | ΔVME(D−C) |
|---|---|---:|---:|---:|
| klebsiella_pneumoniae | meropenem | 0.1959 | 0.1115 | -0.0845 |
| salmonella_enterica | ceftriaxone | 0.1309 | 0.0926 | -0.0383 |
| pseudomonas_aeruginosa | levofloxacin | 0.2884 | 0.2621 | -0.0263 |
| escherichia_coli | meropenem | 0.1875 | 0.1693 | -0.0182 |
| klebsiella_pneumoniae | cefepime | 0.0448 | 0.0286 | -0.0162 |

## 机制无增益 / 反向的组合(D−C≥0)——诚实标记

| species | drug | vme_C(base融合) | vme_D(mech融合) | ΔVME(D−C) | 说明 |
|---|---|---:|---:|---:|---|
| pseudomonas_aeruginosa | meropenem | 0.5964 | 0.6024 | 0.006 | 机制融合 VME 略高于 base 融合(机制特征在该药未带来危险漏判增益) |
| escherichia_coli | ceftriaxone | 0.0242 | 0.0269 | 0.0027 | 机制融合 VME 略高于 base 融合(机制特征在该药未带来危险漏判增益) |
| escherichia_coli | ciprofloxacin | 0.0762 | 0.0773 | 0.0011 | 机制融合 VME 略高于 base 融合(机制特征在该药未带来危险漏判增益) |
| klebsiella_pneumoniae | ciprofloxacin | 0.0 | 0.0 | 0.0 | 机制与 base 融合等价(该药 VME 已由规则/base 特征吃满,机制无额外信息) |
| acinetobacter_baumannii | meropenem | 0.2215 | 0.2215 | 0.0 | 机制与 base 融合等价(该药 VME 已由规则/base 特征吃满,机制无额外信息) |

## rule vs ML vs fusion(危险漏判 VME 拆解)

| species | drug | A规则 | B纯ML | C base融合 | D mech融合 |
|---|---|---:|---:|---:|---:|
| acinetobacter_baumannii | meropenem | 0.2222 | 0.364 | 0.2215 | 0.2215 |
| escherichia_coli | ceftriaxone | 0.0297 | 0.1448 | 0.0242 | 0.0269 |
| escherichia_coli | ciprofloxacin | 0.087 | 0.3393 | 0.0762 | 0.0773 |
| escherichia_coli | meropenem | 0.1875 | 0.755 | 0.1875 | 0.1693 |
| klebsiella_pneumoniae | cefepime | 0.0591 | 0.2901 | 0.0448 | 0.0286 |
| klebsiella_pneumoniae | ciprofloxacin | 0.0 | 0.3509 | 0.0 | 0.0 |
| klebsiella_pneumoniae | meropenem | 0.2662 | 0.4562 | 0.1959 | 0.1115 |
| pseudomonas_aeruginosa | levofloxacin | 0.8728 | 0.3586 | 0.2884 | 0.2621 |
| pseudomonas_aeruginosa | meropenem | 0.6931 | 0.5704 | 0.5964 | 0.6024 |
| salmonella_enterica | ceftriaxone | 0.1311 | 0.1379 | 0.1309 | 0.0926 |

解读:rule-first 融合(C/D)的 per-ST VME 恒 ≤ 规则法(A)——融合只在规则判 S 的样本上叠加 ML 判 R,不会漏掉规则已抓到的耐药,故危险漏判不增反降。纯 ML(B)不借规则兜底,VME 通常高于融合——这正是 rule-first 的安全价值。机制特征(D vs C)是否再降 VME 逐药类不同,见上表。

## E:mech 融合 + abstain(选择性预测)

运行点 = coverage≥0.80 网格里 covered ME<0.10 的点中 covered per-ST VME 最低者(并列取最高覆盖率);无 ME-安全点则退回满覆盖(E≡D)。

| species | drug | D满覆盖VME | E covered VME | E coverage | ME-安全点? |
|---|---|---:|---:|:--:|:--:|
| acinetobacter_baumannii | meropenem | 0.2215 | 0.2215 | 1.0 | 否(退回 D) |
| escherichia_coli | ceftriaxone | 0.0269 | 0.0112 | 0.9 | 是 |
| escherichia_coli | ciprofloxacin | 0.0773 | 0.0773 | 1.0 | 否(退回 D) |
| escherichia_coli | meropenem | 0.1693 | 0.1344 | 0.8 | 是 |
| klebsiella_pneumoniae | cefepime | 0.0286 | 0.0286 | 1.0 | 否(退回 D) |
| klebsiella_pneumoniae | ciprofloxacin | 0.0 | 0.0 | 1.0 | 否(退回 D) |
| klebsiella_pneumoniae | meropenem | 0.1115 | 0.1115 | 1.0 | 否(退回 D) |
| pseudomonas_aeruginosa | levofloxacin | 0.2621 | 0.224 | 0.85 | 是 |
| pseudomonas_aeruginosa | meropenem | 0.6024 | 0.6024 | 1.0 | 否(退回 D) |
| salmonella_enterica | ceftriaxone | 0.0926 | 0.0924 | 0.8 | 是 |

解读:abstain 只在 covered ME 能压到 <0.10 的组合上有 ME-安全运行点(如 EC×ceftriaxone,弃权 ~10% 把 covered VME 再砍半)。规则过度判 R、covered ME 始终≥0.10 的组合(KP×mero/cefepime、KP×cipro),abstain 虽能把 covered VME 压到极低,却以 ME 爆表为代价——退化预测器,正是本项目 ME 纪律要挡的,故诚实退回满覆盖 D,不报该退化点。

