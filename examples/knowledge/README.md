# Local curated mechanism retrieval

Build the local seed from the already delivered reference files, from the repository root:

```sh
python -m examples.knowledge.build_catalog --data-root data/organisms --output local/data_readiness_20261007/knowledge_catalog.json
```

The command fetches nothing and requires the original AB5075 reference and exact native-ID mapping files described in the organism manifest. It refuses changed identities. The ignored local catalog contains seven reference gene product annotations. No pathway or experimental compound–protein interaction is currently curated. The reference delivery's redistribution permission is unverified, so the resulting real catalog remains local.

```python
from praxis_virtualcell.knowledge import search_mechanistic_evidence, query_mechanistic_evidence

annotations = search_mechanistic_evidence(
    "NCBITaxon:470", "gyrA", strain="AB5075", native_ids=["ABUW_0960"]
)
exact_record = query_mechanistic_evidence(
    "NCBITaxon:470", ["AB5075:reference:ABUW_0960"], strain="AB5075"
)
```

Each returned record has a stable `source_id` and exact values that can be quoted with JSON Pointers such as `/records/0/claim` or `/records/0/source/source_locator/row`. Taxon, strain and identifiers remain explicit. A wrong taxon or strain returns no records. There is no orthology or symbol-to-native-ID conversion.

Providing `compound_smiles` restricts a search to curated protein-assay records for the exact stereochemical molecular graph, including salts. Gene annotation is excluded from that search. There is no similarity, tautomer or parent-compound matching. An exact match describes the original protein assay, and does not establish intracellular engagement, bacterial killing or the new candidate's causal target. Gene annotation must never be presented as experimental binding.

`empty_catalog.json` is a portable example with no biology claims. A missing or invalid catalog returns `status="unavailable"`; a valid catalog with no matching evidence returns `status="empty"`. Neither returns raw cached assay labels or abstracts. The strict schema rejects extra fields at every level and has no MIC, whole-cell efficacy or organism activity measurement field.
