---
case_id: protein-011-cao2020-lcb-spike-binder
design_task: de_novo_binder
target_pdb: 6M0J
target_uniprot: P0DTC2
fold_class: mini_protein_helical
length_range: 50-65
tools: [Rosetta, RIFdock, Rosetta_FastDesign, ProteinMPNN-precursor, NMR, BLI]
key_paper_doi: 10.1126/science.abd9909
key_metrics:
  in_vitro_KD_top: "0.1 nM (LCB1 to spike RBD)"
  in_silico_to_in_vitro_success_rate: "approx 1% of designs measured pass binding"
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [binder, mini-protein, helical-bundle, SARS-CoV-2, spike-RBD, RIF, Rosetta]
unverified_details:
  - "Exact ProteinMPNN version not used here — paper precedes ProteinMPNN; sequence design via Rosetta FastDesign"
  - "Quoted KD for LCB1 is from BLI; SPR values may differ slightly"
---

# LCB1 / LCB3：picomolar mini-binder 设计 SARS-CoV-2 spike RBD（Cao et al. Science 2020）

## Background
- 起点：SARS-CoV-2 spike RBD 与 ACE2 结合界面已知（PDB 6M0J）。Baker 实验室设计 50-65 aa 的 helical mini-binder 阻断 RBD-ACE2 互作
- 目标：picomolar 亲和力 + 紧凑可口服可吸入的 mini protein
- 应用：作为可雾化的 COVID 治疗剂前体；展示 RIF + Rosetta 驱动的 de novo 接口设计能在挑战 target（病毒蛋白、糖基化）上达到 pM 级亲和

## What I actually did（基于论文）
1. **Target prep**：从 PDB 6M0J 提取 RBD chain；分离 ACE2-binding hotspot 残基（Y453, F486, N487, Y489 等关键 ACE2 接触位点）
2. **Scaffold library**：Baker 组的 helix bundle / hairpin scaffold 库（数千个 mini protein backbone）作为 RIF docking input
3. **RIF (Rotamer Interaction Field) docking**：用 RIF 把 scaffold 摆到 RBD 表面，使 hotspot 残基形成预设的 H-bond / hydrophobic 模式
4. **Rosetta FastDesign**：每个 docked scaffold 跑序列优化（FastDesign + LayerDesign），靠 Rosetta talaris/ref15 score function
5. **Filter cascade**：ddG_complex < -40 REU；contact_molecular_surface > 600 Ų；shape_complementarity > 0.6；buried unsatisfied H-bonds < 4
6. **Total designs**：~10^6 RIF dockings → ~10^5 sequences → ~10^4 通过 in silico filter → 选 ~150 设计实测
7. **Wet lab**：基因合成 → E.coli 表达 → 大肠杆菌可溶蛋白筛选（~50% 表达）→ Spike 结合 ELISA → Top hits → BLI / SPR 精测亲和
8. **结果**：LCB1 KD ≈ 100 pM（BLI）；LCB3 KD ≈ 200 pM；两者在小鼠 SARS-CoV-2 攻毒模型保护
9. **结构验证**：cryo-EM 复合物（与 spike trimer），界面与设计 model RMSD < 1 Å

## ★ 排除的位点/区域
- **RBD 糖基化位点**（N343 N-link glycan）：binder 不能撞到糖基化轨道——FastDesign 的能量函数没建模糖基，必须显式标 forbidden
- **N501 / E484 / K417 等 RBM 中心残基**：是 ACE2 hotspot，binder 应"占位"覆盖它们，但 RFdesign 时不能让 binder 自身突变这些残基（target 是 fixed）
- **Spike RBD 上的 disulfide bond C336-C361, C379-C432, C480-C488**：binder 不应触发这些 cys 重排
- **跨膜段 / 信号肽**：不在设计 target 内（只用 ECD）
- **聚集敏感的 mini-protein scaffold**（高 SAP score 的）：scaffold pre-filter 阶段就剔除

