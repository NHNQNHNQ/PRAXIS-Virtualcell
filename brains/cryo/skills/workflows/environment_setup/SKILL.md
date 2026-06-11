---
name: environment_setup
description: |
  Diagnostic + install-plan skill for the cryoEM tool stack. Detects which
  binaries / Python deps / GPU / indices are present; prints a typed status
  table; fixes safe-to-fix items (rebuild indices, fetch missing PDB/EMDB
  cache); flags Tier 1/2/3 install gaps for the user. Always run this skill
  BEFORE any motion / CTF / picking / refine / model-build / validation skill.
inputs:
  fix: bool (default false)         # if true, auto-rebuild indices and fetch missing data
  network: bool (default true)      # network probe (CrossRef + RCSB + EMDB)
outputs:
  python_deps: dict                 # name -> bool
  gpu: dict                         # {available, devices}
  binaries: dict                    # {name -> {configured_path, available, on_path}}
  indices: dict                     # which indices/*.json present
  cache: dict                       # {pdb_count, emdb_count, network_reachability}
  tier_gaps: dict                   # {tier_1: [...], tier_2: [...], tier_3: [...]}
  fix_actions: list                 # what was rebuilt / fetched (RMCP Phase 1 capture)
env: praxis-cryo-base
status: ready
stage: pre_execution
domain: ops
case_evidence: []
rule_evidence: [_default_bootstrap]
status: not-deployed
deploy_blocker: staging .53 缺 relion/cryosparc/motioncor2 等 cryo 工具;待补 cryo env
---

# environment_setup — diagnostic + install-plan + safe-fix

The first skill the orchestrator calls. The 4-stage pipeline is forbidden from
proceeding to `execution` until this skill returns clean (or with explicit
user override).

## What it checks

### Tier 1 (mandatory; failure blocks execution)
- Python deps: `pydantic, yaml, jsonschema, requests, biopython, numpy, scipy, mrcfile, rank_bm25, watchdog, anthropic, fastapi`
- Indices: `indices/{sample_type, resolution, molweight, symmetry, detector, detergent, method_choice}.{tag,bin}.json` AND `indices/anti/{neg_cases, anti_rules}.json`
- Memory: `memory/index.json` present + `memory/cases/` has ≥ 10 validated cases + ≥ 12 NEG- cases

### Tier 2 (recommended; warn on missing, do not block)
- GPU (`nvidia-smi` returns at least 1 device)
- External binaries: `motioncor2, ctffind4, topaz, cryolo, modelangelo, phenix, chimerax, cryoef, aretomo, warp_m, deepemhancer, relion, cryosparc, coot, isolde`
- Conda envs: `praxis-cryo-base, praxis-cryo-modelangelo, praxis-cryo-phenix, praxis-cryo-aretomo`
- Network: CrossRef + RCSB + EMDB reachable (for QA + on-demand cache fills)

### Tier 3 (PRAXIS suite collaboration tools)
- PRAXIS-MD inbox: `runs/<task>/envelopes/inbound/` writable
- PRAXIS-Protein inbox: writable; `af_model_as_building_prior` envelope schema parseable
- PRAXIS-Dock outbox: `experimental_receptor_for_docking` envelope generator OK

## Safe fix actions (when `--fix true`)

| Failure | Auto-fix |
|---|---|
| `indices/*.json` missing | run `python scripts/retrieval/build_indices.py` + `python scripts/retrieval/anti.py` |
| `data/pdb/<id>.json` missing for a referenced case | call `tools/rcsb_client.py::fetch_pdb_entry` |
| `data/emdb/<id>.json` missing | call `tools/emdb_client.py::fetch_emdb_entry` |
| `runs/<task>/envelopes/{inbound,outbound}/` missing | mkdir |

## Failure-mode table (when fix isn't possible)

| Symptom | Likely cause | Manual remedy |
|---|---|---|
| `mrcfile` import fails | Optional dep not installed | `pip install mrcfile>=1.5` |
| `relion` binary missing | RELION not on PATH | install RELION 5; set `PRAXIS_CRYO_RELION_BIN` env var |
| `nvidia-smi` returns nothing | macOS dev box / no GPU node | acceptable; downstream skills auto-fall back to `--simulate` |
| `phenix.validation_cryoem` not callable | Phenix env not sourced | `source $PRAXIS_CRYO_PHENIX_BIN/../phenix_env.sh` |
| `model_angelo` not found | Separate conda env (incompatible with RELION env) | `mamba create -n praxis-cryo-modelangelo modelangelo` |
| Indices stale (case added but build_indices not re-run) | Run with `--fix true` | auto-rebuilt |
| EMDB `extract_resolution_a` returns None for some EMDB IDs | API schema variation; v0.2 work | tolerable; QA layer warns |

## Coupling to RMCP Phase 1

Every `--fix true` action this skill performs is captured into the
`learning_envelope.json` `fix_action` bucket so the post-task RMCP pipeline can
turn recurring fixes into landscape rules (e.g. "rebuild indices after every
new case").

## Usage

```bash
# Read-only diagnostic
python -m skills.workflows.environment_setup.run

# Auto-fix indices + fetch missing cache
python -m skills.workflows.environment_setup.run --fix

# Skip network probes (offline)
python -m skills.workflows.environment_setup.run --no-network
```

## Sanity invariants

- Tier 1 fail (missing critical dep / no indices / < 10 cases) → status="fail" with `error_code=ENV_TIER1_BLOCK`
- Tier 2 fail (no GPU / no binary) → status="warn" with downstream skills auto-`--simulate`
- Tier 3 fail (cross-PRAXIS inbox unreachable) → status="warn" with envelope dispatch tagged `delivery=local_only`

## 输出契约

```json
{
  "skill_id": "environment_setup",
  "n_particles": 0,
  "resolution_a": 0.0,
  "map_path": "",
  "diagnostics": {
    "brain": "cryo",
    "archetype": "cryo"
  }
}
```
