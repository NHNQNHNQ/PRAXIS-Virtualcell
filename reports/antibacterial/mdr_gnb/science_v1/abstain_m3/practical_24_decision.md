# S2.1:practical 组合 abstain-aware 分级(本地 EC/KP 13 组合)

把 24 个 practical(rule-first 融合不劣于规则法但未达统计显著)组合,通过 **abstain(选择性预测)** 重新分级:对低置信样本弃权,考察能否在高覆盖率(≥70%)下把 covered 子集危险漏判 VME 压到 ≤ 规则法且 ME 受控,从而升级为 **safety-pass**(平台 fail-closed + abstain 叙事核心)。

## 进度

- 本地 **24/24** 组合已做(EC/KP);PA/AB/SA 的 11 个 practical 待 53 数据管线(S2 后续)。
- 分层:**strong-pass 2** · **safety-pass 7** · **practical-only 15**。

## 一键复现

```bash
.venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v1.abstain_practical \
    --species escherichia_coli,klebsiella_pneumoniae,pseudomonas_aeruginosa,acinetobacter_baumannii,salmonella_enterica
```

确定性:seed=0;置换检验 10000 次固定 seed;覆盖率网格 {1.0,0.9,0.8,0.7,0.6};重跑一致。

## safety-pass 亮点

| species | drug | coverage_at_pass | covered VME | 规则 VME | covered ME |
|---|---|:--:|---:|---:|---:|
| escherichia_coli | aztreonam | 0.9 | 0.0076 | 0.0376 | 0.0795 |
| escherichia_coli | chloramphenicol | 0.9 | 0.0091 | 0.0226 | 0.0217 |
| escherichia_coli | meropenem | 0.8 | 0.0923 | 0.1739 | 0.0239 |
| klebsiella_pneumoniae | tetracycline | 0.9 | 0.1508 | 0.2103 | 0.0738 |
| pseudomonas_aeruginosa | cefepime | 0.9 | 0.5644 | 0.6263 | 0.0766 |
| salmonella_enterica | ceftriaxone | 0.8 | 0.0323 | 0.0369 | 0.0492 |
| salmonella_enterica | tetracycline | 0.9 | 0.0138 | 0.0157 | 0.0493 |

解读:在保留 ≥70% 样本的前提下,covered 子集的危险漏判 VME 已 ≤ 规则法(且 ME<0.10);对弃权的低置信少数样本回落 fail-closed(判 R),整体不劣于规则法而覆盖多数病例。

## remained practical-only

| species | drug | 落层原因 |
|---|---|---|
| acinetobacter_baumannii | meropenem | coverage_insufficient:c≥0.70 内 covered ME 始终≥0.1(c=0.6 时 ME=0.4296),压 ME<0.10 须弃权>30% |
| acinetobacter_baumannii | tobramycin | coverage_insufficient:c≥0.70 内 covered ME 始终≥0.1(c=0.6 时 ME=0.5682),压 ME<0.10 须弃权>30% |
| acinetobacter_baumannii | trimethoprim-sulfamethoxazole | ΔVME=0.0 p=1.0(ML 无增益),abstain 无从降 VME |
| escherichia_coli | amikacin | ΔVME=0.0 p=1.0(ML 无增益),abstain 无从降 VME |
| escherichia_coli | ciprofloxacin | coverage_insufficient:c≥0.70 内 covered ME 始终≥0.1(c=0.6 时 ME=0.2112),压 ME<0.10 须弃权>30% |
| escherichia_coli | levofloxacin | coverage_insufficient:c≥0.70 内 covered ME 始终≥0.1(c=0.6 时 ME=0.5154),压 ME<0.10 须弃权>30% |
| klebsiella_pneumoniae | ampicillin | coverage_insufficient:c≥0.70 内 covered ME 始终≥0.1(c=0.6 时 ME=1.0),压 ME<0.10 须弃权>30% |
| klebsiella_pneumoniae | aztreonam | coverage_insufficient:c≥0.70 内 covered ME 始终≥0.1(c=0.6 时 ME=1.0),压 ME<0.10 须弃权>30% |
| klebsiella_pneumoniae | chloramphenicol | coverage_insufficient:c≥0.70 内 covered ME 始终≥0.1(c=0.6 时 ME=0.7241),压 ME<0.10 须弃权>30% |
| klebsiella_pneumoniae | ciprofloxacin | rule_vme 已 0(规则无漏判),无提升空间;ΔVME=0.0 p=1.0 |
| klebsiella_pneumoniae | levofloxacin | rule_vme 已 0(规则无漏判),无提升空间;ΔVME=0.0 p=1.0 |
| klebsiella_pneumoniae | trimethoprim-sulfamethoxazole | ΔVME=0.0 p=1.0(ML 无增益),abstain 无从降 VME |
| pseudomonas_aeruginosa | amikacin | coverage_insufficient:c≥0.70 内 covered ME 始终≥0.1(c=0.6 时 ME=0.3896),压 ME<0.10 须弃权>30% |
| pseudomonas_aeruginosa | gentamicin | abstain 未在 c≥0.70 降 covered VME 至 <满覆盖融合 VME(ΔVME=-0.0736 p=0.0615,弃权增益不足) |
| pseudomonas_aeruginosa | tobramycin | coverage_insufficient:c≥0.70 内 covered ME 始终≥0.1(c=0.6 时 ME=0.7826),压 ME<0.10 须弃权>30% |

