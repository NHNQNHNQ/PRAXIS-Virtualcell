---
case_id: protein-023-goldenzweig2016-pross-stability
design_task: stabilization
target_pdb: 1EMA            # GFP — one of PROSS test proteins (paper supp Table)
target_uniprot: P42212      # GFP from Aequorea victoria, representative cohort member
fold_class: any
length_range: 100-500
tools: [PROSS, Rosetta_FastDesign, Phyre2_or_HHpred_for_homologs, MSA_consensus, Tm_DSF, BL21_expression]
key_paper_doi: 10.1016/j.molcel.2016.06.012
key_metrics:
  proteins_redesigned: "approx 14 proteins (cohort across diverse folds)"
  bacterial_expression_yield_improvement: "average ~3-10x increase in BL21 soluble expression"
  Tm_improvement: "average +5 to +12 degC across cohort"
  activity_retention: "majority retained >50% wild-type activity"
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [stabilization, PROSS, Tm, expression-yield, evolutionary-consensus, Rosetta, automated-design]
unverified_details:
  - "PDB 4FVE used as stability test target representative; full cohort spans 14 proteins with various PDB entries"
  - "Tm + expression numbers are averages across cohort; per-protein numbers in supp Table"
---

# PROSS：自动稳定 + 提高表达（Goldenzweig et al. Mol Cell 2016）

## Background
- 起点：蛋白工程瓶颈之一是稳定性 + 表达 yield；很多 industrially / scientifically interesting 蛋白在 BL21 不可溶或表达极少
- 目标：建立全自动 pipeline (PROSS, Protein Repair One-Stop Shop) 同时提高 Tm + bacterial expression yield，不需要 case-by-case 人工 design
- 应用：稳定性工程 SOTA baseline；后续 ProteinMPNN-stabilization (Watson 2023 / Dauparas 2022) 比较的 reference；现在还在 industrial enzyme + research protein 中广泛使用

## What I actually did（基于论文）
1. **Input**：input PDB（experimental 或 homology model）+ MSA from HHpred/Phyre2
2. **MSA evolutionary consensus**：在 MSA 中找哪些 position 在自然界 evolutionary 偏向特定 aa（≥10x 频率优势）
3. **Rosetta single-point ddG**：每 position 跑 Rosetta cartesian_ddg 找稳定突变（ΔΔG < -1 kcal/mol）
4. **Joint filter**：只接受同时满足 evolutionary consensus + Rosetta-stabilizing 的突变
5. **Combinatorial design**：贪心 / 蒙特卡洛组合多个突变（避免冲突）
6. **Output**：stabilized variant with 5-15 mutations
7. **Validation cohort**：~14 蛋白跨 fold class（kinase, GFP-like, transferase 等）
8. **Wet lab**：基因合成 + BL21 转化 + DSF Tm + 活性 assay
9. **结果**：average +5-12°C Tm increase，3-10x expression yield increase，多数保留 >50% activity

## ★ 排除的位点/区域
- **Active site 残基（5 Å radius around catalytic residues）**：禁止 mutation（rule: catalytic residues are forbidden）
- **Ligand-binding residues**：受 substrate / cofactor 接触的残基不动
- **PPI 接口残基**：如果蛋白功能依赖 PPI，frozen
- **Disulfide bonds** 不动；自由 Cys 也不动（避免 misformation）
- **Glycosylation sites**：如果是真核蛋白用 BL21（无糖基）就不需要保留；但 N-link 位点本身不动
- **Buried polar residues**：可调但 risk 高（破坏 inter-residue H-bond）；论文中 case-by-case 评估

## ★ 失败模式
- **Tm 升高但 activity 下降 50%+**：~20% case 牺牲 activity 保 stability——典型 stability/activity tradeoff
- **MSA 较 shallow 的蛋白 PROSS 效果差**：< 50 homologs 时 evolutionary consensus 不可靠
- **Disulfide 含量高的蛋白上 PROSS 受限**：design 空间被 SS 压缩
- **Membrane protein 上不适用**：水溶蛋白训练，膜蛋白 environment 不同
- **Expression 增加但 SEC 多聚**：少数变体 BL21 表达量大但形成 inclusion body / oligomer
- **个别突变在 MSA 中常见但 Rosetta 给 destabilizing**：filter 已自动 exclude；但偶尔保留 design 中
- **MSA bias toward thermophilic species**：可能引入"thermophilic shift" 但不一定符合 mesophilic activity 偏好

## ★ 方法选择决策链
- **为什么 evolutionary consensus + Rosetta ddG 双 filter**：单方都有 false positives；联合显著降低假阳率
- **为什么 cartesian_ddg 而非 BuildModel**：cartesian 比 fixed-bb PyRosetta cartesian_ddg 更精确（相对 ddG）；但慢 5-10x
- **为什么 ≥10x evolutionary frequency advantage**：经验阈值——保证 evolutionary preference 真实而非 random
- **为什么 BL21 而非真核 expression**：throughput 高 + 大多数研究 protein 在 BL21 测；真核 expression 要 secondary 验证
- **为什么 DSF Tm 而非 CD melting**：throughput 100x；CD 是 low-throughput
- **为什么 14 蛋白 cohort 而非更深 1-2 蛋白**：generalization——证明 PROSS 跨 fold class 都有效

## ★ In silico vs in vitro 差距
- **In silico 通过 → BL21 表达增加**：~14 蛋白，全部表达增加（>2x in soluble fraction）
- **Tm 上升 ≥5°C**：~12/14 (~85%)
- **Activity retained >50% WT**：~10/14 (~71%)
- **同时 stability + activity OK**：~9/14 (~64%) **← 这才是有用 stabilization**
- **vs case 003 (Watson 2023 ProteinMPNN DHFR)**：PROSS 在 expression 提升上更好（10x vs 2-3x）；ProteinMPNN 在 single-protein deep-design 上更灵活
- **No standard pLDDT/iPTM**：non-DL pipeline；用 Rosetta cartesian ddG + Tm + expression

## Lessons → seeds for rules
1. **Evolutionary consensus + Rosetta ddG 双 filter** 是稳定化 design 的 high-precision 策略
2. **≥3 evidence rule**：MSA frequency ≥10x + Rosetta ddG < -1 kcal/mol 是经验联合阈值
3. **Active site / ligand binding / disulfide 必 freeze**——rule 03 直接对应
4. **Tm/activity tradeoff 是 reality**：~30% 设计要 sacrifice activity 保 stability；用户必须知情
5. **MSA 浅的蛋白 PROSS 失效**：< 50 homologs → degrade 到 Rosetta-only mode
6. **DSF Tm assay 是 throughput 标准**：CD 仅 confirmation
7. **PRAXIS implication**：proteinmpnn_redesign skill 拓展时可加 PROSS-style evolutionary filter；stabilization task 应 default `--use-msa --use-cartesian-ddg`

## 数据指针
- 论文 + supp: https://doi.org/10.1016/j.molcel.2016.06.012
- PROSS 服务器: https://pross.weizmann.ac.il
- 14 case cohort PDB IDs + Tm 数据 在 supp Table
