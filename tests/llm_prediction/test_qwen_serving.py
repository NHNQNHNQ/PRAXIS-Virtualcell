import json
from contextlib import nullcontext
from io import BytesIO
import sys
from types import SimpleNamespace
from pathlib import Path
import subprocess

import pytest

from praxis_virtualcell.llm_prediction.qwen_serving import QwenAnalysisClient, native_messages, parse_completion, smiles_messages
from scripts.finetuning.serve_qwen_adapter import AdapterGenerator, create_handler
from scripts.finetuning import serve_qwen_adapter as serving


TOOLS = [{"type": "function", "function": {"name": "query_features"}}]


def test_native_tool_calls_become_openai_calls_and_roundtrip_into_official_template():
    native = '<tool_call>{"name":"query_features","arguments":{"modality":"genome","feature_ids":["gene-1"]}}</tool_call>'
    message, finish = parse_completion(native + "\n" + native, TOOLS)
    assert finish == "tool_calls"
    assert message["content"] is None
    assert len({call["id"] for call in message["tool_calls"]}) == 2
    arguments = message["tool_calls"][0]["function"]["arguments"]
    assert isinstance(arguments, str) and json.loads(arguments)["feature_ids"] == ["gene-1"]
    messages = native_messages([message, {"role": "tool", "tool_call_id": message["tool_calls"][0]["id"], "content": "{}"}])
    assert isinstance(messages[0]["tool_calls"][0]["function"]["arguments"], dict)
    assert isinstance(message["tool_calls"][0]["function"]["arguments"], str)


@pytest.mark.parametrize("output", [
    '<tool_call>{"name":"unapproved","arguments":{}}</tool_call>',
    '<tool_call>{"name":"query_features","arguments":"{}"}</tool_call>',
    '<tool_call>{"name":"query_features","arguments":{}}',
    '<think>private reasoning</think>{"activity":"uncertain"}',
])
def test_invalid_calls_and_hidden_reasoning_do_not_reach_platform(output):
    with pytest.raises(ValueError):
        parse_completion(output, TOOLS)


async def test_nonthinking_final_json_is_preserved_and_qwen_payload_uses_native_option():
    output = '{"activity":"uncertain","mic_observations":[]}'
    assert parse_completion("<think>\n</think>\n" + output) == ({"role": "assistant", "content": output}, "stop")
    client = QwenAnalysisClient("", "http://127.0.0.1:8790")
    payload = client._build_payload(model="adapter", messages=[{"role": "user", "content": "CCO"}],
                                    max_tokens=4096, system=None, tools=TOOLS, stream=False,
                                    thinking={"type": "disabled"}, reasoning_effort="high")
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert "thinking" not in payload and "reasoning_effort" not in payload
    await client.aclose()


