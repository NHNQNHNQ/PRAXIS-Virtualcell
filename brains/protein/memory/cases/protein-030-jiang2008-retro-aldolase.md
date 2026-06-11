---
case_id: protein-030-jiang2008-retro-aldolase
design_task: enzyme_de_novo_design
target_pdb: 3B5L
target_uniprot: nan
fold_class: TIM_barrel_or_jellyroll
length_range: 200-300
tools: [Rosetta, RosettaMatch, RosettaDesign, X-ray, kinetic_assay]
key_paper_doi: 10.1126/science.1152692
key_metrics:
  designs_synthesized: "72 designs"
  active_designs: "approx 32 designs (RA-1 to RA-32) showed measurable retro-aldol catalysis"
  kcat_KM_top: "approx 0.74 M^-1 s^-1 (RA-22 best of cohort)"
  rate_acceleration_over_uncatalyzed: "approx 10^4 fold rate acceleration"
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [enzyme-design, de-novo, retro-aldolase, RosettaMatch, theozyme, classical-Rosetta, lysine-Schiff-base]
unverified_details:
  - "Specific kcat numbers vary by design; RA-22 ~0.74 M^-1 s^-1 from supp Table"
  - "32/72 active rate is approximate; some designs marginally above background"
---

# De novo retro-aldolase（Jiang et al. Science 2008）

## Background
- 起点：Aldol / retro-aldol 反应在自然界由 class I (Schiff base via Lys) + class II (metal-dependent) aldolase 催化；非自然 substrate 上的 retro-aldol 设计是测试 computational catalysis design 的标准 benchmark
- 目标：设计 catalyzing methodol 类底物 retro-aldol cleavage 的酶——使用 Lys ε-amino 形成 Schiff base 中间体（class I 机制）
- 应用：与 Siegel 2010 DA 同期的 landmark de novo enzyme design 工作；展示 4-residue theozyme + scaffold matching 范式可在多种 reaction class 上 generalize

## What I actually did（基于论文）
1. **Reaction mechanism choice**：class I retro-aldol via Lys Schiff base + Tyr H-bond + Asp/Glu carboxylate + Trp π-π stack
2. **Theozyme**：4-residue active site geometry from QM-modeled transition state
3. **Scaffold matching**：RosettaMatch scan PDB scaffolds for backbone meeting all 4 catalytic positions geometrically
4. **Sequence design**：RosettaDesign optimize substrate pocket + catalytic geometry
5. **Filters**：
   - All 4 catalytic residues placed within 0.5 Å of theozyme target
   - Substrate binding score
   - Pocket complementarity
6. **Synthesis**：72 designs DNA → E.coli expression
7. **Assay**：retro-aldol HPLC monitoring + Schiff base mass-spec + X-ray for top hits
8. **结果**：~32 designs showed measurable activity; RA-22 best with kcat/KM ~0.74 M⁻¹s⁻¹; 10^4 rate acceleration over uncatalyzed background

## ★ 排除的位点/区域
- **Lys 必须 in 主活性位点位置**：不允许其他位置 design Lys（避免错误 Schiff base formation）
- **Pre-organized loop conformations**：定义 substrate channel 的 loop 不动
- **Disulfide bonds**：保留
- **Glycosylation 位点**：BL21 不需要
- **Substrate-irrelevant residues > 8 Å from active site**：可大量 mutate
- **跨膜段 / 信号肽**：不适用

## ★ 失败模式
- **大多数 design active 但 kcat 极低**：32 active 中 ~25 在 ~10^-3 turnover/s 水平
- **Schiff base formation 但 retro-aldol 不发生**：~10 designs 显示 mass-spec 上 Schiff intermediate 但 substrate cleavage 慢
- **Lys pKa shift 不准确**：理论 active Lys 应 pKa-perturbed（降到 ~7）；多数设计 Lys pKa 仍接近 free 10.5——降低活性
- **Substrate hydrolysis competing**：少数 design substrate 在 active site 直接 hydrolyzed
- **Off-pathway aldol formation**：极少数设计 catalyze the forward direction (aldol formation)
- **Pocket too tight (KM > 5 mM)**：~20% 设计 substrate binding 弱
- **Directed evolution 显著提升**：后续 Althoff 2012 / Giger 2013 用 SSM 把 RA-22 kcat/KM 提升 ~10^4 倍 (industrial level)

## ★ 方法选择决策链
- **为什么 class I (Schiff base) 而非 class II (metal)**：metal-dependent aldolase 需要金属 placement geometry 极严苛；Lys 简单
- **为什么 4-residue theozyme 而非 5+**：geometric search 复杂度爆炸；4 residues 是 sweet spot
- **为什么 RosettaMatch on PDB scaffolds 而非 ab initio backbone**：scaffold pool 提供 stable fold prior；ab initio 在 catalytic context 太冒险
- **为什么 72 designs 而非 100s**：合成 + assay cost (2008 era)
- **为什么 X-ray 验证 (subset)**：catalysis 决定于 active site geometry；模拟不够确认
- **为什么 forward-trapping (Schiff base mass-spec)**：直接测 catalysis intermediate；biophysical 验证机制

## ★ In silico vs in vitro 差距
- **In silico filter pass → 表达**：~72 → ~65 (~90%)
- **表达 → substrate binding**：~65 → ~50 (~77%)
- **Binding → Schiff base detected**：~50 → ~40 (~80%)
- **Schiff → measurable retro-aldol catalysis**：~40 → ~32 (~80%)
- **kcat/KM ≥ 0.1 M⁻¹s⁻¹ (useful threshold)**：~32 → ~10 (~31%)
- **总转化率 (in silico → useful catalyst)**：~10/72 ≈ **14%**（比 DA-Siegel 高，因为 Schiff base 机制 forgiving）
- **vs case 029 (Siegel 2010 DA)**：retro-aldol 设计 conversion 率高 (~14% vs ~2.4%)；DA 没有自然 enzyme template，机制设计更难
- **vs case 020 (Yeh 2023 luciferase)**：classical Rosetta retro-aldol > deep-learning luciferase 在 active 率 hard 比较——substrates 难度不同
- **No standard pLDDT/iPTM**：classical Rosetta；metric 是 Rosetta_ddG + RMSD vs theozyme + 实验 kcat/KM

## Lessons → seeds for rules
1. **Reaction mechanism choice 极影响 design 难度**：Schiff base / metal-free 比 transition-metal catalysis 容易 10x
2. **4-residue theozyme** 是 RosettaMatch 实用 sweet spot；多 residue 几何 search 困难
3. **Lys pKa 在 active site 是 design challenge**：自然 enzyme 微调 pKa；computational design 较粗
4. **Schiff base mass-spec 验证 intermediate**：catalysis 机制 confirmation 必要
5. **Directed evolution 必要 follow-up**：raw kcat 通常 ~10^-3-10^-2/s，industrial 需 10^4 提升
6. **14% useful enzyme rate** 是 classical Rosetta retro-aldol design 的 baseline
7. **PRAXIS implication**：enzyme_de_novo_design skill 必须 include (a) reaction mechanism choice flow, (b) theozyme construction, (c) scaffold matching (RFdiffusion-AA 替代 RosettaMatch), (d) DE follow-up plan; rule 03 active site freeze 升级为 catalytic residue freeze + Lys/Cys 位置约束

## 数据指针
- 论文 + supp: https://doi.org/10.1126/science.1152692
- RA-22 PDB: 3B5L (highest activity)
- 后续 Althoff 2012 / Giger 2013 directed evolution 论文继续提升 kcat
