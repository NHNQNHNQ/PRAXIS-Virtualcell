---
rule_id: _default_bootstrap
rule_type: cold_start_defaults
applies_to: {target_class: ALL, modality: ALL}
confidence: domain_knowledge
evidence_cases: []
schema_version: 2
---

# Cold-start defaults for PRAXIS-Drug

When the case library has fewer than 5 cases for the queried (target_class, modality) pair, fall back to these domain priors. Always loaded so an agent never operates without grounding.

## Pipeline order (default for `hit_id` phase, small-mol inhibitor)
1. `chem_id_validate` on every input compound (3-way RDKit/PubChem/ChEMBL agreement)
2. Receptor prep: holo structure preferred over apo; remove non-conserved waters; protonate at pH 7.4
3. Library prep: enumerate stereocenters, protonation states (Dimorphite-DL), tautomers (RDKit), generate 3D ETKDGv3 conformers
4. Dual docking: AutoDock Vina (geometry) + GNINA (CNN re-score). Consensus-rank top 1%
5. Spike-in known actives → require EF1% ≥ 5 before trusting hit list
6. ADMET multi-method: ADMET-AI + SwissADME REST + pkCSM REST. ≥2-of-3 vote on hard endpoints
7. Hard stops auto-reject: hERG IC50 < 1 μM, Ames+, strong CYP3A4 inhib, high DILI risk
8. Synthesis filter: SAscore ≤ 4.5 AND AiZynthFinder ≤ 6 steps with commercial start materials

## Modality-aware overrides
- `covalent`: replace step 4 with covalent docking (Vina+restraints or CovDock); kinact/Ki not IC50
- `protac`: ternary complex sampling required (warhead + linker + E3 ligand); track cooperativity α
- `allosteric`: search apo + holo + cryptic; FPocket / CryptoSite required
- `fragment`: rule of 3 (MW<300, HBA≤3, HBD≤3, logP≤3); physical validation (NMR/SPR/X-ray) required before claiming hit

## 5-D scoring weights (default; user may override)
- predicted_activity: 0.30
- selectivity:        0.20
- admet:              0.25
- sa_score:           0.15
- novelty:            0.10

## Confidence default
`cold_start` — explicit until ≥5 cases / channels / pool hits pass criteria.
