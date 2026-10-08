#!/usr/bin/env python3
"""Validate local Qwen SFT conversations and assistant loss masks without training.

TRL 0.28 does not add generation tags to the native Qwen3 template. We render
that template unchanged and derive token masks from its ChatML role boundaries.
All source messages reject reserved control tokens before rendering.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "configs/finetuning/qwen3_32b_joint_lora.yaml"
_MESSAGE_FIELDS = {"role", "content", "tool_calls", "tool_call_id"}
_RECORD_FIELDS = {"record_id", "source_record_id", "task_scope", "target_contract", "messages", "tools"}
_CONTROL = ("<|im_start|>", "<|im_end|>", "<|endoftext|>", "<think>", "</think>")
_CHATML = re.compile(r"<\|im_start\|>(system|user|assistant)\n")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def _parse_json(value: str) -> Any:
    def reject_constant(_):
        raise ValueError("nonfinite_JSON")
    return json.loads(value, parse_constant=reject_constant)


def load_config(path: str | Path, *, model_dir=None, data_dir=None, output_dir=None, max_length=None) -> dict:
    import yaml

    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("model_id") != "Qwen/Qwen3-32B":
        raise ValueError("config must select the official Qwen/Qwen3-32B checkpoint")
    for name, override in (("model_dir", model_dir), ("data_dir", data_dir), ("output_dir", output_dir)):
        if override is not None:
            config[name] = str(Path(override).resolve())
        if not isinstance(config.get(name), str) or not config[name].strip():
            raise ValueError(f"config requires {name}")
    if max_length is not None:
        config["max_length"] = max_length
    if type(config.get("max_length")) is not int or not 1 <= config["max_length"] <= 32768:
        raise ValueError("max_length must be a positive integer no greater than 32768; GPU capacity is checked separately")
    if (config.get("bf16") is not True or config.get("attn_implementation") != "sdpa"
            or config.get("packing") is not False or config.get("loss_mask") != "assistant_only_native_offsets"):
        raise ValueError("this run requires BF16, SDPA, no packing and explicit assistant masks")
    return config


def _no_controls(value: Any) -> None:
    # Tool results are untrusted source text. A literal role token must never
    # turn into an assistant target after the native template is rendered.
    encoded = _json(value)
    if any(token in encoded for token in _CONTROL):
        raise ValueError("reserved_chat_or_thinking_token_in_source")


def validate_record(record: Any) -> None:
    if not isinstance(record, dict) or set(record) - _RECORD_FIELDS:
        raise ValueError("invalid_or_private_training_record_fields")
    messages, tools = record.get("messages"), record.get("tools")
    if (not isinstance(messages, list) or len(messages) < 2 or not isinstance(tools, list)
            or not isinstance(messages[0], dict) or not isinstance(messages[-1], dict)
            or messages[0].get("role") != "system" or messages[-1].get("role") != "assistant"):
        raise ValueError("training_requires_system_and_final_assistant_messages")
    _no_controls(record)
    names = set()
    for tool in tools:
        if not isinstance(tool, dict) or not isinstance(tool.get("function"), dict):
            raise ValueError("invalid_tool_definition")
        function = tool["function"]
        name = function.get("name")
        if (tool.get("type") != "function" or not isinstance(name, str) or not name
                or name in names or not isinstance(function.get("parameters"), dict)
                or function["parameters"].get("type") != "object"):
            raise ValueError("invalid_tool_definition")
        names.add(name)
    pending, seen = {}, set()
    saw_user = False
    for message in messages:
        if not isinstance(message, dict) or set(message) - _MESSAGE_FIELDS:
            raise ValueError("invalid_or_private_message_fields")
        role, content = message.get("role"), message.get("content")
        if role not in {"system", "user", "assistant", "tool"} or not isinstance(content, str):
            raise ValueError("chat_roles_require_text_content")
        if role == "user":
            saw_user = True
        if pending and role != "tool":
            raise ValueError("unanswered_tool_call_before_next_message")
        calls = message.get("tool_calls", [])
        if not isinstance(calls, list) or calls and role != "assistant":
            raise ValueError("tool_calls_require_assistant_role")
        for call in calls:
            if not isinstance(call, dict) or set(call) != {"id", "type", "function"}:
                raise ValueError("invalid_tool_call_fields")
            identifier, function = call["id"], call["function"]
            if (not isinstance(identifier, str) or not identifier or identifier in seen
                    or call["type"] != "function" or not isinstance(function, dict)
                    or set(function) != {"name", "arguments"} or function["name"] not in names
                    or not isinstance(function["arguments"], dict)):
                raise ValueError("tool_call_requires_unique_id_known_function_and_object_arguments")
            seen.add(identifier)
            pending[identifier] = function
        if role == "tool":
            identifier = message.get("tool_call_id")
            if not isinstance(identifier, str):
                raise ValueError("tool_reply_requires_text_call_id")
            function = pending.pop(identifier, None)
            if function is None:
                raise ValueError("unbound_tool_reply")
            reply = _parse_json(content)
            if (not isinstance(reply, dict) or reply.get("ok") is not True
                    or reply.get("tool_call_id") != identifier or reply.get("name") != function["name"]
                    or reply.get("arguments") != function["arguments"]):
                raise ValueError("tool_reply_does_not_match_call")
        elif "tool_call_id" in message:
            raise ValueError("tool_call_id_requires_tool_role")
    if pending or not saw_user or messages[-1].get("tool_calls") or not messages[-1]["content"].strip():
        raise ValueError("unfinished_or_empty_training_target")
    if not isinstance(_parse_json(messages[-1]["content"]), dict):
        raise ValueError("final_structured_target_must_be_a_JSON_object")


def read_training_records(path: str | Path) -> list[dict]:
    records, identifiers = [], set()
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = _parse_json(line)
                validate_record(record)
                identifier = record.get("record_id", f"line:{line_number}")
                if not isinstance(identifier, str) or not identifier or identifier in identifiers:
                    raise ValueError("record_id_must_be_nonempty_and_unique")
            except (ValueError, TypeError, KeyError, AttributeError) as exc:
                raise ValueError(f"invalid train.jsonl line {line_number}: {exc}") from exc
            identifiers.add(identifier)
            records.append(record)
    if not records:
        raise ValueError("training_dataset_is_empty")
    return records


def role_spans(rendered: str) -> list[tuple[str, int, int, int]]:
    """Return (serialized role, header start, content start, turn end) spans."""
    matches = list(_CHATML.finditer(rendered))
    if not matches or matches[0].start() != 0:
        raise ValueError("unexpected_native_chatml_format")
    spans = []
    for index, match in enumerate(matches):
        end = rendered.find("<|im_end|>", match.end())
        boundary = matches[index + 1].start() if index + 1 < len(matches) else len(rendered)
        if end < 0 or end + len("<|im_end|>") > boundary or rendered[end + len("<|im_end|>"):boundary].strip():
            raise ValueError("unexpected_native_chatml_turn_boundary")
        spans.append((match.group(1), match.start(), match.end(), end + len("<|im_end|>")))
    return spans


def tokenize_record(record: dict, tokenizer: Any, max_length: int) -> tuple[dict, dict]:
    validate_record(record)
    if not tokenizer.is_fast:
        raise ValueError("assistant_masks_require_a_fast_tokenizer_with_offsets")
    native = tokenizer.chat_template
    rendered = tokenizer.apply_chat_template(record["messages"], tools=record["tools"], tokenize=False,
                                             add_generation_prompt=False, enable_thinking=False)
    encoded = tokenizer(rendered, add_special_tokens=False, return_offsets_mapping=True, truncation=False)
    ids, offsets = encoded["input_ids"], encoded["offset_mapping"]
    # Verify the exact same native-template token sequence. No patched template,
    # synthetic role delimiters, or additional BOS/EOS tokens enter training.
    native_ids = tokenizer.apply_chat_template(record["messages"], tools=record["tools"], tokenize=True,
                                               add_generation_prompt=False, enable_thinking=False)
    if ids != native_ids or tokenizer.chat_template != native:
        raise ValueError("native_template_or_token_sequence_changed")
    if len(ids) > max_length:
        raise ValueError(f"record {record.get('record_id', 'unnamed')} has {len(ids)} tokens; limit {max_length}; no truncation performed")
    spans = role_spans(rendered)
    assistant = [(content, end) for role, _, content, end in spans if role == "assistant"]
    # Empty thinking scaffolding from the official template is not a target.
    empty_think = [(match.start(), match.end()) for match in re.finditer(r"<think>\s*</think>\s*", rendered)]
    mask = [int(end > start and any(start >= a and end <= b for a, b in assistant)
                and not any(start < b and end > a for a, b in empty_think)) for start, end in offsets]
    labels = [identifier if selected else -100 for identifier, selected in zip(ids, mask, strict=True)]
    by_role = Counter()
    for role, start, content, end in spans:
        indices = [index for index, (a, b) in enumerate(offsets) if b > a and a < end and b > start]
        if role != "assistant" and any(labels[index] != -100 for index in indices):
            raise ValueError("nonassistant_token_has_training_loss")
        if role == "assistant":
            content_indices = [index for index in indices if offsets[index][0] >= content]
            if not any(mask[index] for index in content_indices):
                raise ValueError("assistant_turn_has_no_supervised_tokens")
        by_role[role] += len(indices)
    if not any(mask):
        raise ValueError("empty_assistant_loss_mask")
    final_start, final_end = assistant[-1]
    final_tokens = sum(selected and start >= final_start and end <= final_end
                       for (start, end), selected in zip(offsets, mask, strict=True))
    return {"input_ids": ids, "labels": labels, "assistant_masks": mask,
            "record_id": record.get("record_id", "unnamed"),
            "task_scope": record.get("task_scope", "unspecified"),
            "target_contract": record.get("target_contract", "unspecified")}, {
        "tokens": len(ids), "assistant_loss_tokens": sum(mask), "final_assistant_tokens": final_tokens,
        "record_id": record.get("record_id", "unnamed"), "serialized_role_tokens": dict(by_role)}


def mask_self_test(tokenizer: Any) -> dict:
    """Exercise real native serialization of assistant calls and untrusted replies."""
    probe = {"messages": [
        {"role": "system", "content": "MASK_SYSTEM_SENTINEL"},
        {"role": "user", "content": "MASK_USER_SENTINEL"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "mask_call", "type": "function", "function": {
            "name": "overview", "arguments": {}}}]},
        {"role": "tool", "tool_call_id": "mask_call", "content": _json({"tool_call_id": "mask_call",
            "name": "overview", "arguments": {}, "ok": True, "data": {"text": "MASK_TOOL_SENTINEL"}})},
        {"role": "assistant", "content": '{"answer":"MASK_ASSISTANT_SENTINEL"}'},
    ], "tools": [{"type": "function", "function": {"name": "overview", "parameters": {"type": "object"}}}]}
    features, report = tokenize_record(probe, tokenizer, 8192)
    from trl.trainer.sft_trainer import DataCollatorForLanguageModeling
    collator = DataCollatorForLanguageModeling(pad_token_id=tokenizer.pad_token_id, completion_only_loss=False)
    batch = collator([features])
    actual = batch["labels"][0].tolist()[:len(features["labels"])]
    if actual != features["labels"]:
        raise ValueError("TRL_collator_does_not_preserve_assistant_labels")
    # Confirm source-role sentinel tokens, not just a nonzero mask sum.
    rendered = tokenizer.apply_chat_template(probe["messages"], tools=probe["tools"], tokenize=False,
                                             add_generation_prompt=False, enable_thinking=False)
    offsets = tokenizer(rendered, add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
    for sentinel, supervised in (("MASK_SYSTEM_SENTINEL", False), ("MASK_USER_SENTINEL", False),
                                 ("MASK_TOOL_SENTINEL", False), ("MASK_ASSISTANT_SENTINEL", True)):
        start = rendered.index(sentinel)
        positions = [i for i, (a, b) in enumerate(offsets) if a < start + len(sentinel) and b > start]
        if not positions or any((actual[i] != -100) != supervised for i in positions):
            raise ValueError("native_role_sentinel_loss_check_failed")
    # Check offset handling of the actual added ChatML/tool tokens as well as
    # ordinary words. An assistant EOS is a target; every role header is masked.
    for role, start, _, end in role_spans(rendered):
        for text, a, b, supervised in (("<|im_start|>", start, start + len("<|im_start|>"), False),
                                       ("<|im_end|>", end - len("<|im_end|>"), end, role == "assistant")):
            indices = [i for i, offset in enumerate(offsets) if tuple(offset) == (a, b)]
            if (len(indices) != 1 or features["input_ids"][indices[0]] != tokenizer.convert_tokens_to_ids(text)
                    or (actual[indices[0]] != -100) != supervised):
                raise ValueError("native_chatml_special_token_offset_or_loss_check_failed")
        if role == "assistant":
            for match in re.finditer(r"</?tool_call>", rendered[start:end]):
                a, b = start + match.start(), start + match.end()
                indices = [i for i, offset in enumerate(offsets) if tuple(offset) == (a, b)]
                if len(indices) != 1 or actual[indices[0]] == -100:
                    raise ValueError("assistant_tool_call_token_is_not_supervised")
    report.update(status="passed", trl_collator_labels_verified=True,
                  system_user_tool_loss_tokens=0, native_template_unchanged=True,
                  chatml_special_token_offsets_verified=True, assistant_tool_call_tokens_verified=True)
    return report


def package_versions() -> dict[str, str | None]:
    result = {}
    for package in ("torch", "transformers", "peft", "trl", "accelerate", "datasets"):
        try:
            result[package] = version(package)
        except PackageNotFoundError:
            result[package] = None
    return result


def load_local_tokenizer(config: dict):
    from transformers import AutoTokenizer
    model = Path(config["model_dir"])
    if not model.is_dir():
        raise ValueError("local model_dir is missing; no remote model download is attempted")
    tokenizer = AutoTokenizer.from_pretrained(model, local_files_only=True, trust_remote_code=False, use_fast=True)
    if tokenizer.pad_token_id is None:
        raise ValueError("official tokenizer must declare a padding token")
    return tokenizer


def preflight(config: dict, *, schema_only: bool = False) -> tuple[dict, list[dict], Any]:
    path = Path(config["data_dir"]) / "train.jsonl"
    records = read_training_records(path)
    if config.get("require_assessment_supervision") and any(
            row.get("target_contract") != "praxis.assessment-supervision.v1" for row in records):
        raise ValueError("this recipe requires Assessment supervision on every training record")
    report = {"status": "schema_passed" if schema_only else "tokenizer_and_mask_passed", "train_path": str(path),
              "record_count": len(records), "max_length": config["max_length"], "training_runs": 0,
              "large_model_loaded": False, "source_trajectory_count": sum(bool(row["tools"]) for row in records),
              "heldout_inputs_used_for_training": False, "package_versions": package_versions()}
    if schema_only:
        report.update(loss_mask_checked=False, token_lengths_checked=False)
        return report, [], None
    tokenizer = load_local_tokenizer(config)
    report["mask_self_test"] = mask_self_test(tokenizer)
    from train_qwen_lora import assistant_loss_self_test
    report["sparse_assistant_loss_self_test"] = assistant_loss_self_test()
    features, sizes, task_stats = [], [], {}
    for record in records:
        feature, size = tokenize_record(record, tokenizer, config["max_length"])
        features.append(feature)
        sizes.append(size)
        scope = feature["task_scope"]
        stats = task_stats.setdefault(scope, {"records": 0, "tokens": 0, "supervised_tokens": 0,
                                            "max_tokens": 0, "max_final_assistant_tokens": 0,
                                            "target_contracts": {}})
        stats["records"] += 1
        stats["tokens"] += size["tokens"]
        stats["supervised_tokens"] += size["assistant_loss_tokens"]
        stats["max_tokens"] = max(stats["max_tokens"], size["tokens"])
        stats["max_final_assistant_tokens"] = max(stats["max_final_assistant_tokens"], size["final_assistant_tokens"])
        contract = feature["target_contract"]
        stats["target_contracts"][contract] = stats["target_contracts"].get(contract, 0) + 1
    total_supervised = sum(size["assistant_loss_tokens"] for size in sizes)
    for stats in task_stats.values():
        stats["record_fraction"] = stats["records"] / len(records)
        stats["supervised_token_fraction"] = stats["supervised_tokens"] / total_supervised
    # A small training JSONL identity is necessary to reject a resume after data
    # changes. The 65 GB base checkpoint is never rehashed by this entrypoint.
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    report.update(loss_mask_checked=True, token_lengths_checked=True, max_observed_tokens=max(size["tokens"] for size in sizes),
                  total_tokens=sum(size["tokens"] for size in sizes),
                  assistant_loss_tokens=sum(size["assistant_loss_tokens"] for size in sizes),
                  nonassistant_loss_tokens=0, truncation_performed=False,
                  native_template_unchanged=True, mask_method="native_chatml_fast_token_offsets",
                  loss_method="native_Qwen3_logits_to_keep_and_shift_labels",
                  training_data_sha256=digest.hexdigest(), task_supervision=task_stats,
                  max_final_assistant_tokens=max(size["final_assistant_tokens"] for size in sizes),
                  max_token_record_id=max(sizes, key=lambda size: size["tokens"])["record_id"],
                  max_final_assistant_record_id=max(sizes, key=lambda size: size["final_assistant_tokens"])["record_id"])
    return report, features, tokenizer


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--config", default=str(DEFAULT_CONFIG))
    result.add_argument("--model-dir")
    result.add_argument("--data-dir")
    result.add_argument("--output-dir")
    result.add_argument("--max-length", type=int, help="Override the token limit; overflow is rejected, never truncated")
    result.add_argument("--schema-only", action="store_true", help="Validate JSON without importing training libraries")
    result.add_argument("--gpu-forward", action="store_true", help="Explicit 8-GPU BF16/FSDP forward; no backward or optimization")
    result.add_argument("--report", help="Optional local readiness JSON path")
    return result


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    if args.schema_only and args.gpu_forward:
        raise ValueError("schema-only and gpu-forward are mutually exclusive")
    config = load_config(args.config, model_dir=args.model_dir, data_dir=args.data_dir, output_dir=args.output_dir,
                         max_length=args.max_length)
    report, features, tokenizer = preflight(config, schema_only=args.schema_only)
    if args.gpu_forward:
        from train_qwen_lora import run_model
        report["gpu_forward"] = run_model(config, features, tokenizer, forward_only=True)
        report["large_model_loaded"] = True
    import os
    if int(os.environ.get("RANK", "0")) == 0:
        if args.report:
            path = Path(args.report)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_json(report) + "\n", encoding="utf-8")
        print(_json(report))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, ImportError) as error:
        print(f"Preflight failed: {error}", file=sys.stderr)
        raise SystemExit(2)
