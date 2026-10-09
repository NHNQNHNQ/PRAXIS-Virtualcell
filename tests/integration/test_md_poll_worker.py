"""poll_worker 集成 — mock ssh_run 模拟 squeue / scontrol,验证状态流转 + ledger 扣费。"""
from unittest.mock import AsyncMock, patch

import pytest

from praxis2.accounting.ledger import Ledger
from praxis2.md.poll_worker import poll_tick
from praxis2.md.repo import MdJobRepo
from praxis2.md.ssh import SshConfig

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


def _cfg() -> SshConfig:
    return SshConfig(host="x", user="x", key_path="/tmp/fake-key")


async def test_running_job_status_updated_from_squeue(pg_pool, fake_user_id):
    repo = MdJobRepo(pg_pool)
    ledger = Ledger(pg_pool)
    async with pg_pool.acquire() as conn:
        jid = await repo.create(conn, fake_user_id, "standard", {"sim_params": {}})
    await repo.update_submitted(jid, slurm_job_id="111")

    # squeue 返 RUNNING + node bio000071
    squeue_out = "111|RUNNING|bio000071\n"

    async def mock_ssh_run(cfg, cmd, **kw):
        if cmd.startswith("squeue"):
            return squeue_out
        return ""

    with patch("praxis2.md.poll_worker.ssh_run", AsyncMock(side_effect=mock_ssh_run)):
        await poll_tick(
            cfg=_cfg(), repo=repo, ledger=ledger, pg_pool=pg_pool,
            free_cpu_h=1.0, price_gpu=10000, price_cpu=500,
        )

    row = await repo.get(jid)
    assert row["status"] == "running"
    assert row["gpu_host"] == "bio000071"


async def test_done_job_finalize_with_ledger_debit(pg_pool, fake_user_id):
    repo = MdJobRepo(pg_pool)
    ledger = Ledger(pg_pool)
    async with pg_pool.acquire() as conn:
        jid = await repo.create(conn, fake_user_id, "standard", {"sim_params": {}})
    await repo.update_submitted(jid, slurm_job_id="222")
    await repo.update_status(jid, "running", gpu_host="bio000071")

    # squeue 返空(job 已不在队列)→ poll worker 调 scontrol show job
    scontrol_out = (
        "JobId=222 JobState=COMPLETED RunTime=01:00:00 "
        "NumCPUs=1 TresPerNode=gres:gpu:1"
    )

    async def mock_ssh_run(cfg, cmd, **kw):
        if cmd.startswith("squeue"):
            return ""
        if cmd.startswith("scontrol"):
            return scontrol_out
        return ""

    with patch("praxis2.md.poll_worker.ssh_run", AsyncMock(side_effect=mock_ssh_run)):
        await poll_tick(
            cfg=_cfg(), repo=repo, ledger=ledger, pg_pool=pg_pool,
            free_cpu_h=1.0, price_gpu=10000, price_cpu=500,
        )

    row = await repo.get(jid)
    assert row["status"] == "done"
    # gpu_h=1, cpu_h=1, free=1 → 不扣 CPU,仅 GPU=10000
    assert row["cost_li"] == 10000
    entries = await ledger.recent(fake_user_id, limit=5)
    assert any(e["kind"] == "md_consume" and e["amount_li"] == -10000
               for e in entries)


async def test_failed_job_status_no_debit(pg_pool, fake_user_id):
    repo = MdJobRepo(pg_pool)
    ledger = Ledger(pg_pool)
    async with pg_pool.acquire() as conn:
        jid = await repo.create(conn, fake_user_id, "standard", {"sim_params": {}})
    await repo.update_submitted(jid, slurm_job_id="333")

    async def mock_ssh_run(cfg, cmd, **kw):
        if cmd.startswith("squeue"):
            return ""
        if cmd.startswith("scontrol"):
            return (
                "JobId=333 JobState=FAILED RunTime=00:01:00 "
                "NumCPUs=1 TresPerNode=gres:gpu:1"
            )
        return ""

    with patch("praxis2.md.poll_worker.ssh_run", AsyncMock(side_effect=mock_ssh_run)):
        await poll_tick(
            cfg=_cfg(), repo=repo, ledger=ledger, pg_pool=pg_pool,
            free_cpu_h=1.0, price_gpu=10000, price_cpu=500,
        )

    row = await repo.get(jid)
    assert row["status"] == "failed"
    # failed 不扣费(MVP 决策)
    assert row["cost_li"] == 0
    entries = await ledger.recent(fake_user_id, limit=5)
    assert not any(e["kind"] == "md_consume" for e in entries)
