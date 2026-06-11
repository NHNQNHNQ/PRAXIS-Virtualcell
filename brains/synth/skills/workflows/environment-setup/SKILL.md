# environment-setup

Auto-detect required Python deps and external binaries for PRAXIS-Synth.

## What it does

- Checks 13 Python deps (`cobra`, `dnachisel`, `biopython`, `rdkit`, ...) and reports `__version__`.
- Resolves 5 external binaries via `${env_var}` first then `which`: antiSMASH, iBioSim, RetroPath2.0, BiG-SCAPE, DeepBGC.
- Reports which package managers are available (`mamba`, `conda`, `pixi`, `pip`) and emits install hints with conda/docker alternatives.

## Usage

```python
from skills.workflows.environment_setup.run import run
report = run()
print(report["all_python_present"], report["all_binaries_present"])
```

CLI: `python skills/workflows/environment-setup/run.py | jq .`

## Provenance

`tool_provenance.full=true` always — no LLM, just system probes.
