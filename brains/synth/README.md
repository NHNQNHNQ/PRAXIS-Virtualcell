# PRAXIS-Synth

Case-based-learning agent for **synthetic biology**: FBA, heterologous pathway design, plasmid assembly (Golden Gate / MoClo / Gibson), codon optimization, genetic-circuit simulation, cell-free systems, biosensor design, strain engineering, and BGC mining.

Part of the PRAXIS suite (peer of [PRAXIS-MD](../MDAgent/Naruto-main/) and [PRAXIS-Enzyme](../EnzymeAgent/)). Inherits the same architectural DNA.

## What's inside

- **10 real-literature seed cases** under `memory/cases/synth-001..010.md` (Monk 2017 iML1515; Paddon 2013 artemisinin; Engler 2009 Golden Gate / MoClo; DNAchisel; Gardner 2000 toggle switch; antiSMASH 7; ...). All DOIs CrossRef-verified.
- **11 case-distilled rules** plus 8 task-overview landscape rules under `memory/rules/`.
- **8-channel retrieval** (`synth_task / host_organism / target_compound / pathway_class / assembly_strategy / scale / method_choice / text`) with RRF fusion (k=60) and `(task, host)` pool routing.
- **6-layer QA pipeline** (`schema → doi_crossref → target_compound_kegg → host_taxon_ncbi → enzyme_uniprot_ec → plasmid_part_registry → mandatory_body`).
- **4-stage orchestrator** (Scoping → Design → Execution → Reporting) with Reviewer gate, max 2 repair loops.
- **5 priority MVP skills**: `fba_simulate`, `golden_gate_assembly`, `codon_optimize`, `heterologous_pathway_design`, `optknock_strain` — each with anti-shortcut enforcement and a sanity test.
- **LIMS pause-resume** for wetlab-data-driven reporting; cross-agent envelopes from PRAXIS-Enzyme / Drug / CRISPR.

## Quick start

```bash
pip install -e .
cp .env.example .env  # fill in NCBI_EMAIL etc.
python scripts/distill/qa.py --all --strict          # validate 10 cases
python -m agents.retrieval --demo                    # demo lycopene query
pytest tests/test_sanity.py -v                       # 4 sanity tests
python scripts/engineer_synth.py \
    --synth-task pathway_design --host "E. coli" \
    --target-compound lycopene --scale fermenter
```

## Design principles

1. **Real literature** — every DOI CrossRef-verified, no hallucination.
2. **Broad coverage** — ≥3 backends per task, 8 retrieval channels.
3. **Genuine analysis** — every number from a real tool with logged stderr/runtime/version. Simulated runs explicitly tagged.
4. **Self-configuring env** — auto-detects binaries, conda/mamba/pixi, Docker fallback.
5. **3-tier memory** — cases (narrative + failures) → rules (≥2 evidence) → skills (no case context).
6. **4-stage orchestrator + Reviewer gate** — schema-validated, max 2 repair loops.
7. **Mandatory ★排除 / ★失败 sections** — every case must explain what NOT to do and what didn't work.
8. **Confidence label always present** — never omit `cold_start | low | medium | high | domain_knowledge`.

## Repository layout

See [CLAUDE.md](CLAUDE.md) for the full operating manual.
