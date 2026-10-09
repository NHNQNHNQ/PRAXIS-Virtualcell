#!/usr/bin/env python3
"""Run an explicitly supplied trial in a gated, memory-limited systemd user unit.

Example (run the supervisor outside the training cgroup):
  python scripts/finetuning/guard_qwen_trial.py --report reports/guard.json -- \
    /absolute/path/to/accelerate launch --config_file configs/finetuning/fsdp_a100_8gpu.yaml \
    scripts/finetuning/train_qwen_lora.py ...
Fractional GiB caps support small probes, e.g. --max-memory-gib .0625
--high-memory-gib .046875. No training command executes until limits are proved.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import signal
import subprocess
import sys
import tempfile
import time
import uuid

GIB = 1024 ** 3
CGROUP_ROOT = Path("/sys/fs/cgroup")
PROC_ROOT = Path("/proc")
PROPERTIES = ("Id", "Description", "LoadState", "ActiveState", "SubState", "Result", "MainPID",
              "ControlGroup", "KillMode", "OOMPolicy", "ExecMainStatus")


def _command(argv, timeout=15):
    return subprocess.run(argv, check=True, capture_output=True, text=True, timeout=timeout)


def _unit_properties(unit, timeout=15):
    try:
        result = _command(["systemctl", "--user", "show", unit,
                           "--property=" + ",".join(PROPERTIES)], timeout=timeout)
    except subprocess.CalledProcessError as exc:
        if "LoadState=not-found" not in (exc.stdout or "").splitlines():
            raise
        return dict(line.split("=", 1) for line in exc.stdout.splitlines() if "=" in line)
    return dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)


def _host_available():
    for line in (PROC_ROOT / "meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("MemAvailable is unavailable")


def _memory_snapshot(cgroup):
    current = int((cgroup / "memory.current").read_text())
    peak_file = cgroup / "memory.peak"
    peak = int(peak_file.read_text()) if peak_file.exists() else current
    events = dict((key, int(value)) for key, value in
                  (line.split() for line in (cgroup / "memory.events").read_text().splitlines()))
    return max(current, peak), events


def _verify_limits(unit, description, props, maximum, high):
    if props.get("Id") != unit or props.get("Description") != description:
        raise RuntimeError("service identity does not match this launch")
    if props.get("KillMode") != "control-group" or props.get("OOMPolicy") != "kill":
        raise RuntimeError("whole-service kill properties are not active")
    if props.get("ActiveState") != "active":
        raise RuntimeError("gated worker service is not active")
    name = props.get("ControlGroup", "")
    parts = PurePosixPath(name).parts
    if not name.startswith("/") or ".." in parts or not parts or parts[-1] != unit:
        raise RuntimeError("service ControlGroup is not an exact unit cgroup")
    cgroup = CGROUP_ROOT / name.lstrip("/")
    actual = {key: int((cgroup / key).read_text()) for key in
              ("memory.max", "memory.high", "memory.swap.max", "memory.oom.group")}
    if not high <= actual["memory.max"] <= maximum <= 300 * GIB:
        raise RuntimeError("memory.max exceeds the requested cap or is below memory.high")
    if actual["memory.high"] != high or actual["memory.swap.max"] != 0 or actual["memory.oom.group"] != 1:
        raise RuntimeError("memory high/swap/OOM group limits are not active")
    pid = int(props.get("MainPID", "0"))
    members = [int(value) for value in (cgroup / "cgroup.procs").read_text().split()]
    if pid <= 0 or members != [pid]:
        raise RuntimeError("only the gated worker may exist before admission")
    if f"0::{name}" not in (PROC_ROOT / str(pid) / "cgroup").read_text().splitlines():
        raise RuntimeError("MainPID is not in the exact service cgroup")
    if f"0::{name}" in (PROC_ROOT / "self/cgroup").read_text().splitlines():
        raise RuntimeError("supervisor must run outside the training cgroup")
    return cgroup, actual


def _cgroup_members(props):
    name = props.get("ControlGroup", "")
    if not name:
        return []
    try:
        return [int(value) for value in (CGROUP_ROOT / name.lstrip("/") / "cgroup.procs").read_text().split()]
    except FileNotFoundError:
        return []


def _stop_owned_unit(unit, description):
    # A failed launch must never kill an unrelated unit that reused the name.
    props = _unit_properties(unit, timeout=5)
    if props.get("Id") != unit or props.get("Description") != description:
        return False
    actions = []
    if int(props.get("MainPID", "0")) > 0 or _cgroup_members(props):
        actions.append(["kill", "--kill-who=all", "--signal=SIGKILL", unit])
    actions.append(["stop", unit])
    errors = []
    for action in actions:
        try:
            _command(["systemctl", "--user", *action], timeout=5)
        except (OSError, subprocess.SubprocessError) as exc:
            errors.append(str(exc))
    if errors:
        raise RuntimeError("unit cleanup failed: " + "; ".join(errors))
    return True


def _worker(gate, command):
    deadline = time.monotonic() + 30
    while not gate.is_file():
        if time.monotonic() >= deadline:
            raise RuntimeError("supervisor did not verify limits within 30 seconds")
        time.sleep(0.1)
    os.execvp(command[0], command)


def run_guard(args):
    unit = args.unit or f"praxis-qwen-{uuid.uuid4().hex[:16]}"
    unit = unit if unit.endswith(".service") else unit + ".service"
    description = "PRAXIS Qwen guard " + uuid.uuid4().hex
    maximum, high = math.ceil(args.max_memory_gib * GIB), math.ceil(args.high_memory_gib * GIB)
    report = {"unit": unit, "command": args.command, "started_at": datetime.now(timezone.utc).isoformat(),
              "limits_verified": False, "gate_released": False, "outcome": "error", "phase": "preflight",
              "requested_limits": {"memory.max": maximum, "memory.high": high, "memory.swap.max": 0},
              "min_host_available_gib": None, "cgroup_peak_gib": 0, "memory_events": {}, "result": None}
    launched = False
    old_handlers = {}

    def interrupted(signum, _frame):
        raise RuntimeError(f"supervisor received signal {signal.Signals(signum).name}")

    def sample_host():
        available = _host_available()
        measured = available / GIB
        old = report["min_host_available_gib"]
        report["min_host_available_gib"] = measured if old is None else min(old, measured)
        if available < args.min_host_available_gib * GIB:
            report["outcome"] = "host_low_memory"
            raise RuntimeError("host MemAvailable is below the required reserve")

    def read_state(timeout=15):
        props = _unit_properties(unit, timeout=timeout)
        if props.get("Id") != unit or props.get("Description") != description:
            raise RuntimeError("service identity changed during monitoring")
        if props.get("ControlGroup") and props["ControlGroup"] != report["control_group"]:
            raise RuntimeError("service ControlGroup changed during monitoring")
        report["active_state"], report["result"] = props.get("ActiveState"), props.get("Result")
        report["sub_state"] = props.get("SubState")
        report["main_pid"] = int(props.get("MainPID", "0"))
        report["service_exit_status"] = props.get("ExecMainStatus")
        terminal = props.get("ActiveState") in {"inactive", "failed"} or (
            props.get("ActiveState") == "active" and props.get("SubState") == "exited"
            and report["main_pid"] == 0)
        return props, terminal

    args.report.parent.mkdir(parents=True, exist_ok=True)
    try:
        for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            old_handlers[signum] = signal.signal(signum, interrupted)
        sample_host()
        if _unit_properties(unit).get("LoadState") != "not-found":
            raise RuntimeError("refusing to reuse an existing unit")
        with tempfile.TemporaryDirectory(prefix=unit + "-", dir=args.report.parent) as directory:
            gate = Path(directory) / "verified.gate"
            env = {"OMP_NUM_THREADS": "1", "TOKENIZERS_PARALLELISM": "false",
                   "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
                   "PYTHONPATH": str(args.working_directory / "runtime"),
                   "TORCH_NCCL_ASYNC_ERROR_HANDLING": "1", "TORCH_NCCL_ENABLE_MONITORING": "1",
                   "TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC": "120"}
            properties = {"Description": description, "MemoryMax": maximum, "MemoryHigh": high,
                          "MemorySwapMax": 0, "MemoryAccounting": "yes", "OOMPolicy": "kill",
                          "KillMode": "control-group", "TimeoutStopSec": "10s",
                          "RemainAfterExit": "yes",
                          "RuntimeMaxSec": args.max_seconds, "WorkingDirectory": str(args.working_directory)}
            argv = ["systemd-run", "--user", "--unit=" + unit, "--service-type=exec"]
            argv += [f"--property={key}={value}" for key, value in properties.items()]
            argv += [f"--setenv={key}={value}" for key, value in env.items()]
            argv += ["--", sys.executable, str(Path(__file__).resolve()), "--worker-gate", str(gate),
                     "--", *args.command]
            report["phase"] = "launch"
            deadline = time.monotonic() + args.max_seconds
            launched = True  # Ownership is rechecked even if systemd-run times out.
            _command(argv)
            props = _unit_properties(unit)
            report["phase"] = "verify_limits"
            cgroup, actual = _verify_limits(unit, description, props, maximum, high)
            report["control_group"] = props["ControlGroup"]
            report["actual_limits"] = actual
            report["limits_verified"] = True
            peak, events = _memory_snapshot(cgroup)
            report["cgroup_peak_gib"], report["memory_events"] = peak / GIB, events
            report["cgroup_peak_source"] = ("kernel_memory_peak" if (cgroup / "memory.peak").exists()
                                             else "sampled_memory_current")
            sample_host()
            if time.monotonic() >= deadline:
                report["outcome"] = "deadline"
                raise RuntimeError("supervisor runtime deadline reached before admission")
            gate.touch(exist_ok=False)
            report["gate_released"] = True
            report["phase"] = "monitor"
            missing_deadline = None
            while True:
                sample_host()
                timeout = 15
                if missing_deadline is not None:
                    remaining = missing_deadline - time.monotonic()
                    if remaining <= 0:
                        report["outcome"] = "cgroup_missing"
                        raise RuntimeError("active service cgroup remains unavailable after bounded exit-race retries")
                    timeout = min(1, remaining)
                props, terminal = read_state(timeout=timeout)
                try:
                    peak, events = _memory_snapshot(cgroup)
                    report["cgroup_peak_gib"] = max(report["cgroup_peak_gib"], peak / GIB)
                    report["memory_events"] = events
                    missing_deadline = None
                except FileNotFoundError:
                    report["final_memory_snapshot_unavailable"] = True
                    # The process may exit between systemctl show and this
                    # read. Refresh ownership and state before classifying it.
                    missing_deadline = missing_deadline or min(time.monotonic() + 3, deadline)
                    sample_host()
                    remaining = missing_deadline - time.monotonic()
                    if remaining <= 0:
                        report["outcome"] = "cgroup_missing"
                        raise RuntimeError("service cgroup disappeared without confirmed terminal state")
                    props, terminal = read_state(timeout=min(1, remaining))
                    if not terminal:
                        time.sleep(min(.1, max(0, missing_deadline - time.monotonic())))
                        continue
                if terminal:
                    members = _cgroup_members(props)
                    report["remaining_cgroup_pids"] = members
                    if members:
                        report["outcome"] = "orphaned_children"
                        raise RuntimeError("completed service still contains live child processes")
                    success = (report["main_pid"] == 0 and props.get("Result") == "success"
                               and props.get("ExecMainStatus") == "0")
                    report["outcome"] = "success" if success else "service_failed"
                    if report["memory_events"].get("oom_kill", 0) or props.get("Result") == "oom-kill":
                        report["outcome"] = "cgroup_oom"
                    break
                if time.monotonic() >= deadline:
                    report["outcome"] = "deadline"
                    raise RuntimeError("supervisor runtime deadline reached")
                time.sleep(1)
    except (Exception, KeyboardInterrupt) as exc:
        report["failure_reason"] = str(exc)
    finally:
        for signum in old_handlers:
            signal.signal(signum, signal.SIG_IGN)
        if launched:
            try:
                report["cleanup_owned_unit"] = _stop_owned_unit(unit, description)
                final = _unit_properties(unit, timeout=5)
                report["cleanup_result"] = final.get("Result")
                report["result"] = report["result"] or final.get("Result")
                report["cleanup_active_state"] = final.get("ActiveState")
            except (Exception, KeyboardInterrupt) as exc:
                report["cleanup_error"] = str(exc)
                if report["outcome"] == "success":
                    report["outcome"] = "cleanup_failed"
                    report["failure_reason"] = str(exc)
        for signum, previous in old_handlers.items():
            signal.signal(signum, previous)
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    return 0 if report["outcome"] == "success" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--unit")
    parser.add_argument("--working-directory", type=Path, default=Path.cwd())
    parser.add_argument("--max-memory-gib", type=float, default=300)
    parser.add_argument("--high-memory-gib", type=float, default=260)
    parser.add_argument("--min-host-available-gib", type=float, default=160)
    parser.add_argument("--max-seconds", type=int, default=2400)
    parser.add_argument("--worker-gate", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    args.command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not args.command:
        parser.error("a command after -- is required")
    if args.worker_gate:
        _worker(args.worker_gate, args.command)
        return 0
    if args.report is None:
        parser.error("--report is required")
    if args.unit and not re.fullmatch(r"praxis-qwen-[A-Za-z0-9_-]+(?:\.service)?", args.unit):
        parser.error("--unit must be a unique praxis-qwen-* service name")
    if not all(math.isfinite(value) and value > 0 for value in
               (args.max_memory_gib, args.high_memory_gib, args.min_host_available_gib)):
        parser.error("GiB limits must be positive finite numbers")
    if not 0 < args.high_memory_gib <= args.max_memory_gib <= 300 or not 0 < args.max_seconds <= 2400:
        parser.error("require high <= max <= 300 GiB and 0 < max-seconds <= 2400")
    args.report = args.report.resolve()
    args.working_directory = args.working_directory.resolve()
    if not args.working_directory.is_dir():
        parser.error("working directory does not exist")
    return run_guard(args)


if __name__ == "__main__":
    raise SystemExit(main())
