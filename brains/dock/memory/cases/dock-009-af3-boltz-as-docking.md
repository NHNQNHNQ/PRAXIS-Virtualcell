---
case_id: dock-009-af3-boltz-as-docking
docking_type: foundation_model_complex_prediction
target_pdb: multi (PoseBusters benchmark + AstexDiverse)
target_uniprot: any
ligand_type: small_mol_or_protein
tools: [AlphaFold3, Boltz-1, Chai-1, RoseTTAFold-AA (RFAA), DiffDock]
key_paper_doi: 10.1038/s41586-024-07487-w
status: validated
---

# AF3 / Boltz-1 / Chai-1 当 docking：foundation model 的崛起与陷阱

## Background
AlphaFold3 (2024) + Boltz-1 (2024 开源) + Chai-1 (2024) 把蛋白结构预测扩到含 ligand/nucleic acid/cofactor 的复合物——本质上是"docking 的替代品"，输入 receptor 序列 + ligand SMILES → 输出复合物结构。在某些 benchmark 上击败传统 docking，但有 distinct failure modes。

## What I actually did
1. **Setup**：受体序列 + ligand SMILES → 服务/local 输入，得到 complex structure
2. **关键 metric**：
   - pLDDT_ligand (ligand 周围 plddt) > 70
   - PAE_interface (蛋白-ligand 残基间 PAE) < 5 Å
   - chain_pair_iptm_ligand > 0.6
3. **PoseBusters benchmark**：评估 ligand pose physical plausibility
   - AF3 top-1 RMSD ≤ 2Å rate: ~76% (paper claim)
   - 但：~50% 的 PoseBusters checks fail（atom clash、键长异常等）
4. **Cross-validation**：与 Vina/GNINA pose 比对，3 方一致 = high confidence；分歧 → 物理 sanity check
5. **Train set leakage caveat**：AF3 训练含 PDB pre-2021，对 2021 后新化合物 fair evaluation 才有意义
6. **Novel ligand**：训练分布外的 ligand（unusual scaffold、non-drug-like）AF3 退化到 Vina 水平或更差

## ★ 排除/不做的事
- **AF3 当 affinity predictor**：iPTM ≠ KD；AF3 给 confidence not free energy
- **Train set 内化合物当公平 benchmark**：信息泄漏，performance 假高
- **不查 PoseBusters check**：top 1 RMSD < 2Å 但 pose 含 clash / 不合理键长——physically invalid
- **Single seed**：AF3 不同 seed 给 different pose；至少 5 seed
- **Co-factor 缺失**：与 cofactor 共结合的酶（NAD/heme），AF3 不含 cofactor 时 active site 塌
- **Membrane / glycan 系统**：AF3 不显式建模 lipid bilayer 与糖屏蔽

## ★ 失败模式
- **OOD ligand**：训练数据外（新合成 chemotype），fold 错位
- **Stereochemistry 处理粗糙**：手性 ligand AF3 偶尔给 wrong enantiomer
- **多 binding site 不区分**：受体多个 pocket（如 RNA polymerase），AF3 给 highest-confidence one 不知是否正确 site
- **Cofactor-dependent fold**：cofactor 缺失时 active site 模型崩
- **Ion 处理不稳**：Mg/Zn/Ca 等共结晶 ion 时有时无
- **PoseBusters check 失败**：pose 看似合理但物理细节错（键长、价态、原子间距）

## Lessons → seeds for rules
1. **AF3/Boltz/Chai 多 model 共识**：≥ 2 model 一致才 high confidence
2. **PoseBusters check 强制**：通过率 100% 才 production-ready；< 100% 警告
3. **Cofactor / metal / glycan 显式列出**：模型外因素必报告
4. **Cross-check with Vina**：传统 docking 一致性是 sanity
5. **Train data leakage check**：post-2021 的化合物 才 fair benchmark
6. **Confidence 不是 affinity**：iPTM/pLDDT 不能转 KD
