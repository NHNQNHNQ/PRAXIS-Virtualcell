"""Explicit local Qwen/PEFT serving; imports do not load model weights."""
from __future__ import annotations

import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import sys
from uuid import uuid4

from praxis_virtualcell.llm_prediction.qwen_serving import parse_completion, smiles_messages


def validate_memory_guard(**kwargs):
    """Reuse the trainer's stdlib-only guard, before importing any model runtime."""
    original_path = sys.path[:]
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from train_qwen_lora import validate_memory_guard as validate
        return validate(**kwargs)
    finally:
        sys.path[:] = original_path


def _model_identity(base, adapter, model_name, max_context):
    # Base shards were verified during download; fingerprint their immutable
    # local metadata instead of rereading all 32B weights on every service start.
    def fingerprint(path, *, contents):
        if contents:
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            return {"name": path.name, "sha256": digest.hexdigest()}
        stat = path.stat()
        return {"name": path.name, "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}
    metadata = ("config.json", "generation_config.json", "model.safetensors.index.json",
                "tokenizer_config.json", "tokenizer.json", "vocab.json", "merges.txt")
    assets = {"base_dir": str(base.resolve()), "adapter_dir": str(adapter.resolve()) if adapter else None,
              "model": model_name, "max_context": max_context,
              "base": [fingerprint(base / name, contents=True) for name in metadata if (base / name).is_file()],
              "base_weights": [fingerprint(path, contents=False) for path in sorted(base.glob("*.safetensors"))]}
    if adapter:
        assets["adapter"] = [fingerprint(path, contents=True) for path in sorted(adapter.iterdir())
                             if path.is_file() and (path.name in {"adapter_config.json", "tokenizer_config.json",
                                                                  "tokenizer.json", "adapter_model.bin"}
                                                    or path.name.endswith(".safetensors"))]
    return hashlib.sha256(json.dumps(assets, sort_keys=True).encode()).hexdigest()


class AdapterGenerator:
    def __init__(self, base_dir: str, adapter_dir: str | None = None, *, model_name: str, max_context: int = 32768):
        self.memory_guard = validate_memory_guard()
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        base, adapter = Path(base_dir), Path(adapter_dir) if adapter_dir is not None else None
        if not (base / "config.json").is_file() or adapter is not None and not (adapter / "adapter_config.json").is_file():
            raise ValueError("local_base_and_adapter_required")
        if isinstance(max_context, bool) or not isinstance(max_context, int) or max_context < 1:
            raise ValueError("invalid_max_context")
        tokenizer_dir = adapter if adapter is not None and (adapter / "tokenizer_config.json").is_file() else base
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_dir, local_files_only=True)
        placement = {}
        if getattr(torch, "cuda", None) is not None and torch.cuda.is_available():
            # Leave room for KV cache and long-context prefill; auto placement
            # otherwise fills the first GPUs almost entirely with base weights.
            placement["max_memory"] = {index: int(torch.cuda.mem_get_info(index)[0] * 0.75)
                                        for index in range(torch.cuda.device_count())}
        model = AutoModelForCausalLM.from_pretrained(base, local_files_only=True, torch_dtype=torch.bfloat16,
                                                    device_map="balanced", attn_implementation="sdpa", **placement)
        self.adapter_loaded = adapter is not None
        if adapter is not None:
            from peft import PeftModel
            model = PeftModel.from_pretrained(model, adapter, local_files_only=True, is_trainable=False)
        self.model = model.eval()
        self.model.config.use_cache = True
        native_context = getattr(self.model.config, "max_position_embeddings", max_context)
        self.model_name, self.max_context = model_name, min(max_context, native_context)
        self.model_identity = _model_identity(base, adapter, model_name, self.max_context)

    def complete(self, payload: dict) -> dict:
        import torch

        if payload.get("model") != self.model_name:
            raise ValueError("unknown_model")
        if payload.get("stream"):
            raise ValueError("streaming_not_supported")
        options = payload.get("chat_template_kwargs", {})
        if options.get("enable_thinking", False) is not False or payload.get("thinking", {}).get("type") == "enabled":
            raise ValueError("this_adapter_requires_nonthinking_generation")
        requested_budget = payload.get("max_tokens", 12288)
        if isinstance(requested_budget, bool) or not isinstance(requested_budget, int) or requested_budget < 1:
            raise ValueError("invalid_max_tokens")
        text = self.tokenizer.apply_chat_template(smiles_messages(payload.get("messages")), tools=payload.get("tools"),
                                                  tokenize=False, add_generation_prompt=True, enable_thinking=False)
        inputs = self.tokenizer(text, add_special_tokens=False, return_tensors="pt", truncation=False)
        prompt_tokens = inputs["input_ids"].shape[-1]
        remaining = self.max_context - prompt_tokens
        if remaining < 1:
            raise ValueError("context_budget_exceeded_no_truncation")
        budget = min(requested_budget, remaining)
        inputs = {key: value.to(self.model.get_input_embeddings().weight.device) for key, value in inputs.items()}
        with torch.inference_mode():
            generated = self.model.generate(**inputs, max_new_tokens=budget, do_sample=False,
                                            pad_token_id=self.tokenizer.pad_token_id)
        tokens = generated[0, prompt_tokens:]
        token_ids = tokens.tolist()
        eos = self.model.generation_config.eos_token_id or self.tokenizer.eos_token_id
        eos_ids = set(eos if isinstance(eos, list) else [eos])
        reached_end = bool(token_ids and token_ids[-1] in eos_ids)
        if reached_end:
            token_ids.pop()
        # Keep native tool delimiters even if a tokenizer classifies them as
        # special. Only the actual terminal EOS ID is removed above.
        output = self.tokenizer.decode(token_ids, skip_special_tokens=False)
        if len(tokens) >= budget and not reached_end:
            message, finish = {"role": "assistant", "content": output}, "length"
        else:
            message, finish = parse_completion(output, payload.get("tools"))
        return {"id": "chatcmpl_" + uuid4().hex, "object": "chat.completion", "model": self.model_name,
                "choices": [{"index": 0, "message": message, "finish_reason": finish}],
                "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": len(tokens),
                          "total_tokens": prompt_tokens + len(tokens)},
                "generation_budget": {"requested_max_tokens": requested_budget, "max_new_tokens": budget,
                                      "prompt_tokens": prompt_tokens, "max_context": self.max_context,
                                      "remaining_context_tokens": remaining, "reduced": budget < requested_budget,
                                      "input_truncated": False}}


