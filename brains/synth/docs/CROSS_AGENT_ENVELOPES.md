# Cross-agent envelopes (LIMS pause / resume)

PRAXIS-Synth talks to its sibling agents (PRAXIS-Drug / PRAXIS-CRISPR / PRAXIS-MD / PRAXIS-Enzyme) via JSON envelopes that flow through `runs/{task_id}/wetlab_data/` (inbound) and `runs/{task_id}/outbound/` (outbound).

## Schema

`lims/envelope.schema.json` defines the unified envelope:
- `envelope_kind`: `"inbound"` | `"outbound"` | `"wetlab"`
- `experiment_type`: 10 values
  - **inbound from sibling agents**: `enzyme_handoff` (← Enzyme), `compound_target` (← Drug), `ko_handoff` (← CRISPR)
  - **outbound to sibling agents**: `strain_simulation_request` (→ MD)
  - **wetlab**: `wetlab_titer`, `wetlab_fluorescence`, `wetlab_colony_pcr`, `wetlab_full_plasmid_seq`, `wetlab_flow_cytometry`, `wetlab_growth_rate`
- `samples[]`, `payload`, `qc`, `operator`, `timestamp_utc`

## Inbound flow

```
   PRAXIS-Drug                            PRAXIS-Synth
   ───────────                            ────────────
   designs compound                       runs/{task_id}/wetlab_data/
        │                                          │
        ▼                                          │
   emits envelope ──────► drops JSON ────────────► │ filedrop_watcher --watch
        │                                          │       │
                                                   │       ▼
                                                   │   schema validate
                                                   │   move to _validated/
                                                   │   record in checkpoint.sqlite
                                                   │       │
                                                   │       ▼
                                                   │   --resume-from reporting
                                                   │       │
                                                   │       ▼
                                                   │   merge into wetlab_results
                                                   │       │
                                                   ▼       ▼
                                                  Reporting agent re-runs
```

## Run the demo

```bash
# 1. Run the lysine demo (creates runs/demo-lysine-cglutamicum-industrial/)
python scripts/engineer_synth.py --synth-task strain_engineering \
    --host "Corynebacterium glutamicum" --target-compound lysine --scale industrial

# 2. Drop a CRISPR ko_handoff envelope
cp tests/fixtures/envelopes/inbound-ko-handoff-from-crispr.json \
   runs/demo-lysine-cglutamicum-industrial/wetlab_data/

# 3. Watch validates + moves + records
python lims/filedrop_watcher.py --once --task-id demo-lysine-cglutamicum-industrial

# 4. Inspect checkpoint
python lims/checkpoint.py demo-lysine-cglutamicum-industrial
# {"received_count": 1, ...}

# 5. Resume reporting — Synth re-runs only the report stage with the merged envelope
python -m agents.orchestrator \
    --task-file tests/fixtures/example_lysine.json \
    --mode llm \
    --resume-from reporting
# Report's interpretation.literature_alignment now includes:
#   "Wetlab/cross-agent envelope merged: ko_handoff from crispr ..."
```

## Outbound flow (Synth → MD)

```python
from lims.emit_envelope import emit

env = emit(
    target_agent="md",
    experiment_type="strain_simulation_request",
    linked_run_id="demo-lycopene-ecoli-fermenter",
    linked_design_id="D3_crtI_cassette",
    payload={
        "request_kind": "stability_under_fermentation_conditions",
        "protein": {"name": "CrtI", "ec": "1.3.99.31", "uniprot_native": "Q01585"},
        "conditions_to_simulate": {"temperature_kelvin": 303, "pH": 7.0, ...},
        "questions_for_md": ["Is the FAD-binding site stable at 30°C?"],
    },
)
# Writes runs/demo-lycopene-ecoli-fermenter/outbound/synth-md-handoff-strain-simulation-request.json
```

```bash
# Or via CLI:
python lims/emit_envelope.py \
    --target-agent md \
    --experiment-type strain_simulation_request \
    --linked-run-id demo-lycopene-ecoli-fermenter \
    --payload-json-file my_payload.json
```

## All 5 sample envelopes shipped

`tests/fixtures/envelopes/`:
| File | direction | source/target | demonstrates |
|---|---|---|---|
| `inbound-compound-target-from-drug.json` | inbound | ← Drug | resveratrol product → Synth designs producer strain |
| `inbound-ko-handoff-from-crispr.json` | inbound | ← CRISPR | multiplex sgRNA design → Synth confirms via OptKnock |
| `inbound-wetlab-titer.json` | wetlab | direct | HPLC fed-batch lysine titer 42 g/L → merged into report |
| `inbound-wetlab-flow-cytometry.json` | wetlab | direct | toggle bistable bimodal distribution confirmed |
| `outbound-strain-simulation-to-md.json` | outbound | → MD | CrtI stability question for the lycopene pathway |

7 e2e tests in `tests/test_envelope_e2e.py` exercise the full validate → checkpoint → resume → report cycle.
