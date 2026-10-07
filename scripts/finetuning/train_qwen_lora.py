#!/usr/bin/env python3
"""Preflight local Qwen3-32B data; train only with explicit --train.

Launch --train or --gpu-forward through the checked-in 8-GPU Accelerate FSDP
configuration. Native Qwen serialization is preserved; prepared labels supervise
assistant text and calls while masking system/user/tool text. Only the final
LoRA adapter is saved. Answer-free heldout inputs are never an eval_dataset.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from preflight_qwen import DEFAULT_CONFIG, load_config, package_versions, preflight


def assistant_loss_inputs(inputs: dict) -> dict:
    """Select exactly the original supervised next-token positions for lm_head.

    The decoder still receives every input token and its unchanged attention
    mask. Qwen3 4.57.6 accepts Tensor logits_to_keep and explicitly aligned
    shift_labels; these preserve the ordinary masked causal CE objective.
    """
    import torch
    from torch.nn.functional import pad
    if "logits_to_keep" in inputs or "shift_labels" in inputs:
        raise ValueError("training inputs must not supply their own sparse loss positions")
    labels = inputs.get("labels")
    if not isinstance(labels, torch.Tensor) or labels.ndim != 2 or labels.dtype != torch.long:
        raise ValueError("sparse assistant loss requires a batch of int64 labels")
    shifted = pad(labels, (0, 1), value=-100)[:, 1:]
    # A shared sequence-axis index supports batch >1 too: positions supervised
    # for another row stay -100 in this row and retain the original reduction.
    keep = shifted.ne(-100).any(dim=0).nonzero(as_tuple=True)[0]
    if keep.numel() == 0:
        raise ValueError("no supervised next-token positions in the batch")
    return {**inputs, "use_cache": False, "logits_to_keep": keep,
            "shift_labels": shifted.index_select(1, keep)}


def sparse_trainer_class():
    from transformers import Trainer
    from trl import SFTTrainer

    class SparseAssistantSFTTrainer(SFTTrainer):
        def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
            # Retain HF's gradient-accumulation/global-token normalization. TRL
            # 0.28 entropy/accuracy assumes logits span the entire input, so its
            # optional metrics are bypassed rather than reporting wrong values.
            return Trainer.compute_loss(self, model, assistant_loss_inputs(inputs),
                                        return_outputs=return_outputs, num_items_in_batch=num_items_in_batch)

    return SparseAssistantSFTTrainer


def assistant_loss_self_test() -> dict:
    """Compare native/full vs sparse loss and gradients on random tiny Qwen3.

    This is a CPU numerical unit check, not a training run or a loaded checkpoint.
    Both ordinary dense and PEFT models cover disjoint assistant spans, padding,
    batch-union selection, mean CE, and Trainer's supplied token denominator.
    """
    from copy import deepcopy
    from types import SimpleNamespace
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import Qwen3Config, Qwen3ForCausalLM

    trainer_type = sparse_trainer_class()
    settings = Qwen3Config(vocab_size=97, hidden_size=32, intermediate_size=64,
                          num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=2,
                          head_dim=8, attention_dropout=0.0, max_position_embeddings=64, use_cache=False)
    settings._attn_implementation = "sdpa"
    previous_threads = torch.get_num_threads()
    max_loss_error, max_gradient_error, comparisons, cases = 0.0, 0.0, 0, 0
    try:
        torch.set_num_threads(1)
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(20261007)
            ids = torch.randint(1, settings.vocab_size, (2, 21))
            attention = torch.ones_like(ids)
            attention[1, -3:] = 0
            labels = torch.full_like(ids, -100)
            labels[0, 3:6] = ids[0, 3:6]
            labels[0, 13:18] = ids[0, 13:18]
            labels[1, 6:9] = ids[1, 6:9]
            labels[1, 16:18] = ids[1, 16:18]
            batch = {"input_ids": ids, "attention_mask": attention, "labels": labels, "use_cache": False}
            for peft_model in (False, True):
                base = Qwen3ForCausalLM(deepcopy(settings))
                if peft_model:
                    base = get_peft_model(base, LoraConfig(task_type="CAUSAL_LM", r=2, lora_alpha=4,
                                                         lora_dropout=0.0, target_modules=["q_proj", "v_proj", "gate_proj"]))
                for normalized in (False, True):
                    full, sparse = deepcopy(base), deepcopy(base)
                    full.train()
                    sparse.train()
                    denominator = labels[:, 1:].ne(-100).sum() * 2 if normalized else None
                    ordinary = full(**batch, num_items_in_batch=denominator)
                    state = SimpleNamespace(label_smoother=None, compute_loss_func=None,
                                            model_accepts_loss_kwargs=True,
                                            args=SimpleNamespace(past_index=-1, average_tokens_across_devices=False))
                    selected_loss, selected = trainer_type.compute_loss(state, sparse, batch, return_outputs=True,
                                                                        num_items_in_batch=denominator)
                    torch.testing.assert_close(selected_loss, ordinary.loss, rtol=3e-5, atol=2e-6)
                    selected_inputs = assistant_loss_inputs(batch)
                    if (selected_inputs["input_ids"] is not ids or selected_inputs["attention_mask"] is not attention
                            or selected.logits.shape[1] >= ids.shape[1] or "shift_labels" in batch):
                        raise ValueError("sparse loss changed context, failed selection, or mutated input")
                    max_loss_error = max(max_loss_error, float((selected_loss - ordinary.loss).detach().abs()))
                    ordinary.loss.backward()
                    selected_loss.backward()
                    other = dict(sparse.named_parameters())
                    for name, parameter in full.named_parameters():
                        gradient, compared = parameter.grad, other[name].grad
                        if (gradient is None) != (compared is None):
                            raise ValueError("full_and_sparse_gradient_presence_differs")
                        if gradient is not None:
                            torch.testing.assert_close(compared, gradient, rtol=3e-5, atol=2e-6)
                            max_gradient_error = max(max_gradient_error, float((compared - gradient).abs().max()))
                            comparisons += 1
                    cases += 1
    finally:
        torch.set_num_threads(previous_threads)
    return {"status": "passed", "model": "random_tiny_Qwen3", "device": "cpu", "numeric_cases": cases,
            "parameter_gradient_comparisons": comparisons, "max_loss_absolute_error": max_loss_error,
            "max_gradient_absolute_error": max_gradient_error, "full_context_preserved": True,
            "dense_and_peft_checked": True, "optimizer_steps": 0}


def validate_runtime(config: dict) -> None:
    """Fail before loading 32B weights when the pinned FSDP runtime is absent."""
    installed = package_versions()
    expected = config.get("expected_packages", {})
    for package, wanted in expected.items():
        actual = installed.get(package)
        if actual is None or actual.split("+", 1)[0] != str(wanted):
            raise ValueError(f"expected {package}=={wanted}, found {actual}")
    if (int(os.environ.get("WORLD_SIZE", "1")) != 8
            or os.environ.get("ACCELERATE_USE_FSDP", "").lower() != "true"
            or os.environ.get("FSDP_CPU_RAM_EFFICIENT_LOADING", "").lower() != "true"):
        raise ValueError("launch using configs/finetuning/fsdp_a100_8gpu.yaml: eight ranks and RAM-efficient FSDP are required")


def run_model(config: dict, features: list[dict], tokenizer, *, forward_only: bool = False,
              max_steps: int | None = None) -> dict:
    """Explicit large-model operation; caller must have completed mask preflight."""
    validate_runtime(config)
    if not features or tokenizer is None:
        raise ValueError("model operation requires tokenized and mask-checked training data")
    if max_steps is not None and (type(max_steps) is not int or max_steps < 1):
        raise ValueError("max_steps must be a positive integer")
    output = Path(config["output_dir"])
    if not forward_only and output.exists() and any(output.iterdir()):
        raise ValueError("output_dir is not empty; choose a new adapter directory")
    # Local checkpoint and packages only. No hub download or telemetry is needed.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from peft.utils.other import fsdp_auto_wrap_policy
    from transformers import AutoModelForCausalLM, set_seed
    from trl import SFTConfig
    from trl.trainer.sft_trainer import DataCollatorForLanguageModeling

    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise ValueError("CUDA with native BF16 support is required")
    training = dict(config["training"])
    # Prevent a YAML edit from silently enabling full checkpoints or online eval.
    if (training.get("save_strategy") != "no" or training.get("eval_strategy") != "no"
            or training.get("report_to") != "none" or training.get("save_only_model") is not True):
        raise ValueError("this recipe requires no intermediate checkpoints, no Trainer eval and no remote reporting")
    if max_steps is not None:
        training["max_steps"] = max_steps
    args = SFTConfig(
        output_dir=str(output), bf16=True, fp16=False,
        max_length=None, packing=False, padding_free=False,
        # TRL 0.28's built-in flag expects a generation-tagged conversational
        # dataset. Our native-template masks are already present in these rows.
        assistant_only_loss=False, completion_only_loss=False,
        dataset_kwargs={"skip_prepare_dataset": True},
        remove_unused_columns=False, loss_type="nll",
        gradient_checkpointing_kwargs={"use_reentrant": False},
        push_to_hub=False, **training,
    )
    # Initialize distributed state before from_pretrained, allowing only rank 0
    # to read checkpoint tensors and the other ranks to construct meta weights.
    _ = args.device
    set_seed(args.seed)
    model = AutoModelForCausalLM.from_pretrained(
        config["model_dir"], torch_dtype=torch.bfloat16,
        attn_implementation="sdpa", low_cpu_mem_usage=True,
        local_files_only=True, trust_remote_code=False,
    )
    model.config.use_cache = False
    if model.config.model_type != "qwen3":
        raise ValueError("checkpoint must be the official dense Qwen3 causal language model")
    lora = LoraConfig(task_type="CAUSAL_LM", bias="none", **config["lora"])
    collator = DataCollatorForLanguageModeling(pad_token_id=tokenizer.pad_token_id,
                                             completion_only_loss=False)
    trainer = sparse_trainer_class()(
        model=model, args=args, train_dataset=Dataset.from_list(features),
        processing_class=tokenizer, peft_config=lora, data_collator=collator,
    )
    plugin = getattr(trainer.accelerator.state, "fsdp_plugin", None)
    if plugin is None or not trainer.is_fsdp_enabled or plugin.use_orig_params:
        raise ValueError("PEFT requires the configured FSDP plugin with use_orig_params=false")
    plugin.auto_wrap_policy = fsdp_auto_wrap_policy(trainer.model)
    trainable = sum(p.numel() for p in trainer.model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in trainer.model.parameters())
    if not trainable or trainable >= total:
        raise ValueError("only nonempty LoRA adapter parameters may be trainable")
    report = {"base_model": config["model_id"], "precision": "bf16", "attention": "sdpa",
              "world_size": trainer.accelerator.num_processes, "trainable_parameters": trainable,
              "total_parameters": total, "native_template_unchanged": True,
              "heldout_inputs_used_for_training": False, "loss": "native_sparse_assistant_causal_CE",
              "full_context_preserved": True}
    torch.cuda.reset_peak_memory_stats()
    if forward_only:
        model = trainer.accelerator.prepare_model(trainer.model)
        model.eval()
        longest = max(features, key=lambda row: len(row["input_ids"]))
        batch = {key: value.to(trainer.accelerator.device) for key, value in collator([longest]).items()}
        sparse_batch = assistant_loss_inputs(batch)
        with torch.no_grad(), trainer.accelerator.autocast():
            loss = model(**sparse_batch).loss
        if loss is None or not bool(torch.isfinite(loss).all()):
            raise ValueError("GPU preflight produced a nonfinite loss")
        peaks = trainer.accelerator.gather(torch.tensor([torch.cuda.max_memory_allocated()],
                                                       device=trainer.accelerator.device)).cpu().tolist()
        trainer.accelerator.wait_for_everyone()
        report.update(status="gpu_forward_passed", tokens=len(longest["input_ids"]), loss=float(loss.detach().cpu()),
                      lm_head_positions=int(sparse_batch["logits_to_keep"].numel()),
                      peak_allocated_GiB_per_rank=[round(value / 1024**3, 3) for value in peaks],
                      optimizer_steps=0, backward_runs=0, saved_adapter=False)
        trainer.accelerator.end_training()
        return report
    result = trainer.train()
    # Official PEFT/FSDP save path gathers state to rank 0 CPU and writes the
    # adapter through PeftModel.save_pretrained, without merging or copying base.
    plugin.set_state_dict_type("FULL_STATE_DICT")
    trainer.save_model(str(output))
    trainer.accelerator.wait_for_everyone()
    report.update(status="trained", optimizer_steps=trainer.state.global_step,
                  train_loss=float(result.training_loss), saved_adapter=True, output_dir=str(output))
    trainer.accelerator.end_training()
    return report


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--config", default=str(DEFAULT_CONFIG))
    result.add_argument("--model-dir")
    result.add_argument("--data-dir")
    result.add_argument("--output-dir")
    result.add_argument("--max-length", type=int)
    result.add_argument("--schema-only", action="store_true")
    result.add_argument("--train", action="store_true", help="Explicitly permit optimizer steps and adapter saving")
    result.add_argument("--max-steps", type=int, help="Optional explicit short training run; requires --train")
    result.add_argument("--report", help="Optional local readiness/result JSON path")
    return result


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    if args.train and args.schema_only or args.max_steps is not None and not args.train:
        raise ValueError("--train requires full preflight; --max-steps requires explicit --train")
    config = load_config(args.config, model_dir=args.model_dir, data_dir=args.data_dir, output_dir=args.output_dir,
                         max_length=args.max_length)
    report, features, tokenizer = preflight(config, schema_only=args.schema_only)
    if args.train:
        report["training"] = run_model(config, features, tokenizer, max_steps=args.max_steps)
        report["training_runs"] = 1
        report["large_model_loaded"] = True
    if int(os.environ.get("RANK", "0")) == 0:
        text = json.dumps(report, ensure_ascii=False, allow_nan=False)
        if args.report:
            path = Path(args.report)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text + "\n", encoding="utf-8")
        print(text)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, ImportError) as error:
        print(f"Qwen LoRA preparation failed: {error}", file=sys.stderr)
        raise SystemExit(2)
