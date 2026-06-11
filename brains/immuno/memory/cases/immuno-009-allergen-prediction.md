---
case_id: immuno-009-allergen-prediction
schema_version: 1
task: allergenicity_assessment
immuno_task: allergenicity_assessment
antigen_class: plant_protein
hla_class: n/a
hla_alleles: []
peptide_length_bin: n/a
disease_indication: gmo_safety
target_protein: novel transgenic crop protein OR novel therapeutic biologic
target_protein_uniprot: []
tools: [AllergenOnline (FARRP), AllerCatPro, AlgPred, AllerTOP, SDAP, AlgPred-2.0]
key_paper_doi: 10.3390/ijms20030531
status: validated
source: praxis_seed
---

# Allergen 预测：转基因作物 + biologic safety 关键

## Background
新蛋白（GMO crop / 工程酶 / therapeutic biologic）必须做 allergenicity 评估。WHO/FAO 给 standard：(1) sequence similarity to known allergen (≥ 35% identity over 80 aa, or 8 contiguous aa)；(2) IgE binding 实验。In silico 是必步前置。

## What I actually did
1. **Sequence to AllergenOnline**：query against 2400+ allergen DB
2. **WHO/FAO 标准**：≥ 35% identity over 80-aa window OR 6-contiguous-aa identity → allergenic potential
3. **AllerCatPro**：DL-based allergen classifier（不只是 sequence similarity，结构 + epitope 综合）
4. **AlgPred-2.0**：multiple feature 集成，包括 motif、physicochemical、PSSM
5. **Multiple methods consensus**：3+ tools agree → high concern
6. **IgE epitope mapping**：known IgE binding region in homologous allergen → 该 region 在 query 是否保守
7. **PEP / SDAP cross-reactivity 数据库**：linear + conformational epitope
8. **Decision**：3+ tool flagged + WHO 标准 met → wet lab IgE binding ELISA 必须；否则可 proceed

## ★ 排除/不做的事
- **WHO criteria only**：纯 sequence similarity miss novel allergen with no homolog
- **Single tool**：tools 互不一致
- **Linear epitope only**：3D conformational epitope 同样 IgE-binding
- **Skip wet lab IgE binding 当 in silico flag**：监管要求实验数据
- **Glycosylation pattern忽略**：glycan epitope 是 important allergen group
- **Cross-reactivity only intra-species**：plant vs animal cross 也常见（profilin 在多种植物 + animal）

## ★ 失败模式
- **Prediction false positive**：~30% in silico flag 实际无 IgE binding
- **Prediction false negative**：novel allergen with no homolog 不 detect
- **Glycosylation 引入 allergenicity**：N-glycan，xylose/fucose plant-specific glycan high allergen
- **Conformational epitope**：sequence 不 share 但 surface shape share → cross-react
- **Population variability**：同 protein 不同 patient 不同 IgE response
- **Stability under digestion**：胃酸 + pepsin 降解后 epitope 仍存在 = 真 allergen

## Lessons → seeds for rules
1. **Multi-method consensus** ≥ 3 tools
2. **WHO/FAO sequence criteria + DL classifier** combine
3. **Conformational epitope DB**（SDAP / IEDB allergen subset）
4. **Glycan epitope** for plant / parasitic allergen
5. **Wet lab IgE binding** for any in silico flag
6. **Pepsin digestion stability** assessment
7. **Population testing** for clinical allergen
