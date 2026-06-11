---
case_id: NEG-12-na-with-pp-docker
schema_version: 1
docking_type: protein_nucleic_acid
target_pdb: anti-pattern reference (TF-DNA / Cas9-gRNA)
target_class: transcription_factor
ligand_type: nucleic_acid
system_specifics:
  na_strandedness: ds
  sequence_specificity: PWM
tools: [HADDOCK 2.4, ClusPro 2.0]
flexibility_required: rigid
validation_benchmark: none
key_paper_doi: 10.1093/nar/gkx1037
status: anti_pattern
source: praxis_seed_neg
anti_rule: anti-rule-12-na-pp-docker
tags: [NEG, anti-pattern, NA, PP-docker, no-PWM-validation, no-PAM]
---

# NEG-12: Protein-NA docking with pure PP docker (no NA mode + no PWM/PAM) (anti-rule-12)

## Background (anti-pattern)
团队对 TF-DNA (Zif268 like) 跑 ClusPro (default PP weights, no NA scoring)。
**Top-1 cluster 把 DNA 朝 zinc finger 远端 surface; 没验证 base-specific 接触是否匹配 PWM**。
湿实验 EMSA 显示 TF 对 randomized DNA 完全无 specificity — pose 错位。
另一案例：CRISPR-Cas9 + sgRNA + dsDNA dock，**没指定 PAM (NGG for SpCas9)**，pose 把 dsDNA 反向放 — Cas9 PI domain 对 Arg1333/Arg1335 没接触 G of NGG。

## ★ 排除/不做的事
- ❌ **PP docker (ClusPro / HADDOCK without NA mode) on protein-NA system** (NA scoring biased to PP)
- ❌ **Sequence specificity 不 validate**: TF-DNA pose 必须 base-specific H-bond match PWM
- ❌ **Cas-gRNA 不指定 PAM**: SpCas9 NGG / SaCas9 NNGRRT / Cas12a TTN — family-specific
- ❌ **DNA 默认 B-form rigid**: TBP 弯 90°, IHF 弯 160°; rigid B-form 失败
- ❌ **RNA helix-only assumption**: hairpin / internal loop / pseudoknot oversimplify
- ❌ **Modified bases (5mC/6mA/m1A)** without specialized FF
- ❌ **ssRNA rigid docking**: 极柔, rigid 假设破坏

## ★ 失败模式
- **PP scoring function biased**: protein-protein interface contacts (electrostatic + hydrophobic complementarity) dominant; NA backbone-base specific contact under-weighted
- **TF-DNA without PWM check**: top-1 pose may have correct interface RMSD but base-specific H-bond network 错; EMSA randomized DNA shows no specificity
- **CRISPR-Cas9 PAM 反向**: Cas9 PI domain (residues 1097-1130) has Arg1333/Arg1335 reading G of NGG. Wrong PAM orientation → no docking score penalty but biology错
- **DNA bending missed**: TBP-TATA at 90° vs B-form rigid: ~15 Å RMSD difference
- **R-loop / triplex / G-quadruplex**: standard NA docker 不支持 → false binding modes
- **CRISPR off-target prediction 弱**: mismatch tolerance 来自 chromatin + cellular context, docking 单 RNP 不够

## ★ 方法选择决策链 (correct alternative)
**Correct path** (case dock-010 + dock-015):
1. **Use NA-specific docker**: HDOCK / NPDock / **AF3 (NA mode) / Boltz / RoseTTAFold-2NA**
2. **AF3-NA / Boltz first-line** (case dock-010 + dock-015): foundation models handle joint protein-NA fold
3. **Sequence specificity validation**:
   - TF-DNA: interface residue ↔ base specific H-bond → match PWM motif
   - Cas-gRNA: PAM (NGG / TTN) explicit specify; PI domain contact verification
4. **DNA bending**: TBP-class TF need ensemble of bent forms (B-form rigid not enough)
5. **Cas9 multi-step**: (a) Cas9-sgRNA pre-bind (4OO8 holo, NOT 4CMP apo), (b) RNP-target dsDNA
6. **Modified bases**: explicit FF (CHARMM-modified-DNA) OR caveat in confidence_label

**Why this beats the anti-pattern**:
- AF3-NA / Boltz / RFAA-2NA top-1 ≤ acceptable rate ~50% vs HDOCK 30% on TF-DNA benchmark
- PWM / PAM specificity check 强制 biological correctness
- Multi-step Cas9 (pre-bind → target) avoids HNH domain rotation loss

## ★ Validation metric
- docking_type == protein_nucleic_acid + chosen_methods 含 cluspro_blind_pp / haddock_pp_with_air (no NA mode) → BLOCK
- 缺 sequence_specificity in system_specifics → BLOCK
- For sequence_specificity == "PWM" 缺 expected_motif → BLOCK
- For sequence_specificity == "PAM" 缺 pam_sequence → BLOCK
- For Cas9-gRNA case: receptor must be holo (sgRNA-bound, e.g., 4OO8) NOT apo (4CMP) → WARN

## Lessons → anti-rule
- **anti-rule-12**: protein_nucleic_acid 用 pure PP docker → BLOCK; PWM/PAM specificity 必 validate; AF3-NA first-line
- Cross-case evidence: dock-010 (Zif268 TF-DNA), dock-015 (CRISPR Cas9 RNP)
- Confidence: high
