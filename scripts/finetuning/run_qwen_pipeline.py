#!/usr/bin/env python3
"""Run the frozen baseline, bounded formal SFT, and matched validation in order.

The controller reads public pilot files and completed result receipts. Only the
separate scorer opens heldout MIC labels, after a prediction file is complete.
Run this controller in a persistent, small systemd user service. Every GPU
worker has its own verified memory guard and a 40-minute maximum lifetime.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def completed_count(inputs, output):
    expected = {row["record_id"] for row in rows(inputs)}
    if len(expected) != len(rows(inputs)) or not expected:
        raise ValueError("pilot_ids_must_be_unique_and_nonempty")
    predictions = rows(output) if Path(output).exists() else []
    supplied = {row["record_id"] for row in predictions}
    if len(supplied) != len(predictions) or not supplied <= expected:
        raise ValueError("duplicate_or_unknown_prediction")
    return len(supplied), len(expected)


def checked_command(command, *, cwd, timeout=None):
    """Allow an interrupted controller to stop the guard and its owned GPU unit."""
    process = subprocess.Popen(command, cwd=cwd)
    try:
        code = process.wait(timeout=timeout)
        if code:
            raise RuntimeError(f"command_failed_exit_{code}: {command[1]}")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=25)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def evaluation_worker(args):
    """Keep the model server and predictor in the same bounded worker cgroup."""
    scripts = args.root / "scripts/finetuning"
    command = [sys.executable, "-u", str(scripts / "serve_qwen_adapter.py"),
               "--base-dir", str(args.root / "models/Qwen3-32B"),
               "--model-name", args.model, "--port", str(args.port)]
    if args.adapter:
        command += ["--adapter-dir", str(args.adapter)]
    server = subprocess.Popen(command, cwd=args.root)
    try:
        deadline = time.monotonic() + 300
        while True:
            if server.poll() is not None:
                raise RuntimeError("model_server_exited_before_ready")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{args.port}/health", timeout=2) as response:
                    health = json.load(response)
                if health.get("model") != args.model or health.get("adapter_loaded") is not bool(args.adapter):
                    raise RuntimeError("model_server_identity_mismatch")
                break
            except (OSError, TimeoutError):
                if time.monotonic() >= deadline:
                    raise RuntimeError("model_server_readiness_timeout") from None
                time.sleep(1)
        # Startup <=300s + soft work <=1050s + one last record <=900s + cleanup
        # fits below the guard's 2400s hard deadline. Inputs are never truncated.
        predictor = [sys.executable, "-u", str(scripts / "predict_qwen.py"),
                     "--inputs", str(args.inputs), "--output", str(args.output),
                     "--model", args.model, "--base-url", f"http://127.0.0.1:{args.port}",
                     "--data-root", str(args.root / "runtime/data/organisms"),
                     "--max-turns", "4", "--max-tokens", "12288",
                     "--max-seconds", "1050", "--record-timeout-seconds", "900"]
        if args.output.with_name(args.output.name + ".run.json").is_file():
            predictor.append("--resume")
        checked_command(predictor, cwd=args.root)
        if any(row.get("service_error", {}).get("error") == "cuda_out_of_memory" for row in rows(args.output)):
            raise RuntimeError("evaluation_gpu_oom_requires_review")
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()


def evaluate(args, label, inputs, *, adapter=None):
    output = args.reports / f"{label}.predictions.jsonl"
    model = "qwen3-praxis-base" if adapter is None else "qwen3-praxis-sft-v4"
    while True:
        count, total = completed_count(inputs, output)
        if count == total:
            return output
        guard_report = args.reports / f"{label}.segment-{count:03d}.guard.json"
        if guard_report.exists():
            raise RuntimeError("previous_segment_requires_review_before_retry")
        worker = [sys.executable, "-u", str(Path(__file__).resolve()), "--worker",
                  "--root", str(args.root), "--inputs", str(inputs), "--output", str(output),
                  "--model", model, "--port", str(args.port)]
        if adapter:
            worker += ["--adapter", str(adapter)]
        checked_command([sys.executable, "-u", str(args.root / "scripts/finetuning/guard_qwen_trial.py"),
                         "--working-directory", str(args.root), "--report", str(guard_report),
                         "--max-seconds", "2400", "--", *worker], cwd=args.root)
        guard = json.loads(guard_report.read_text())
        if guard.get("outcome") != "success" or guard.get("memory_events", {}).get("oom_kill", 0):
            raise RuntimeError("evaluation_guard_failed")
        after, _ = completed_count(inputs, output)
        if after <= count:
            raise RuntimeError("evaluation_segment_made_no_progress")


def score(args, label, predictions):
    output = args.reports / f"{label}.score.json"
    if not output.exists():
        checked_command([sys.executable, str(args.root / "scripts/datasets/score_qwen.py"),
                         "--dataset-dir", str(args.scoring_dataset), "--split", "validation",
                         "--predictions", str(predictions), "--audit", str(args.audit),
                         "--source-path-map", str(args.source_path_map), "--pilot-subset",
                         "--report", str(output)], cwd=args.root)
    return output


def compare_results(reports):
    from praxis_virtualcell.datasets.qwen_evaluation import _metrics

    scores = {label: json.loads((reports / f"{label}.score.json").read_text())
              for label in ("baseline", "sft", "sft_without_omics", "sft_without_structure")}
    full = {row["record_id"]: row for row in scores["sft"]["cases"]}
    base_ids = {row["record_id"] for row in scores["baseline"]["cases"]}
    if base_ids != set(full):
        raise ValueError("before_after_case_identity_mismatch")
    comparisons = {}
    for label in ("sft_without_omics", "sft_without_structure"):
        omitted = scores[label]["cases"]
        identifiers = {row["record_id"] for row in omitted}
        if not identifiers <= set(full):
            raise ValueError("ablation_case_identity_mismatch")
        comparisons[label] = {"paired_case_count": len(identifiers),
                              "full_inputs": _metrics([full[value] for value in sorted(identifiers)]),
                              "ablated_inputs": _metrics(omitted)}
    result = {"schema_version": "praxis.qwen-paired-comparison.v1", "status": "completed",
              "baseline": scores["baseline"]["metrics"], "sft": scores["sft"]["metrics"],
              "paired_ablations": comparisons, "heldout_mechanism_gold_count": 0,
              "mechanism_accuracy": None,
              "limitations": ["This fixed pilot is a development validation subset, not the final test set.",
                              "Omission comparisons report MIC error and coverage on the same cases; changes alone do not prove biological causality.",
                              "Mechanism accuracy remains unmeasured without independently reviewed heldout labels."]}
    result["generation_validation"] = {}
    for label in scores:
        predictions = rows(reports / f"{label}.predictions.jsonl")
        result["generation_validation"][label] = {
            "status_counts": dict(Counter(row.get("status") for row in predictions)),
            "platform_eligible_count": sum(row.get("platform_eligible") is True for row in predictions),
            "evidence_issues": dict(Counter(issue for row in predictions
                                            for issue in row.get("evidence_validation", {}).get("issues", [])))}
    write_json(reports / "comparison.json", result)
    return result


def run_pipeline(args):
    args.reports.mkdir(parents=True, exist_ok=True)
    status_path = args.reports / "pipeline.json"
    pilot_files = {name: args.pilot / f"{name}.inputs.jsonl"
                   for name in ("validation", "without_omics", "without_structure")}
    identity = {"pilot_files": {name: digest(path) for name, path in pilot_files.items()},
                "formal_config_sha256": digest(args.config), "root": str(args.root),
                "scoring_dataset": str(args.scoring_dataset), "audit_sha256": digest(args.audit),
                "source_path_map_sha256": digest(args.source_path_map)}
    previous = json.loads(status_path.read_text()) if status_path.exists() else {}
    if previous and previous.get("identity") != identity:
        raise ValueError("pipeline_identity_changed")
    if previous.get("status") == "failed":
        raise ValueError("failed_pipeline_requires_review_before_retry")
    status = previous or {"schema_version": "praxis.qwen-pipeline.v1", "identity": identity,
                          "started_at": datetime.now(timezone.utc).isoformat(), "completed_stages": []}

    def stage(name):
        status.update(status="running", stage=name, updated_at=datetime.now(timezone.utc).isoformat())
        write_json(status_path, status)
        print(json.dumps({"stage": name, "status": "running"}), flush=True)

    try:
        stage("baseline")
        baseline = evaluate(args, "baseline", pilot_files["validation"])
        score(args, "baseline", baseline)
        status["completed_stages"] = ["baseline"]
        stage("formal_sft")
        checked_command([sys.executable, "-u", str(args.root / "scripts/finetuning/run_qwen_formal.py"),
                         "--root", str(args.root), "--config", str(args.config),
                         "--reports", str(args.reports / "training")], cwd=args.root)
        status["completed_stages"].append("formal_sft")
        import yaml
        adapter = Path(yaml.safe_load(args.config.read_text())["output_dir"]) / "adapter"
        if not (adapter / "adapter_config.json").exists():
            raise RuntimeError("formal_adapter_not_exported")
        for label, view in (("sft", "validation"), ("sft_without_omics", "without_omics"),
                            ("sft_without_structure", "without_structure")):
            stage(label)
            predictions = evaluate(args, label, pilot_files[view], adapter=adapter)
            score(args, label, predictions)
            status["completed_stages"].append(label)
        compare_results(args.reports)
        status.update(status="completed", stage="completed", finished_at=datetime.now(timezone.utc).isoformat())
    except BaseException as exc:
        status.update(status="failed", failure_type=type(exc).__name__, failure_reason=str(exc),
                      finished_at=datetime.now(timezone.utc).isoformat())
        raise
    finally:
        write_json(status_path, status)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--reports", type=Path)
    parser.add_argument("--pilot", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--scoring-dataset", type=Path)
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--source-path-map", type=Path)
    parser.add_argument("--port", type=int, default=8790)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--adapter", type=Path)
    args = parser.parse_args()
    args.root = args.root.resolve()
    required = ("inputs", "output", "model") if args.worker else (
        "reports", "pilot", "config", "scoring_dataset", "audit", "source_path_map")
    if any(getattr(args, name) is None for name in required) or not 1024 <= args.port <= 65535:
        parser.error("required run paths or valid port missing")
    for name in required:
        value = getattr(args, name)
        if isinstance(value, Path):
            setattr(args, name, value.resolve())
    os.environ["PYTHONPATH"] = str(args.root / "runtime")

    def interrupted(signum, _frame):
        raise RuntimeError(f"pipeline received {signal.Signals(signum).name}")

    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, interrupted)
    evaluation_worker(args) if args.worker else run_pipeline(args)


if __name__ == "__main__":
    main()
