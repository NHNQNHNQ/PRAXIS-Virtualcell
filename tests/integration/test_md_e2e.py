"""M11.2 e2e — submit/list/get/cancel/gpu-pool 通过真 ASGI + mock ssh。"""
import uuid
from unittest.mock import AsyncMock, patch

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def _register_user(client: httpx.AsyncClient, email: str) -> str:
    r = await client.post(
        "/api/auth/email/send-code",
        json={"email": email, "purpose": "register"},
    )
    assert r.status_code == 200, r.text
    code = r.json()["dev_code"]
    r = await client.post(
        "/api/auth/register",
        json={"email": email, "code": code,
              "password": "md-test-pw", "display_name": "md"},
    )
    assert r.status_code == 200, r.text
    return r.headers["set-cookie"].split("praxis_session=")[1].split(";")[0]


async def _set_balance(pool, email: str, balance_li: int) -> str:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE users SET balance_li=$1 WHERE email=$2 RETURNING id",
            balance_li, email,
        )
    return str(row["id"])


async def _upload_fake_file(pool, fs_store, user_id: str, content: bytes) -> str:
    """直接 SQL + fs_store.write_stream 插入 files 行 + 真写 fs。返 file_id。

    fs_store 用 (user_id, file_id) 拼路径,storage_key 字段我们设 = file_id 字符串。
    """
    fid = str(uuid.uuid4())

    async def chunks_gen():
        yield content

    await fs_store.write_stream(user_id, fid, chunks_gen())
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO files (id, user_id, filename, size_bytes, mime, "
            "purpose, storage_key) VALUES ($1, $2, 'input.pdb', $3, "
            "'chemical/x-pdb', 'md_input', $4)",
            uuid.UUID(fid), uuid.UUID(user_id), len(content), fid,
        )
    return fid


def _auth(token: str) -> dict[str, str]:
    return {"Cookie": f"praxis_session={token}"}


def _md_body(structure_fid: str, sim_type: str = "standard", **kw) -> dict:
    body = {
        "structure_file_id": structure_fid,
        "force_field": "amber99sb",
        "water_model": "tip3p",
        "ensemble": "NPT",
        "temperature_k": 300,
        "time_ns": 10,
        "timestep_fs": 2,
        "notes": "e2e",
        "sim_type": sim_type,
    }
    body.update(kw)
    return body


async def test_happy_path_submit_to_done(app_with_real_backends):
    """submit → mock ssh sbatch → poll worker mock sacct COMPLETED → done + ledger."""
    app, pool, _ = app_with_real_backends
    fs_store = app._app._md_deps["fs_store"]

    async def mock_ssh_run(cfg, cmd, **kw):
        if cmd.startswith("mkdir"):
            return ""
        if cmd.startswith("sbatch"):
            return "Submitted batch job 999\n"
        if cmd.startswith("squeue"):
            return ""    # 已离队列
        if cmd.startswith("sacct"):
            return "999|COMPLETED|3600|01:00:00|gpu:1\n"
        return ""

    with patch("praxis2.md.handlers.ssh_run", AsyncMock(side_effect=mock_ssh_run)), \
         patch("praxis2.md.handlers.ssh_write_file", AsyncMock()), \
         patch("praxis2.md.poll_worker.ssh_run", AsyncMock(side_effect=mock_ssh_run)):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test",
        ) as client:
            email = f"happy-{uuid.uuid4()}@x.x"
            token = await _register_user(client, email)
            uid = await _set_balance(pool, email, 100000)
            fid = await _upload_fake_file(pool, fs_store, uid, b"FAKE PDB CONTENT")

            r = await client.post(
                "/api/md/submit", json=_md_body(fid), headers=_auth(token),
            )
            assert r.status_code == 200, r.text
            job_id = r.json()["id"]
            assert r.json()["status"] == "queued"

            # 手动跑一次 poll_tick(代替等 30s)
            from praxis2.md.poll_worker import poll_tick
            d = app._app._md_deps
            await poll_tick(
                cfg=d["ssh_cfg"], repo=d["md_repo"], ledger=d["ledger"],
                pg_pool=d["pg_pool"], free_cpu_h=1.0,
                price_gpu=10000, price_cpu=500,
            )

            r = await client.get(
                f"/api/md/jobs/{job_id}", headers=_auth(token),
            )
            row = r.json()
            assert row["status"] == "done"
            # gpu_h=1, cpu_h=1, free=1 → cost = 10000
            assert row["cost_li"] == 10000


