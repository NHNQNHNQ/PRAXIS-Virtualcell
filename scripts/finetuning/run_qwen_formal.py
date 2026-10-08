#!/usr/bin/env python3
"""Run the authorized first epoch as guarded three-step checkpoint segments.

The controller reads only small manifests/reports/checkpoint metadata. Run it in
a persistent systemd user unit; each training segment gets a separate capped
unit through guard_qwen_trial.py. A failed segment stops the pipeline immediately.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import signal
import subprocess
import sys
import uuid

import yaml

from preflight_qwen import load_config
from train_qwen_lora import validate_resume_checkpoint


def _write(path, report):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def plan(config, manifest, world_size=8):
    training = config["training"]
    records = manifest["files"]["train.jsonl"]["records"]
    if (records != 7193 or manifest.get("training_record_count") != records or world_size != 8
            or config.get("short_trial") or training["num_train_epochs"] != 1
            or training["per_device_train_batch_size"] != 1 or training["gradient_accumulation_steps"] != 4
            or training.get("dataloader_drop_last", False)
            or training["save_steps"] != 3 or training["logging_steps"] != 1):
        raise ValueError("formal runner requires 7193 records, one epoch, eight ranks, batch1/accum4 and save3/log1")
    microbatches = math.ceil(records / world_size)
    steps = math.ceil(microbatches / training["gradient_accumulation_steps"])
    if training.get("max_steps") != steps:
        raise ValueError("formal max_steps must equal the complete one-epoch schedule")
    return {"records": records, "world_size": world_size, "microbatches_per_rank": microbatches,
            "optimizer_steps": steps, "rank_padding_slots": microbatches * world_size - records,
            "train_sha256": manifest["files"]["train.jsonl"]["sha256"], "segment_steps": 3}


def run(args):
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = load_config(config_path)
    manifest = json.loads((Path(config["data_dir"]) / "manifest.json").read_text())
    fsdp_path = root / "configs/finetuning/fsdp_a100_8gpu.yaml"
    schedule = plan(config, manifest, yaml.safe_load(fsdp_path.read_text())["num_processes"])
    output = Path(config["output_dir"])
    start, identity, checkpoint = 0, None, None
    if args.resume_from_checkpoint:
        checkpoint = (args.resume_from_checkpoint if args.resume_from_checkpoint.is_absolute()
                      else root / args.resume_from_checkpoint).resolve()
        marker = json.loads((checkpoint / "praxis_checkpoint.json").read_text())
        identity = marker["training_identity"]
        start = validate_resume_checkpoint(checkpoint, output, identity)["global_step"]
        if not 0 < start < schedule["optimizer_steps"] or start % 3:
            raise ValueError("formal restart requires a completed intermediate three-step checkpoint")
    elif output.exists() and any(output.iterdir()):
        raise ValueError("fresh formal training requires an empty output; restart needs an explicit completed checkpoint")
    reports = args.reports if args.reports.is_absolute() else root / args.reports
    if reports.exists() and any(reports.iterdir()):
        raise ValueError("use a new reports directory to preserve previous segment evidence")
    state = {"schema": "praxis.qwen-formal-segments.v1", "status": "planned", "schedule": schedule,
             "output_dir": str(output), "completed_optimizer_steps": start, "segments": [],
             "started_at": datetime.now(timezone.utc).isoformat()}
    if args.plan_only:
        print(json.dumps(state))
        return 0
    reports.mkdir(parents=True, exist_ok=True)
    # Freeze this small recipe; weights and datasets stay at their original paths.
    recipe = reports / "recipe.yaml"
    recipe.write_text(yaml.safe_dump(config, sort_keys=False))
    state["recipe_sha256"] = hashlib.sha256(recipe.read_bytes()).hexdigest()
    state_path = reports / "runner.json"
    _write(state_path, state)
    process, stop_sent = None, False

    def interrupted(signum, _frame):
        nonlocal stop_sent
        for item in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            signal.signal(item, signal.SIG_IGN)
        if process is not None and process.poll() is None:
            process.send_signal(signal.SIGTERM)
            stop_sent = True
        raise RuntimeError(f"formal runner interrupted by {signal.Signals(signum).name}")

    old_handlers = {item: signal.signal(item, interrupted)
                    for item in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)}
    try:
        for target in range(start + 3, schedule["optimizer_steps"] + 1, 3):
            segment = {"from_step": start, "through_step": target, "status": "running"}
            state["segments"].append(segment)
            state["status"] = "running"
            _write(state_path, state)
            train_report, guard_report = reports / f"step-{target}.train.json", reports / f"step-{target}.guard.json"
            command = [sys.executable, "-m", "accelerate.commands.launch", "--config_file", str(fsdp_path),
                       str(root / "scripts/finetuning/train_qwen_lora.py"), "--config", str(recipe), "--train",
                       "--max-steps", str(schedule["optimizer_steps"]), "--stop-after-steps", str(target),
                       "--report", str(train_report)]
            if checkpoint is not None:
                validate_resume_checkpoint(checkpoint, output, identity)
                command += ["--resume-from-checkpoint", str(checkpoint)]
            unit = f"praxis-qwen-formal-{uuid.uuid4().hex[:12]}"
            segment.update(unit=unit + ".service", guard_report=str(guard_report), train_report=str(train_report))
            _write(state_path, state)
            guard_command = [sys.executable, str(root / "scripts/finetuning/guard_qwen_trial.py"),
                             "--unit", unit, "--report", str(guard_report), "--working-directory", str(root),
                             "--max-seconds", str(args.max_seconds), "--max-memory-gib", "300",
                             "--high-memory-gib", "260", "--min-host-available-gib", "160", "--", *command]
            process = subprocess.Popen(guard_command, cwd=root)
            code = process.wait(timeout=args.max_seconds + 25)
            process = None
            guarded = json.loads(guard_report.read_text())
            if (code or guarded.get("outcome") != "success" or not guarded.get("limits_verified")
                    or not guarded.get("gate_released") or not guarded.get("cleanup_owned_unit")
                    or any(guarded.get("memory_events", {}).get(event, 0) for event in ("high", "max", "oom", "oom_kill"))):
                raise RuntimeError(f"segment {target} failed or exceeded its resource limits: {guarded.get('outcome')}")
            result = json.loads(train_report.read_text())
            trained, evidence = result["training"], result["training"]["runtime_evidence"]
            expected_steps = target - start
            if (result["record_count"] != schedule["records"] or result["training_data_sha256"] != schedule["train_sha256"]
                    or trained["optimizer_steps"] != target or not trained.get("saved_adapter")
                    or evidence["resumed_global_step"] != start or evidence["finite_gradient_checks"] != expected_steps
                    or evidence["training_microbatches_per_rank"] != expected_steps * 4
                    or evidence["microbatches_per_optimizer_step"] != [4] * expected_steps
                    or evidence["max_sampled_lora_update"] <= 0
                    or start and not (evidence.get("rng_state_restored") and evidence.get("scheduler_state_restored")
                                      and evidence.get("optimizer_state_restored", {}).get("nonzero_moments_restored"))):
                raise RuntimeError("segment did not prove unchanged data, finite updates, accumulation and full restoration")
            checkpoint = output / f"checkpoint-{target}"
            identity = identity or trained["training_identity"]
            validate_resume_checkpoint(checkpoint, output, identity)
            if trained["training_identity"] != identity or Path(trained["resumable_checkpoint"]).resolve() != checkpoint.resolve():
                raise RuntimeError("segment changed recipe identity or checkpoint destination")
            segment.update(status="complete", checkpoint=str(checkpoint), guard_outcome=guarded["outcome"],
                           cgroup_peak_gib=guarded["cgroup_peak_gib"], train_loss_this_run=trained["train_loss_this_run"])
            start = target
            state["completed_optimizer_steps"] = start
            _write(state_path, state)
        state["status"] = "complete"
        state["final_checkpoint"] = str(checkpoint)
        state["adapter_dir"] = str(output / "adapter")
    except (Exception, KeyboardInterrupt) as error:
        for item in old_handlers:
            signal.signal(item, signal.SIG_IGN)
        if process is not None and process.poll() is None:
            if not stop_sent:
                process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=25)
            except subprocess.TimeoutExpired:
                state["guard_cleanup_unconfirmed"] = True
        state.update(status="failed", failure_reason=str(error))
        if state["segments"]:
            state["segments"][-1]["status"] = "failed"
    finally:
        for item, handler in old_handlers.items():
            signal.signal(item, handler)
        state["finished_at"] = datetime.now(timezone.utc).isoformat()
        _write(state_path, state)
    print(json.dumps(state, allow_nan=False))
    return 0 if state["status"] == "complete" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/finetuning/qwen3_32b_joint_lora_v4_compact.yaml"))
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--resume-from-checkpoint", type=Path)
    parser.add_argument("--max-seconds", type=int, default=2400)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)
    if not 0 < args.max_seconds <= 2400:
        parser.error("each segment requires 0 < max-seconds <= 2400")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
