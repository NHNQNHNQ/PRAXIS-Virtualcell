# Reproducing PRAXIS-VirtualCell experiments

This guide separates a local software demonstration, replay of frozen research
artifacts, and reproduction of the quantitative experiments reported in the
[preprint v1](https://arxiv.org/abs/2609.29221v1).
Restoring source code does not supply every external dataset or trained weight.

## Record the source and environment

Record the Git commit, package version, Python and dependency versions, and
platform for each run. Preserve the original request, ordered features, Pack and
model identities, adapter, environment, evidence, and all generated provenance
alongside the numerical output or abstention.

The package version remains `1.7.0`. Package metadata supports Python 3.11+;
the checked-in application locks are for Python 3.13. A local locked setup is:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: \
  --require-hashes -r requirements/build-py313.lock
.venv/bin/python -m pip install --require-hashes -r requirements/dev-py313.lock
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
```

Run these commands from the repository root. Read
[requirements/README.md](../requirements/README.md) for the supported lock
platforms. These application locks do not reproduce the separate historical
Linux/CUDA GEARS training environment.

For a runtime demonstration, follow the [README](../README.md). The
`examples/ahr_k562.json` offline example exercises routing and governance; it
does not recreate the paper's Golden benchmark results. For software checks,
use [docs/TESTING.md](TESTING.md); fixtures and mocks are software test evidence.

## K562: checked-in protocols, code, and records

The following files are available in this source snapshot. Evaluation scripts
verify frozen contracts and asset identities; substitute inputs are not
equivalent reproductions.

| Experiment | Protocol | Code | Frozen result |
|---|---|---|---|
| Train-only additive candidate and Golden validation | [training](../data/golden/norman_2019/additive_train_only_protocol.json), [validation](../data/golden/norman_2019/additive_train_only_validation_protocol.json) | [candidate builder](../scripts/build_golden_additive_train_only_candidate.py), [evaluator](../scripts/evaluate_golden_additive_train_only_validation.py) | [result JSON](../reports/science/golden-additive-train-only-validation-result.json) |
| Three-seed GEARS and Golden validation | [training](../data/golden/norman_2019/gears_train_only_protocol.json), [Linux run](../data/golden/norman_2019/gears_train_only_linux_a100_run.json), [validation](../data/golden/norman_2019/gears_train_only_validation_protocol.json) | [builder](../scripts/build_golden_gears_train_only_candidate.py), [trainer](../scripts/train_golden_gears_train_only_candidate.py), [Linux runner](../scripts/run_golden_gears_train_only_linux_a100.py), [evaluator](../scripts/evaluate_golden_gears_train_only_validation.py) | [report](../reports/science/GEARS-NORMAN-GOLDEN-VALIDATION-2026-08-17.md), [result JSON](../reports/science/golden-gears-linux-a100-validation-result.json) |
| GSE220974 additive external stress test | [protocol](../data/golden/norman_2019/external_gse220974_protocol.json) | [evaluator](../scripts/evaluate_golden_external_gse220974.py) | [report](../reports/science/GOLDEN-GSE220974-EXTERNAL-STRESS-2026-08-12.md), [result JSON](../reports/science/golden-gse220974-external-stress-result.json) |
| GSE146194 additive external stress test | [protocol](../data/golden/norman_2019/external_gse146194_additive_protocol.json) | [evaluator](../scripts/evaluate_golden_additive_external_gse146194.py) | [report](../reports/science/GSE146194-ADDITIVE-EXTERNAL-STRESS-2026-08-17.md), [result JSON](../reports/science/gse146194-additive-external-stress-result.json) |
| Additive Candidate-2 deterministic replay | [release record](../data/golden/norman_2019/additive_train_only_candidate2_release.json) | [replay tool](../scripts/replay_additive_candidate_determinism.py) | [replay receipt](../reports/science/candidate2-deterministic-replay-receipt.json) |

Read each script's `--help` and protocol before execution. Obtain the exact
external input files, feature axes, control/split records, model artifacts, and
environment required by that protocol. The repository contains manifests and
receipts, not all large H5AD/matrix inputs, fitted arrays, or GEARS checkpoints.
Historical absolute paths in records describe their original execution hosts;
they are not installation instructions.

The checked-in GEARS record reports complete native prediction coverage while
the preregistered Golden gate **failed**. The two external evaluations remain
stress tests. Neither a completed inference nor a successful replay changes
`scientifically_validated`, promotion eligibility, or production status.
The reports disclose prior validation reuse, upstream preprocessing, and
applicable feature/biological identity limitations.

## Run the explicitly registered K562 research task

The existing real-data product path is the exact Norman AHR+KLF1 CRISPRa
research request. It requires an assembled research registration root, matching
Pack assets, and matching model cache. See
[foundation operations](runbooks/FOUNDATION-PLATFORM-OPERATIONS.md) and the
[Golden Pack runbook](runbooks/VIRTUALCELLPACK-GOLDEN-NORMAN.md) for preparation.

After those external roots are available, run from the repository root:

```bash
praxis-vc direct-v2 run \
  --request examples/golden_ahr_klf1_request_v2.json \
  --pack-id norman-2019-k562-golden \
  --pack-version 1.0.0 \
  --out runs/golden-ahr-klf1 \
  --golden-registration-root /ABSOLUTE/PATH/research-release \
  --golden-pack-root /ABSOLUTE/PATH/pack \
  --golden-model-cache-root /ABSOLUTE/PATH/model_cache
```

Replace the three placeholder paths with prepared local directories.
This release is `research_only`; its benchmark, scientific validation, promotion
eligibility, and production promotion flags remain false. It is not installed
into the default model pool. Running it does not reproduce every K562 experiment
listed above. Its UI path is enabled by supplying the same three flags to
`praxis-vc serve`, then reviewing and confirming the server-discovered task.

## Microbial experiments: current packaging boundary

The preprint describes iML1515/Keio E. coli growth experiments and iMM904 yeast
deletion-fitness experiments. This snapshot includes the
[E. coli predictor](../praxis_virtualcell/predictors/mechanistic/ecoli_gem.py),
[yeast predictor](../praxis_virtualcell/predictors/mechanistic/yeast_gem.py),
[GEM assets](../data/gems/), and their contracts and tests.

The complete real-data microbial benchmark pipelines, processed experimental
fitness tables, and complete corresponding result bundles are **not packaged
in this restored snapshot**. Installing the `mechanistic` extra and running the
predictor tests exercises the implementation; it does not reproduce those
paper results. Reproduction requires the original experimental inputs,
condition/identifier mappings, preprocessing, solver configuration, and
benchmark evaluator in addition to the GEMs.

## Interpret evidence within its scope

Keep development validation, external stress testing, technical reproducibility,
and scientific validation separate. Supported scope is attached to the exact
biological context and assets. Infeasible models, unavailable environments,
incompatible features, and out-of-scope requests can produce structured
abstention. No LLM or mock fills in a missing scientific prediction.

This guide exposes the available reproduction paths and missing assets; it
does not certify a new scientific result or release. Historical records remain
available in [reports](../reports/) and [the documentation index](INDEX.md).
