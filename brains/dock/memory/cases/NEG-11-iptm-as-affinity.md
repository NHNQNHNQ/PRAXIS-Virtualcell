---
case_id: NEG-11-iptm-as-affinity
schema_version: 1
docking_type: foundation_model_complex_prediction
target_pdb: anti-pattern reference (AF3 / Boltz output)
target_class: mixed
ligand_type: small_mol_or_protein
system_specifics: {}
tools: [AlphaFold3, Boltz-1, Chai-1]
flexibility_required: backbone_flex
validation_benchmark: PoseBusters
key_paper_doi: 10.1038/s41586-024-07487-w
status: anti_pattern
source: praxis_seed_neg
anti_rule: anti-rule-11-iptm-as-affinity
tags: [NEG, anti-pattern, AF3, Boltz, iPTM, KD, foundation-model, no-PoseBusters]
---

# NEG-11: AF3/Boltz iPTM reported as binding affinity / KD (anti-rule-11)

## Background (anti-pattern)
团队跑 AF3 on receptor + ligand SMILES → 得到 iPTM = 0.85, plddt_ligand = 79。
**报告写："top-1 model iPTM 0.85 → estimated KD ~10 nM"** — 这是 confounding。
iPTM 是 pose quality confidence (0-1)，**不是 binding affinity**。
湿实验 SPR 测到的 KD 是 1.5 µM (150x 偏差)。同时输出 pose 没跑 PoseBusters check，
post-hoc 发现 atom clash + 键长异常。

## ★ 排除/不做的事
- ❌ **iPTM / pLDDT / PAE 转 binding affinity / KD / IC50**: 不能直接转, 需 calibration curves
- ❌ **AF3/Boltz/Chai output 跳过 PoseBusters check** (case dock-009 mandate)
- ❌ **Single seed** for foundation model output: multi-seed (n=5) consensus
- ❌ **Train data leakage 不检查**: PDB ID < 2021 在 AF3 训练集 → fair benchmark 失效
- ❌ **Cofactor / metal / glycan 缺失声明**: AF3 不显式建模 → active site 几何 may collapse
- ❌ **手性 ligand 不验证 chirality**: AF3 偶尔翻转 R/S
- ❌ **Stereochemistry not isomeric SMILES** input: 给 AF3 racemate ambiguous
- ❌ **声称 AF3 = "doc king replacement"**: 仍需 Vina cross-validation (case dock-009)

## ★ 失败模式
- **iPTM ≠ ΔG**: AF3 confidence 是 pose quality, 与 binding free energy 没单调映射 (literature: r ~0.4-0.6, not 1)
- **PoseBusters check fail rate ~50%** for AF3 outputs (case dock-009): top-1 RMSD < 2 Å 但 atom clash
- **OOD ligand**: PROTAC / macrocycle > 8-membered / metal-coordinated → AF3 退化 random pose
- **Cofactor-dependent fold**: cofactor 缺 → active site 塌; e.g., NAD+ -dependent oxidoreductase 漏 NAD
- **Membrane / lipid 缺**: GPCR / 膜蛋白 in water-only AF3 不真实
- **Different seeds give different poses**: single seed unreliable
- **湿实验 KD vs iPTM-claim**: 150x 偏差 (above NEG case)

## ★ 方法选择决策链 (correct alternative)
**Correct path** (case dock-009 + dock-013 + rule_02-candidate):
1. **iPTM is pose quality, not affinity** — explicit declaration in report (`iptm_does_not_mean_KD: true`)
2. **PoseBusters mandatory** for every output pose (overall_pass_rate ≥ 80% high; 50-80% medium; < 50% low)
3. **n_seeds ≥ 5** for foundation model
4. **Multi-method consensus**: AF3 + Boltz (open-source) + RFAA + Vina cross-check
5. **Train data leakage check**: target PDB release year < 2021 → train-set leakage warn
6. **Cofactor / metal / glycan** explicit list in `system_specifics.cofactors_present`
7. **Stereochemistry verification**: input isomeric SMILES; verify output chirality
8. **For affinity prediction**: use FEP+ / AB-FEP / OpenFE — not iPTM

**Why this beats the anti-pattern**:
- iPTM ≠ KD is documented across all foundation model literature
- PoseBusters is the standard physical sanity layer (case dock-009 mandate)
- Cross-method consensus catches single-method failure modes

## ★ Validation metric
- docking_type == foundation_model_complex_prediction + posebusters_check == null → BLOCK
- posebusters_check.overall_pass_rate < 0.5 + confidence_label == high → BLOCK
- report 中 mentions "binding affinity" / "KD" / "IC50" derived from iPTM/pLDDT → BLOCK
- n_seeds < 5 → WARN
- target_pdb release year < 2021 (in benchmark cases) without explicit `train_set_leakage_acknowledged` → WARN

## Lessons → anti-rule
- **anti-rule-11**: foundation_model_complex_prediction 必有 PoseBusters check; iPTM 不能转 KD; n_seeds ≥ 5
- Cross-case evidence: dock-009 (AF3 PoseBusters fail rate 50%), dock-013 (RFAA cross-validation), rule_02 candidate
- Confidence: high
