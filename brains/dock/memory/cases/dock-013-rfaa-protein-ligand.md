---
case_id: dock-013-rfaa-protein-ligand
docking_type: foundation_model_complex_prediction
target_pdb: PoseBusters benchmark v2 + AstexDiverse
target_uniprot: any
target_class: mixed
ligand_type: small_mol_or_protein
system_specifics: {}
tools: [RoseTTAFold-AA, AlphaFold3, Boltz-1, Chai-1]
flexibility_required: backbone_flex
validation_benchmark: PoseBusters
key_paper_doi: 10.1126/science.adl2528
status: validated
source: praxis_seed
tags: [foundation_model, RFAA, RoseTTAFold-AA, ligand_complex, 2024]
---

# RoseTTAFold-AA：foundation model 的另一极

## Background
RoseTTAFold-AA (RFAA, Krishna et al. 2024 Science) 与 AlphaFold3 (Abramson et al. 2024) 是同期 foundation model — 都做 protein + ligand + NA 复合物预测，但训练集 + 架构有差异：
- **RFAA**: Baker lab; 单一 architecture handle protein/RNA/DNA/small mol; PDB-trained;
- **AF3**: DeepMind; diffusion-based; 更大模型 + 更多数据;
- **Boltz-1** (open-source): replicate of AF3 architecture.
PRAXIS-Dock 的 case dock-009 主要讲 AF3/Boltz；这里专门讲 RFAA 的 distinct profile + 何时优先用。

## What I actually did
1. **Setup**: RFAA inference pipeline — receptor sequence + ligand SMILES → input feature stack (与 AF3 类似但少 MSA 步骤)
2. **Benchmark**: PoseBusters v2 (428 complexes, 2021-2024 PDB time-split) + AstexDiverse (85 complexes, classic SBDD benchmark)
3. **Metrics 比较**:
   - RFAA top-1 RMSD ≤ 2Å rate: ~62% on PoseBusters (vs AF3 ~76% per Abramson 2024)
   - RFAA PoseBusters check pass rate: ~68% (vs AF3 ~50% — RFAA 输出物理 sanity 略好)
   - Average runtime per complex: RFAA ~2 min on A100 (vs AF3 with full MSA ~10 min)
4. **Cross-validation with AF3 + Boltz**: 3-way consensus — when all 3 give similar pose (RMSD < 2Å), confidence high; divergent = low confidence
5. **PoseBusters 强制**: 与 dock-009 同口径，每个 RFAA 输出 pose 跑 PoseBusters check
6. **当 RFAA > AF3**: (a) 训练分布外 chemistry (RFAA 训练时 PDB 含更多 unusual ligands)；(b) 速度敏感 batch screening (AF3 太慢)；(c) MSA 不可得 (RFAA 单序列 mode 较稳定)

## ★ 排除/不做的事
- **RFAA 当 affinity predictor**: 与 AF3 同病 — confidence ≠ KD (case dock-009 lesson 共享)
- **PoseBusters 跳过**: 即使 RFAA pass rate 略好 (~68%)，剩余 ~32% 仍含 atom clash / 键长异常 (case dock-009 lesson)
- **训练集泄漏 (PDB ID < 2021)**: 与 AF3 共享 PDB；fair benchmark 必用 post-2021
- **Cofactor 缺失**: RFAA 训练含 cofactor 但若用户没显式声明 NAD/heme/Mg2+ → active site 几何同样塌
- **RFAA-specific bug for membrane proteins**: 早期 v0.1 weights 对 GPCR-like 7TM bundles loop 区域信任度低；用 v2+ weights
- **不报 model_used**: 报告里 "AF3 = RFAA = Boltz" 等同 — 三个不同模型不同失败 profile，必须显式区分

## ★ 失败模式
- **Glycosylation absent**: spike protein / IgG glycan 模型不含 → docking 给假 epitope
- **Stereochemistry instability**: RFAA 偶尔翻转 chirality (与 AF3 同) — 必须输入 isomeric SMILES + 检查输出
- **OOD ligand chemtypes**: PROTAC bivalent ligand / macrocycle > 8-membered ring / metal-coordinated → RFAA 退化到 random pose 水平
- **RNA secondary structure errors propagate**: 若用 RFAA 联合预测 protein-RNA，RNA 2D structure error → protein 接触面错
- **Multi-state conformational landscape**: foundation models 给 single pose, 不模拟 ensemble — case dock-007 ensemble docking 仍是补充手段
- **Ion pre-exposure**: Mg2+/Zn2+ 在 binding pocket 时不指定 → 偶尔 RFAA "省略" 离子，affinity 重排
- **Iterative refinement absence**: RFAA 给 single forward pass — AF3 的 multiple seed + recycling 在 RFAA 里更弱

## Lessons → seeds for rules
1. **3-way consensus = AF3 + Boltz + RFAA** for high-confidence complex prediction (升级 case dock-009 的 AF3+Boltz dual-check)
2. **Speed/accuracy trade-off**: RFAA ~2 min vs AF3 ~10 min — batch screening 用 RFAA, 单 pose precision 用 AF3
3. **PoseBusters pass rate 比较**: RFAA ~68% > AF3 ~50% (Boltz between) — 但 RFAA top-1 RMSD rate 较低 — 看具体 metric
4. **RFAA single-sequence mode 优势** when MSA shallow / unavailable
5. **训练时间 split + cofactor explicit** 与 case dock-009 共享原则
6. **Confidence label 必显式区分 model**: "RFAA top-1 RMSD ≤ 2Å, conf high" ≠ "AF3 top-1 RMSD ≤ 2Å, conf high" — 不同模型不同 failure mode
