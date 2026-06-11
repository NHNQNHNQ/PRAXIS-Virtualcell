---
case_id: {target}-{firstauthor}-{year}-{shorthand}
schema_version: 2
project_phase: hit_id        # hit_id | hit_to_lead | lead_opt | lead_opt_to_clinic | preclinical
target_uniprot: P00533
target_pdb: 1M17
target_class: kinase         # kinase | gpcr | protease | nuclear_receptor | ion_channel | gtpase | bromodomain | ligase | other
chembl_target_id: CHEMBL203  # for chemical_similarity ranking
indication: NSCLC
modality: small_mol_inhibitor # small_mol_inhibitor | agonist | allosteric | covalent | protac | molecular_glue | peptide | fragment
hit_id_method: virtual_screen # virtual_screen | de_novo_generative | sbdd | fbdd | covalent_design | protac_design | repurposing | sar_optimization
representative_compounds:
  - chembl_id: CHEMBL553
    name: erlotinib
    inchikey: AAKJLRGGTJKAMG-UHFFFAOYSA-N
    smiles: COCCOc1cc2ncnc(Nc3cccc(C#C)c3)c2cc1OCCOC
    activity: IC50=2nM
    role: tool_compound       # tool_compound | hit | lead | clinical_candidate | resistance_probe
tools: [AutoDock Vina 1.2.5, GNINA 1.0, RDKit, OpenBabel, Meeko]
key_paper_doi: 10.1002/jcc.21334
status: validated             # validated | failed | partial | proposed
validated: true
source: praxis_seed           # praxis_seed | literature_distill | inhouse | synthetic_starter
tags: [kinase, EGFR, virtual_screen]
---

# {Concise title}

## Background
What target / indication / modality this case is about. Why it matters. 1-3 paragraphs.

## What I actually did
1. Receptor / ligand / library prep details
2. Specific tools + parameters + thresholds
3. Iteration / decision points
4. Results

## ★ 排除的化合物/scaffold/反应基团
(MANDATORY — non-empty; "无报道" allowed as placeholder if truly nothing reported)
- Specific scaffolds, reactive warheads, IP-occupied series, ADMET red lines that were
  ruled out, with reasons.

## ★ 失败的优化路径
(MANDATORY — non-empty; describe potency-vs-PK collapse, off-target, in-vitro/in-vivo gap,
clinical termination, resistance mechanisms.)

## ★ 方法选择决策链
(MANDATORY — why Vina vs GNINA, why covalent vs reversible, why Pocket2Mol vs REINVENT, etc.)

## ★ Multi-objective tradeoff
(MANDATORY — activity vs selectivity vs ADMET vs SA vs novelty calls.)

## Lessons → seeds for rules
1. Concise rule candidate
2. ...
