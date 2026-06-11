"""Real Anthropic API integration for arbitrary-task LLM-mode synthesis.

When `task_id` is NOT in `agents.llm_synthesis._LLM_OUTPUTS`, this module is the
next-best path: actually call the Anthropic API with the stage prompt + retrieval
bundle + prior history, and parse the model's output via a `final_*` tool call
into the schema-conformant dict.

Three-tier fallback in `orchestrator.run_pipeline(mode='llm')`:
  1. embedded synthesis from `agents.llm_synthesis` (canonical demos; no API needed)
  2. Anthropic API via this module (any task; needs `ANTHROPIC_API_KEY`)
  3. deterministic stub (no LLM at all; always works)

Environment:
  ANTHROPIC_API_KEY  required to use API mode
  PRAXIS_LLM_MODEL   override the model (default 'claude-opus-4-7')
  PRAXIS_LLM_DRY_RUN if 'true', construct the API request but do not call (used in tests)

Public API:
  is_api_available() -> bool
  synthesize(stage, task_input, retrieval_bundle, prior_history, **kw) -> dict | None
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PROJECT_ROOT / "agents" / "prompts"
SCHEMAS_DIR = PROJECT_ROOT / "schemas"

logger = logging.getLogger("agents.llm_api")

DEFAULT_MODEL = os.environ.get("PRAXIS_LLM_MODEL", "claude-opus-4-7")
MAX_TURNS = 8
MAX_TOKENS = 8000

# Schema name used by the `final_*` tools the model must call to terminate a stage.
_TERMINAL_TOOLS = {
    "scoping": ("final_scoping_plan", "scoping_plan.schema.json"),
    "design": ("final_design_plan", "design_plan.schema.json"),
    "report_interpretation": ("final_report_interpretation", None),
}


def is_api_available() -> bool:
    """True when the Anthropic SDK is importable AND ANTHROPIC_API_KEY is set."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False


def _load_prompt(stage: str) -> str:
    p = PROMPTS_DIR / f"{stage}.md"
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def _load_schema(name: str) -> dict:
    p = SCHEMAS_DIR / name
    return json.loads(p.read_text(encoding="utf-8"))


def _build_tools(stage: str) -> list[dict]:
    """Build Anthropic tool specs for the stage. The model must call one final_* tool to emit."""
    tools = []
    final_name, schema_name = _TERMINAL_TOOLS[stage]
    if schema_name:
        schema = _load_schema(schema_name)
        # Anthropic expects an `input_schema` JSONSchema. We strip the $schema/$id keys.
        clean = {k: v for k, v in schema.items() if k not in ("$schema", "$id", "title")}
        tools.append({
            "name": final_name,
            "description": f"Emit the final {stage} output. Must conform to the schema.",
            "input_schema": clean,
        })
    else:
        tools.append({
            "name": final_name,
            "description": f"Emit the final {stage} object.",
            "input_schema": {
                "type": "object",
                "required": ["why_succeeded", "why_failed", "literature_alignment", "rules_invoked"],
                "properties": {
                    "why_succeeded": {"type": "array", "items": {"type": "string"}},
                    "why_failed": {"type": "array", "items": {"type": "string"}},
                    "literature_alignment": {"type": "array", "items": {"type": "string"}},
                    "rules_invoked": {"type": "array", "items": {"type": "string"}},
                },
            },
        })
    # Auxiliary tool: read a memory file
    tools.append({
        "name": "read_memory",
        "description": "Read a file under memory/ (cases or rules) by relative path.",
        "input_schema": {
            "type": "object",
            "required": ["path"],
            "properties": {"path": {"type": "string"}},
        },
    })
    return tools


def _block_attr(block: Any, key: str) -> Any:
    """Read attribute `key` from an Anthropic content block (SDK object or plain dict)."""
    if isinstance(block, dict):
        return block.get(key)
    return getattr(block, key, None)


def _read_memory_tool(rel_path: str) -> str:
    p = PROJECT_ROOT / rel_path
    if not p.exists() or not p.resolve().is_relative_to((PROJECT_ROOT / "memory").resolve()):
        return f"ERROR: path {rel_path!r} not under memory/"
    try:
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR: {e}"


