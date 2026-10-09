# PRAXIS-VirtualCell

A programmable platform and agent framework for reproducible virtual cell
experiments. PRAXIS-VirtualCell connects biological data, specialized predictive
models, perturbations, adapters, execution environments, and validation evidence
through explicit contracts.

This repository is the VirtualCell platform described in
[PRAXIS-VirtualCell: A Programmable and Trustworthy Framework for Agentic Virtual Cell Experiments](https://arxiv.org/abs/2609.29221v1)
by Zhenyu Ma and Xukai Jiang. See the [paper PDF](https://arxiv.org/pdf/2609.29221v1),
[citation metadata](CITATION.cff), and [restoration record](docs/RESTORATION.md).

## How it works

A biological question becomes a structured virtual experiment:

**Ask → Review → Route → Run → Results**

The agent interprets the question, proposes routes, and explains results.
The deterministic runtime checks biological compatibility, compiles the
experiment, invokes registered scientific predictors, and records the result or
structured abstention. Numerical predictions come from the selected predictor.

The runtime preserves the request, data and model identities, adapter,
environment, evidence scope, execution trace, and provenance. Missing assets,
incompatible inputs, and unsupported perturbations remain explicit.

## Platform components

| Component | Source | Purpose |
|---|---|---|
| VirtualCellPack | [data_packs](praxis_virtualcell/data_packs/) | Biological identity, conditions, features, controls, omics, and provenance |
| Experiment runtime | [core/runtime.py](praxis_virtualcell/core/runtime.py), [virtual_experiment.py](praxis_virtualcell/virtual_experiment.py) | Structured execution, compatibility checks, and experiment DAGs |
| Model registry and Adapter SDK | [model_zoo](praxis_virtualcell/model_zoo/) | Separate model, artifact, adapter, environment, evidence, and policy identities |
| Scientific predictors | [predictors](praxis_virtualcell/predictors/) | Task-specific mechanistic and data-driven model execution |
| Agent orchestration | [agents](praxis_virtualcell/agents/), [agents_llm](praxis_virtualcell/agents_llm/) | Interpretation, routing, reliability checks, and report generation |
| API and local interface | [praxis_vc_api](praxis_vc_api/), [praxis_vc_react](praxis_vc_react/) | Local experiment workflow and auditable results |
| General agent framework | [praxis2](praxis2/), [brains](brains/) | Shared tools, skills, messaging, memory, and domain brains |

## Install from source

Python 3.11 or newer is supported by package metadata. Use Python 3.13 for the
checked-in dependency locks; see [installation](docs/INSTALL.md) and
[locked environments](requirements/README.md).

```bash
git clone https://github.com/NHNQNHNQ/PRAXIS-Virtualcell.git
cd PRAXIS-Virtualcell
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[api]"
praxis-vc --version
```

Add `mechanistic` for COBRApy/GEM models or `omics` for AnnData/MuData:
`python -m pip install -e ".[api,mechanistic,omics]"`.

## Run an offline experiment

The default mode requires no LLM API key.

```bash
praxis-vc run \
  --request examples/ahr_k562.json \
  --mode offline \
  --out runs/ahr

praxis-vc ask \
  --text "在 human K562 里敲掉 AHR 会怎么样" \
  --mode offline \
  --yes \
  --out runs/ahr-question
```

The output directory contains the report and structured experiment records.
These examples demonstrate the runtime and its evidence checks; they are not a
reproduction of the paper's quantitative benchmarks.

## Open the local platform

Build the React interface, then start the API from the repository root:

```bash
cd praxis_vc_react
npm ci
npm run build
cd ..
praxis-vc serve --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).
The source checkout serves the built React interface at the same origin.
The optional Streamlit interface is available with the `web` extra and
`praxis-vc web` while the API is running.

## Optional LLM assistance

Set `DEEPSEEK_API_KEY` in your environment and use `--mode llm-assisted` with
`praxis-vc ask` or `praxis-vc run`. Missing credentials or provider failures
fall back to the offline path. See [.env.example](.env.example).

The LLM can assist with parsing, routing proposals, critique, and wording.
It cannot alter predictor outputs, invent feature mappings, issue validation
evidence, or override the runtime's compatibility checks and final verdict.

## Biological tasks and evidence scope

| System | Representative task | Repository entry points |
|---|---|---|
| E. coli | Gene knockout → growth | [E. coli GEM predictor](praxis_virtualcell/predictors/mechanistic/ecoli_gem.py), [growth contract](praxis_virtualcell/model_zoo/ecoli_growth_contract.py) |
| S. cerevisiae | Gene deletion → fitness | [yeast GEM predictor](praxis_virtualcell/predictors/mechanistic/yeast_gem.py), [fitness contract](praxis_virtualcell/model_zoo/yeast_deletion_fitness_contract.py) |
| Human K562 | Genetic perturbation → expression response | [Golden Norman benchmark](praxis_virtualcell/benchmarks/golden_norman.py), [research adapter](praxis_virtualcell/model_zoo/golden_additive_research.py) |

A valid Pack, compatible model, successful execution, benchmark performance, and
scientific validation are separate facts. Research-only releases and historical
failed gates retain their recorded status. The default catalog does not imply
that every listed task or model is installed or scientifically validated.

The paper reports cross-species experiments. The restored source includes K562
protocols, evaluation scripts, and result records; large data and trained assets
remain external. The complete microbial benchmark pipelines are not packaged in
this snapshot. Follow [reproducibility](docs/REPRODUCIBILITY.md) for the available
paths and their limits.

## Documentation and contribution

For developers, [P17 compilation](docs/runbooks/VIRTUALCELL-VIRTUAL-EXPERIMENT-DAG.md)
is the planning interface. [U1 direct-v2 execution](docs/ADR-0009-virtualcell-model-zoo-v2.md)
defines the explicit factory execution boundary for the local, unreleased generic
research path; see the [Adapter SDK runbook](docs/runbooks/VIRTUALCELL-MODEL-ADAPTER-SDK.md)
for caller contracts.

- [Install](docs/INSTALL.md) · [Test](docs/TESTING.md) · [Documentation index](docs/INDEX.md)
- [Foundation platform operations](docs/runbooks/FOUNDATION-PLATFORM-OPERATIONS.md)
- [Reproducibility](docs/REPRODUCIBILITY.md) · [Restoration](docs/RESTORATION.md)
- [Contributing](CONTRIBUTING.md) · [Support](SUPPORT.md) · [Provenance](PROVENANCE.md)

Licensed under [MIT](LICENSE). Cite the preprint and the exact software commit
or release used in your work; [CITATION.cff](CITATION.cff) provides the metadata.
