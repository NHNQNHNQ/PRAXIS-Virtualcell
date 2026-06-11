---
case_id: synth-007-cell-free-system
task: cell_free_protein_synthesis_design
target_protein: GFP / antibody fragment / membrane protein
system: PURE / TX-TL E.coli extract
tools: [iBioSim TX-TL, NEBExpress, Arbor PURExpress]
key_paper_doi: 10.1038/nbt980
status: validated
---

# Cell-free TX-TL：fast prototyping + membrane protein 表达

## Background
Cell-free protein synthesis (CFPS) — 不在 cell 中而在 cell extract / reconstituted system 表达蛋白。**优势**：无 cell 限制（可表达 toxic protein, membrane protein, non-natural aa）、快速（小时级 vs cell day级）、易加 chemical environment。**劣势**：成本、yield 低于 fermentation。

## What I actually did
1. **System 选**：
   - **TX-TL E.coli extract**：成本低、yield ok（mg/mL）、含 endogenous machinery 可能 interfere
   - **PURE (Purified Recombinant Elements)**：纯化组分，可控但成本高、yield 低（μg）
2. **DNA template**：linear or plasmid，T7 promoter（recommend）+ optimized RBS + CDS + T7 terminator
3. **Reaction setup**：standard 25-50 μL，含 NTPs / amino acids / energy mix / cell extract
4. **Conditions tune**：
   - Mg²⁺ 8-15 mM critical
   - Temperature 30°C optimal
   - Reaction time 4-8h
5. **Output**：fluorescent reporter (GFP) → real-time plate reader monitor;ELISA / Western for non-fluorescent
6. **Membrane protein 特殊**：加 detergent / nanodisc / liposome 让 membrane protein fold
7. **Codon optimization for E.coli** (TX-TL extract is E.coli)
8. **Common pitfall**：endogenous mRNA / protease in extract 干扰 → use S30 extract or PURE for cleaner

## ★ 排除/不做的事
- **不 codon optimize**：cell-free 同样需要 host-matched codon
- **Linear template < 50 ng/μL**：太低 yield 极低
- **Mg²⁺ 不 tune**：默认 standard buffer Mg 不对每 system 都 optimal
- **Long reaction (>10h)**：energy depleted, byproduct accumulate, yield 不再升
- **Single replicate**：cell-free batch-to-batch variation 大
- **Forget DNase/RNase contamination**：linear DNA easy degrade

## ★ 失败模式
- **Endogenous mRNA in extract**：S30 extract 含 endogenous mRNA → background protein synthesis
- **ATP regeneration**：cell-free energy 有限，需 pyruvate kinase / phosphoenolpyruvate 持续 regenerate ATP
- **Protein aggregation**：高浓度 reaction 中 protein aggregate；chaperone 加可帮
- **Membrane protein folding**：detergent choice critical；PURE + nanodisc 是 SOTA
- **Toxic intermediate**：toxic to cell 同样 inhibit cell-free reaction (e.g., RNases, proteases)
- **Glycosylation absent**：bacterial extract 不 glycosylate，eukaryotic protein 不 functional

## Lessons → seeds for rules
1. **TX-TL 快 prototyping vs PURE 干净**
2. **Mg²⁺ tuning** 关键 (8-15 mM)
3. **T7 promoter system** standard
4. **Membrane protein** + detergent / nanodisc
5. **Linear template ≥ 100 ng/μL**
6. **Replicates ≥ 3** for batch variation
7. **Real-time plate reader** for kinetics
