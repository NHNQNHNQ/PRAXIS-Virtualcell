"""GET /api/storage/trajectories — 端点测试。"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from praxis2.server.routes.files import _job_to_trajectory, handle_storage_trajectories

# ---- _job_to_trajectory 单元测试 ----

def _make_job(**kwargs) -> dict:
    base = {
        "id": "aaaabbbb-0000-0000-0000-000000000001",
        "user_id": "user-111",
        "sim_type": "standard",
        "params": {"notes": "lysozyme test", "ensemble": "NPT", "time_ns": 10.0,
                   "structure_file_id": "fid-xyz"},
        "status": "done",
        "slurm_job_id": "local:12345",
        "gpu_host": "10.102.106.53",
        "progress": 100,
        "error": None,
        "cost_li": 500,
        "cpu_hours": 0.5,
        "gpu_hours": 0.5,
        "created_at": datetime(2026, 6, 10, 12, 0, 0, tzinfo=UTC),
        "started_at": datetime(2026, 6, 10, 12, 1, 0, tzinfo=UTC),
        "finished_at": datetime(2026, 6, 10, 14, 0, 0, tzinfo=UTC),
    }
    base.update(kwargs)
    return base


def test_job_to_trajectory_basic():
    t = _job_to_trajectory(_make_job(), ssh_user="zkyd")
    assert t["job_id"] == "aaaabbbb-0000-0000-0000-000000000001"
    assert t["name"] == "lysozyme test"
    assert t["status"] == "done"
    assert t["ensemble"] == "NPT"
    assert t["time_ns"] == 10.0
    assert t["remote_path"] == "/home/zkyd/praxis-md/aaaabbbb-0000-0000-0000-000000000001"
    assert t["finished_at"] is not None


def test_job_to_trajectory_no_notes_uses_sim_type():
    job = _make_job(params={"ensemble": "NVT", "time_ns": 5.0})
    t = _job_to_trajectory(job, ssh_user="zkyd")
    assert "standard" in t["name"]


def test_job_to_trajectory_null_finished_at():
    job = _make_job(finished_at=None)
    t = _job_to_trajectory(job, ssh_user="zkyd")
    assert t["finished_at"] is None


def test_job_to_trajectory_download_url():
    t = _job_to_trajectory(_make_job(), ssh_user="zkyd")
    assert t["download_url"].startswith("/api/md/jobs/")


# ---- handler 集成测试 ----

class _FakeMdRepo:
    def __init__(self, rows):
        self._rows = rows

    async def list_recent(self, user_id, limit=200):
        return self._rows


class _FakeSend:
    def __init__(self):
        self.calls = []

    async def __call__(self, msg):
        self.calls.append(msg)


async def _noop_receive():
    return {}


@pytest.mark.asyncio
async def test_handler_returns_trajectories():
    rows = [_make_job()]
    from types import SimpleNamespace
    fake_cfg = SimpleNamespace(host="10.102.106.53", user="zkyd", key_path="/dev/null")
    scope = {"user": {"user_id": "user-111"}}
    deps = {"md_repo": _FakeMdRepo(rows), "ssh_cfg": fake_cfg}
    send = _FakeSend()

    await handle_storage_trajectories(scope, _noop_receive, send, deps)

    assert send.calls[0]["status"] == 200
    import json
    body = json.loads(send.calls[1]["body"])
    assert len(body["trajectories"]) == 1
    assert body["trajectories"][0]["status"] == "done"


@pytest.mark.asyncio
async def test_handler_returns_empty_when_md_repo_none():
    scope = {"user": {"user_id": "user-111"}}
    deps = {"md_repo": None}
    send = _FakeSend()

    await handle_storage_trajectories(scope, _noop_receive, send, deps)

    assert send.calls[0]["status"] == 200
    import json
    body = json.loads(send.calls[1]["body"])
    assert body["trajectories"] == []


@pytest.mark.asyncio
async def test_handler_401_without_user():
    scope = {}
    deps = {"md_repo": None}
    send = _FakeSend()

    await handle_storage_trajectories(scope, _noop_receive, send, deps)

    assert send.calls[0]["status"] == 401