def create_handler(generator):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, body):
            raw = json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path != "/health":
                self.reply(404, {"error": "not_found"})
                return
            self.reply(200, {"status": "ok", "model": generator.model_name,
                             "adapter_loaded": generator.adapter_loaded, "enable_thinking": False,
                             "model_identity": generator.model_identity, "max_context": generator.max_context,
                             "memory_guard": generator.memory_guard, "generation": "greedy_remaining_context.v1"})

        def do_POST(self):
            if self.path != "/v1/chat/completions":
                self.reply(404, {"error": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 8 * 1024 * 1024:
                    raise ValueError("invalid_request_size")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("request_must_be_object")
                self.reply(200, generator.complete(payload))
            except (ValueError, TypeError, KeyError) as exc:
                self.reply(400, {"error": "invalid_generation_request", "reason": str(exc)})
            except Exception as exc:
                name = type(exc).__name__
                self.reply(500, {"error": "cuda_out_of_memory" if name == "OutOfMemoryError"
                                else "adapter_generation_failed", "exception_type": name})

        def log_message(self, *_args):
            pass
    return Handler


def main():
    parser = argparse.ArgumentParser(description="Serve an existing local Qwen base or PEFT adapter; never download weights")
    parser.add_argument("--base-dir", required=True)
    parser.add_argument("--adapter-dir", help="Omit for the unmodified base-model baseline")
    parser.add_argument("--model-name", default="qwen3-praxis-joint")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8790)
    parser.add_argument("--max-context", type=int, default=32768)
    args = parser.parse_args()
    generator = AdapterGenerator(args.base_dir, args.adapter_dir, model_name=args.model_name, max_context=args.max_context)
    HTTPServer((args.host, args.port), create_handler(generator)).serve_forever()


if __name__ == "__main__":
    main()
