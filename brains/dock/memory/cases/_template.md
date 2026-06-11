---
case_id: dock-{nnn}-{shorthand}
schema_version: 1
docking_type: protein_ligand_redocking | protein_protein_with_restraints | protein_protein_blind | antibody_antigen | peptide_protein | covalent_protein_ligand | ensemble_protein_ligand | induced_fit_protein_ligand | foundation_model_complex_prediction | protein_nucleic_acid
target_pdb: 1ABC                     # 真实 PDB ID; 多 case 可逗号分隔
target_uniprot: P00000               # 可填 [list] 或 null
target_class: kinase | protease | GPCR | nuclear_receptor | ribosome | transcription_factor | other
ligand_type: small_mol_drug_like | peptide | antibody_Fv | nucleic_acid | covalent_warhead_small_mol | other
system_specifics:                    # 按 docking_type 选填以下子段; 其它留 null
  # PL: target_class + ligand_drug_likeness
  ligand_drug_likeness: drug_like | fragment | macrocycle | metalloligand | null
  # PP: interface_type
  interface_type: transient | obligate | symmetric | null
  # antibody: CDR_H3_length
  CDR_H3_length: null                # int aa; >18 → low-confidence flag
  # peptide: length_bin
  peptide_length_bin: null           # 5-15 | 15-20 | >20
  peptide_structure: null            # helix | extended | cyclic | null
  # covalent: warhead_type
  warhead_type: null                 # acrylamide | chloroacetamide | michael_acceptor | null
  reactive_residue: null             # Cys|Ser|Lys + resnum, e.g., "Cys12"
  # NA: strandedness + sequence specificity
  na_strandedness: null              # ss | ds | hairpin | null
  sequence_specificity: null         # PWM | PAM | random | null
tools: [Vina 1.2.5, GNINA 1.0, ...]  # 实际用过的 docker + 版本
flexibility_required: rigid | sidechain_flex | backbone_flex | ensemble
validation_benchmark: PDBbind | CAPRI | PoseBusters | DUD-E | AstexDiverse | none
provenance:
  source_type: literature | benchmark | inhouse
  doi: 10.xxxx/xxxxx                 # CrossRef 必校验
  extracted_at: YYYY-MM-DD
status: validated | proposed | failed | partial
source: praxis_seed | distill_proposed
tags: [PL, kinase, redocking, ...]
---

# {Case 标题}

## Background
- 系统背景 + 为什么这个 case 重要 + 学界 baseline 是什么.
- 如果是 benchmark case (如 PDBbind redocking), 说明数据集大小 + 通用 success rate.

## What I actually did
1. **Receptor prep**: 去 ligand + 去水 (保留 conserved water if specified) + Reduce 加 H + meeko / MGLTools PDBQT
2. **Ligand prep**: RDKit ETKDGv3 3D + tautomer/protonation/stereo enum + Open Babel pH 7.4
3. **Docking modes**: ...
4. **关键 metric**: top-1 / top-5 / top-10 / RMSD / CAPRI / PoseBusters / cluster_size
5. **Validation**: ...

## ★ 排除/不做的事 (★ 必填)
- 哪些方法不适用 (covalent ligand 用 Vina 必拒 / 抗体用通用 PP docker / etc.)?
- 哪些假设破坏 (rigid receptor 在大幅 conformational change case)?
- 哪些 receptor prep 偷工不能做 (跳 ligand 重 prep / 默认删 conserved water)?
- (即使写 "未报道" 也要写, 强制思考)

## ★ 失败模式 (★ 必填)
- RMSD > 4 Å 的具体 system / 物理不合理 pose / 假阳率高的 case
- 已知 conformational change / IDR / glycan / cofactor / metal coordination 等模型外因素
- (未报道也要写明)

## ★ 方法选择决策链 (★ 必填)
- 为什么选 method X 而非 Y? (e.g., Vina vs DiffDock 在 box 信息可知时; IFD vs ensemble 在 backbone vs side-chain 变化; AF3 vs HDOCK 在新化合物 vs 训练集内)
- 为什么参数选 N (exhaustiveness=32 vs 8 / box 22 Å³ / cluster radius 9 Å)?

## ★ Validation metric (★ 必填)
- 用了哪些 metric (top-1 ≤ 2Å rate / CAPRI medium quality / PoseBusters pass rate / cluster_size)?
- 与 ground truth (crystal pose / cryo-EM / 实验 KD) 对比结果?

## Lessons → seeds for rules
1. 可上升为 rule 的总结 (≥3 case 后 promote)
2. 应避免的 anti-pattern
3. Cold-start 时优先尝试什么

## Provenance
- doi: ...
- 关键 supplementary: ...
- raw poses path: ...
