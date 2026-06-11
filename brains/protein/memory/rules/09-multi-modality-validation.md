---
rule_id: 09-multi-modality-validation
schema_version: 1
applies_to:
  design_tasks: ["hallucination_de_novo", "cyclic_peptide_de_novo", "cyclic_peptide_topology_sampling", "symmetric_oligomer_de_novo", "enzyme_de_novo_design"]
  fold_classes: ["ALL"]
evidence_cases:
  - "protein-013-bhardwaj2016-hyperstable-cyclic-peptide"
  - "protein-014-hosseinzadeh2017-macrocycle-topologies"
  - "protein-015-anishchenko2021-hallucination"
  - "protein-017-bhardwaj2022-membrane-traversing-macrocycle"
  - "protein-022-ingraham2023-chroma"
  - "protein-029-siegel2010-diels-alderase"
  - "protein-031-king2014-coassembling-nanomaterial"
  - "protein-033-hsia2016-icosahedron"
confidence: high
last_updated: 2026-05-01
---

## 规则
**De novo / hallucination / cyclic / symmetric / enzyme 设计的 in vitro 验证必须 multi-modality**：每 modality 检测不同 failure mode，单 modality 不足以 claim "fold-correct"。

最低 modality 组合（根据任务）：
| 任务 | 必备 modality | 检测内容 |
|---|---|---|
| Cyclic peptide fold-only | NMR (2D NOE / DOSY) + CD | secondary structure + ensemble RMSD |
| Cyclic peptide cell-permeable | + PAMPA + MDCK uptake | passive permeability + active efflux |
| Hallucination / generative | CD + SEC + SAXS + NMR/X-ray | secondary + oligomer + globular + atomic |
| Symmetric assembly | SEC + SEC-MALS + native MS + cryo-EM/X-ray | oligomer state + cage assembly + atomic |
| De novo enzyme | SEC + activity assay + X-ray (top hits) | fold + catalysis + active site geometry |

**单 modality 推荐 (e.g., 仅 SEC) 视为 anti-pattern**——SEC monomer ≠ correct fold；CD pattern ≠ correct topology。

## 依据
- **protein-013 (Bhardwaj 2016 cyclic peptide)**：12/12 NMR fold-validated；NMR ensemble + temperature serie 是 cyclic peptide standard；X-ray subset 互补
- **protein-014 (Hosseinzadeh 2017 macrocycle topologies)**：~30 design 跨 topology；NMR ensemble RMSD <1.5 Å vs design 是 quantitative metric
- **protein-015 (Anishchenko 2021 hallucination)**：CD (secondary) + SEC (oligomer) + NMR/X-ray (top hits)；27% multi-modality validated
- **protein-017 (Bhardwaj 2022 cell-permeable macrocycle)**：NMR fold + PAMPA + MDCK + LC-MS uptake — 不能省 PAMPA → cell uptake 步骤
- **protein-022 (Ingraham 2023 Chroma)**：CD + SEC + mass-spec + SAXS + NMR/X-ray subset；48% multi-modality fold-correct；single-modality (CD only) 假阳率高
- **protein-029 (Siegel 2010 DA)**：HPLC catalysis + GC-MS enantio + X-ray active site — 三 modality；single-modality 不能 claim catalysis
- **protein-031 (King 2014 cages)**：SEC + 负染 EM + cryo-EM；3-modality 必要
- **protein-033 (Hsia 2016 icosahedron)**：X-ray + cryo-EM + native MS；single-modality (e.g., 仅 SEC) 假阳 30-40%

## 边界 (★ 必填)
- **High-throughput screening 阶段**：可用 single modality (CD-only or SEC-only)，但 final 推荐必须 multi-modality
- **资源极限 task** (no NMR/cryo-EM 可用)：报告必须 explicit "single-modality only, low confidence"
- **Mini-binder fold-only**：可用 ESMFold prediction + SEC (case 002)，因为 binder 任务有自己的 binding assay 作为 functional readout
- **Stabilization 任务 (case 003, 023, 024)**：DSF Tm 是 throughput；CD melting / X-ray 仅 top hits — fold 不变是默认 assumption
- **Mutation effect prediction** (case 004, 027, 028)：DMS-based fitness 数据本身是 multi-replicate；单 fitness assay 已经够
- **Antibody fold (case 005, 025, 026)**：抗体 framework + fold 已知；CDR-specific NMR/X-ray subset 验证

## How to apply
- **Scoping**：design strategy 必须列 `validation_modalities` 字段；< 2 modality → warning；< 3 for hallucination/cyclic/symmetric → block
- **Design**：validation_plan 必须包含每 modality 的 protocol + sample requirement
- **Execution**：generates wet-lab plan 包含 multi-modality validation steps；不允许 "fold confirmed by SEC alone"
- **Reporting**：每 design 的 validation status 表显示每 modality 结果；missing modality 标 "not yet tested"
- **Reviewer**：(a) hallucination/cyclic/symmetric/enzyme 任务报告中 < 3 modality → block; (b) "fold confirmed" 但只 single modality → block
