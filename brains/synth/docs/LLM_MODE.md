# `--mode llm` — three-tier synthesis

PRAXIS-Synth's LLM mode produces case-grounded scoping/design/reporting outputs. It uses a 3-tier fallback so the brain works at every tier:

```
                              ┌─────────────────────────┐
  task_id ∈ canonical demos?  │  embedded llm_synthesis │  ← Tier 1 (zero API cost)
                              └─────────────────────────┘
                                          │ no
                                          ▼
                              ┌─────────────────────────┐
  ANTHROPIC_API_KEY set?      │  llm_api → Anthropic    │  ← Tier 2 (real API)
                              └─────────────────────────┘
                                          │ no
                                          ▼
                              ┌─────────────────────────┐
                              │  deterministic stub     │  ← Tier 3 (always works)
                              └─────────────────────────┘
```

## Tier 1 — embedded synthesis (`agents/llm_synthesis.py`)

For the **9 canonical demos** (one per `synth_task` type), Claude has pre-read every relevant case file and embedded the synthesis directly. These outputs cite specific case_ids, rule_ids, and ★排除/失败 entries; they're the gold-standard reference.

Use when:
- you're running a canonical demo (lycopene / lysine / toggle / fba / moclo / codonopt / cellfree / biosensor / bgc)
- you don't want any API cost
- you want fully reproducible output

Example:
```bash
python -m agents.orchestrator \
    --task-file tests/fixtures/example_lycopene.json \
    --mode llm
# → runs/demo-lycopene-ecoli-fermenter/outputs/report.json
```

## Tier 2 — real Anthropic API (`agents/llm_api.py`)

For **arbitrary new tasks** the user invents, this tier:
1. Loads the appropriate stage prompt (`agents/prompts/{scoping|design|reporting|reviewer}.md`) as `system`.
2. Builds an initial `user` message with the task input + 8-channel retrieval bundle + prior stages.
3. Offers two tools to the model: `final_<stage>_plan` (terminal) + `read_memory` (auxiliary, sandboxed to `memory/`).
4. Loops up to `MAX_TURNS=8` while the model uses `read_memory`; terminates when it calls `final_*` and returns the validated `tool_input`.
5. The schema for the terminal tool is the actual JSON schema (`schemas/{stage}.schema.json`) — Anthropic enforces it.

Setup:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export PRAXIS_LLM_MODEL="claude-opus-4-7"  # optional override
python agents/llm_api.py --check
# {"api_available": true, "model": "claude-opus-4-7", ...}
```

Usage:
```bash
# A non-canonical task: the model gets the retrieval bundle + reads cases + emits a real plan
python -m agents.orchestrator \
    --task-file my_custom_task.json \
    --mode llm
```

The `_synthesis_source` field in `intermediates/scoping_plan.json` (and `design_plan.json`) tells you which tier was used:
- `"llm_synthesis (case-grounded, embedded)"` — Tier 1
- `"llm_api (Anthropic API)"` — Tier 2
- `"stub (deterministic from retrieval + rules)"` — Tier 3

### Path traversal protection

The `read_memory` tool only resolves paths under `memory/`. Any `../`-style attempt is rejected (`tests/test_llm_api_mode.py::test_read_memory_rejects_paths_outside_memory`).

### Cost expectations

A single `--mode llm` Tier-2 run spans 3 stages × up to 8 turns × (system prompt + retrieval bundle + tool schemas + prior stages). With Opus 4.7 default pricing this is roughly $0.10-0.40 per task depending on how many `read_memory` rounds the model needs.

## Tier 3 — deterministic stub

Always works (no LLM, no API, no API key). Composes plans by template-filling from retrieval results. Used:
- as a safety net if both Tier 1 and Tier 2 fail
- for CI / reproducibility tests
- when you want zero external dependencies

The `_synthesis_source` will start with `"stub"`.

## Programmatic use

```python
from agents.orchestrator import run_pipeline

# Tier 1 path: matches embedded demo
history = run_pipeline(
    {"task_id": "demo-lycopene-ecoli-fermenter",
     "problem": {"synth_task": "pathway_design", "host_organism": "E. coli",
                  "target_compound": {"name": "lycopene"}, "constraints": []}},
    mode="llm",
)
print(history["scoping_plan"]["_synthesis_source"])
# 'llm_synthesis (case-grounded, embedded)'
```

```python
# Tier 2 path: arbitrary task, requires ANTHROPIC_API_KEY
history = run_pipeline(
    {"task_id": "my-novel-pathway",
     "problem": {"synth_task": "pathway_design", "host_organism": "Pichia pastoris",
                  "target_compound": {"name": "menaquinone-7"}, "constraints": []}},
    mode="llm",
)
print(history["scoping_plan"]["_synthesis_source"])
# 'llm_api (Anthropic API)'  (if API key set)
# 'stub (deterministic from retrieval + rules)'  (if not)
```

## Override / dry-run for testing

```bash
# Force the API path to construct request but not call (used for cost estimation)
export PRAXIS_LLM_DRY_RUN=true

# Inject your own api_call function in tests:
from agents import llm_api
out = llm_api.synthesize(
    "scoping", task_input, retrieval_bundle,
    api_call=my_fake_api_call,  # callable with kwargs(messages, system, tools, model, max_tokens)
)
```

`tests/test_llm_api_mode.py` shows the mock pattern.
