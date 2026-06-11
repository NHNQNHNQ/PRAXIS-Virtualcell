---
rule_id: 01-chem-id-triple-check
rule_type: case_distilled
applies_to: {target_class: ALL, modality: ALL, project_phase: ALL}
confidence: high
evidence_cases: [drug-002-reinvent-jak2-de-novo, drug-003-pocket2mol-sbdd, drug-004-admet-multi-parameter, drug-006-fbdd-vemurafenib, drug-008-sotorasib-kras-covalent]
schema_version: 2
---

# Rule 01: Three-way chemical ID validation is mandatory

## Statement
Every compound entering any PRAXIS-Drug pipeline (case ingestion, retrieval, design, execution, reporting) must pass a three-way agreement check on its chemical identity:

1. **RDKit-computed InChIKey** from the SMILES (ground truth — local computation)
2. **PubChem REST** lookup by the computed InChIKey (existence check)
3. **ChEMBL REST** lookup by the claimed ChEMBL ID, returning `molecule_structures.standard_inchi_key`

Pass criterion: **≥ 2 of 3 sources agree on InChIKey**. If ChEMBL ID returns 404, automatically search by name; if pref_name doesn't match the claim, flag.

## Why
Empirically validated on the 10 PRAXIS-Drug seed cases (`scratch/validate_drug_cases.py` run): **5 of 9 compounds had ID mismatches** — wrong ChEMBL IDs that resolve to entirely different molecules (e.g., CHEMBL906 was Minoxidil sulfate, not terfenadine; CHEMBL1336 was sorafenib, not vemurafenib), wrong tautomer SMILES (sotorasib pyrimidone), 404-returning legacy IDs (ruxolitinib's CHEMBL3046547).

LLM-generated case content is the highest hallucination risk in scientific knowledge bases. Three-way agreement at every chokepoint catches what a single-source check would silently let through.

## How to apply
- **Case ingestion** (`scripts/distill/qa.py` layer 3): all `representative_compounds` 3-way checked; on mismatch, suggest replacement and block promote.
- **Retrieval** (`agents/retrieval.py`): when a query compound is provided, validate before computing Tanimoto / scaffold match.
- **Execution** (`agents/orchestrator.py` Reviewer gate stage 3): every candidate's InChIKey logged + checked. Block on mismatch.
- **Rate limit**: `time.sleep(0.4)` per API call (≈2.5 req/sec, polite to PubChem/ChEMBL public endpoints).

## Evidence
- drug-002: ChEMBL3046547 → 404; correct ID is CHEMBL1789941
- drug-003: claimed InChIKey FAQDUNYVKQKNLD differs from ChEMBL canonical FDLYAMZZIXQODN (tautomer)
- drug-004 (terfenadine): CHEMBL906 returns Minoxidil sulfate, not terfenadine; correct CHEMBL17157
- drug-006: CHEMBL1336 returns Sorafenib, not vemurafenib; correct CHEMBL1229517
- drug-008: claimed InChIKey BJQHLKABXJIVAM differs from canonical NXQKSXLFSAEQCZ-SFHVURJKSA-N (tautomer of pyrimidone ring)

## Implementation pointer
`skills/workflows/chem_id_validate/run.py` is the production callable — ports `tests/baselines/validate_drug_cases.py`.
