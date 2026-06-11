---
case_id: protein-012-chevalier2017-flu-ha-mini-binder
design_task: de_novo_binder
target_pdb: 4FNK
target_uniprot: P03452
fold_class: mini_protein_helical
length_range: 40-65
tools: [Rosetta, FoldIt, oligonucleotide_chip_synthesis_yeast_display]
key_paper_doi: 10.1038/nature23912
key_metrics:
  designs_synthesized: "~22000 (oligo chip + yeast display, massively parallel)"
  in_vitro_binder_success_rate: "~3% of synthesized passed yeast display + further validated"
  best_binder_KD: "approx 1 nM (post-affinity-maturation)"
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [binder, mini-protein, massively-parallel, flu-HA, yeast-display, scaffold-library]
unverified_details:
  - "Exact target PDB 4FNK is the canonical influenza H1 HA structure used in the paper (one of several variants)"
  - "binder_KD 1 nM is approximate; affinity matured variants reported in low-nM range"
---

# Massively parallel mini-binder 设计 flu HA stem（Chevalier et al. Nature 2017）

## Background
- 起点：Influenza HA stem 是 universal flu vaccine target（受体结合保守区）。已知 broadly neutralizing antibodies bind 此 epitope
- 目标：用 Rosetta 设计 mini-binder（40-65 aa）模拟 HA stem 抗体的 hotspot 残基；用 oligo chip 合成 + 酵母展示做 massively parallel screening（~22,000 designs）
- 应用：超越 case-by-case 单分子设计的 throughput，验证 mini-binder design 是否可在群体上 reproducible，以及 yeast display + DNA chip 是否可以替代 E.coli expression 作为 high-throughput 验证

## What I actually did（基于论文）
1. **Target prep**：选取 H1 stem epitope（CR9114 / FI6 抗体接触表面），定义 hotspot 残基
2. **Scaffold library**：~10^4 mini-protein scaffold backbone（40-65 aa, mainly 3-4 helix bundles）
3. **RosettaScripts pipeline**：每个 scaffold rotamer-place hotspot residues at HA contact surface → FastDesign 周边 → ddG / shape complementarity filter
4. **Filter cutoffs**：ddG_complex < -25 REU；shape complementarity > 0.6；at least 3 hotspot H-bonds satisfied
5. **DNA library**：~22,000 designs DNA-encoded via oligo chip → Gibson assembly → 酵母展示
6. **Selection**：FACS 用 fluorophore-labeled HA 选 enrichment
7. **Validation**：top hits in E.coli 表达 → SEC monomer → BLI 测亲和
8. **Affinity maturation**：对 top binder 做 site-saturation mutagenesis，select for higher affinity → 多轮选出 nM 级 binder

## ★ 排除的位点/区域
- **HA receptor binding site (RBS)**：不应让 binder 阻塞 receptor binding（设计目标是 stem，不是 head）；显式标 RBS 为 forbidden
- **HA glycosylation sites**：HA 重糖基化，glycan shield 会遮挡 epitope；选 epitope 时避开 N-link 位点
- **HA cleavage site (HA1/HA2 boundary)**：不应让 binder 触发或抑制 HA0→HA1+HA2 切割
- **跨亚型保守度 < 50% 的位点**：universal target 要求 H1+H3+H5 都保留；只在某株保守的位点不进 hotspot 名单
- **聚集 prone scaffold**：SAP-score 高的 scaffold pre-filter 删除

## ★ 失败模式
- **酵母展示 false positive**：~22,000 设计中 ~700 在酵母 FACS 信号阳性，但 ~70% 在 E.coli 重表达后亲和测不到——酵母 display 浓度 / avidity effect 让弱 binder 看起来强
- **Mini-binder 表达成功率 50-60%**（与 Cao 2020 LCB 一致）
- **SEC 多聚 ~30%**——mini-protein 通病
- **Wild-type design 多数 micromolar**：未做 affinity maturation 的 raw design 大多数 KD > 1 μM；要 SSM + 多轮选才到 nM
- **跨株失效**：在 H1 上 hit，到 H3 / H5 失活——universal binder 仍是挑战，single-step 设计不天然 cross-strain
- **Off-target 在 yeast surface 蛋白**：少数 hits 实际结合酵母细胞表面而非 HA——negative selection（无 HA 时 FACS gate）必要

## ★ 方法选择决策链
- **为什么 oligo chip + yeast display 而非单个 E.coli**：throughput 100x；尤其 mini-binder 的 in vitro 成功率本身只 ~5%，需要 1000+ designs 才能稳定拿到 hit
- **为什么 Rosetta FastDesign 而非更早的 fixed-bb design**：mini-binder 的 backbone 都需要 sub-Å rearrangement 容许，固定 backbone 太僵
- **为什么 affinity maturation 必须**：raw design 通常 μM；nM-level 要 SSM 选；这是 "design + select" 的混合策略
- **为什么 SEC + BLI 两步**：FACS 信号 + ELISA 信号都可能 false positive，monomer 状态 SEC + 量化亲和 BLI 才能确认
- **为什么不用 cryo-EM 定 epitope**：throughput 限制；只对 top 5-10 个 hits 做 X-ray / cryo-EM

## ★ In silico vs in vitro 差距
- **酵母展示阳性率**：22,000 designs → ~700 (~3%) FACS 阳性
- **E.coli 表达 + SEC 单峰**：~700 → ~250 (~36%)
- **BLI 测得亲和（KD < 10 μM）**：~250 → ~50 (~20%)
- **Sub-μM 率**：~50 → ~10 (~20%)
- **Affinity-matured 后 nM 率**：~10 → ~3-5（~50%；matured 提高 10-100x 亲和）
- **总转化率（DNA 设计 → nM-level binder）**：3-5 / 22,000 ≈ **0.02%**

## Lessons → seeds for rules
1. **Massively parallel synth + yeast display 是 mini-binder 的 enabler**——单 binder 拿 hit 概率太低，需 throughput
2. **Yeast display 信号不等于真亲和**——必须 E.coli 表达 + SEC + BLI/SPR 验证
3. **Raw design 多数 μM，nM 必须 affinity maturation**：design + selection 双轨
4. **Universal target 不天然 cross-strain**——即使 stem 设计也要 multi-strain 验证
5. **Negative selection 防止 off-target 表面蛋白**——yeast 自身蛋白是常见 false positive 源
6. **Filter 过严不如做更多设计**：~3% in silico filter pass 是 yield 上限——增加 throughput 比拼命收紧 filter 更高效

## 数据指针
- 论文 + supp: https://doi.org/10.1038/nature23912
- 设计 + 选中 binder 的氨基酸序列在 supp materials
- 若需 PDB IDs of validated binder + HA complex: 见 supp Table S2