def _build_initial_user_message(stage: str, task_input: dict, retrieval_bundle: dict,
                                 prior_history: dict) -> str:
    """Construct the initial user message with all the context the model needs."""
    pretty = json.dumps
    parts = [
        f"# Task ({stage})",
        "",
        "## Input task",
        "```json",
        pretty(task_input, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Retrieval bundle (top cases + applicable rules)",
        "```json",
        pretty(retrieval_bundle, ensure_ascii=False, indent=2),
        "```",
    ]
    if prior_history:
        parts += [
            "",
            "## Prior stages (already emitted)",
            "```json",
            pretty({k: v for k, v in prior_history.items() if not k.endswith("_review")},
                   ensure_ascii=False, indent=2),
            "```",
        ]
    final_name, _ = _TERMINAL_TOOLS[stage]
    parts += [
        "",
        f"Emit the {stage} output by calling the `{final_name}` tool. Cite case_ids "
        "and rule_ids from the retrieval bundle. Never invent DOIs. Read specific "
        "case files via `read_memory` if you need their ★排除/失败 sections.",
    ]
    return "\n".join(parts)


def _call_api(messages: list[dict], system: str, tools: list[dict],
              model: str = DEFAULT_MODEL, max_tokens: int = MAX_TOKENS) -> Any:
    import anthropic
    client = anthropic.Anthropic()
    return client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        tools=tools,
        messages=messages,
    )


def synthesize(
    stage: str,
    task_input: dict,
    retrieval_bundle: dict,
    prior_history: dict | None = None,
    *,
    model: str = DEFAULT_MODEL,
    max_turns: int = MAX_TURNS,
    api_call: Callable | None = None,
) -> dict | None:
    """Run the API tool-use loop for `stage`. Returns the parsed output dict
    (matching the corresponding schema) or None if the API path is unavailable.

    `api_call` is injectable for testing — when given, it receives kwargs
    (messages, system, tools, model, max_tokens) and returns an object with
    `.content` (list of blocks). The default uses the Anthropic SDK.
    """
    if stage not in _TERMINAL_TOOLS:
        raise ValueError(f"unknown stage {stage!r}")
    if api_call is None:
        if not is_api_available() and not os.environ.get("PRAXIS_LLM_DRY_RUN"):
            return None
        api_call = _call_api

    system = _load_prompt("reviewer" if stage == "report_interpretation" else stage)
    if not system:
        system = f"You are PRAXIS-Synth's {stage} agent."

    tools = _build_tools(stage)
    messages = [{
        "role": "user",
        "content": _build_initial_user_message(stage, task_input, retrieval_bundle, prior_history or {}),
    }]
    final_name, _ = _TERMINAL_TOOLS[stage]

    for turn in range(max_turns):
        if os.environ.get("PRAXIS_LLM_DRY_RUN") == "true" and api_call is _call_api:
            # Dry-run: would call API but didn't. Caller (tests) must inject api_call.
            return None

        response = api_call(messages=messages, system=system, tools=tools,
                            model=model, max_tokens=MAX_TOKENS)
        content_blocks = getattr(response, "content", []) or []

        # Look for a final_* tool call
        saw_tool_use = False
        for block in content_blocks:
            if _block_attr(block, "type") != "tool_use":
                continue
            saw_tool_use = True
            tool_name = _block_attr(block, "name")
            tool_input = _block_attr(block, "input") or {}
            if tool_name == final_name:
                return tool_input
            if tool_name == "read_memory":
                rel = (tool_input or {}).get("path", "")
                tool_id = _block_attr(block, "id")
                messages.append({"role": "assistant",
                                 "content": [_block_to_dict(b) for b in content_blocks]})
                messages.append({"role": "user", "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": _read_memory_tool(rel),
                }]})
                break
        if not saw_tool_use:
            # Plain-text response with no tool_use — end the loop
            break
    return None


def _block_to_dict(block: Any) -> dict:
    """Normalize SDK block / dict → dict for messages history echo."""
    if isinstance(block, dict):
        return block
    out = {"type": getattr(block, "type", "text")}
    for k in ("text", "name", "input", "id"):
        v = getattr(block, k, None)
        if v is not None:
            out[k] = v
    return out


# ---------- CLI helper ----------

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Probe the Anthropic API integration")
    ap.add_argument("--check", action="store_true", help="just print is_api_available()")
    args = ap.parse_args()
    if args.check:
        print(json.dumps({
            "api_available": is_api_available(),
            "model": DEFAULT_MODEL,
            "anthropic_api_key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "dry_run": os.environ.get("PRAXIS_LLM_DRY_RUN") == "true",
        }, indent=2))
        sys.exit(0)
