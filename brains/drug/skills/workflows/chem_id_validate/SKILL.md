---
name: chem_id_validate
description: |
  Three-way chemical identity validation. RDKit InChIKey ⟂ PubChem InChIKey ⟂ ChEMBL InChIKey,
  pass criterion ≥ 2-of-3 agreement. The signature PRAXIS-Drug skill — empirically caught
  5/9 mismatches in the seed library. Implements rule 01.
inputs:
  smiles: str (required)
  chembl_id: str (optional)
  name: str (optional, used for ChEMBL search-by-name fallback)
  claimed_inchikey: str (optional)
outputs:
  status: pass|fail|warn
  error_code: DRUG_QA_CHEMID_01..05
  rdkit: {canonical_smiles, inchikey_computed, mw, logp, qed, lipinski_pass, ...}
  pubchem: {pubchem_status, ...}
  chembl: {chembl_status, pref_name, max_phase, inchikey_chembl, canonical_smiles}
  agreement_count: int (0..3)
  suggested_chembl_id: str | null
  suggested_smiles: str | null
env: praxis-drug-base
status: ready
stage: all
domain: chem_id
---

# chem_id_validate

The signature PRAXIS-Drug skill. Validates a compound's identity by 3-way agreement among:

1. **RDKit-computed InChIKey** from the SMILES — local ground truth
2. **PubChem REST** — InChIKey lookup (existence)
3. **ChEMBL REST** — `molecule_structures.standard_inchi_key` for the claimed ChEMBL ID

Pass when ≥ 2 of 3 sources agree. On failure (especially ChEMBL 404), automatically searches ChEMBL by compound name and returns the suggested correct ChEMBL ID.

Rate-limited at `time.sleep(0.4)` per API call (≈ 2.5 req/sec, polite to PubChem and ChEMBL public endpoints).

## Empirical baseline (catches 5 mismatches in the 9-compound regression set)

| compound | original wrong ID | correct ID |
|---|---|---|
| ruxolitinib | CHEMBL3046547 (404) | CHEMBL1789941 |
| olaparib | wrong tautomer SMILES | ChEMBL canonical SMILES |
| terfenadine | CHEMBL906 (Minoxidil sulfate) | CHEMBL17157 |
| vemurafenib | CHEMBL1336 (Sorafenib) | CHEMBL1229517 |
| sotorasib | wrong tautomer SMILES | ChEMBL canonical SMILES |

## Usage

```bash
# Single compound
python -m skills.workflows.chem_id_validate.run \
    --smiles "Cc1ccc(NC(=O)c2ccc(CN3CCN(C)CC3)cc2)cc1Nc1nccc(-c2cccnc2)n1" \
    --chembl CHEMBL941 --name imatinib

# Regression baseline (the 9 compounds from validate_drug_cases.py)
python -m skills.workflows.chem_id_validate.run --baseline
```

## 输出契约

```json
{
  "skill_id": "chem_id_validate",
  "n_compounds": 0,
  "best_score": 0.0,
  "compound_csv": "",
  "diagnostics": {
    "brain": "drug",
    "archetype": "drug"
  }
}
```
