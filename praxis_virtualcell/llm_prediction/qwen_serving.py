"""Nonthinking Qwen client and native tool parsing; no model weights are loaded."""
from __future__ import annotations

from copy import deepcopy
import json
import re
from uuid import uuid4

from praxis2.llm.client import LLMClient
from .schemas import MICConditions


class QwenAnalysisClient(LLMClient):
    def _build_payload(self, **kwargs):
        payload = super()._build_payload(**kwargs)
        payload.pop("thinking", None)
        payload.pop("reasoning_effort", None)
        payload["chat_template_kwargs"] = {"enable_thinking": False}
        return payload


def analysis_client(settings):
    if not settings.analysis_model:
        return None
    client_type = QwenAnalysisClient if settings.analysis_provider == "qwen" else LLMClient
    return client_type(settings.analysis_api_key, settings.analysis_base_url or settings.base_url, timeout_s=180)


def native_messages(messages: list[dict]) -> list[dict]:
    """Convert OpenAI argument strings to the objects required by Qwen's template."""
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages_required")
    result = deepcopy(messages)
    for message in result:
        if not isinstance(message, dict) or message.get("role") not in {"system", "user", "assistant", "tool"}:
            raise ValueError("invalid_chat_message")
        message.pop("reasoning_content", None)
        if message.get("content") is None:
            message["content"] = ""
        if not isinstance(message["content"], str):
            raise ValueError("chat_content_must_be_text")
        for call in message.get("tool_calls", []):
            if message["role"] != "assistant" or call.get("type") != "function":
                raise ValueError("invalid_tool_call")
            function = call["function"]
            arguments = function.get("arguments")
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            if not isinstance(arguments, dict):
                raise ValueError("tool_arguments_must_be_object")
            function["arguments"] = arguments
    return result


def smiles_messages(messages: list[dict]) -> list[dict]:
    """Validate candidate.smiles and keep names/IDs out of public candidate features."""
    from .workflow import normalize_molecule, public_candidate

    result = native_messages(messages)
    found = False
    for message in result:
        if message["role"] != "user":
            continue
        try:
            payload = json.loads(message["content"])
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict) or "candidate" not in payload:
            continue
        candidate = payload["candidate"]
        if not isinstance(candidate, dict):
            raise ValueError("candidate_smiles_required")
        molecule = normalize_molecule(candidate.get("smiles"))
        payload["candidate"] = public_candidate(molecule)
        payload["conditions"] = MICConditions.model_validate(payload.get("conditions") or {}).model_dump()
        message["content"] = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        found = True
    if not found:
        raise ValueError("candidate_smiles_required")
    return result


def parse_completion(output: str, tools: list[dict] | None = None) -> tuple[dict, str]:
    """Expose native Qwen calls as OpenAI calls with fresh IDs and string arguments."""
    output = re.sub(r"^\s*<think>\s*</think>\s*", "", output).strip()
    if "<think>" in output or "</think>" in output:
        raise ValueError("unexpected_thinking_output")
    matches = list(re.finditer(r"<tool_call>\s*(.*?)\s*</tool_call>", output, flags=re.DOTALL))
    remainder = re.sub(r"<tool_call>\s*.*?\s*</tool_call>", "", output, flags=re.DOTALL).strip()
    if "<tool_call>" in remainder or "</tool_call>" in remainder:
        raise ValueError("incomplete_tool_call")
    if not matches:
        return {"role": "assistant", "content": output}, "stop"
    allowed = {tool["function"]["name"] for tool in tools or []}
    if len(matches) > 4:
        raise ValueError("tool_calls_per_turn_limit")
    calls = []
    for match in matches:
        call = json.loads(match.group(1))
        if not isinstance(call, dict) or set(call) != {"name", "arguments"} or call["name"] not in allowed:
            raise ValueError("unapproved_tool_call")
        if not isinstance(call["arguments"], dict):
            raise ValueError("tool_arguments_must_be_object")
        calls.append({"id": "call_" + uuid4().hex, "type": "function", "function": {
            "name": call["name"], "arguments": json.dumps(call["arguments"], ensure_ascii=False, allow_nan=False),
        }})
    return {"role": "assistant", "content": remainder or None, "tool_calls": calls}, "tool_calls"
