"""Formal orchestration proofs using small metadata and mocked guarded jobs."""
import importlib.util
import json
from pathlib import Path
import signal
import sys

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts/finetuning"
sys.path.insert(0, str(SCRIPTS))
try:
    spec = importlib.util.spec_from_file_location("run_qwen_formal", SCRIPTS / "run_qwen_formal.py")
    formal = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(formal)
finally:
    sys.path.pop(0)


def setup(tmp_path):
    config = yaml.safe_load((SCRIPTS.parents[1] / "configs/finetuning/qwen3_32b_joint_lora_v4_compact.yaml").read_text())
    data, output = tmp_path / "data", tmp_path / "output"
    data.mkdir()
    manifest = {"training_record_count": 7193, "files": {"train.jsonl": {"records": 7193, "sha256": "f" * 64}}}
    (data / "manifest.json").write_text(json.dumps(manifest))
    config.update(data_dir=str(data), model_dir=str(tmp_path / "model"), output_dir=str(output))
    (tmp_path / "recipe.yaml").write_text(yaml.safe_dump(config))
    (tmp_path / "configs/finetuning").mkdir(parents=True)
    (tmp_path / "configs/finetuning/fsdp_a100_8gpu.yaml").write_text("num_processes: 8\n")
    return config, manifest


class Jobs:
    def __init__(self, tmp_path, monkeypatch, *, outcome="success", incomplete=False, interrupt=False):
        self.root, self.calls = tmp_path, []
        self.outcome, self.incomplete, self.interrupt = outcome, incomplete, interrupt
        self.signals, self.waits = [], []
        monkeypatch.setattr(formal.subprocess, "Popen", self.launch)

    def launch(self, argv, cwd):
        owner = self
        self.calls.append(argv)
        command = argv[argv.index("--") + 1:]
        target = int(command[command.index("--stop-after-steps") + 1])
        begin = target - 3
        class Process:
            code = None
            def poll(self):
                return self.code
            def send_signal(self, signum):
                owner.signals.append(signum)
            def wait(self, timeout):
                owner.waits.append(timeout)
                if owner.interrupt:
                    owner.interrupt = False
                    signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
                guard_path = Path(argv[argv.index("--report") + 1])
                guard_path.write_text(json.dumps({"outcome": owner.outcome, "limits_verified": True,
                    "gate_released": True, "cleanup_owned_unit": True, "memory_events": {}, "cgroup_peak_gib": 200}))
                if not owner.signals and owner.outcome == "success":
                    output = owner.root / "output"
                    checkpoint = output / f"checkpoint-{target}"
                    checkpoint.mkdir(parents=True)
                    names = ["pytorch_model_fsdp.bin", "optimizer.bin", "scheduler.pt", "trainer_state.json"]
                    names += [f"rng_state_{i}.pth" for i in range(8)]
                    for name in names:
                        (checkpoint / name).write_bytes(b"state")
                    (checkpoint / "trainer_state.json").write_text(json.dumps({"global_step": target}))
                    if not owner.incomplete:
                        (checkpoint / "praxis_checkpoint.json").write_text(json.dumps({
                            "schema": "praxis.fsdp-lora-checkpoint.v1", "training_identity": "identity",
                            "world_size": 8, "global_step": target, "fsdp": True, "state_dict_type": "FULL_STATE_DICT"}))
                    Path(command[command.index("--report") + 1]).write_text(json.dumps({
                        "record_count": 7193, "training_data_sha256": "f" * 64, "training": {
                            "optimizer_steps": target, "saved_adapter": True, "training_identity": "identity",
                            "resumable_checkpoint": str(checkpoint), "train_loss_this_run": 0.25,
                            "runtime_evidence": {"resumed_global_step": begin, "finite_gradient_checks": 3,
                                "training_microbatches_per_rank": 12, "microbatches_per_optimizer_step": [4, 4, 4],
                                "max_sampled_lora_update": 0.001, "rng_state_restored": True,
                                "scheduler_state_restored": True, "optimizer_state_restored": {"nonzero_moments_restored": True}}}}))
                self.code = 0 if owner.outcome == "success" else 1
                return self.code
        return Process()


def invoke(tmp_path, **options):
    argv = ["--root", str(tmp_path), "--config", "recipe.yaml", "--reports", "reports"]
    for key, value in options.items():
        argv += ["--" + key.replace("_", "-")] + ([] if value is True else [str(value)])
    return formal.main(argv)


def test_one_epoch_plan_is_225_steps_and_does_not_launch(tmp_path, monkeypatch, capsys):
    config, manifest = setup(tmp_path)
    monkeypatch.setattr(formal.subprocess, "Popen", lambda *a, **k: pytest.fail("plan launched training"))
    assert invoke(tmp_path, plan_only=True) == 0
    assert json.loads(capsys.readouterr().out)["schedule"] == formal.plan(config, manifest)
    assert formal.plan(config, manifest)["optimizer_steps"] == 225
    assert formal.plan(config, manifest)["rank_padding_slots"] == 7
    assert not (tmp_path / "reports").exists()


def test_all_segments_keep_one_schedule_and_only_resume_completed_states(tmp_path, monkeypatch):
    setup(tmp_path)
    jobs = Jobs(tmp_path, monkeypatch)
    assert invoke(tmp_path) == 0
    assert len(jobs.calls) == 75
    for index, argv in enumerate(jobs.calls):
        command = argv[argv.index("--") + 1:]
        assert command[command.index("--max-steps") + 1] == "225"
        assert command[command.index("--stop-after-steps") + 1] == str((index + 1) * 3)
        assert ("--resume-from-checkpoint" in command) == (index > 0)
        if index:
            assert command[command.index("--resume-from-checkpoint") + 1].endswith(f"checkpoint-{index * 3}")
        assert argv[argv.index("--max-seconds") + 1] == "2400"
    state = json.loads((tmp_path / "reports/runner.json").read_text())
    assert state["status"] == "complete" and state["completed_optimizer_steps"] == 225


@pytest.mark.parametrize("failure", ["cgroup_oom", "incomplete"])
def test_a_failed_or_incomplete_segment_stops_without_retry(tmp_path, monkeypatch, failure):
    setup(tmp_path)
    jobs = Jobs(tmp_path, monkeypatch, outcome="cgroup_oom" if failure == "cgroup_oom" else "success",
                incomplete=failure == "incomplete")
    assert invoke(tmp_path) == 1 and len(jobs.calls) == 1
    state = json.loads((tmp_path / "reports/runner.json").read_text())
    assert state["status"] == "failed" and state["completed_optimizer_steps"] == 0


def test_term_is_forwarded_once_and_cleanup_wait_is_bounded(tmp_path, monkeypatch):
    setup(tmp_path)
    jobs = Jobs(tmp_path, monkeypatch, interrupt=True)
    assert invoke(tmp_path) == 1 and len(jobs.calls) == 1
    assert jobs.signals == [signal.SIGTERM] and jobs.waits[-1] == 25


def test_nonempty_output_requires_explicit_complete_checkpoint(tmp_path, monkeypatch):
    setup(tmp_path)
    (tmp_path / "output").mkdir()
    (tmp_path / "output/adapter-only").write_text("not resumable")
    monkeypatch.setattr(formal.subprocess, "Popen", lambda *a, **k: pytest.fail("invalid restart launched training"))
    with pytest.raises(ValueError, match="empty output"):
        invoke(tmp_path)