def test_serving_loads_existing_base_and_adapter_without_network_or_merging(tmp_path, monkeypatch):
    base, adapter = tmp_path / "base", tmp_path / "adapter"
    base.mkdir()
    adapter.mkdir()
    (base / "config.json").write_text("{}")
    (adapter / "adapter_config.json").write_text("{}")
    (adapter / "tokenizer_config.json").write_text("{}")
    calls = []
    monkeypatch.setattr(serving, "validate_memory_guard", lambda: {"verified": True})
    model = SimpleNamespace(config=SimpleNamespace(use_cache=False))
    model.eval = lambda: model
    def load_tokenizer(path, **kwargs):
        calls.append(("tokenizer", path, kwargs))
        return "tokenizer"
    def load_base(path, **kwargs):
        calls.append(("base", path, kwargs))
        return model
    def load_adapter(received_model, path, **kwargs):
        assert received_model is model
        calls.append(("adapter", path, kwargs))
        return model
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(bfloat16="bf16", cuda=SimpleNamespace(
        is_available=lambda: True, device_count=lambda: 8, mem_get_info=lambda _: (1024 ** 3, 1024 ** 3))))
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(
        AutoTokenizer=SimpleNamespace(from_pretrained=load_tokenizer),
        AutoModelForCausalLM=SimpleNamespace(from_pretrained=load_base)))
    monkeypatch.setitem(sys.modules, "peft", SimpleNamespace(PeftModel=SimpleNamespace(from_pretrained=load_adapter)))
    generated = AdapterGenerator(str(base), str(adapter), model_name="adapter")
    assert [call[0] for call in calls] == ["tokenizer", "base", "adapter"]
    assert all(call[2]["local_files_only"] for call in calls)
    assert calls[-1][2]["is_trainable"] is False and generated.model.config.use_cache is True
    assert generated.adapter_loaded is True
    assert generated.memory_guard == {"verified": True}
    assert calls[1][2]["device_map"] == "balanced"
    assert calls[1][2]["max_memory"] == {index: 3 * 1024 ** 3 // 4 for index in range(8)}
    calls.clear()
    baseline = AdapterGenerator(str(base), model_name="base")
    assert [call[0] for call in calls] == ["tokenizer", "base"] and baseline.adapter_loaded is False
    assert baseline.model_identity != generated.model_identity


def test_model_loading_is_refused_before_runtime_import_when_memory_guard_fails(monkeypatch):
    def refused():
        raise ValueError("bounded cgroup required")
    monkeypatch.setattr(serving, "validate_memory_guard", refused)
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(
        AutoModelForCausalLM=SimpleNamespace(from_pretrained=lambda *a, **k: pytest.fail("loaded weights"))))
    with pytest.raises(ValueError, match="bounded cgroup"):
        AdapterGenerator("unused", model_name="baseline")


def test_shared_memory_guard_import_does_not_import_torch():
    code = ("import sys; from scripts.finetuning.serve_qwen_adapter import validate_memory_guard\n"
            "try: validate_memory_guard()\n"
            "except ValueError: pass\n"
            "assert 'torch' not in sys.modules\n")
    subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[2], check=True,
                   capture_output=True, text=True)


def test_http_handler_exposes_openai_completion_shape_without_loading_weights():
    request = {"model": "adapter", "messages": [{"role": "user", "content": '{"candidate":{"smiles":"CCO"}}'}],
               "chat_template_kwargs": {"enable_thinking": False}}
    def complete(payload):
        assert payload == request
        return {"model": "adapter", "choices": [{"message": {"role": "assistant", "content": "{}"}, "finish_reason": "stop"}]}
    Handler = create_handler(SimpleNamespace(model_name="adapter", complete=complete))
    handler = Handler.__new__(Handler)
    raw = json.dumps(request).encode()
    handler.path, handler.headers, handler.rfile = "/v1/chat/completions", {"Content-Length": str(len(raw))}, BytesIO(raw)
    replies = []
    handler.reply = lambda status, body: replies.append((status, body))
    handler.do_POST()
    assert replies[0][0] == 200 and replies[0][1]["choices"][0]["finish_reason"] == "stop"


@pytest.mark.parametrize("name,error", [("OutOfMemoryError", "cuda_out_of_memory"),
                                       ("RuntimeError", "adapter_generation_failed")])
def test_http_generation_failures_identify_cuda_oom_for_pipeline_stop(name, error):
    exception = type(name, (RuntimeError,), {})
    def complete(_payload):
        raise exception("generation stopped")
    Handler = create_handler(SimpleNamespace(model_name="baseline", complete=complete))
    handler = Handler.__new__(Handler)
    raw = b'{"model":"baseline"}'
    handler.path, handler.headers, handler.rfile = "/v1/chat/completions", {"Content-Length": str(len(raw))}, BytesIO(raw)
    replies = []
    handler.reply = lambda status, body: replies.append((status, body))
    handler.do_POST()
    assert replies == [(500, {"error": error, "exception_type": name})]


