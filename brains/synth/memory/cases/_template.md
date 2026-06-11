---
case_id: synth-NNN-{short-slug}
task: {flux_balance_analysis | heterologous_pathway_design | plasmid_construction | codon_optimization | genetic_circuit_design | dna_constraint_optimization | cell_free_protein_synthesis_design | biosensor_circuit_design | strain_engineering_for_production | biosynthetic_gene_cluster_mining}
host_organism: {E. coli K-12 | S. cerevisiae | C. glutamicum | Streptomyces | cell_free | ...}
# OR target_data, target_protein, input_protein when host is not the focus
target_compound: {KEGG-aware compound name; preferred when applicable}
pathway_class: {terpenoid | polyketide | amino_acid | alkaloid | RiPP | none}        # optional
assembly_strategy: {golden_gate | gibson | yeast_assembly | moclo | klenow}            # optional
scale: {test_tube | shake_flask | fermenter | industrial}                              # optional
tools: [tool1, tool2, ...]
key_paper_doi: 10.xxxx/yyyy
status: {validated | failed | partial}
provenance:
  source_type: literature
  citation: "Author Year, Journal"
  extracted_at: 2026-MM-DD
  unverified_details: []     # list anything not directly from the paper
tags: [tag1, tag2]
---

# {Case title — short noun phrase}

## Background
{1-3 paragraphs setting up the problem and the literature context.}

## What I actually did
1. ...
2. ...
3. ...

## ★ 排除/不做的事
- **不可 KO 的 essential gene / 已知 toxic intermediate**: ...
- **方法不应做的事**: ...
- (≥3 entries; "未报道"/"无" allowed if literature is silent)

## ★ 失败模式
- **失败一**: ...
- **失败二**: ...
- (≥3 entries)

## Lessons → seeds for rules
1. {Generalizable rule with applicability boundary}
2. ...

## Citations
- 主文献: doi:{key_paper_doi}
- 辅助 (DOIs validated by CrossRef): ...
