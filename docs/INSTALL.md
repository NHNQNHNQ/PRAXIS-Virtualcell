# Installation

PRAXIS-VirtualCell 1.0.0 runs its standalone scientific runtime through a CLI,
local API, and browser interface. Use a source checkout to install it. Package metadata
supports Python 3.11 or newer. Python 3.13 has
[checked-in dependency locks](../requirements/README.md).

## Source setup

```bash
git clone https://github.com/NHNQNHNQ/PRAXIS-Virtualcell.git
cd PRAXIS-Virtualcell
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[api]"
praxis-vc --version
```

Run subsequent commands from the repository root with this environment active.

| Optional extra | Purpose |
|---|---|
| `api` | FastAPI and the local API server |
| `mechanistic` | COBRApy and genome-scale metabolic model execution |
| `omics` | AnnData/MuData data inputs |
| `web` | The optional Streamlit interface |
| `dev` | Python development and test tools |

For scientific data and mechanistic models:

```bash
python -m pip install -e ".[api,mechanistic,omics]"
```

Trained models and large datasets require their own assets and environments.
See [reproducibility](REPRODUCIBILITY.md) before running research evaluations.

## Offline CLI

```bash
praxis-vc run --request examples/ahr_k562.json --mode offline --out runs/ahr
praxis-vc ask --text "What happens when AHR is knocked out in human K562 cells?" \
  --mode offline --yes --out runs/ahr-question
```

Omit `--yes` to inspect the parsed request before execution.
The result directory contains a report and structured records.

## Local interface

Use a Node.js version supported by the frontend's Vite dependency.

```bash
cd praxis_vc_react
npm ci
npm run build
cd ..
praxis-vc serve --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).
The API serves the built React interface from the source checkout.

For frontend development, leave the API running and use `npm run dev` in
`praxis_vc_react`. The optional Streamlit interface requires the `web` extra
and `praxis-vc web` while the API is running.

## Optional LLM assistance

Set `DEEPSEEK_API_KEY` in your environment, then use `--mode llm-assisted` with
`praxis-vc ask` or `praxis-vc run`. See [.env.example](../.env.example) for
configuration. Missing credentials or a failed provider call falls back to the
offline path.

The LLM assists with interpretation, candidate routing, critique, and wording.
The deterministic runtime retains authority over compatibility, numerical
predictor outputs, evidence states, and the final verdict.

## Offline presentation

Open [presentation.html](presentation.html) directly in a browser. Its styles,
diagrams, and interactions are included in the file; no server or network is
required. Use **Present** to step through the platform overview.

[Documentation](INDEX.md) · [Testing](TESTING.md)
