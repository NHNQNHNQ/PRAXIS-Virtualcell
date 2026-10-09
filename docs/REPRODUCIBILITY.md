# Reproducibility

A reproducible virtual experiment preserves its request, biological context,
ordered features, data and model identities, adapter, environment, execution
configuration, output, evidence state, and provenance.

Record the exact Git commit, software version, dependency versions, and platform
with every experiment. The package version is `1.7.0`; application dependency
locks are documented in [requirements/README.md](../requirements/README.md).

## Local demonstration

Follow the [quickstart](../README.md) or [installation guide](INSTALL.md).
The offline AHR example exercises the experiment runtime and evidence checks.
It does not recreate the quantitative evaluations in the
[preprint](https://arxiv.org/abs/2609.29221v1).

## Available K562 research materials

These protocols, scripts, and results are included in the repository:

| Evaluation | Protocols and implementation | Recorded results |
|---|---|---|
| Train-only additive candidate | [Training protocol](../data/golden/norman_2019/additive_train_only_protocol.json), [validation protocol](../data/golden/norman_2019/additive_train_only_validation_protocol.json), [builder](../scripts/build_golden_additive_train_only_candidate.py), [evaluator](../scripts/evaluate_golden_additive_train_only_validation.py) | [Golden validation](../reports/science/golden-additive-train-only-validation-result.json) |
| Three-seed GEARS | [Training protocol](../data/golden/norman_2019/gears_train_only_protocol.json), [Linux execution contract](../data/golden/norman_2019/gears_train_only_linux_a100_run.json), [validation protocol](../data/golden/norman_2019/gears_train_only_validation_protocol.json), [trainer](../scripts/train_golden_gears_train_only_candidate.py), [evaluator](../scripts/evaluate_golden_gears_train_only_validation.py) | [Golden validation](../reports/science/golden-gears-linux-a100-validation-result.json) |
| GSE220974 external stress test | [Protocol](../data/golden/norman_2019/external_gse220974_protocol.json), [evaluator](../scripts/evaluate_golden_external_gse220974.py) | [Result](../reports/science/golden-gse220974-external-stress-result.json) |
| GSE146194 external stress test | [Protocol](../data/golden/norman_2019/external_gse146194_additive_protocol.json), [evaluator](../scripts/evaluate_golden_additive_external_gse146194.py) | [Result](../reports/science/gse146194-additive-external-stress-result.json) |
| Additive deterministic replay | [Release record](../data/golden/norman_2019/additive_train_only_candidate2_release.json), [replay tool](../scripts/replay_additive_candidate_determinism.py) | [Receipt](../reports/science/candidate2-deterministic-replay-receipt.json) |

Read each protocol and the script's `--help` before execution. Reproduction
requires the exact input matrices, control and split records, feature axes,
fitted model artifacts, and environment. Large datasets, fitted arrays, and
GEARS checkpoints remain external. The application dependency locks do not
reproduce the separate historical Linux/CUDA training environment.

The recorded GEARS Golden gate failed despite complete native prediction
coverage. External evaluations retain their stress-test scope. Successful
inference or deterministic replay does not automatically establish scientific
validation, promotion eligibility, or production status.

## Registered K562 research task

The explicit real-data product path supports the exact Norman AHR+KLF1 CRISPRa
research request. Prepare a matching registration root, Pack, and model cache;
the [registration metadata](../praxis_virtualcell/model_zoo/registrations/golden_additive_research_release.json)
records the release scope and artifact identities.

```bash
praxis-vc direct-v2 run \
  --request examples/golden_ahr_klf1_request_v2.json \
  --pack-id norman-2019-k562-golden --pack-version 1.0.0 \
  --out runs/golden-ahr-klf1 \
  --golden-registration-root /path/to/research-release \
  --golden-pack-root /path/to/pack \
  --golden-model-cache-root /path/to/model-cache
```

Replace the placeholder paths with prepared directories. The release is
research-only, with scientific validation and production promotion false.
Supply the same three root flags to `praxis-vc serve` to expose the registered
task in the local interface. This single request is distinct from the research
evaluations in the table above.

## Microbial packaging scope

The preprint describes E. coli knockout-growth and S. cerevisiae
deletion-fitness experiments. GEM predictors, model assets, contracts, and tests
are included. The complete real-data microbial benchmark pipelines, processed
fitness tables, and corresponding result bundles are not packaged here.
Reproducing those evaluations requires their original experimental inputs,
condition and identifier mappings, preprocessing, solver configuration, and
benchmark evaluator.

## Evidence interpretation

Keep **development validation**, **external stress testing**, **technical
reproducibility**, and **scientific validation** distinct. Predictions carry
their biological context and evidence scope. Missing assets, incompatible
features, infeasible models, or unsupported requests can produce structured
abstention.

[Documentation](INDEX.md) · [Preprint PDF](https://arxiv.org/pdf/2609.29221v1) ·
[BibTeX](../CITATION.bib)

The Golden artifact manifest uses a configurable `<PRAXIS_GOLDEN_ROOT>` in the public
source tree. Its `source_manifest_sha256` retains the original metadata identity;
scientific file hashes, recorded scores, and validation states are unchanged.

## External model configuration

Historical donor benchmarks require an external source checkout and checkpoints. Set
`PRAXIS_DONOR_SOURCE_ROOT` and `PRAXIS_DONOR_CHECKPOINT_ROOT` to your own acquired assets.
GEARS adapters and benchmarks read `GEARS_DATA_ROOT`. The scGPT training benchmark reads
`SCGPT_PRETRAINED_ROOT` and writes under `SCGPT_OUTPUT_ROOT` (default: `runs/scgpt/norman_2019`).
These directories are not distributed with this repository. Missing configuration must fail
explicitly or abstain; it must not silently select a private operator's environment.
