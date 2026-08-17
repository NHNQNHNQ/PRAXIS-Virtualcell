# Candidate-2 × GSE146194 external stress test

Date: 2026-08-17

Outcome: **FAILED**

Scope: prospective day-8 external stress test on seven seen single-gene targets; not P16 validation

## Result

The frozen Candidate-2 pipeline did not beat the frozen alpha-1 comparator under the preregistered paired test.

| Metric | Candidate-2 | Comparator | Candidate minus comparator |
| --- | ---: | ---: | ---: |
| Seven-target macro MSE | 0.0011821340688138939 | 0.0009607387409633737 | +0.00022139532785052046 |

The paired condition bootstrap used `numpy.PCG64`, seed 0, 2,000 replicates, and a 95% percentile interval. Its interval was
`[-0.00012229384638288038, 0.0007915839367302017]`. The pass rule required both the mean difference and the interval upper
bound to be strictly below zero; neither condition was met. Candidate-2's observed macro MSE was 23.0443% higher.

Candidate-2 had lower MSE on four of seven targets, but it was worse on three. The larger IRF1 degradation dominated the
macro effect. IRF1 cannot be removed after seeing the result, and the four-of-seven sign count is descriptive only.

| Target | Cells | Candidate MSE | Comparator MSE | Difference |
| --- | ---: | ---: | ---: | ---: |
| IGDCC3 | 72 | 0.0012682376171412474 | 0.0013742110264870573 | -0.00010597340934580994 |
| IRF1 | 193 | 0.0035168354218926543 | 0.0016535765756312450 | +0.0018632588462614093 |
| KLF1 | 260 | 0.0005019124547136996 | 0.0006430697656493758 | -0.00014115731093567623 |
| MAP2K3 | 517 | 0.0005396827964934818 | 0.0006764649498020649 | -0.00013678215330858307 |
| MAP2K6 | 298 | 0.0004318366322452594 | 0.0005597476696309496 | -0.00012791103738569022 |
| MAPK1 | 102 | 0.0011710962452398442 | 0.0011594626625381192 | +0.00001163358270172502 |
| PRTG | 226 | 0.0008453373139710716 | 0.0006586385370048035 | +0.00018669877696626813 |

The exact canonical result is
[`gse146194-additive-external-stress-result.json`](gse146194-additive-external-stress-result.json), 13,335 bytes,
SHA-256 `fbb54bc1429d7621cf90ddadd3782ed72e53b0f47f527763cb24ed99757bb382`.

## Frozen identities and execution boundary

- Metadata-only pending preregistration commit: `d4a9f5d6e4d4089a8723919339f010f5bad334e6`
- Frozen executable commit, made before matrix-entry decoding: `a4ec600bac5e40bca2577468901eb73eb919ea6c`
- Protocol payload: `0c4ae3875e3d1f5f663db70cbeb3c897b6b6b3d36e995b564a7595b95277fcf0`
- Evaluator: `0e8d54cee80a23ed8e4c57fec30220be48f9d78090fbba8ddda706ee8315a6be`
- Candidate record: `743bc29d2659de8eb8ee51511937f8e4f4532d02fe89bc3a82ce4cae087e1518`
- External matrix: 1,255,248,401 bytes, SHA-256 `a95e56292f8341296497c7e1091fd94c21af5880c19b302b8e73de5d8a91acc0`

The metadata-only preregistration fixed the targets, controls, comparison, metric, bootstrap, and pass rule. Before any matrix
coordinate entry or external outcome was decoded, feature-type metadata showed that 168 of 33,862 rows were CRISPR guide
capture rather than RNA. The frozen evaluator therefore corrected library-size normalization to use the 33,694 `Gene
Expression` rows only. This outcome-blind correction is explicit in the protocol. It first computed each cell's library size
over all 33,694 expression features, then selected the exact ordered 5,045 Ensembl rows and applied the full-axis library size
for scaling to 10,000 counts, `log1p`, and float64 reduction.

An independent implementation streamed all 337,886,581 nonzero entries and reproduced every loss within
`2.2e-18`, the macro effects and bootstrap interval to floating-point roundoff, and all 14 frozen prediction hashes exactly.
The seven truth-vector byte hashes were not reproduced bit-for-bit across alternative but mathematically equivalent float64
reduction orders; they remain identities of the frozen evaluator implementation, not cross-implementation canonical hashes.
This limitation does not change any MSE or gate result.

This frozen GSE146194 execution and evaluator did not access or use Golden test expression or outcomes. Historical accidental
visibility of an existing Golden report/scalar was recorded elsewhere and was not used here. Neither candidate nor comparator
was trained, tuned, calibrated, or selected using GSE146194 expression outcomes.

## Interpretation and claim ceiling

This result supports only the statement that Candidate-2 did not outperform the comparator in this exact external stress
test. It does not establish that Candidate-2 is generally worse, and it is not a pure alpha comparison because the two
pipelines were trained over different condition and target universes.

GSE146194 cannot satisfy P16: it is measured at day 8 rather than the exact day-5 scope, requires raw-count normalization and
a 33,694-to-5,045 feature projection, and covers only seven previously seen single-gene targets with no combinations, AHR,
or AHR+KLF1. Authoritative states remain:

- `external_stress_test_passed = false`
- `p16_exact_external_gate_satisfied = false`
- `benchmark_status = NOT_RUN`
- `benchmark_passed = null`
- `scientifically_validated = false`
- `promotion_eligible = false`
- `production_promoted = false`
- `registry_or_default_route_changed = false`

GSE146194 is now outcome-exposed and must not be reused as confirmatory evidence for a later candidate. Formal scientific
validation remains `BLOCKED_EXTERNAL / NOT_RUN` until two previously untouched, exact day-5 K562 CRISPRa outcome sources are
frozen or escrowed, alongside the required P12/P16 multi-artifact identity and honest P21 deterministic-replay contract.
