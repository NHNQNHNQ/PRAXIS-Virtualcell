---
rule_id: 08-symmetry-enforced-throughout
schema_version: 1
applies_to:
  design_tasks: ["symmetric_oligomer_de_novo"]
  fold_classes: ["helical_bundle_C2", "helical_bundle_C3", "helical_bundle_C4", "helical_bundle_C5", "helical_bundle_T_O_I_symmetry", "icosahedral_60_subunit", "ALL_symmetric"]
evidence_cases:
  - "protein-009-symmetric-rfdiffusion-oligomer"
  - "protein-019-wicky2022-symmetric-hallucination"
  - "protein-031-king2014-coassembling-nanomaterial"
  - "protein-033-hsia2016-icosahedron"
confidence: high
last_updated: 2026-05-01
---

## 规则
**Symmetric design 必须从头到尾 enforce symmetry**——不仅 backbone 设计步骤，序列设计 (tied-position MPNN) + 结构验证 (cryo-EM + native MS) + 表达后 oligomeric state 检查 (SEC + SEC-MALS) 都不可省。Post-hoc filter (设计完后再筛对称的) 不被 accept。

具体 hard constraints:
1. **Backbone generation**: RFdiffusion symmetric mode / RPXdock / hallucination MCMC 必须显式 symmetry constraint
2. **Sequence design**: ProteinMPNN with `--tied_positions_jsonl`, all symmetry-related residues identical
3. **Validation chain**: SEC → SEC-MALS → cryo-EM 或 X-ray + native MS — **all four** required for high-confidence claim
4. **Lower symmetry first**: C2/C3/C4 优先 ；D2 / C5 / icosahedral 转化率显著下降，需更大 design pool
5. **Single-component vs two-component**: T/O/I 高对称推荐 single-component (Hsia 2016) 或 two-component (King 2014)；纯 single C5+ 几何困难

## 依据
- **protein-009 (Watson 2023 RFdiff symmetric C3)**：120 aa monomer × 3 copies；MPNN tied positions 必须；缺 tied → 序列破坏对称；MD 100ns 验证 symmetry preservation 不动态破坏
- **protein-019 (Wicky 2022 hallucination C2-D2)**：MCMC 中所有 symmetry-related position 同步 mutate；post-hoc 不行；43% 设计 fold + 对称都对
- **protein-031 (King 2014 two-component cages)**：T/O/I 几何 RPXdock systematic enumeration；50% 设计形成 cage；cryo-EM 验证不可省（SEC 仅 necessary 不 sufficient）
- **protein-033 (Hsia 2016 single-component icosahedron)**：60-subunit cage；trimer-based scaffold + I3 symmetry；X-ray + cryo-EM + native MS 三 modality；43% atomic-detail validated；hyperstability (Tm > 100°C) 是 nanomaterial 标准

## 边界 (★ 必填)
- **C2 dimer simple cases** (no inter-monomer interface 设计需要)：可松动 tied-MPNN 要求；但仍需 SEC + native MS
- **Asymmetric heterodimers**：本规则不适用 (复合物 prediction 走 rule 02 paired_msa)
- **Hyperstability requirement**：vaccine / nanomaterial 应用 Tm > 80°C 是 baseline；研究用 cage 可放宽
- **Cryo-EM resolution limit**：early-stage designs 10-30 Å 可接受 (识别 cage shape)；high-confidence 推荐需 ≤ 5 Å
- **Asymmetry breaking in MD**：static design 在 dynamics 下 break symmetry 是 known failure (case 009)；MD 100ns 验证 stability

## How to apply
- **Scoping**：symmetric design 任务必须显式选 symmetry type (C2/C3/.../I)；自动 prefer lower symmetry first
- **Design**：design_plan 必须含 `tied_positions_jsonl` for ProteinMPNN；后端 RFdiffusion 必须 `inference.symmetry=Cn`
- **Execution**：symmetric_design_pipeline skill 强制 enforce + warning if lower-symmetry attempted first
- **Reporting**：报告必须含 oligomeric state validation table (SEC + SEC-MALS + native MS + cryo-EM resolution)
- **Reviewer**：检测 (a) MPNN missing tied_positions → block; (b) 没 cryo-EM data 但 claim "high confidence" → block; (c) skipped MD stability check on symmetric assembly → warning
