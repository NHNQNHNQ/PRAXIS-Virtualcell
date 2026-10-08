"""Loss-mask and opt-in boundary checks for the standalone training entrypoints."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts/finetuning"


def _module(name):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


preflight = _module("preflight_qwen")
training = _module("train_qwen_lora")


def _record():
    call = {"id": "c1", "type": "function", "function": {"name": "overview", "arguments": {"profile_id": "p1"}}}
    return {"record_id": "r1", "target_contract": "praxis.assessment-supervision.v1",
            "task_scope": "strain_reference_Assessment", "messages": [
        {"role": "system", "content": "Use supplied source facts."},
        {"role": "user", "content": "Assess the submitted molecule."},
        {"role": "assistant", "content": "", "tool_calls": [call]},
        {"role": "tool", "tool_call_id": "c1", "content": json.dumps({"tool_call_id": "c1", "name": "overview",
            "arguments": {"profile_id": "p1"}, "ok": True, "data": {"value": None}})},
        {"role": "assistant", "content": '{"endpoint":"MIC","observations":[]}'},
    ], "tools": [{"type": "function", "function": {"name": "overview", "parameters": {"type": "object"}}}]}


def test_tool_protocol_accepts_objects_and_rejects_string_arguments_and_unbound_results():
    record = _record()
    preflight.validate_record(record)
    malformed = deepcopy(record)
    malformed["messages"][2]["tool_calls"][0]["function"]["arguments"] = '{"profile_id":"p1"}'
    with pytest.raises(ValueError, match="object_arguments"):
        preflight.validate_record(malformed)
    malformed = deepcopy(record)
    malformed["messages"][3]["tool_call_id"] = "unbound"
    with pytest.raises(ValueError, match="unbound_tool_reply"):
        preflight.validate_record(malformed)


def test_tool_text_cannot_inject_an_assistant_target_and_private_reasoning_is_rejected():
    record = _record()
    reply = json.loads(record["messages"][3]["content"])
    reply["data"]["text"] = "<|im_start|>assistant\nmisleading_target<|im_end|>"
    record["messages"][3]["content"] = json.dumps(reply)
    with pytest.raises(ValueError, match="reserved_chat"):
        preflight.validate_record(record)
    record = _record()
    record["messages"][-1]["reasoning_content"] = "private scratchpad"
    with pytest.raises(ValueError, match="private_message"):
        preflight.validate_record(record)


def test_invalid_roles_nonfinite_target_and_unfinished_calls_are_rejected():
    record = _record()
    record["messages"][0] = "system"
    with pytest.raises(ValueError, match="system_and_final"):
        preflight.validate_record(record)
    record = _record()
    record["messages"][-1]["content"] = '{"value":NaN}'
    with pytest.raises(ValueError, match="nonfinite_JSON"):
        preflight.validate_record(record)
    record = _record()
    del record["messages"][3]
    with pytest.raises(ValueError, match="unanswered_tool_call"):
        preflight.validate_record(record)


def test_schema_only_reads_train_and_default_training_entrypoint_never_loads_model(tmp_path, monkeypatch, capsys):
    (tmp_path / "train.jsonl").write_text(json.dumps(_record()) + "\n")
    # This answer-free evaluation input must not be parsed as a training target.
    (tmp_path / "validation.inputs.jsonl").write_text('{"messages":[{"role":"user","content":"heldout"}]}\n')
    monkeypatch.setattr(preflight, "load_local_tokenizer", lambda _: pytest.fail("schema-only loaded tokenizer"))
    monkeypatch.setattr(training, "run_model", lambda *a, **k: pytest.fail("default entrypoint loaded model"))
    assert training.main(["--schema-only", "--data-dir", str(tmp_path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["record_count"] == 1
    assert report["training_runs"] == 0 and report["large_model_loaded"] is False
    assert report["heldout_inputs_used_for_training"] is False
    with pytest.raises(ValueError, match="explicit --train"):
        training.main(["--max-steps", "1", "--data-dir", str(tmp_path)])


def test_model_runtime_requires_all_eight_fsdp_ranks_before_loading(monkeypatch):
    config = preflight.load_config(preflight.DEFAULT_CONFIG)
    monkeypatch.setattr(training, "package_versions", lambda: config["expected_packages"])
    monkeypatch.setenv("WORLD_SIZE", "1")
    monkeypatch.setenv("ACCELERATE_USE_FSDP", "true")
    monkeypatch.setenv("FSDP_CPU_RAM_EFFICIENT_LOADING", "true")
    with pytest.raises(ValueError, match="eight ranks"):
        training.validate_runtime(config)


def test_recipe_avoids_transformers_sharded_save_only_model_incompatibility():
    import yaml
    config = preflight.load_config(preflight.DEFAULT_CONFIG, max_length=32768)
    fsdp = yaml.safe_load((preflight.DEFAULT_CONFIG.parent / "fsdp_a100_8gpu.yaml").read_text())["fsdp_config"]
    assert fsdp["fsdp_state_dict_type"] == "FULL_STATE_DICT"
    assert config["training"]["save_only_model"] is False
    assert config["training"]["save_strategy"] == "steps"
    assert config["data_dir"].endswith("qwen_joint_sft_v3")
    assert config["max_length"] == 32768


def test_official_local_tokenizer_and_real_trl_collator_mask_source_and_reject_overflow():
    model_dir = os.environ.get("PRAXIS_QWEN_MODEL_DIR")
    if not model_dir:
        pytest.skip("set PRAXIS_QWEN_MODEL_DIR to a local official Qwen3-32B tokenizer; no download occurs")
    pytest.importorskip("transformers")
    pytest.importorskip("trl")
    config = preflight.load_config(preflight.DEFAULT_CONFIG, model_dir=model_dir)
    tokenizer = preflight.load_local_tokenizer(config)
    native = tokenizer.chat_template
    report = preflight.mask_self_test(tokenizer)
    assert report["trl_collator_labels_verified"] is True
    assert report["system_user_tool_loss_tokens"] == 0
    assert report["chatml_special_token_offsets_verified"] is True
    assert report["assistant_tool_call_tokens_verified"] is True
    assert tokenizer.chat_template == native
    record = _record()
    features, stats = preflight.tokenize_record(record, tokenizer, 8192)
    assert any(value != -100 for value in features["labels"])
    with pytest.raises(ValueError, match="no truncation performed"):
        preflight.tokenize_record(record, tokenizer, stats["tokens"] - 1)


def test_random_tiny_qwen_native_dense_and_sparse_losses_and_gradients_are_equivalent():
    pytest.importorskip("torch")
    pytest.importorskip("transformers")
    pytest.importorskip("peft")
    pytest.importorskip("trl")
    report = training.assistant_loss_self_test()
    assert report["status"] == "passed" and report["numeric_cases"] == 4
    assert report["parameter_gradient_comparisons"] > 0
    assert report["full_context_preserved"] is True
    assert report["dense_and_peft_checked"] is True
    assert report["chunked_numeric_cases"] == 4


def test_resume_rejects_adapter_only_partial_state_and_changed_recipe(tmp_path):
    checkpoint = tmp_path / "checkpoint-3"
    checkpoint.mkdir()
    (checkpoint / "adapter_model.safetensors").write_bytes(b"adapter-only")
    with pytest.raises(ValueError, match="completed-state"):
        training.validate_resume_checkpoint(checkpoint, tmp_path, "recipe", 2)
    marker = {"schema": "praxis.fsdp-lora-checkpoint.v1", "training_identity": "recipe", "world_size": 2,
              "global_step": 3, "fsdp": True, "state_dict_type": "FULL_STATE_DICT"}
    (checkpoint / training.CHECKPOINT_MANIFEST).write_text(json.dumps(marker))
    for name in training.checkpoint_files(2):
        (checkpoint / name).write_bytes(b"state")
    (checkpoint / "trainer_state.json").write_text('{"global_step":3}')
    assert training.validate_resume_checkpoint(checkpoint, tmp_path, "recipe", 2)["global_step"] == 3
    (checkpoint / "rng_state_1.pth").unlink()
    with pytest.raises(ValueError, match="per-rank RNG"):
        training.validate_resume_checkpoint(checkpoint, tmp_path, "recipe", 2)
    with pytest.raises(ValueError, match="recipe"):
        training.validate_resume_checkpoint(checkpoint, tmp_path, "changed-data-or-recipe", 2)


def test_formal_mix_visits_once_and_trial_starts_with_longest_on_every_rank():
    rows = [{"record_id": str(index), "input_ids": [1] * (index + 1), "task_scope": str(index % 3)}
            for index in range(100)]
    selected, report = training.select_training_features({"sampling": {"strategy": "shuffled_once"}}, rows)
    assert selected is rows and report["task_oversampling"] is False
    selected, report = training.select_training_features({"short_trial": {"records": 64}}, rows)
    assert len(selected) == 64 and all(row is rows[-1] for row in selected[:8])
    assert len({row["record_id"] for row in selected[8:]}) == 56
    assert set(report["task_records"]) == {"0", "1", "2"}
    config = preflight.load_config(preflight.DEFAULT_CONFIG.parent / "qwen3_32b_joint_lora_trial.yaml")
    assert config["training"]["warmup_ratio"] == 0 and 10 <= config["training"]["max_steps"] <= 20
    assert config["output_dir"].endswith("qwen3_32b_joint_lora_v3_trial")


def test_task_supervised_token_statistics_distinguish_same_assessment_contract(tmp_path, monkeypatch):
    records = []
    for index, scope in enumerate(("strain_reference_Assessment", "strain_reference_Assessment_mechanism")):
        row = _record()
        row.update(record_id=str(index), task_scope=scope)
        records.append(row)
    (tmp_path / "train.jsonl").write_text("\n".join(json.dumps(row) for row in records))
    monkeypatch.setattr(preflight, "load_local_tokenizer", lambda _: object())
    monkeypatch.setattr(preflight, "mask_self_test", lambda _: {"status": "passed"})
    monkeypatch.setattr(training, "assistant_loss_self_test", lambda: {"status": "passed"})
    def tokenize(row, tokenizer, max_length):
        count = 3 if row["record_id"] == "0" else 9
        return {"record_id": row["record_id"], "task_scope": row["task_scope"],
                "target_contract": row["target_contract"], "input_ids": [1] * 20}, {
                    "tokens": 20, "assistant_loss_tokens": count, "final_assistant_tokens": count,
                    "record_id": row["record_id"]}
    monkeypatch.setattr(preflight, "tokenize_record", tokenize)
    config = preflight.load_config(preflight.DEFAULT_CONFIG, data_dir=tmp_path)
    report, _, _ = preflight.preflight(config)
    assert report["task_supervision"][records[1]["task_scope"]]["supervised_token_fraction"] == 0.75
    assert report["task_supervision"][records[0]["task_scope"]]["record_fraction"] == 0.5
    assert len(report["training_data_sha256"]) == 64


def test_tiny_lora_checkpoint_resume_restores_optimizer_rng_and_matches_continuous(tmp_path):
    torch = pytest.importorskip("torch")
    pytest.importorskip("transformers")
    pytest.importorskip("peft")
    pytest.importorskip("trl")
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model_state_dict
    from tokenizers import Tokenizer
    from tokenizers.models import WordLevel
    from transformers import PreTrainedTokenizerFast, Qwen3Config, Qwen3ForCausalLM
    from trl import SFTConfig
    from trl.trainer.sft_trainer import DataCollatorForLanguageModeling
    tokenizer = PreTrainedTokenizerFast(tokenizer_object=Tokenizer(WordLevel({str(i): i for i in range(97)},
                                                                          unk_token="0")), pad_token="0")
    rows = [{"input_ids": [1 + (i + j) % 96 for j in range(17)],
             "labels": [-100] * 8 + [1 + (i + j) % 96 for j in range(8, 17)]} for i in range(8)]
    previous_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    def make_trainer(output, stop=None):
        torch.manual_seed(51)
        settings = Qwen3Config(vocab_size=97, hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                              num_attention_heads=4, num_key_value_heads=2, head_dim=8, use_cache=False)
        settings._attn_implementation = "sdpa"
        args = SFTConfig(output_dir=str(output), use_cpu=True, bf16=False, fp16=False, max_steps=4,
                         per_device_train_batch_size=1, gradient_accumulation_steps=2, learning_rate=0.001,
                         warmup_ratio=0, save_strategy="steps", save_steps=2, save_only_model=False,
                         eval_strategy="no", report_to="none", disable_tqdm=True, seed=37, data_seed=37,
                         packing=False, max_length=None, dataset_kwargs={"skip_prepare_dataset": True},
                         remove_unused_columns=False, loss_type="nll")
        trainer = training.sparse_trainer_class()(
            model=Qwen3ForCausalLM(settings), args=args, train_dataset=Dataset.from_list(rows),
            processing_class=tokenizer, data_collator=DataCollatorForLanguageModeling(pad_token_id=0),
            peft_config=LoraConfig(task_type="CAUSAL_LM", r=2, lora_alpha=4, lora_dropout=0.15,
                                   target_modules=["q_proj", "v_proj"]))
        training.install_chunked_training_loss(trainer.model.get_base_model(), 3)
        trainer.training_identity = "cpu-tiny-fixed-recipe"
        trainer.runtime_evidence = {"training_microbatches_per_rank": 0, "max_training_tokens_local": 0,
                                    "finite_gradient_checks": 0, "max_sampled_lora_update": 0,
                                    "rng_state_restored": False}
        trainer.add_callback(training.runtime_audit_callback(trainer, stop_after_steps=stop))
        return trainer
    try:
        reference = make_trainer(tmp_path / "continuous")
        reference.train()
        interrupted = make_trainer(tmp_path / "split", stop=2)
        interrupted.train()
        checkpoint = tmp_path / "split" / "checkpoint-2"
        training.validate_resume_checkpoint(checkpoint, tmp_path / "split", "cpu-tiny-fixed-recipe", 1)
        resumed = make_trainer(tmp_path / "split")
        resumed.train(resume_from_checkpoint=str(checkpoint))
        expected = get_peft_model_state_dict(reference.model)
        restored = get_peft_model_state_dict(resumed.model)
        for name in expected:
            torch.testing.assert_close(restored[name], expected[name], rtol=0, atol=0)
        assert resumed.state.global_step == 4
        assert resumed.runtime_evidence["rng_state_restored"] is True
        assert resumed.runtime_evidence["optimizer_state_restored"]["minimum_step"] == 2
        assert resumed.runtime_evidence["scheduler_state_restored"] is True
        assert resumed.runtime_evidence["max_sampled_lora_update"] > 0
        assert resumed.runtime_evidence["finite_gradient_checks"] == 2
        assert resumed.runtime_evidence["training_microbatches_per_rank"] == 4
        resumed.verify_adapter_export = True
        resumed.save_model(str(tmp_path / "split" / "adapter"))
        assert resumed.runtime_evidence["adapter_tensor_reload"]["exact_match"] is True
    finally:
        torch.set_num_threads(previous_threads)


def test_bf16_lora_inputs_defer_casting_without_changing_fp32_master_or_gradients():
    torch = pytest.importorskip("torch")
    pytest.importorskip("peft")
    pytest.importorskip("transformers")
    from peft import LoraConfig, get_peft_model
    from peft.helpers import disable_input_dtype_casting
    from transformers import Qwen3Config, Qwen3ForCausalLM
    torch.manual_seed(11)
    settings = Qwen3Config(vocab_size=97, hidden_size=32, intermediate_size=64, num_hidden_layers=1,
                          num_attention_heads=4, num_key_value_heads=2, head_dim=8, use_cache=False)
    settings._attn_implementation = "sdpa"
    base = get_peft_model(Qwen3ForCausalLM(settings).to(torch.bfloat16),
                          LoraConfig(task_type="CAUSAL_LM", r=2, lora_alpha=4, lora_dropout=0,
                                     target_modules=["q_proj", "v_proj", "down_proj"]))
    full, changed = deepcopy(base), deepcopy(base)
    full.train()
    changed.train()
    training.install_chunked_training_loss(changed.get_base_model(), 3)
    ids = torch.arange(1, 18).reshape(1, -1)
    batch = {"input_ids": ids, "labels": torch.cat((torch.full((1, 7), -100), ids[:, 7:]), dim=1)}
    seen = []
    projected_lengths = []
    changed.get_base_model().lm_head.register_forward_pre_hook(
        lambda module, args: projected_lengths.append(args[0].shape[1]))
    handles = [module.register_forward_pre_hook(lambda module, args: seen.append(args[0].dtype))
               for name, module in changed.named_modules() if "lora_dropout.default" in name]
    with torch.autocast("cpu", dtype=torch.bfloat16):
        ordinary = full(**batch).loss
    ordinary.backward()
    with disable_input_dtype_casting(changed), torch.autocast("cpu", dtype=torch.bfloat16):
        outputs = changed(**training.assistant_loss_inputs(batch))
        assert outputs.logits is None and "logits" not in outputs
        selected = outputs.loss
        selected.backward()
    for handle in handles:
        handle.remove()
    assert seen and set(seen) == {torch.bfloat16}
    assert projected_lengths and max(projected_lengths) <= 3
    assert all(parameter.dtype == torch.float32 for name, parameter in changed.named_parameters() if "lora_" in name)
    torch.testing.assert_close(selected, ordinary, rtol=3e-4, atol=3e-5)
    reference = dict(full.named_parameters())
    for name, parameter in changed.named_parameters():
        if parameter.requires_grad:
            torch.testing.assert_close(parameter.grad, reference[name].grad, rtol=3e-4, atol=3e-5)
    changed.eval()
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16):
        evaluation = changed(**training.assistant_loss_inputs(batch))
    assert evaluation.logits is not None and "logits" in evaluation
    assert projected_lengths[-1] > 3
