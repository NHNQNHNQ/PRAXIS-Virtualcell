# GEARS × Norman train-only Golden validation

Date: 2026-08-17

Outcome: **FAILED**

Scope: frozen Linux-A100 candidates, Golden validation only

## Result

The three-seed GEARS candidate did not meet either preregistered validation threshold.

| Scope | Three-seed macro MSE | Required |
|---|---:|---:|
| Single perturbations (14 conditions) | 0.0025116104270559436 | < 0.0021203121 |
| Combination perturbations (16 conditions) | 0.005687998213201724 | < 0.0025272989 |
| All 30 conditions | 0.004205683913000359 | not a gate |

Native GEARS coverage was 30/30 conditions (1.0); no fallback was used. The exact result is
[`golden-gears-linux-a100-validation-result.json`](golden-gears-linux-a100-validation-result.json),
8,128 bytes, SHA-256
`7a1ed0310dda4c48b2850dfc3486ed0d0f1852e6370a9f5c3da8f3bf90fb846f`.
It was produced by Slurm job 329, which completed with exit code 0 in 13 minutes 14 seconds; stderr was empty.

## Frozen identities

- Validation protocol payload: `8814db3a99702067b7981996c5e61cb97c669d83f2fcbd1269c7de6ed97fdd20`
- Evaluator: `e7b5f796b364039782cf462c3e4d14f9aaa323d7080c5e62343f7483ebaada2b`
- Linux candidate collection: `e45020c925e52a674363f928c51667687c29017819634be5a1224d07f703c3f9`
- Training seeds/epochs: `11/23/37 × 20`
- Validation truth: 30 conditions × 5,045 features, float64; test expression/outcomes were not decoded or used

The evaluator rebuilt the train-only graph in the same frozen Linux package environment used by training,
verified both graph representations against the candidate receipts, loaded checkpoints with
`weights_only=True` and strict state-dict matching, sampled controls with the frozen query-local PCG64 rule,
and averaged the three seed predictions in float64.

## Interpretation and claim ceiling

This result means only that this exact candidate set failed the frozen Golden validation gate. It does not
show that GEARS generally fails, and it is not a benchmark or external scientific validation result. Golden
test access is not authorized by this failure.

Authoritative states remain:

- `benchmark_status = NOT_RUN`
- `benchmark_passed = null`
- `scientifically_validated = false`
- `promotion_eligible = false`
- `production_promoted = false`
- `registry_or_default_route_changed = false`

The candidate inherits upstream full-dataset preprocessing and uses external GO/perturbation-vocabulary
priors. Filesystem read isolation was disclosed as not OS-enforced, although the evaluator received no full
Golden Pack or test path. Prospective test blinding was already false, so any future test would require a
separate authorization and would be descriptive, not confirmatory.
