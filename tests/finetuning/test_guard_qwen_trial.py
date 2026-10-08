"""Admission and failure checks using real cgroup/proc fixtures, without systemd or GPUs."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/finetuning/guard_qwen_trial.py"
spec = importlib.util.spec_from_file_location("guard_qwen_trial", SCRIPT)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class FakeSystemd:
    def __init__(self, tmp_path, monkeypatch, *, corrupt=None, finish="success", existing=False, orphan=False):
        self.commands = []
        self.timeouts = []
        self.description = "unrelated existing unit"
        self.launched = False
        self.stopped = False
        self.completed = False
        self.orphan = orphan
        self.gate = None
        self.finish = finish
        self.existing = existing
        self.corrupt = corrupt or {}
        self.unit = "praxis-qwen-test.service"
        self.cgroup_name = "/user.slice/" + self.unit
        self.cgroup = tmp_path / "cgroup" / self.cgroup_name.lstrip("/")
        self.cgroup.mkdir(parents=True)
        self.proc = tmp_path / "proc"
        (self.proc / "123").mkdir(parents=True)
        (self.proc / "self").mkdir()
        (self.proc / "123/cgroup").write_text("0::" + self.cgroup_name + "\n")
        (self.proc / "self/cgroup").write_text("0::/supervisor.service\n")
        (self.proc / "meminfo").write_text(f"MemAvailable: {500 * guard.GIB // 1024} kB\n")
        monkeypatch.setattr(guard, "CGROUP_ROOT", tmp_path / "cgroup")
        monkeypatch.setattr(guard, "PROC_ROOT", self.proc)
        monkeypatch.setattr(guard, "_command", self.command)

    def command(self, argv, timeout=15):
        self.commands.append(argv)
        self.timeouts.append((argv, timeout))
        if argv[0] == "systemd-run":
            assert not self.existing
            self.launched = True
            properties = dict(value.removeprefix("--property=").split("=", 1)
                              for value in argv if value.startswith("--property="))
            self.description = properties["Description"]
            self.gate = Path(argv[argv.index("--worker-gate") + 1])
            assert not self.gate.exists()
            contents = {"memory.max": properties["MemoryMax"], "memory.high": properties["MemoryHigh"],
                        "memory.swap.max": "0", "memory.oom.group": "1", "cgroup.procs": "123",
                        "memory.current": "1024", "memory.peak": "4096",
                        "memory.events": "low 0\nhigh 1\nmax 0\noom 0\noom_kill 0\n"}
            contents.update(self.corrupt)
            for name, value in contents.items():
                (self.cgroup / name).write_text(value)
            return subprocess.CompletedProcess(argv, 0, "Running unit", "")
        assert argv[:2] == ["systemctl", "--user"]
        action = argv[2]
        if action == "show":
            assert argv[3] == self.unit
            if not self.launched and not self.existing:
                return subprocess.CompletedProcess(argv, 0, "LoadState=not-found\n", "")
            released = self.gate is not None and self.gate.exists()
            if released and self.finish != "running":
                self.completed = True
                (self.cgroup / "cgroup.procs").write_text("456" if self.orphan else "")
            state, substate = "active", "running"
            if self.completed:
                state, substate = ("active", "exited") if self.finish == "success" else ("failed", "failed")
            if self.stopped:
                state, substate = "inactive", "dead"
            result = self.finish if self.completed else "success"
            if self.stopped:
                result = "signal"
            props = {"Id": self.unit, "Description": self.description, "LoadState": "loaded",
                     "ActiveState": state, "SubState": substate, "Result": result,
                     "MainPID": "0" if self.completed or self.stopped else "123",
                     "ControlGroup": self.cgroup_name, "KillMode": "control-group", "OOMPolicy": "kill",
                     "ExecMainStatus": "0" if result == "success" else "9"}
            return subprocess.CompletedProcess(argv, 0, "\n".join(f"{k}={v}" for k, v in props.items()), "")
        assert argv[-1] == self.unit
        if action == "stop":
            self.stopped = True
        return subprocess.CompletedProcess(argv, 0, "", "")


def run(tmp_path, **options):
    argv = ["--report", str(tmp_path / "report.json"), "--unit", "praxis-qwen-test",
            "--working-directory", str(tmp_path)]
    for key, value in options.items():
        argv += ["--" + key.replace("_", "-"), str(value)]
    code = guard.main([*argv, "--", "/venv/bin/torchrun", "--nproc_per_node=8", "train.py", "a;$HOME"])
    return code, json.loads((tmp_path / "report.json").read_text())


def test_real_proofs_admit_only_limited_worker_and_keep_argv_literal(tmp_path, monkeypatch):
    systemd = FakeSystemd(tmp_path, monkeypatch)
    code, report = run(tmp_path, max_memory_gib=.0625, high_memory_gib=.046875)
    assert code == 0 and report["outcome"] == "success"
    assert report["limits_verified"] and report["gate_released"]
    assert report["actual_limits"]["memory.max"] == 64 * 1024 ** 2
    assert report["actual_limits"]["memory.high"] == 48 * 1024 ** 2
    assert report["cgroup_peak_gib"] == 4096 / guard.GIB
    argv = next(command for command in systemd.commands if command[0] == "systemd-run")
    assert argv[-1] == "a;$HOME"
    assert "--property=WorkingDirectory=" + str(tmp_path) in argv
    assert "--property=RuntimeMaxSec=2400" in argv
    assert "--property=RemainAfterExit=yes" in argv
    assert "--setenv=PYTHONPATH=" + str(tmp_path / "runtime") in argv
    assert not any("--collect" in value for value in argv)
    assert report["active_state"] == "active" and report["sub_state"] == "exited"
    assert report["remaining_cgroup_pids"] == [] and report["result"] == "success"
    assert report["cleanup_owned_unit"] and systemd.stopped
    assert not any(command[2] == "kill" for command in systemd.commands if command[0] == "systemctl")


def test_completed_active_exited_service_with_live_orphan_is_rejected_and_killed(tmp_path, monkeypatch):
    systemd = FakeSystemd(tmp_path, monkeypatch, orphan=True)
    code, report = run(tmp_path)
    assert code == 1 and report["outcome"] == "orphaned_children"
    assert report["active_state"] == "active" and report["sub_state"] == "exited" and report["main_pid"] == 0
    assert report["remaining_cgroup_pids"] == [456] and report["result"] == "success"
    assert "live child" in report["failure_reason"]
    assert ["systemctl", "--user", "kill", "--kill-who=all", "--signal=SIGKILL", systemd.unit] in systemd.commands
    assert systemd.stopped


@pytest.mark.parametrize("corrupt", [{"memory.max": "max"}, {"memory.max": str(301 * guard.GIB)},
                                     {"memory.high": "1"}, {"memory.swap.max": "1"},
                                     {"memory.oom.group": "0"}, {"cgroup.procs": "123\n456"}])
def test_failed_kernel_proof_never_releases_gate_and_kills_only_owned_unit(tmp_path, monkeypatch, corrupt):
    systemd = FakeSystemd(tmp_path, monkeypatch, corrupt=corrupt)
    code, report = run(tmp_path)
    assert code == 1 and not report["gate_released"] and not report["limits_verified"]
    assert report["phase"] == "verify_limits" and report["failure_reason"]
    assert ["systemctl", "--user", "kill", "--kill-who=all", "--signal=SIGKILL", systemd.unit] in systemd.commands
    assert report["cleanup_owned_unit"] is True and systemd.stopped


@pytest.mark.parametrize("location", ["worker", "supervisor"])
def test_process_cgroup_identity_must_be_exact(tmp_path, monkeypatch, location):
    systemd = FakeSystemd(tmp_path, monkeypatch)
    path = "123/cgroup" if location == "worker" else "self/cgroup"
    value = "/wrong.service" if location == "worker" else systemd.cgroup_name
    (systemd.proc / path).write_text("0::" + value + "\n")
    code, report = run(tmp_path)
    assert code == 1 and not report["gate_released"]


def test_host_reserve_blocks_launch_or_stops_admitted_training(tmp_path, monkeypatch):
    systemd = FakeSystemd(tmp_path, monkeypatch, finish="running")
    monkeypatch.setattr(guard, "_host_available", lambda: 159 * guard.GIB)
    code, report = run(tmp_path)
    assert code == 1 and report["outcome"] == "host_low_memory" and not systemd.launched
    available = iter([500, 500, 159])
    monkeypatch.setattr(guard, "_host_available", lambda: next(available) * guard.GIB)
    code, report = run(tmp_path)
    assert code == 1 and report["gate_released"] and report["min_host_available_gib"] == 159
    assert systemd.stopped and report["cleanup_owned_unit"]


def test_existing_unit_is_never_launched_or_stopped(tmp_path, monkeypatch):
    systemd = FakeSystemd(tmp_path, monkeypatch, existing=True)
    code, report = run(tmp_path)
    assert code == 1 and "existing unit" in report["failure_reason"]
    assert all(command[2] == "show" for command in systemd.commands)


def test_unit_replaced_during_monitoring_is_never_killed(tmp_path, monkeypatch):
    systemd = FakeSystemd(tmp_path, monkeypatch, finish="running")
    original = systemd.command

    def replaced(argv, timeout=15):
        if argv[:3] == ["systemctl", "--user", "show"] and systemd.gate and systemd.gate.exists():
            systemd.description = "another owner"
        return original(argv, timeout=timeout)

    monkeypatch.setattr(guard, "_command", replaced)
    code, report = run(tmp_path)
    assert code == 1 and report["cleanup_owned_unit"] is False
    assert "identity changed" in report["failure_reason"]
    assert not any(command[2] in {"kill", "stop"} for command in systemd.commands if command[0] == "systemctl")


def test_launch_timeout_still_cleans_up_unit_that_was_created(tmp_path, monkeypatch):
    systemd = FakeSystemd(tmp_path, monkeypatch)
    original = systemd.command

    def timed_out(argv, timeout=15):
        result = original(argv, timeout=timeout)
        if argv[0] == "systemd-run":
            raise subprocess.TimeoutExpired(argv, 15)
        return result

    monkeypatch.setattr(guard, "_command", timed_out)
    code, report = run(tmp_path)
    assert code == 1 and report["phase"] == "launch" and not report["gate_released"]
    assert systemd.stopped and report["cleanup_owned_unit"]


def test_service_oom_is_failed_even_if_cgroup_already_disappeared(tmp_path, monkeypatch):
    systemd = FakeSystemd(tmp_path, monkeypatch, finish="oom-kill")
    original = guard._memory_snapshot
    calls = 0

    def snapshot(cgroup):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise FileNotFoundError("removed cgroup")
        return original(cgroup)

    monkeypatch.setattr(guard, "_memory_snapshot", snapshot)
    code, report = run(tmp_path)
    assert code == 1 and report["outcome"] == "cgroup_oom"
    assert report["result"] == "oom-kill"
    assert report["final_memory_snapshot_unavailable"]
    assert systemd.stopped
    assert "cleanup_error" not in report
    assert not any(command[2] == "kill" for command in systemd.commands if command[0] == "systemctl")


@pytest.mark.parametrize("signum", [signal.SIGTERM, signal.SIGINT, signal.SIGHUP])
def test_supervisor_signals_clean_up_owned_service_and_preserve_failure_phase(tmp_path, monkeypatch, signum):
    systemd = FakeSystemd(tmp_path, monkeypatch, finish="running")

    def interrupted_sleep(_seconds):
        signal.getsignal(signum)(signum, None)

    monkeypatch.setattr(guard.time, "sleep", interrupted_sleep)
    code, report = run(tmp_path)
    assert code == 1 and report["phase"] == "monitor"
    assert signal.Signals(signum).name in report["failure_reason"]
    assert systemd.stopped and report["cleanup_owned_unit"]


def test_deadline_stops_training_without_waiting_for_runtime_cap(tmp_path, monkeypatch):
    systemd = FakeSystemd(tmp_path, monkeypatch, finish="running")
    clock = iter([0, 1, 2401])
    monkeypatch.setattr(guard.time, "monotonic", lambda: next(clock))
    code, report = run(tmp_path)
    assert code == 1 and report["outcome"] == "deadline"
    assert systemd.stopped


def test_cleanup_ignores_duplicate_signals_and_uses_five_second_commands(tmp_path, monkeypatch):
    systemd = FakeSystemd(tmp_path, monkeypatch, finish="running")
    original = guard._stop_owned_unit
    def cleanup(unit, description):
        for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            assert signal.getsignal(signum) == signal.SIG_IGN
        return original(unit, description)
    monkeypatch.setattr(guard, "_stop_owned_unit", cleanup)
    monkeypatch.setattr(guard.time, "sleep", lambda _: signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None))
    code, report = run(tmp_path)
    assert code == 1 and report["cleanup_owned_unit"] is True
    assert all(timeout == 5 for _, timeout in systemd.timeouts[-4:])


def test_cleanup_timeout_cannot_be_reported_as_success(tmp_path, monkeypatch):
    systemd = FakeSystemd(tmp_path, monkeypatch)
    original = systemd.command
    def timed_out_stop(argv, timeout=15):
        if argv[:3] == ["systemctl", "--user", "stop"]:
            assert timeout == 5
            raise subprocess.TimeoutExpired(argv, timeout)
        return original(argv, timeout=timeout)
    monkeypatch.setattr(guard, "_command", timed_out_stop)
    code, report = run(tmp_path)
    assert code == 1 and report["outcome"] == "cleanup_failed" and report["cleanup_error"]


def test_worker_does_not_execute_until_gate_exists(tmp_path):
    gate, marker = tmp_path / "gate", tmp_path / "executed"
    command = [sys.executable, str(SCRIPT), "--worker-gate", str(gate), "--", sys.executable,
               "-c", "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('ran')", str(marker)]
    process = subprocess.Popen(command)
    try:
        time.sleep(.3)
        assert process.poll() is None and not marker.exists()
        gate.touch()
        assert process.wait(timeout=5) == 0
        assert marker.read_text() == "ran"
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


@pytest.mark.parametrize("options", [["--max-memory-gib", "301"], ["--max-memory-gib", "nan"],
                                    ["--unit", "unrelated.service"], ["--max-seconds", "2401"]])
def test_invalid_limits_and_unit_names_cannot_start_services(tmp_path, monkeypatch, options):
    monkeypatch.setattr(guard, "_command", lambda _: pytest.fail("invalid arguments invoked systemd"))
    with pytest.raises(SystemExit):
        guard.main(["--report", str(tmp_path / "report.json"), *options, "--", "train"])