def test_serving_candidate_requires_structure_and_strips_private_name_and_id():
    messages = [{"role": "user", "content": json.dumps({"candidate": {
        "id": "CHEMBL_PRIVATE", "name": "PRIVATE_NAME", "smiles": "OCC"}, "conditions": {"medium": None}})}]
    public = smiles_messages(messages)
    assert json.loads(public[0]["content"])["candidate"] == {"smiles": "CCO"}
    assert all(value is None for value in json.loads(public[0]["content"])["conditions"].values())
    assert "PRIVATE" not in public[0]["content"]
    with pytest.raises(ValueError):
        smiles_messages([{"role": "user", "content": '{"candidate":{"name":"aspirin"}}'}])


def test_exhausted_generation_preserves_length_status_and_decoder_keeps_tool_delimiters(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(inference_mode=nullcontext))
    class Tensor:
        shape = (1, 1)
        def to(self, device):
            return self
    class Tokens(list):
        def tolist(self):
            return list(self)
    class Generated:
        def __getitem__(self, key):
            return Tokens([7, 8])
    class Tokenizer:
        pad_token_id = 0
        eos_token_id = 2
        def apply_chat_template(self, messages, **kwargs):
            assert kwargs["enable_thinking"] is False
            return "rendered"
        def __call__(self, text, **kwargs):
            assert kwargs["truncation"] is False
            return {"input_ids": Tensor()}
        def decode(self, tokens, **kwargs):
            assert kwargs["skip_special_tokens"] is False
            return "<tool_call>{"
    generator = AdapterGenerator.__new__(AdapterGenerator)
    generator.model_name, generator.max_context, generator.tokenizer = "adapter", 10, Tokenizer()
    generator.model = SimpleNamespace(generation_config=SimpleNamespace(eos_token_id=2),
        get_input_embeddings=lambda: SimpleNamespace(weight=SimpleNamespace(device="cpu")),
        generate=lambda **kwargs: Generated())
    result = generator.complete({"model": "adapter", "max_tokens": 2, "messages": [
        {"role": "user", "content": '{"candidate":{"smiles":"CCO"}}'}]})
    assert result["choices"][0]["finish_reason"] == "length"
    assert result["choices"][0]["message"]["content"] == "<tool_call>{"


@pytest.mark.parametrize("prompt_tokens", [8, 10])
def test_long_prompt_uses_remaining_context_without_truncation_and_keeps_length_failure(monkeypatch, prompt_tokens):
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(inference_mode=nullcontext))
    class Tensor:
        shape = (1, prompt_tokens)
        def to(self, _device):
            return self
    class Tokens(list):
        def tolist(self):
            return list(self)
    class Generated:
        def __getitem__(self, _key):
            return Tokens([7, 8])
    class Tokenizer:
        pad_token_id, eos_token_id = 0, 2
        def apply_chat_template(self, messages, **kwargs):
            return "full prompt"
        def __call__(self, _text, **kwargs):
            assert kwargs["truncation"] is False
            return {"input_ids": Tensor()}
        def decode(self, _tokens, **kwargs):
            return '{"partial":'
    calls = []
    def generate(**kwargs):
        calls.append(kwargs)
        assert kwargs["max_new_tokens"] == 2 and kwargs["input_ids"].shape == (1, 8)
        return Generated()
    generator = AdapterGenerator.__new__(AdapterGenerator)
    generator.model_name, generator.max_context, generator.tokenizer = "baseline", 10, Tokenizer()
    generator.model = SimpleNamespace(generation_config=SimpleNamespace(eos_token_id=2), generate=generate,
        get_input_embeddings=lambda: SimpleNamespace(weight=SimpleNamespace(device="cpu")))
    payload = {"model": "baseline", "max_tokens": 12288,
               "messages": [{"role": "user", "content": '{"candidate":{"smiles":"CCO"}}'}]}
    if prompt_tokens == 10:
        with pytest.raises(ValueError, match="context_budget_exceeded_no_truncation"):
            generator.complete(payload)
        assert not calls
    else:
        result = generator.complete(payload)
        assert result["generation_budget"] == {"requested_max_tokens": 12288, "max_new_tokens": 2,
            "prompt_tokens": 8, "max_context": 10, "remaining_context_tokens": 2, "reduced": True,
            "input_truncated": False}
        assert result["choices"][0]["finish_reason"] == "length"
