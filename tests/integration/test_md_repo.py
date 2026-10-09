"""MdJobRepo CRUD 集成测试 — 真实 PG(testcontainers)。"""
import pytest

from praxis2.md.repo import MdJobRepo

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def test_create_then_get(pg_pool, fake_user_id):
    repo = MdJobRepo(pg_pool)
    params = {
        "structure_file_id": "fake-fid",
        "force_field": "amber99sb",
        "water_model": "tip3p",
        "ensemble": "NPT",
        "temperature_k": 300,
        "time_ns": 10,
        "timestep_fs": 2,
        "notes": "",
        "sim_params": {},
    }
    async with pg_pool.acquire() as conn:
        jid = await repo.create(conn, fake_user_id, "standard", params)
    row = await repo.get(jid)
    assert row["id"] == jid
    assert row["status"] == "queued"
    assert row["sim_type"] == "standard"
    assert row["params"]["force_field"] == "amber99sb"
    assert row["cost_li"] == 0


async def test_update_submitted_sets_slurm_id_and_running(pg_pool, fake_user_id):
    repo = MdJobRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        jid = await repo.create(conn, fake_user_id, "standard", {"sim_params": {}})
    await repo.update_submitted(jid, slurm_job_id="12345")
    row = await repo.get(jid)
    assert row["slurm_job_id"] == "12345"
    assert row["status"] == "queued"   # update_submitted 不改 status


async def test_update_status_to_running_sets_started_at(pg_pool, fake_user_id):
    repo = MdJobRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        jid = await repo.create(conn, fake_user_id, "standard", {"sim_params": {}})
    await repo.update_submitted(jid, slurm_job_id="12345")
    await repo.update_status(jid, "running", gpu_host="bio000071")
    row = await repo.get(jid)
    assert row["status"] == "running"
    assert row["gpu_host"] == "bio000071"
    assert row["started_at"] is not None


async def test_count_active(pg_pool, fake_user_id):
    repo = MdJobRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        await repo.create(conn, fake_user_id, "standard", {"sim_params": {}})
        j2 = await repo.create(conn, fake_user_id, "standard", {"sim_params": {}})
        await repo.update_submitted(j2, slurm_job_id="11")
        await repo.update_status(j2, "running")
        j3 = await repo.create(conn, fake_user_id, "standard", {"sim_params": {}})
        await repo.update_cancelled(j3)
    assert await repo.count_active(fake_user_id) == 2


async def test_finalize_writes_cost_and_ledger(pg_pool, fake_user_id):
    """finalize 必须在调用方事务里同时写 md_jobs 和 ledger。"""
    from praxis2.accounting.ledger import Ledger
    repo = MdJobRepo(pg_pool)
    ledger = Ledger(pg_pool)
    async with pg_pool.acquire() as conn:
        jid = await repo.create(conn, fake_user_id, "standard", {"sim_params": {}})

    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            await repo.finalize(
                conn, jid, status="done",
                cpu_hours=3.5, gpu_hours=2.0, cost_li=20000,
                error=None,
            )
            await ledger.record(
                conn, fake_user_id, -20000,
                kind="md_consume", ref_type="md_job", ref_id=jid,
                meta={"gpu_hours": 2.0, "cpu_hours": 3.5},
            )

    row = await repo.get(jid)
    assert row["status"] == "done"
    assert row["cost_li"] == 20000
    assert row["cpu_hours"] == pytest.approx(3.5)
    assert row["gpu_hours"] == pytest.approx(2.0)
    assert row["finished_at"] is not None
    entries = await ledger.recent(fake_user_id, limit=5)
    assert any(e["kind"] == "md_consume" and e["amount_li"] == -20000
               for e in entries)


async def test_list_active_returns_only_queued_running(pg_pool, fake_user_id):
    repo = MdJobRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        j1 = await repo.create(conn, fake_user_id, "standard", {"sim_params": {}})
        j2 = await repo.create(conn, fake_user_id, "standard", {"sim_params": {}})
        await repo.update_submitted(j2, slurm_job_id="22")
        await repo.update_status(j2, "running")
        j3 = await repo.create(conn, fake_user_id, "standard", {"sim_params": {}})
        await repo.update_cancelled(j3)
    rows = await repo.list_active()
    ids = {r["id"] for r in rows}
    assert j1 in ids and j2 in ids and j3 not in ids
