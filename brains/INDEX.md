# PRAXIS VirtualCell agent brains

The repository contains a VirtualCell brain and shared rules. Cases, rules, skill
contracts, and prompts support retrieval before execution and traceable answers.

| Brain | Purpose |
| --- | --- |
| `virtualcell` | Species-aware perturbation prediction, applicability, and abstention |
| `_common` | Evidence discipline, database routing, output formatting, and shared tool utilities |

`DISCIPLINE_SLUGS = ["virtualcell"]` is defined in `praxis2/brains/migrate.py`.
The seed case is a bootstrap record, not experimental evidence. Numerical
predictions and validated evidence belong to the VirtualCell runtime and its
scientific data packs.

See the [preprint](https://arxiv.org/abs/2609.29221) and
[reproducibility guide](../docs/REPRODUCIBILITY.md) for the scientific scope.
