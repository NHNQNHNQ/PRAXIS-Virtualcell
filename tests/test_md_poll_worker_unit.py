"""poll_worker pure-function parsers — scontrol output → (state, cpus, elapsed, gpus)."""
from __future__ import annotations

from praxis2.md.poll_worker import (
    _parse_elapsed,
    _parse_gpus_from_scontrol,
    _parse_scontrol,
)


def test_parse_scontrol_completed_real_sample():
    # zkyd 真实 sample (job 3, 2026-05-27): JobState=COMPLETED, 1 GPU, 1s runtime
    out = (
        "JobId=3 JobName=wrap UserId=zkyd(1000) JobState=COMPLETED "
        "ExitCode=0:0 RunTime=00:00:01 NumNodes=1 NumCPUs=1 NumTasks=1 "
        "TRES=cpu=1,mem=515000M,node=1,billing=1 TresPerNode=gres:gpu:1"
    )
    result = _parse_scontrol(out, "3")
    assert result is not None
    state, cpus, elapsed, gpus = result
    assert state == "COMPLETED"
    assert cpus == 1
    assert elapsed == 1
    assert gpus == 1


def test_parse_scontrol_running_multi_gpu():
    out = (
        "JobId=10 JobState=RUNNING RunTime=01:30:45 NumCPUs=8 "
        "TresPerNode=gres:gpu:4"
    )
    assert _parse_scontrol(out, "10") == (
        "RUNNING", 8, 1 * 3600 + 30 * 60 + 45, 4,
    )


def test_parse_scontrol_failed_state():
    out = "JobId=5 JobState=FAILED RunTime=00:00:30 NumCPUs=2 TresPerNode=gres:gpu:1"
    state, _, elapsed, _ = _parse_scontrol(out, "5")
    assert state == "FAILED"
    assert elapsed == 30


def test_parse_scontrol_empty_out_returns_none():
    assert _parse_scontrol("", "1") is None
    assert _parse_scontrol("   \n  ", "1") is None


def test_parse_scontrol_wrong_jobid_returns_none():
    out = "JobId=99 JobState=COMPLETED RunTime=00:00:01 NumCPUs=1 TresPerNode=gres:gpu:1"
    assert _parse_scontrol(out, "100") is None


def test_parse_elapsed_basic():
    assert _parse_elapsed("00:00:00") == 0
    assert _parse_elapsed("00:00:30") == 30
    assert _parse_elapsed("01:30:45") == 1 * 3600 + 30 * 60 + 45
    assert _parse_elapsed("2-12:00:00") == 2 * 86400 + 12 * 3600


def test_parse_elapsed_malformed_returns_zero():
    assert _parse_elapsed("") == 0
    assert _parse_elapsed("bad") == 0
    assert _parse_elapsed("00:00") == 0  # 缺秒段


def test_parse_gpus_tres_per_node_preferred_over_tres():
    d = {"TresPerNode": "gres:gpu:4", "TRES": "cpu=1,gres/gpu=2"}
    assert _parse_gpus_from_scontrol(d) == 4


def test_parse_gpus_tres_fallback_when_no_tres_per_node():
    d = {"TresPerNode": "", "TRES": "cpu=8,mem=10G,gres/gpu=2"}
    assert _parse_gpus_from_scontrol(d) == 2


def test_parse_gpus_default_1_when_both_missing():
    d = {"TRES": "cpu=1,mem=4G"}
    assert _parse_gpus_from_scontrol(d) == 1


def test_parse_gpus_malformed_falls_back_to_1():
    d = {"TresPerNode": "gres:gpu:bad"}
    assert _parse_gpus_from_scontrol(d) == 1
