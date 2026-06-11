# optknock-strain

## Skill ID
`optknock_strain`

## What it does
optknock_strain — propose KO sets that improve target product yield.

## Backends
cobra-bilevel, Cameo OptKnock, OptStoic

## Anti-shortcut enforcement
Enforces: rule 08.

## Sanity test
See `tests/test_sanity.py` and `tests/test_phase2_skills.py`.

## Negative tests (counter-examples)
See `tests/test_negative_skills.py`.

## CLI
```
python skills/workflows/optknock-strain/run.py --help
```
