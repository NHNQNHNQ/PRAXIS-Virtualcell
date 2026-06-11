# bgc-mining

## Skill ID
`bgc_mining`

## What it does
bgc_mining — biosynthetic gene cluster prediction + MIBiG cross-check.

## Backends
antiSMASH, DeepBGC, motif scanner, MIBiG

## Anti-shortcut enforcement
Enforces: rule 09.

## Sanity test
See `tests/test_sanity.py` and `tests/test_phase2_skills.py`.

## Negative tests (counter-examples)
See `tests/test_negative_skills.py`.

## CLI
```
python skills/workflows/bgc-mining/run.py --help
```
