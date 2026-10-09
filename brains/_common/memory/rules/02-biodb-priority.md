---
rule_id: 02-biodb-priority
schema_version: 1
rule_type: tool_routing
scope: external_data_verification
applies_to:
  all_agents: true
confidence: domain_knowledge
---

# Verify biological sources with database APIs

Prefer `mcp__biodb__*` for verified literature, sequences, structures, and compound
records. Retrieve local evidence with BrainQuery first when appropriate. Never
invent DOI citations, accessions, sequences, or molecular properties.

| Evidence | Tool |
| --- | --- |
| Literature and DOI records | `search_pubmed` |
| Article abstract | `get_pubmed_abstract` |
| Protein sequence, function, species | `get_uniprot` |
| PDB structure metadata | `get_pdb` |
| Compound activity and SMILES | `search_chembl` |
| Compound formula and molecular properties | `get_pubchem` |

These tools return structured records from authoritative APIs. Use WebFetch for
sources not covered by BioDB, and report absent or failed evidence explicitly.