## 分组合 coverage-risk 摘要

| species | drug | 分层 | 满覆盖融合VME | 规则VME | ΔVME(per-ST) | p |
|---|---|:--:|---:|---:|---:|---:|
| acinetobacter_baumannii | ampicillin | strong | 0.0062 | 0.3665 | -0.2966 | 0.0001 |
| acinetobacter_baumannii | aztreonam | strong | 0.2559 | 0.9336 | -0.5289 | 0.0001 |
| acinetobacter_baumannii | meropenem | practical_only | 0.1685 | 0.1795 | -0.0007 | 0.5035 |
| acinetobacter_baumannii | tobramycin | practical_only | 0.0481 | 0.1803 | -0.0191 | 0.5054 |
| acinetobacter_baumannii | trimethoprim-sulfamethoxazole | practical_only | 0.003 | 0.003 | 0.0 | 1.0 |
| escherichia_coli | amikacin | practical_only | 0.193 | 0.193 | 0.0 | 1.0 |
| escherichia_coli | aztreonam | safety_pass | 0.015 | 0.0376 | -0.0285 | 0.0601 |
| escherichia_coli | chloramphenicol | safety_pass | 0.0181 | 0.0226 | -0.0063 | 0.2497 |
| escherichia_coli | ciprofloxacin | practical_only | 0.0212 | 0.0243 | -0.0097 | 0.0632 |
| escherichia_coli | levofloxacin | practical_only | 0.0115 | 0.0126 | -0.0118 | 0.4986 |
| escherichia_coli | meropenem | safety_pass | 0.1159 | 0.1739 | -0.0182 | 0.2475 |
| klebsiella_pneumoniae | ampicillin | practical_only | 0.0 | 0.0021 | -0.0063 | 0.5052 |
| klebsiella_pneumoniae | aztreonam | practical_only | 0.0394 | 0.0787 | -0.0198 | 0.0591 |
| klebsiella_pneumoniae | chloramphenicol | practical_only | 0.1786 | 0.2143 | -0.0667 | 0.5079 |
| klebsiella_pneumoniae | ciprofloxacin | practical_only | 0.0 | 0.0 | 0.0 | 1.0 |
| klebsiella_pneumoniae | levofloxacin | practical_only | 0.0 | 0.0 | 0.0 | 1.0 |
| klebsiella_pneumoniae | tetracycline | safety_pass | 0.1963 | 0.2103 | -0.0044 | 0.5058 |
| klebsiella_pneumoniae | trimethoprim-sulfamethoxazole | practical_only | 0.0183 | 0.0183 | 0.0 | 1.0 |
| pseudomonas_aeruginosa | amikacin | practical_only | 0.1857 | 0.3 | -0.1088 | 0.0639 |
| pseudomonas_aeruginosa | cefepime | safety_pass | 0.6263 | 0.6263 | 0.0 | 1.0 |
| pseudomonas_aeruginosa | gentamicin | practical_only | 0.3956 | 0.9084 | -0.0736 | 0.0615 |
| pseudomonas_aeruginosa | tobramycin | practical_only | 0.0467 | 0.0506 | -0.002 | 0.4957 |
| salmonella_enterica | ceftriaxone | safety_pass | 0.0346 | 0.0369 | -0.0385 | 0.4958 |
| salmonella_enterica | tetracycline | safety_pass | 0.0157 | 0.0157 | 0.0 | 1.0 |

口径提醒:coverage-risk 曲线用 **pooled VME**(covered 里 y==1 且 base==0 的比例);strong-pass 显著性用 **per-ST VME**(st_level_vme 均值 + 配对置换),两者不可混。

