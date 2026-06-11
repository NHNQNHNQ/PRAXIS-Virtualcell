# heterologous-pathway-design

## Skill ID
`heterologous_pathway_design`

## What it does
heterologous_pathway_design — propose enzyme + plasmid plan for a target compound.

## Backends
KEGG REST, RetroPath2.0, Cameo

## Anti-shortcut enforcement
Enforces: rules 02, 11.

## Sanity test
See `tests/test_sanity.py` and `tests/test_phase2_skills.py`.

## Negative tests (counter-examples)
See `tests/test_negative_skills.py`.

## CLI
```
python skills/workflows/heterologous-pathway-design/run.py --help
```
