---
name: pubchem_chembl_lookup
description: |
  Lookup utility — given a compound name, return all valid IDs + canonical structures
  from PubChem and ChEMBL. Useful when a case is being authored and the user has only
  the trivial name. Logic is already inside chem_id_validate; this skill is the
  user-facing CLI wrapper (P2 nice-to-have).
inputs: {name: str}
outputs: {pubchem: [...], chembl: [...], canonical_smiles_chembl: str, canonical_inchikey: str}
env: praxis-drug-base
status: skeleton
stage: all
domain: chem_id
---

# pubchem_chembl_lookup — SKELETON (P2)

Stub in v0.1; the underlying functionality (search by name on ChEMBL + PubChem) is already
in `tools/chembl_client.search_chembl_by_name` and `tools/pubchem_client.search_pubchem_by_name`.
At v0.5 this skill exposes a clean CLI: `python -m skills.workflows.pubchem_chembl_lookup.run --name imatinib`.

## 输出契约

```json
{
  "skill_id": "pubchem_chembl_lookup",
  "n_compounds": 0,
  "best_score": 0.0,
  "compound_csv": "",
  "diagnostics": {
    "brain": "drug",
    "archetype": "drug"
  }
}
```