async def test_cancel_running(app_with_real_backends):
    app, pool, _ = app_with_real_backends
    fs_store = app._app._md_deps["fs_store"]

    async def mock_ssh_run(cfg, cmd, **kw):
        if cmd.startswith("sbatch"):
            return "Submitted batch job 888\n"
        if cmd.startswith("scancel"):
            return ""
        return ""

    with patch("praxis2.md.handlers.ssh_run", AsyncMock(side_effect=mock_ssh_run)), \
         patch("praxis2.md.handlers.ssh_write_file", AsyncMock()):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test",
        ) as client:
            email = f"cancel-{uuid.uuid4()}@x.x"
            token = await _register_user(client, email)
            uid = await _set_balance(pool, email, 100000)
            fid = await _upload_fake_file(pool, fs_store, uid, b"PDB")

            r = await client.post(
                "/api/md/submit", json=_md_body(fid), headers=_auth(token),
            )
            job_id = r.json()["id"]

            rc = await client.post(
                f"/api/md/jobs/{job_id}/cancel", headers=_auth(token),
            )
            assert rc.status_code == 200

            r = await client.get(
                f"/api/md/jobs/{job_id}", headers=_auth(token),
            )
            assert r.json()["status"] == "cancelled"
            assert r.json()["cost_li"] == 0


async def test_quota_insufficient(app_with_real_backends):
    app, pool, _ = app_with_real_backends
    fs_store = app._app._md_deps["fs_store"]

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
    ) as client:
        email = f"noquota-{uuid.uuid4()}@x.x"
        token = await _register_user(client, email)
        uid = await _set_balance(pool, email, 0)
        fid = await _upload_fake_file(pool, fs_store, uid, b"PDB")

        r = await client.post(
            "/api/md/submit", json=_md_body(fid), headers=_auth(token),
        )
        assert r.status_code == 402
        assert r.json()["error"] == "insufficient_balance"


async def test_concurrent_over_limit(app_with_real_backends):
    app, pool, _ = app_with_real_backends
    fs_store = app._app._md_deps["fs_store"]

    async def mock_ssh_run(cfg, cmd, **kw):
        if cmd.startswith("sbatch"):
            return "Submitted batch job 777\n"
        return ""

    with patch("praxis2.md.handlers.ssh_run", AsyncMock(side_effect=mock_ssh_run)), \
         patch("praxis2.md.handlers.ssh_write_file", AsyncMock()):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test",
        ) as client:
            email = f"concur-{uuid.uuid4()}@x.x"
            token = await _register_user(client, email)
            uid = await _set_balance(pool, email, 100000)
            fid = await _upload_fake_file(pool, fs_store, uid, b"PDB")

            r1 = await client.post(
                "/api/md/submit", json=_md_body(fid), headers=_auth(token),
            )
            r2 = await client.post(
                "/api/md/submit", json=_md_body(fid), headers=_auth(token),
            )
            assert r1.status_code == 200 and r2.status_code == 200

            r3 = await client.post(
                "/api/md/submit", json=_md_body(fid), headers=_auth(token),
            )
            assert r3.status_code == 429
            assert r3.json()["error"] == "too_many_active"


async def test_sim_params_missing_pull_rate(app_with_real_backends):
    app, pool, _ = app_with_real_backends
    fs_store = app._app._md_deps["fs_store"]

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
    ) as client:
        email = f"badparams-{uuid.uuid4()}@x.x"
        token = await _register_user(client, email)
        uid = await _set_balance(pool, email, 100000)
        fid = await _upload_fake_file(pool, fs_store, uid, b"PDB")

        body = _md_body(fid, sim_type="smd_pulling", sim_params={
            "pull_coord_geometry": "distance",
            # 缺 pull_rate
            "pull_k1": 1000,
            "pull_group1_name": "A",
            "pull_group2_name": "B",
        })
        r = await client.post("/api/md/submit", json=body, headers=_auth(token))
        assert r.status_code == 400
        assert r.json()["error"] == "missing_sim_param"
        assert r.json()["field"] == "pull_rate"
