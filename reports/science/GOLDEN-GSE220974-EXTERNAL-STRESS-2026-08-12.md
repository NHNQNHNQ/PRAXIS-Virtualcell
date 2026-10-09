# Golden additive model: real scientific evaluation (2026-08-12)

## Outcome

The frozen P8 `norman_additive_linear` baseline artifacts and prediction algorithm
passed a locally prespecified, independent-dataset external stress test against the
frozen `norman_global_mean` comparator. They also reproduced the complete internal
Golden Norman benchmark record.

This result does **not** satisfy the exact P16 external gate and does **not** change
the model's authoritative status: `scientifically_validated=false`,
`promotion_eligible=false`, and `production_promoted=false`.

| Evidence plane | Result |
| --- | --- |
| Frozen internal Golden benchmark reproduction check | PASS |
| Locally prespecified GSE220974 external stress gate | PASS |
| Authoritative P21 `benchmark_passed` | FALSE / NOT PRODUCED |
| Exact P16 external-validation gate | NOT SATISFIED |
| Model-wide scientific validation | NOT GRANTED |
| Policy or production promotion | NO CHANGE |

The external evaluator used the frozen P8 artifact predictor, not the current
Direct-v2 release adapter. It does not bind the registered release, its adapter, or
its release-wide runtime identity. The registered adapter is intentionally
restricted to the exact AHR+KLF1 request, whereas this test evaluates five
single-gene targets. The result therefore supplies limited evidence about the
underlying artifacts and algorithm; it does not expand or validate the executable
scope of the current release.

## Independent external test

The test used the public [GEO GSE220974](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE220974)
K562 CRISPRai Perturb-seq dataset associated with
[Pacalin et al.](https://www.nature.com/articles/s41587-024-02213-3). The protocol,
all five downloaded file hashes, evaluator hash, prediction implementation hash,
model/comparator identities, Pack identity, runtime versions, target selection,
preprocessing, metric, and pass rule were frozen before the expression matrix was
parsed.

The primary analysis selected all five GSE220974 single-guide CRISPRa targets that
were present in the candidate's Norman seen-training target set: IRF1, JUN, KLF1,
LYL1, and MAP2K3. It used 1,740 perturbed cells and 1,058 same-capture
non-targeting controls. Raw counts were library-size normalized to 10,000 and
`log1p` transformed. Each condition delta was compared with the corresponding
model prediction across the exact 3,015 case-sensitive gene-symbol intersection.

The locally prespecified primary statistic was the mean, over five targets, of:

`Spearman(candidate, external delta) - Spearman(global mean, external delta)`

The one-sided exact paired sign-flip test enumerated all 32 sign assignments at
`alpha=0.05`.

| Target | Cells | Additive ρ | Global-mean ρ | Difference |
| --- | ---: | ---: | ---: | ---: |
| IRF1 | 475 | 0.09416 | 0.03494 | +0.05922 |
| JUN | 362 | 0.06050 | 0.04237 | +0.01813 |
| KLF1 | 338 | 0.18179 | 0.10741 | +0.07439 |
| LYL1 | 288 | -0.04086 | -0.08589 | +0.04503 |
| MAP2K3 | 277 | 0.09623 | 0.04460 | +0.05163 |
| **Mean** | **1,740** | **0.07836** | **0.02868** | **+0.04968** |

All five paired differences were positive. The enumerated one-sided p-value was
`1/32 = 0.03125`, so the locally prespecified external stress gate passed. Its
scientific interpretation assumes the five target-level effects are sign
exchangeable/symmetric under the null; the targets also share the same control
mean. Enumeration is exact conditional on that assumption, not an unconditional
guarantee of scientific significance. LYL1 remained negatively correlated for
both models; the positive aggregate result must not be read as uniform
target-level biological accuracy.

Two complete executions produced byte-identical result records:

- result size: `5,610` bytes
- result SHA-256: `08331f1381efd4c67e5d1b50b933f96df3323a7457eb5ba64bedab992e8cb4d0`
- protocol SHA-256: `d934234a8ef48eae6d5873d9be209fa4e6bc3d1832c8efbc8afcc39d62990f87`
- evaluator SHA-256: `8582fc8048e8f795d8390555319a6d355ec8dc0712726773e4e0b23b861680cf`

The canonical result is
[`golden-gse220974-external-stress-result.json`](golden-gse220974-external-stress-result.json).

## Internal benchmark reproduction

The existing P8 Golden evaluator was rerun over all 30 validation and 116 test
conditions for all three baselines (438 formal runtime calls). This is broader than
the current exact-scope Direct-v2 adapter and is not evidence that the registered
release executed all 146 conditions. The new artifact was byte-identical to the
checked benchmark record:

- artifact size: `243,236` bytes
- SHA-256: `1cc1110a75183f1b271a8caf34db9998046f93bd42abda278f725879d38eb79c`
- test MSE: additive `0.00325706`, global mean `0.00458205`, no change `0.00620609`
- paired `global_mean - additive` 95% CI: `[0.00084228, 0.00187622]`

The internal test set was also audited by frozen scope. For 37 single-gene
conditions, the paired additive-minus-global-mean 95% CI was
`[-0.00012973, +0.00003952]` and crossed zero. For 79 combination conditions it
was `[-0.00275935, -0.00128720]` and favored additive. This prevents the aggregate
internal win from being generalized into a uniform single- and combination-scope
claim.

For the UI example AHR+KLF1, the additive MSE was `0.00094926`; its 5,045-value
prediction hash matched the API/UI run. This is a held-out condition but not a
target-held-out test because both AHR and KLF1 occurred in training conditions.

## Why the formal science flag remains false

The external result is real and independent, but it is a deliberately narrower
stress test:

- GSE220974 uses a different CRISPRa system and timing from the exact Norman 5-day contract.
- Evaluation projects 5,045 Norman features to a 3,015-symbol intersection, so external adaptation is not zero.
- GSE220974 contains neither AHR nor AHR+KLF1.
- All five eligible external targets were seen in candidate training.
- The external predictions used the shared hash-locked artifact implementation, not the current AHR+KLF1-only Direct-v2 release path.
- `norman_additive_linear` is itself the frozen P16 additive comparator; comparing it with itself under P16's candidate-minus-additive superiority rule yields a zero effect and cannot pass.
- Five targets give the sign-flip test only 32 permutations; this is limited external stress evidence, not a broad model-validation sample.
- The custom result is not a `vc.benchmark-result.v1`, has no P21 run authorization/composite trust chain, and does not produce authoritative `benchmark_passed=true`.

No release pin, evidence record, operator policy, registry state, science badge, or
production state was changed by this run. A formal P16 positive result requires a
distinct candidate model, scope-separated single/combination evaluation, and an
exact independently authorized external dataset under the frozen P16/P21 gates.

## Project artifacts

- Protocol: [`external_gse220974_protocol.json`](../../data/golden/norman_2019/external_gse220974_protocol.json)
- Evaluator: [`evaluate_golden_external_gse220974.py`](../../scripts/evaluate_golden_external_gse220974.py)
- Directed tests: [`test_golden_external_gse220974.py`](../../tests/test_golden_external_gse220974.py)
- Canonical result: [`golden-gse220974-external-stress-result.json`](golden-gse220974-external-stress-result.json)