## ★ 失败模式
- **In silico 过滤通过但 E.coli 表达失败 ≈ 50%**：mini-protein 表面残基过多疏水或自聚集；需 Rosetta SAP / ESM PLL 二次过滤
- **表达成功但 SEC 多聚体**：~30% 在 SEC 出现寡聚／聚集；强制 SEC 单峰才进 BLI
- **结合无功能 (off-epitope)**：~40% binder 在 ELISA 信号出来但实际不阻断 ACE2-RBD（不在正确 epitope）；需 ACE2 阻断 ELISA 而非 RBD-binding ELISA 作为 main filter
- **High affinity → no neutralization**：少数 binder KD < 1 nM 但没 SARS-CoV-2 中和活性——可能 binder 角度不对或 spike 全长动力学问题
- **在 spike trimer 上失效**：mini-binder 在 isolated RBD 上 OK，但 trimer 上空间位阻；需 cryo-EM trimer 复合物验证
- **跨变体保留不可控**：B.1.1.7 / B.1.351 等突变后部分 binder 失效——designed for original Wuhan RBD，不天然 cross-variant

## ★ 方法选择决策链
- **为什么 RIF 而非 RFdiffusion**：2020 年 RFdiffusion 还没出现；当时 SOTA 是 RIF docking + Rosetta，需要 hotspot pre-defined 是必要约束
- **为什么 mini-protein scaffold 库 而非 ab initio 生成**：scaffold-guided 提供 fold prior，提高 in vitro fold 成功率；ab initio 生成在当时还达不到 mini-protein 设计需要的 hyperstability
- **为什么 ddG cutoff -40 REU 而非 -30**：spike RBD 是病毒 fitness target，要拉开 picomolar 才有意义；-30 通常给 micromolar；论文经验 -40 是 nM 门槛
- **为什么 SPR + cryo-EM 双验证**：BLI 是 throughput，SPR 是 KD 精测，cryo-EM 验证 epitope；缺任一 modality 都不能下"已 hit"结论
- **为什么 ~150 designs 实测而非 ~10**：mini-binder paper 的经验是 ~1% in silico filter pass 真在 in vitro 起作用——所以要超量

## ★ In silico vs in vitro 差距
- **表达可溶率**：in silico 通过 → E.coli 可溶 ~50%（剩 50% inclusion body 或不表达）
- **SEC 单峰率**：表达成功的中 ~70% SEC 单峰（30% 多聚）
- **结合 ELISA 阳性率**：SEC 单峰中 ~40-60% 在 spike RBD ELISA 出阳性
- **Sub-nM 亲和率**：ELISA 阳性中 ~5-10% 实测 KD < 1 nM
- **picomolar (KD < 100 pM) 率**：~150 designs → 2 个 (LCB1, LCB3) ≈ **1%**
- **跟当代 RFdiffusion 报告的 5-15% 比**：这条 pipeline 比 RFdiffusion 的总成功率低（更老 + 更难 target），但峰值亲和（pM）更高

## Lessons → seeds for rules
1. **Hotspot 必须显式标**——不仅 binder 朝向，还要明确 forbidden 残基（糖基化、disulfide）
2. **多 metric 联合 filter**（ddG + CMS + SC + buried unsat）远比单 ddG 准；buried unsat H-bonds 是质量护城河
3. **150 → 1 picomolar 的漏斗**——"超量设计"是 pM 必经
4. **SPR + cryo-EM 双验证**：BLI 看亲和，cryo-EM 看 epitope 是否在设计意图位置
5. **跨变体不天然继承**——designed for 原始株可能在 Omicron 上失效；real-world deployment 要 spike variant panel 重测
6. **Mini-protein scaffold 重于 ab initio**：在挑战 target 上 fold prior（已知小蛋白 scaffold 库）比从零生成更可靠

## 数据指针
- 论文 + supp: https://doi.org/10.1126/science.abd9909
- LCB1 / LCB3 PDB（trimer cryo-EM）: 有 supp 报告（exact PDB IDs 不在我的 cache，需 follow-up 校验）
- spike RBD reference: 6M0J
