#!/usr/bin/env python3
"""Preflight local Qwen3-32B data; train only with explicit --train.

Launch --train or --checkpoint-smoke through the guarded 8-GPU Accelerate FSDP
configuration. Native Qwen serialization is preserved; prepared labels supervise
assistant text and calls while masking system/user/tool text. Intermediate
checkpoints restore LoRA, optimizer, scheduler and RNG; base weights stay local
and are never written into checkpoints. Heldout inputs are never an eval_dataset.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from preflight_qwen import DEFAULT_CONFIG, load_config, package_versions, preflight

CHECKPOINT_MANIFEST = "praxis_checkpoint.json"


def training_identity(config: dict, data_sha256: str, features: list[dict]) -> str:
    recipe = {key: config.get(key) for key in ("model_id", "model_dir", "expected_packages", "lora",
                                             "training", "sampling", "short_trial", "loss_chunk_tokens",
                                             "fsdp_bf16_lora_inputs", "activation_cpu_offload", "max_length", "bf16",
                                             "attn_implementation", "loss_mask", "packing")}
    recipe["training_implementation"] = "qwen3_projection_chunk_ce_unpinned_offload.v2"
    recipe.update(training_data_sha256=data_sha256,
                  selected_records=[row.get("record_id", "unnamed") for row in features])
    return hashlib.sha256(json.dumps(recipe, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def checkpoint_files(world_size: int, *, fsdp: bool = True) -> list[str]:
    names = (["pytorch_model_fsdp.bin", "optimizer.bin"] if fsdp
             else ["adapter_model.safetensors", "optimizer.pt"])
    return names + ["scheduler.pt", "trainer_state.json"] + (
        [f"rng_state_{rank}.pth" for rank in range(world_size)] if world_size > 1 else ["rng_state.pth"])


def validate_resume_checkpoint(path: str | Path, output: str | Path, identity: str,
                               world_size: int = 8) -> dict:
    """Reject adapter-only, incomplete, other-data and other-recipe restarts."""
    checkpoint, root = Path(path).resolve(), Path(output).resolve()
    if checkpoint.parent != root or not checkpoint.name.startswith("checkpoint-"):
        raise ValueError("resume must select a checkpoint-N directory in the configured output_dir")
    marker = checkpoint / CHECKPOINT_MANIFEST
    if not marker.is_file():
        raise ValueError("checkpoint has no completed-state manifest; an empty output or adapter is not resumable")
    report = json.loads(marker.read_text(encoding="utf-8"))
    if (report.get("schema") != "praxis.fsdp-lora-checkpoint.v1" or report.get("training_identity") != identity
            or report.get("world_size") != world_size or report.get("state_dict_type") != "FULL_STATE_DICT"):
        raise ValueError("checkpoint data, recipe, world size or state format differs from this run")
    expected = checkpoint_files(world_size, fsdp=report.get("fsdp", True))
    if any(not (checkpoint / name).is_file() or (checkpoint / name).stat().st_size == 0 for name in expected):
        raise ValueError("checkpoint is missing model, optimizer, scheduler, Trainer or per-rank RNG state")
    recorded_sizes = report.get("files")
    if recorded_sizes is not None and any(recorded_sizes.get(name) != (checkpoint / name).stat().st_size
                                          for name in expected):
        raise ValueError("checkpoint recovery files differ from the completed-state manifest")
    state = json.loads((checkpoint / "trainer_state.json").read_text(encoding="utf-8"))
    if state.get("global_step") != report.get("global_step") or checkpoint.name != f"checkpoint-{state['global_step']}":
        raise ValueError("checkpoint completion manifest and Trainer progress disagree")
    return report


def select_training_features(config: dict, features: list[dict], world_size: int = 8) -> tuple[list[dict], dict]:
    """Formal mixing visits each record once; the trial starts with a capacity probe."""
    if config.get("sampling", {}).get("strategy", "shuffled_once") != "shuffled_once":
        raise ValueError("the initial mixed recipe must use shuffled_once without task oversampling")
    longest = max(features, key=lambda row: len(row["input_ids"]))
    if not config.get("short_trial"):
        return features, {"strategy": "shuffled_once", "task_oversampling": False, "records": len(features)}
    limit = int(config["short_trial"].get("records", 64))
    if limit < world_size * 2:
        raise ValueError("short_trial.records must leave room for the longest-record probe and mixed tasks")
    # First global microbatch puts the actual longest context on every rank.
    # These diagnostic repetitions are exclusive to the disposable short trial.
    selected = [longest] * world_size
    groups = {}
    for row in features:
        if row is not longest:
            groups.setdefault(row.get("task_scope", "unspecified"), []).append(row)
    for rows in groups.values():
        rows.sort(key=lambda row: (len(row["input_ids"]), row.get("record_id", "")))
    while len(selected) < limit and any(groups.values()):
        for scope in sorted(groups):
            if groups[scope] and len(selected) < limit:
                selected.append(groups[scope].pop(0))
    return selected, {"strategy": "sequential_mixed_capacity_trial", "records": len(selected),
                      "longest_record_id": longest.get("record_id"), "longest_tokens": len(longest["input_ids"]),
                      "longest_record_repetitions": world_size, "formal_task_oversampling": False,
                      "task_records": {scope: sum(row.get("task_scope", "unspecified") == scope for row in selected)
                                       for scope in sorted({row.get("task_scope", "unspecified") for row in selected})}}


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


def install_chunked_training_loss(model, chunk_tokens: int) -> None:
    """Scope projection/CE recomputation to this Qwen instance's training path.

    The official decoder receives the entire unchanged context. Projecting and
    reducing each selected hidden-state chunk together avoids both full logits
    and their full backward buffers. Evaluation/generation use native forward.
    """
    from types import MethodType
    import torch
    from torch.nn.functional import cross_entropy, pad
    from torch.utils.checkpoint import checkpoint
    from transformers.modeling_outputs import CausalLMOutputWithPast
    if type(chunk_tokens) is not int or chunk_tokens < 1:
        raise ValueError("loss_chunk_tokens must be a positive integer")
    if model.config.model_type != "qwen3":
        raise ValueError("chunked training loss requires the official Qwen3 causal model")
    original_forward = model.forward

    def forward(self, input_ids=None, attention_mask=None, position_ids=None, past_key_values=None,
                inputs_embeds=None, labels=None, use_cache=None, cache_position=None, logits_to_keep=0, **kwargs):
        if not self.training or labels is None:
            return original_forward(input_ids=input_ids, attention_mask=attention_mask, position_ids=position_ids,
                                    past_key_values=past_key_values, inputs_embeds=inputs_embeds, labels=labels,
                                    use_cache=use_cache, cache_position=cache_position,
                                    logits_to_keep=logits_to_keep, **kwargs)
        num_items_in_batch = kwargs.pop("num_items_in_batch", None)
        shift_labels = kwargs.pop("shift_labels", None)
        outputs = self.model(input_ids=input_ids, attention_mask=attention_mask, position_ids=position_ids,
                             past_key_values=past_key_values, inputs_embeds=inputs_embeds, use_cache=use_cache,
                             cache_position=cache_position, **kwargs)
        positions = slice(-logits_to_keep, None) if isinstance(logits_to_keep, int) else logits_to_keep
        selected = outputs.last_hidden_state[:, positions, :]
        targets = (pad(labels, (0, 1), value=-100)[:, 1:][:, positions]
                   if shift_labels is None else shift_labels).to(selected.device)
        if targets.shape != selected.shape[:2]:
            raise ValueError("selected hidden states and causal targets differ")
        denominator = num_items_in_batch if num_items_in_batch is not None else targets.ne(-100).sum()
        if torch.is_tensor(denominator):
            denominator = denominator.to(selected.device)
        def projected_ce(values, target):
            # Force 2-D Linear in both passes: FSDP/offload can change strides
            # and otherwise switch 3-D inputs between batched matmul and mm.
            logits = self.lm_head(values.reshape(-1, values.shape[-1]))
            return cross_entropy(logits.float().reshape(-1, self.config.vocab_size), target.reshape(-1),
                                 ignore_index=-100, reduction="sum")
        pieces = []
        for start in range(0, selected.shape[1], chunk_tokens):
            # Keep the chunk contiguous before reshaping and CPU restoration,
            # preserving the layout during PEFT/FSDP recomputation.
            values = selected[:, start:start + chunk_tokens].contiguous()
            target = targets[:, start:start + chunk_tokens]
            if torch.is_grad_enabled() and values.requires_grad:
                pieces.append(checkpoint(projected_ce, values, target, use_reentrant=False))
            else:
                pieces.append(projected_ce(values, target))
        return CausalLMOutputWithPast(loss=torch.stack(pieces).sum() / denominator,
                                     past_key_values=outputs.past_key_values,
                                     hidden_states=outputs.hidden_states, attentions=outputs.attentions)

    model.forward = MethodType(forward, model)


def sparse_trainer_class():
    import torch
    from peft import get_peft_model_state_dict
    from safetensors.torch import load_file
    from torch.utils.data import SequentialSampler
    from transformers import Trainer
    from trl import SFTTrainer

    class SparseAssistantSFTTrainer(SFTTrainer):
        def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
            inputs = dict(inputs)
            lengths = inputs.pop("_audit_lengths", None)
            evidence = getattr(self, "runtime_evidence", None)
            if evidence is not None and model.training:
                evidence["training_microbatches_per_rank"] += 1
                if lengths is not None:
                    evidence["max_training_tokens_local"] = max(evidence["max_training_tokens_local"],
                                                                 int(lengths.max()))
            # Retain HF's gradient-accumulation/global-token normalization. TRL
            # 0.28 entropy/accuracy assumes logits span the entire input, so its
            # optional metrics are bypassed rather than reporting wrong values.
            from contextlib import nullcontext
            # Non-reentrant checkpoints save their boundary inputs before
            # entering their own hooks. Offload those activations without
            # changing Qwen's decoder or the full-context loss calculation.
            offload = getattr(self, "activation_cpu_offload", False) and model.training
            # Pinned host blocks are cached by rounded size. Eight ranks with
            # varying 32k contexts exhaust host RAM across these size pools;
            # ordinary CPU tensors release their storage after backward.
            context = torch.autograd.graph.save_on_cpu(pin_memory=False) if offload else nullcontext()
            with context:
                loss, outputs = Trainer.compute_loss(self, model, assistant_loss_inputs(inputs),
                                                     return_outputs=True, num_items_in_batch=num_items_in_batch)
            if evidence is not None:
                finite = self.accelerator.reduce(torch.isfinite(loss.detach()).all().to(torch.int64), reduction="sum")
                if int(finite) != self.accelerator.num_processes:
                    raise ValueError("nonfinite loss on one or more ranks")
            return (loss, outputs) if return_outputs else loss

        def _get_train_sampler(self, train_dataset=None):
            if getattr(self, "capacity_trial", False):
                return SequentialSampler(train_dataset if train_dataset is not None else self.train_dataset)
            return super()._get_train_sampler(train_dataset)

        def save_model(self, output_dir=None, _internal_call=False):
            if _internal_call and self.is_fsdp_enabled:
                # HF's next checkpoint operation saves adapter_only FSDP weights
                # and optimizer state. Avoid a second full gather/public export.
                return
            return super().save_model(output_dir, _internal_call=_internal_call)

        def _save(self, output_dir=None, state_dict=None):
            super()._save(output_dir, state_dict)
            if getattr(self, "verify_adapter_export", False):
                model = self.accelerator.unwrap_model(self.model)
                expected = get_peft_model_state_dict(model, state_dict=state_dict)
                loaded = load_file(str(Path(output_dir) / "adapter_model.safetensors"))
                if expected.keys() != loaded.keys():
                    raise ValueError("saved/reloaded adapter tensor keys differ")
                for name, value in loaded.items():
                    if not bool(torch.isfinite(value).all()) or not torch.equal(value, expected[name].cpu()):
                        raise ValueError(f"saved/reloaded adapter tensor differs: {name}")
                self.runtime_evidence["adapter_tensor_reload"] = {
                    "status": "passed", "tensor_count": len(loaded), "all_finite": True, "exact_match": True}

        def _save_checkpoint(self, model, trial):
            super()._save_checkpoint(model, trial)
            self.accelerator.wait_for_everyone()

            path = Path(self.args.output_dir) / f"checkpoint-{self.state.global_step}"
            if self.is_world_process_zero():
                names = checkpoint_files(self.accelerator.num_processes, fsdp=self.is_fsdp_enabled)
                if any(not (path / name).is_file() or (path / name).stat().st_size == 0 for name in names):
                    raise ValueError("checkpoint save did not produce every recovery state file")
                report = {"schema": "praxis.fsdp-lora-checkpoint.v1", "training_identity": self.training_identity,
                          "world_size": self.accelerator.num_processes, "global_step": self.state.global_step,
                          "state_dict_type": "FULL_STATE_DICT", "fsdp": self.is_fsdp_enabled,
                          "files": {name: (path / name).stat().st_size for name in names}}
                temporary = path / f"{CHECKPOINT_MANIFEST}.tmp"
                temporary.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
                temporary.replace(path / CHECKPOINT_MANIFEST)
            self.accelerator.wait_for_everyone()

        def _load_rng_state(self, checkpoint):
            super()._load_rng_state(checkpoint)
            if hasattr(self, "runtime_evidence"):
                self.runtime_evidence["rng_state_restored"] = True

    return SparseAssistantSFTTrainer


def fsdp_adapter_reload_probe(trainer, plugin, checkpoint: Path, probe: dict) -> dict:
    """Prove a checkpoint restores an intentionally changed trainable LoRA shard."""
    import torch
    from accelerate.utils.fsdp_utils import load_fsdp_model

    model, accelerator = trainer.model, trainer.accelerator
    candidates = [(name, parameter) for name, parameter in model.named_parameters()
                  if "lora_B" in name and parameter.requires_grad and parameter.numel()]

    def all_ranks(condition: bool) -> bool:
        flag = torch.tensor(int(condition), dtype=torch.int64, device=accelerator.device)
        return int(accelerator.reduce(flag, reduction="sum")) == accelerator.num_processes

    if not all_ranks(bool(candidates)):
        raise ValueError("reload probe requires a nonempty trainable LoRA_B shard on every rank")
    name, parameter = sorted(candidates, key=lambda item: item[0])[0]
    original = parameter.detach().clone()
    model.eval()
    with torch.no_grad(), accelerator.autocast():
        before = model(**probe).logits.detach()
        parameter.add_(0.125)
        perturbed = model(**probe).logits.detach()
    changed = bool(torch.isfinite(before).all() and torch.isfinite(perturbed).all()
                   and not torch.equal(perturbed, before))
    if not all_ranks(changed):
        raise ValueError("reload probe LoRA_B perturbation did not change finite forward outputs on every rank")
    max_perturbed_error = float((perturbed - before).abs().max())
    del perturbed
    loaded = load_fsdp_model(plugin, accelerator, model, str(checkpoint), adapter_only=True)
    missing_lora = [key for key in getattr(loaded, "missing_keys", []) if "lora_" in key]
    unexpected = list(getattr(loaded, "unexpected_keys", []))
    if not all_ranks(not missing_lora and not unexpected):
        raise ValueError("reload probe checkpoint has missing LoRA keys or unexpected keys")
    if not all_ranks(torch.equal(parameter.detach(), original)):
        raise ValueError("reload probe did not restore the perturbed LoRA_B shard exactly")
    with torch.no_grad(), accelerator.autocast():
        after = model(**probe).logits.detach()
    if not all_ranks(torch.allclose(after, before, rtol=1e-4, atol=1e-5)):
        raise ValueError("reload probe did not restore the baseline forward outputs")
    return {"status": "passed", "checkpoint": str(checkpoint), "perturbed_parameter": name,
            "perturbation_delta": 0.125, "perturbation_detected": True, "restored_shard": True,
            "restored_forward": True, "missing_lora_keys": missing_lora, "unexpected_keys": unexpected,
            "max_perturbed_logit_error": max_perturbed_error,
            "max_logit_error": float((after - before).abs().max())}


def _training_loss_fields(trainer, hf_loss: float) -> dict:
    steps = trainer.state.global_step - trainer.runtime_evidence["resumed_global_step"]
    loss_sum = float(trainer._total_loss_scalar)
    return {"train_loss": float(hf_loss), "train_loss_this_run": loss_sum / steps,
            "loss_sum_this_run": loss_sum, "optimizer_steps_this_run": steps,
            "train_loss_normalization": {
                "train_loss": "HF current-invocation loss sum / cumulative global_step",
                "train_loss_this_run": "current-invocation loss sum / optimizer_steps_this_run"}}


def runtime_audit_callback(trainer, *, stop_after_steps: int | None = None):
    import torch
    from transformers import TrainerCallback

    class RuntimeAuditCallback(TrainerCallback):
        def on_train_begin(self, args, state, control, model=None, optimizer=None, **kwargs):
            self.samples = {}
            self.previous_microbatches = 0
            trainer.runtime_evidence["microbatches_per_optimizer_step"] = []
            for name, parameter in model.named_parameters():
                if parameter.requires_grad and parameter.numel():
                    indices = torch.linspace(0, parameter.numel() - 1, min(64, parameter.numel()),
                                             device=parameter.device).long().unique()
                    self.samples[name] = (indices, parameter.detach().flatten()[indices].clone())
            trainer.runtime_evidence["resumed_global_step"] = state.global_step
            if state.global_step:
                states = list(optimizer.state.values())
                steps = [float(value["step"]) for value in states if "step" in value]
                if not steps or min(steps) != state.global_step:
                    raise ValueError("resume did not restore Adam optimizer step state")
                moments = [value["exp_avg"] for value in states if "exp_avg" in value]
                local_moments = torch.stack((torch.stack([torch.isfinite(value).all() for value in moments]).all(),
                                             torch.stack([value.ne(0).any() for value in moments]).any())).to(torch.int64)
                restored_flags = trainer.accelerator.reduce(local_moments, reduction="sum")
                if int(restored_flags[0]) != trainer.accelerator.num_processes or int(restored_flags[1]) == 0:
                    raise ValueError("resume restored invalid or globally empty optimizer moments")
                trainer.runtime_evidence["optimizer_state_restored"] = {
                    "parameter_states": len(states), "minimum_step": min(steps), "maximum_step": max(steps),
                    "moments_finite": True, "nonzero_moments_restored": True}
                if trainer.lr_scheduler.state_dict().get("last_epoch") != state.global_step:
                    raise ValueError("resume did not restore scheduler progress")
                trainer.runtime_evidence["scheduler_state_restored"] = True

        def on_pre_optimizer_step(self, args, state, control, model=None, **kwargs):
            observed = trainer.runtime_evidence["training_microbatches_per_rank"]
            trainer.runtime_evidence["microbatches_per_optimizer_step"].append(observed - self.previous_microbatches)
            self.previous_microbatches = observed
            gradients = [parameter.grad for parameter in model.parameters()
                         if parameter.requires_grad and parameter.grad is not None]
            if not gradients:
                local = torch.zeros(2, dtype=torch.int64, device=trainer.accelerator.device)
            else:
                local = torch.stack((torch.stack([torch.isfinite(g).all() for g in gradients]).all(),
                                     torch.stack([g.ne(0).any() for g in gradients]).any())).to(torch.int64)
            global_flags = trainer.accelerator.reduce(local, reduction="sum")
            if int(global_flags[0]) != trainer.accelerator.num_processes or int(global_flags[1]) == 0:
                raise ValueError("optimizer received nonfinite or globally empty/zero LoRA gradients")
            trainer.runtime_evidence["finite_gradient_checks"] += 1

        def on_optimizer_step(self, args, state, control, model=None, **kwargs):
            parameters = dict(model.named_parameters())
            changes = [parameters[name].detach().flatten()[indices].sub(before).abs().max()
                       for name, (indices, before) in self.samples.items()]
            largest = torch.stack(changes).max() if changes else torch.zeros((), device=trainer.accelerator.device)
            gathered = trainer.accelerator.gather(largest.reshape(1))
            trainer.runtime_evidence["max_sampled_lora_update"] = max(
                trainer.runtime_evidence["max_sampled_lora_update"], float(gathered.max()))

        def on_step_end(self, args, state, control, **kwargs):
            if stop_after_steps is not None and state.global_step >= stop_after_steps:
                control.should_training_stop = True
            return control

    return RuntimeAuditCallback()


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
    max_loss_error, max_gradient_error, comparisons, cases, chunk_cases, offload_cases = 0.0, 0.0, 0, 0, 0, 0
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
                    chunked = deepcopy(base)
                    chunked.train()
                    loss_model = chunked.get_base_model() if peft_model else chunked
                    install_chunked_training_loss(loss_model, 3)
                    chunk_loss = trainer_type.compute_loss(state, chunked, batch, num_items_in_batch=denominator)
                    torch.testing.assert_close(chunk_loss, ordinary.loss, rtol=3e-5, atol=2e-6)
                    chunk_loss.backward()
                    other = dict(chunked.named_parameters())
                    for name, parameter in full.named_parameters():
                        if parameter.grad is not None:
                            torch.testing.assert_close(other[name].grad, parameter.grad, rtol=3e-5, atol=2e-6)
                            max_gradient_error = max(max_gradient_error, float((other[name].grad - parameter.grad).abs().max()))
                            comparisons += 1
                    max_loss_error = max(max_loss_error, float((chunk_loss - ordinary.loss).detach().abs()))
                    chunk_cases += 1
                    offloaded = deepcopy(base)
                    offloaded.train()
                    offloaded.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
                    install_chunked_training_loss(offloaded.get_base_model() if peft_model else offloaded, 3)
                    state.activation_cpu_offload = True
                    offload_loss = trainer_type.compute_loss(state, offloaded, batch, num_items_in_batch=denominator)
                    state.activation_cpu_offload = False
                    torch.testing.assert_close(offload_loss, ordinary.loss, rtol=3e-5, atol=2e-6)
                    offload_loss.backward()
                    other = dict(offloaded.named_parameters())
                    for name, parameter in full.named_parameters():
                        if (parameter.grad is None) != (other[name].grad is None):
                            raise ValueError("full_and_offloaded_gradient_presence_differs")
                        if parameter.grad is not None:
                            torch.testing.assert_close(other[name].grad, parameter.grad, rtol=3e-5, atol=2e-6)
                            max_gradient_error = max(max_gradient_error, float((other[name].grad - parameter.grad).abs().max()))
                            comparisons += 1
                    max_loss_error = max(max_loss_error, float((offload_loss - ordinary.loss).detach().abs()))
                    offload_cases += 1
    finally:
        torch.set_num_threads(previous_threads)
    return {"status": "passed", "model": "random_tiny_Qwen3", "device": "cpu", "numeric_cases": cases,
            "parameter_gradient_comparisons": comparisons, "max_loss_absolute_error": max_loss_error,
            "max_gradient_absolute_error": max_gradient_error, "full_context_preserved": True,
            "dense_and_peft_checked": True, "chunked_numeric_cases": chunk_cases,
            "activation_offload_numeric_cases": offload_cases, "nonreentrant_checkpoint_checked": True,
            "activation_offload_pin_memory": False,
            "optimizer_steps": 0}


def validate_memory_guard(*, cgroup_root="/sys/fs/cgroup", proc_cgroup="/proc/self/cgroup",
                          meminfo="/proc/meminfo") -> dict:
    """Require real cgroup-v2 limits before any large-model operation."""
    if sys.platform != "linux":
        raise ValueError("large-model operations require the Linux cgroup memory guard")
    root = Path(cgroup_root).resolve()
    try:
        paths = [line[3:] for line in Path(proc_cgroup).read_text().splitlines() if line.startswith("0::")]
        if len(paths) != 1 or not paths[0].startswith("/"):
            raise ValueError("memory guard requires one unified cgroup-v2 path")
        cgroup = (root / paths[0].lstrip("/")).resolve()
        if not cgroup.is_relative_to(root):
            raise ValueError("memory guard cgroup path escapes the mounted hierarchy")
        names = ("memory.max", "memory.high", "memory.swap.max", "memory.oom.group")
        values = {name: int((cgroup / name).read_text().strip()) for name in names}
        available = next(line.split() for line in Path(meminfo).read_text().splitlines()
                         if line.startswith("MemAvailable:"))
        if len(available) != 3 or available[2] != "kB":
            raise ValueError("memory guard requires MemAvailable in kB")
        available_bytes = int(available[1]) * 1024
    except (OSError, ValueError, StopIteration) as error:
        raise ValueError(f"memory guard requires readable, bounded cgroup-v2 limits: {error}") from error
    if (not 0 < values["memory.max"] <= 300 * 1024**3
            or not 0 < values["memory.high"] <= 260 * 1024**3
            or values["memory.swap.max"] != 0 or values["memory.oom.group"] != 1):
        raise ValueError("memory guard requires max<=300GiB, high<=260GiB, swap=0 and oom.group=1")
    if available_bytes < 160 * 1024**3:
        raise ValueError("memory guard requires at least 160GiB host MemAvailable before model loading")
    return {"cgroup_path": str(cgroup), "memory_max_bytes": values["memory.max"],
            "memory_high_bytes": values["memory.high"], "memory_swap_max_bytes": values["memory.swap.max"],
            "memory_oom_group": values["memory.oom.group"], "host_mem_available_bytes": available_bytes}


def validate_runtime(config: dict) -> dict:
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
    return validate_memory_guard()


def run_model(config: dict, features: list[dict], tokenizer, *, forward_only: bool = False,
              max_steps: int | None = None, resume_from_checkpoint: str | None = None,
              stop_after_steps: int | None = None, data_sha256: str = "", checkpoint_smoke: bool = False) -> dict:
    """Explicit large-model operation; caller must have completed mask preflight."""
    if checkpoint_smoke and (forward_only or any(value is not None for value in
                                               (max_steps, resume_from_checkpoint, stop_after_steps))):
        raise ValueError("checkpoint smoke cannot use forward-only or training progress/resume options")
    memory_guard = validate_runtime(config)
    if not features or tokenizer is None:
        raise ValueError("model operation requires tokenized and mask-checked training data")
    if max_steps is not None and (type(max_steps) is not int or max_steps < 1):
        raise ValueError("max_steps must be a positive integer")
    if stop_after_steps is not None and (type(stop_after_steps) is not int or stop_after_steps < 1):
        raise ValueError("stop_after_steps must be a positive absolute optimizer step")
    features, sampling_report = select_training_features(config, features)
    training = dict(config["training"])
    if max_steps is not None:
        training["max_steps"] = max_steps
    effective_config = {**config, "training": training}
    identity = training_identity(effective_config, data_sha256, features)
    output = Path(config["output_dir"])
    resume_report = None
    if resume_from_checkpoint:
        if forward_only:
            raise ValueError("resume requires training, not forward-only preflight")
        resume_report = validate_resume_checkpoint(resume_from_checkpoint, output, identity)
        if stop_after_steps is not None and stop_after_steps <= resume_report["global_step"]:
            raise ValueError("stop_after_steps must exceed the resumed step")
    elif not forward_only and output.exists() and any(output.iterdir()):
        raise ValueError("output_dir is not empty; select a completed checkpoint to resume or choose a new directory")
    # Local checkpoint and packages only. No hub download or telemetry is needed.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from peft.helpers import disable_input_dtype_casting
    from peft.utils.other import fsdp_auto_wrap_policy
    from transformers import AutoModelForCausalLM, set_seed
    from trl import SFTConfig
    from trl.trainer.sft_trainer import DataCollatorForLanguageModeling

    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise ValueError("CUDA with native BF16 support is required")
    if (training.get("save_strategy") != "steps" or training.get("save_only_model") is not False
            or not isinstance(training.get("save_steps"), int) or training["save_steps"] < 1
            or training.get("eval_strategy") != "no" or training.get("report_to") != "none"):
        raise ValueError("training requires recovery checkpoints, no Trainer eval and no remote reporting")
    if config.get("short_trial") and (training.get("warmup_ratio") != 0 or
                                      not 10 <= training.get("max_steps", -1) <= 20):
        raise ValueError("short_trial requires zero warmup and 10–20 optimizer steps")
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
    if config.get("loss_chunk_tokens"):
        install_chunked_training_loss(model, config["loss_chunk_tokens"])
    if model.config.model_type != "qwen3":
        raise ValueError("checkpoint must be the official dense Qwen3 causal language model")
    lora = LoraConfig(task_type="CAUSAL_LM", bias="none", **config["lora"])
    collator = DataCollatorForLanguageModeling(pad_token_id=tokenizer.pad_token_id,
                                             completion_only_loss=False)
    def audited_collator(rows):
        batch = collator(rows)
        batch["_audit_lengths"] = torch.tensor([len(row["input_ids"]) for row in rows], dtype=torch.long)
        return batch
    trainer = sparse_trainer_class()(
        model=model, args=args, train_dataset=Dataset.from_list(features),
        processing_class=tokenizer, peft_config=lora, data_collator=audited_collator,
    )
    plugin = getattr(trainer.accelerator.state, "fsdp_plugin", None)
    if plugin is None or not trainer.is_fsdp_enabled or plugin.use_orig_params:
        raise ValueError("PEFT requires the configured FSDP plugin with use_orig_params=false")
    plugin.auto_wrap_policy = fsdp_auto_wrap_policy(trainer.model)
    if "FULL_STATE_DICT" not in str(plugin.state_dict_type):
        raise ValueError("the pinned recovery recipe requires FULL_STATE_DICT for optimizer restoration")
    trainer.training_identity = identity
    trainer.activation_cpu_offload = bool(config.get("activation_cpu_offload", False))
    trainer.capacity_trial = bool(config.get("short_trial"))
    trainer.runtime_evidence = {"training_microbatches_per_rank": 0, "max_training_tokens_local": 0,
                                "finite_gradient_checks": 0, "max_sampled_lora_update": 0.0,
                                "gradient_accumulation_steps": args.gradient_accumulation_steps,
                                "rng_state_restored": False}
    trainer.add_callback(runtime_audit_callback(trainer, stop_after_steps=stop_after_steps))
    trainable = sum(p.numel() for p in trainer.model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in trainer.model.parameters())
    if (not trainable or trainable >= total or any("lora_" not in name for name, parameter
                                                 in trainer.model.named_parameters() if parameter.requires_grad)):
        raise ValueError("only nonempty LoRA adapter parameters may be trainable")
    report = {"base_model": config["model_id"], "precision": "bf16", "attention": "sdpa",
              "world_size": trainer.accelerator.num_processes, "trainable_parameters": trainable,
              "total_parameters": total, "native_template_unchanged": True,
              "base_parameters_frozen": True,
              "heldout_inputs_used_for_training": False, "loss": "checkpointed_chunked_sparse_assistant_causal_CE",
              "loss_chunk_tokens": config.get("loss_chunk_tokens"),
              "fsdp_bf16_lora_inputs": bool(config.get("fsdp_bf16_lora_inputs")),
              "chunked_output_projection": bool(config.get("loss_chunk_tokens")),
              "activation_cpu_offload": trainer.activation_cpu_offload,
              "activation_cpu_offload_pin_memory": False,
              "full_context_preserved": True, "sampling": sampling_report, "training_identity": identity,
              "memory_guard": memory_guard}
    torch.cuda.reset_peak_memory_stats()
    if checkpoint_smoke:
        from accelerate.utils.fsdp_utils import save_fsdp_model
        accelerator = trainer.accelerator
        model = accelerator.prepare_model(trainer.model)
        trainer.model = trainer.model_wrapped = model
        smoke_dir = output / "checkpoint-smoke"
        save_fsdp_model(plugin, accelerator, model, str(smoke_dir), adapter_only=True)
        accelerator.wait_for_everyone()
        valid, tensor_count = True, 0
        if accelerator.is_main_process:
            try:
                weights_path = smoke_dir / "pytorch_model_fsdp.bin"
                if not weights_path.is_file() or not weights_path.stat().st_size:
                    raise ValueError("checkpoint smoke produced no nonempty FSDP weights file")
                weights = torch.load(weights_path, map_location="cpu", weights_only=True)
                tensor_count = len(weights)
                valid = bool(weights) and all(isinstance(name, str) and "lora_" in name
                                             and torch.is_tensor(value) and bool(torch.isfinite(value).all())
                                             for name, value in weights.items())
                del weights
            except Exception:
                # Propagate rank-0 validation failure through the collective,
                # rather than leaving other ranks waiting at a later barrier.
                valid = False
        checked = accelerator.reduce(torch.tensor([int(valid), tensor_count], dtype=torch.int64,
                                                   device=accelerator.device), reduction="sum")
        if int(checked[0]) != accelerator.num_processes:
            raise ValueError("checkpoint smoke requires finite, nonempty LoRA-only FSDP weights")
        probe = collator([min(features, key=lambda row: len(row["input_ids"]))])
        probe = assistant_loss_inputs({key: value.to(accelerator.device) for key, value in probe.items()})
        restored = fsdp_adapter_reload_probe(trainer, plugin, smoke_dir, probe)
        accelerator.wait_for_everyone()
        peaks = accelerator.gather(torch.tensor([torch.cuda.max_memory_allocated()],
                                               device=accelerator.device)).cpu().tolist()
        report.update(status="checkpoint_smoke_passed", optimizer_steps=0, backward_runs=0,
                      saved_adapter=False, resumable_checkpoint=False, fsdp_adapter_weights_saved=True,
                      weights_only_smoke_dir=str(smoke_dir), fsdp_adapter_tensor_count=int(checked[1]),
                      fsdp_adapter_weights_only_lora=True, fsdp_adapter_weights_finite=True,
                      fsdp_adapter_reload_forward=restored,
                      peak_allocated_GiB_per_rank=[round(value / 1024**3, 3) for value in peaks])
        accelerator.end_training()
        return report
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
    # FSDP's child LoRA Linear wrappers cast weights to BF16. The parent PEFT
    # layer sees FP32 master views before those child hooks and would otherwise
    # allocate FP32 long MLP inputs/dropout; the official helper defers to FSDP.
    with disable_input_dtype_casting(trainer.model, active=bool(config.get("fsdp_bf16_lora_inputs"))):
        result = trainer.train(resume_from_checkpoint=resume_from_checkpoint)
    checkpoint = output / f"checkpoint-{trainer.state.global_step}"
    if not (checkpoint / CHECKPOINT_MANIFEST).is_file():
        trainer._save_checkpoint(trainer.model, None)
    maxima = trainer.accelerator.gather(torch.tensor([trainer.runtime_evidence["max_training_tokens_local"]],
                                                    device=trainer.accelerator.device)).cpu().tolist()
    trainer.runtime_evidence["max_training_tokens_per_rank"] = maxima
    trainer.runtime_evidence["backward_microbatches_per_rank"] = trainer.runtime_evidence["training_microbatches_per_rank"]
    if trainer.runtime_evidence["max_sampled_lora_update"] <= 0:
        raise ValueError("optimizer steps completed without a measurable LoRA weight update")
    if config.get("short_trial") and any(value != sampling_report["longest_tokens"] for value in maxima):
        raise ValueError("short trial did not backpropagate the longest sample on every rank")
    if config.get("short_trial") and any(value != args.gradient_accumulation_steps
                                         for value in trainer.runtime_evidence["microbatches_per_optimizer_step"]):
        raise ValueError("short trial did not execute the configured gradient accumulation on every optimizer step")
    if resume_from_checkpoint and not trainer.runtime_evidence["rng_state_restored"]:
        raise ValueError("resume did not restore RNG state")
    # Final public export is separate from resumable Trainer checkpoints.
    adapter_output = output / "adapter"
    trainer.verify_adapter_export = True
    plugin.set_state_dict_type("FULL_STATE_DICT")
    trainer.save_model(str(adapter_output))
    if config.get("short_trial"):
        probe = collator([min(features, key=lambda row: len(row["input_ids"]))])
        probe = assistant_loss_inputs({key: value.to(trainer.accelerator.device) for key, value in probe.items()})
        trainer.runtime_evidence["fsdp_adapter_reload_forward"] = fsdp_adapter_reload_probe(
            trainer, plugin, checkpoint, probe)
    trainer.accelerator.wait_for_everyone()
    peaks = trainer.accelerator.gather(torch.tensor([torch.cuda.max_memory_allocated()],
                                                   device=trainer.accelerator.device)).cpu().tolist()
    report.update(status="stopped_at_checkpoint" if stop_after_steps else "trained",
                  optimizer_steps=trainer.state.global_step, saved_adapter=True,
                  output_dir=str(output), adapter_dir=str(adapter_output), resumable_checkpoint=str(checkpoint),
                  resumed_from=resume_from_checkpoint, runtime_evidence=trainer.runtime_evidence,
                  peak_allocated_GiB_per_rank=[round(value / 1024**3, 3) for value in peaks])
    report.update(_training_loss_fields(trainer, result.training_loss))
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
    result.add_argument("--checkpoint-smoke", action="store_true",
                        help="Explicitly load the model for cold FSDP LoRA weights save/reload; no training")
    result.add_argument("--max-steps", type=int, help="Optional explicit short training run; requires --train")
    result.add_argument("--resume-from-checkpoint", help="Completed checkpoint-N in output_dir; requires --train")
    result.add_argument("--stop-after-steps", type=int, help="Stop at an absolute optimizer step, retaining the full schedule")
    result.add_argument("--report", help="Optional local readiness/result JSON path")
    return result


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    if args.checkpoint_smoke and (args.train or args.schema_only):
        raise ValueError("--checkpoint-smoke requires full preflight and cannot combine with --train or --schema-only")
    if args.train and args.schema_only or any(value is not None for value in
                                            (args.max_steps, args.resume_from_checkpoint, args.stop_after_steps)) and not args.train:
        raise ValueError("--train requires full preflight; --max-steps requires explicit --train")
    config = load_config(args.config, model_dir=args.model_dir, data_dir=args.data_dir, output_dir=args.output_dir,
                         max_length=args.max_length)
    report, features, tokenizer = preflight(config, schema_only=args.schema_only)
    if args.checkpoint_smoke:
        report["checkpoint_smoke"] = run_model(config, features, tokenizer, checkpoint_smoke=True,
                                               data_sha256=report["training_data_sha256"])
        report["large_model_loaded"] = True
    if args.train:
        report["training"] = run_model(config, features, tokenizer, max_steps=args.max_steps,
                                       resume_from_checkpoint=args.resume_from_checkpoint,
                                       stop_after_steps=args.stop_after_steps,
                                       data_sha256=report["training_data_sha256"])
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
