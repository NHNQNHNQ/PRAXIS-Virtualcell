---
name: perturbation_predict
description: Prepare a structured perturbation request for the VirtualCell runtime
host_env: praxis-virtualcell
status: deployed
---

# Perturbation request adapter

Provide baseline context and a perturbation specification. The bundled `run.py`
is a bootstrap input adapter: it returns an input receipt and a simulation flag.
It does not run a numerical predictor or provide validated biological results.
Use the VirtualCell CLI or API for predictions and their reliability report.

## SOP

1. Identify species, cell type, baseline data, genes or drugs, dose, and time.
2. Retrieve relevant model applicability and evidence rules.
3. Submit the request through the supported VirtualCell runtime entrypoint.
4. Report prediction, uncertainty, abstention, and provenance from the runtime.

## Inputs

- `perturbation`: genes, knockout combinations, drugs, dose, and timing.
- `cell_type` and `species`: biological context.
- `simulate`: whether the input receipt represents a dry run.
