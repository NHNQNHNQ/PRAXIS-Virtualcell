# dna-constraint-solve

## Skill ID
`dna_constraint_solve`

## What it does
dna_constraint_solve — DNA-level constraint solver (no protein required).

## Backends
DNAchisel, greedy fallback

## Anti-shortcut enforcement
Enforces: rule 04.

## Sanity test
See `tests/test_sanity.py` and `tests/test_phase2_skills.py`.

## Negative tests (counter-examples)
See `tests/test_negative_skills.py`.

## CLI
```
python skills/workflows/dna-constraint-solve/run.py --help
```
