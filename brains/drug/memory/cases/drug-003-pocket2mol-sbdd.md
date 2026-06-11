---
case_id: drug-003-pocket2mol-sbdd
project_phase: hit_id
target_uniprot: Q86W56 (PARP1) 
target_pdb: 4UND
target_class: enzyme_DNA_repair
indication: oncology_BRCA_mutant
modality: small_mol_inhibitor
hit_id_method: structure_based_de_novo
representative_compound:
  - chembl_id: CHEMBL521686 (olaparib)
    inchikey: FDLYAMZZIXQODN-UHFFFAOYSA-N   # corrected; original case had wrong tautomer
    smiles: O=C(c1cc(Cc2n[nH]c(=O)c3ccccc23)ccc1F)N1CCN(C(=O)C2CC2)CC1
tools: [Pocket2Mol, TargetDiff, DiffSBDD, RDKit, Vina post-eval]
qa_notes:
  - "Original SMILES had hydrazone tautomer instead of ChEMBL canonical; QA pipeline (RDKit InChIKey vs ChEMBL standard_inchi_key) caught the mismatch and replaced with canonical."
key_paper_doi: 10.48550/arXiv.2205.07249
unverified_details: [doi]   # arXiv preprint; not indexed in CrossRef public API
status: validated
validated: true
source: praxis_seed
---

# Pocket2Mol：基于 pocket 的分子生成（不依赖 reference ligand）

## Background
Pocket2Mol（Peng 2022）和 TargetDiff（2023）等 structure-based generative models 输入是 pocket 3D 结构，输出 atom-by-atom 生成的分子，能在 pocket 内 "原位" 设计。优势：不需要 reference ligand 启动；劣势：物理可信度有限，需 docking + MD 后验。

## What I actually did
1. **Pocket prep**：4UND 去 ligand → fpocket/Pocket2Mol pocket detection → 取 active site pocket（不是任何 surface pocket）
2. **Pocket2Mol 生成**：default config，~10 atoms/sec，per pocket 生成 1000 分子；每个 ~30 秒
3. **Validity check**：RDKit MolFromSmiles → valence + ring 合理性。Pocket2Mol output 90%+ valid SMILES，但 ring system 时有奇怪（4-元 ring、桥环等）
4. **Drug-likeness filter**：QED ≥ 0.5 + MW 250-550 + logP 0-5 + HBA ≤ 10 + HBD ≤ 5
5. **Synthesis filter**：SAscore ≤ 4.5
6. **Re-dock 验证**：用 Vina 把生成分子放回 pocket，看 score。Pocket2Mol 输出 pose 与 Vina re-dock pose RMSD < 2 Å = 可信；> 4 Å = 生成 pose 物理不合理
7. **Activity prediction**：QSAR model on ChEMBL PARP1 数据评估 predicted IC50
8. **Top 50 → MD 50ns**：复合物稳定性，> 80% 时间 ligand 留 pocket = stable
9. **比对 Olaparib**：Olaparib 的 phthalazinone scaffold 出现在 generated 中? 一般 < 5% generation 含已知 scaffold（大多新颖）

## ★ 排除/不做的事
- **不 re-dock 验证**：生成 pose 物理可信度不保；必须 Vina/GNINA 重 dock
- **不 filter PAINS / reactive groups**：Pocket2Mol 不知道这些规则，可能生成 quinone/Michael acceptor
- **不算 SAscore**：生成可能很 exotic 化学，合成步骤 8+ 是常态
- **跳过 MD 验证**：单 docking pose 不代表 binding stability
- **直接用生成分子做 wet lab**：未做 sanity check + 物理验证 + ADMET 是 reckless
- **Pocket detection 只信自动**：fpocket 可能给 surface pocket 不是 active；human review 必须
- **生成数量太少**（< 100）：sampling 噪声大，多样性不够看

## ★ 失败模式
- **Strain energy 高**：生成 ligand 在 pocket 的 conformation 内能高 (> 5 kcal/mol)，物理不可达
- **Atom collisions in generated**：Pocket2Mol 偶尔生成原子互相 clash（尤其 H-deficient 表示）
- **同 atom 重复**：生成分子有多个 cation，不合理 zwitterion
- **Cofactor missing**：PARP 与 NAD+ 共结合，生成时未考虑 NAD+ 占位
- **Selectivity 不评估**：PARP1 vs PARP2 vs PARP3 selectivity 是临床问题，generative 完全不管
- **Re-dock 失败**：Pocket2Mol pose 在 Vina 重 dock 后跑到 pocket 外，原 pose 与 Vina pose 矛盾——选哪个？建议 trust Vina

## Lessons → seeds for rules
1. **Re-dock 验证强制**：生成 pose 与 docking pose RMSD < 2 Å 才信
2. **多 filter 串联**：valence → drug-likeness → SAscore → PAINS → re-dock → MD
3. **Pocket detection human review**：自动 detection 给候选，人工 confirm active site
4. **Strain energy 评估**：生成 conformation 内能 ≤ 5 kcal/mol vs 优化 conformation
5. **Selectivity 单独 docking**：family 里其他成员（PARP1 vs 2 vs 3）需 panel
6. **Cofactor / water 模型外提示**：报告生成时 pocket 缺什么
