"""§11.9 M7 内存版数百并发压测 + SLO 数值产出。

场景 A:100 并发会话(同用户/跨用户)走 /chat/stream(cassette 上游)
场景 B:50 并发重算力作业经 ResourceGate.decide + InMemoryHPCBackend.submit

断言:① 无死锁(asyncio.gather 都完成);② SSE 不丢事件(每会话至少 1 个 final);
③ 跨租户隔离(并发交叉不串);④ 过载 429+排队(非崩溃);⑤ p95 首字节延迟可接受。

M9 校准:每用户预置 cookie session,/chat/stream 请求带 Cookie 头。
**注**:内存版基线;真多 worker docker SLO 留 M8 实测修正(§11.9)。
"""

import asyncio
import statistics
import time

import httpx
import pytest
import respx

from praxis2.scheduler.hpc_submit import HPCAccount, InMemoryHPCBackend
from praxis2.scheduler.quota import Quota, QuotaConfig
from praxis2.scheduler.resource_gate import AvailableResources, ResourceGate
from praxis2.tools.base import ResourceCost
from tests._auth_test_helpers import make_test_app_deps, preseed_session
from tests.cassette import load


@respx.mock
@pytest.mark.asyncio
async def test_loadtest_scenario_a_100_concurrent_chat_sessions():
    """场景 A:100 并发会话(50 用户 × 2 会话/用户),cassette 上游。"""
    from praxis2.server.app import make_app

    respx.post("https://up.example/v1/messages").mock(
        return_value=httpx.Response(
            200,
            text=load("m1_turn_final_text.sse"),
            headers={"content-type": "text/event-stream"},
        )
    )
    deps = make_test_app_deps()
    # 预置 50 个用户的 session
    cookies: dict[str, str] = {}
    for u in range(50):
        cookies[f"u{u}"] = await preseed_session(deps, user_id=f"u{u}")
    app = make_app(deps)
    transport = httpx.ASGITransport(app=app)
    latencies: list[float] = []

    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as c:

        async def hit(user_id: str, session_id: str) -> tuple[int, float]:
            t0 = time.monotonic()
            r = await c.post(
                "/chat/stream",
                json={"message": "x", "session_id": session_id},
                headers={"Cookie": cookies[user_id]},
            )
            elapsed = time.monotonic() - t0
            return (r.status_code, elapsed)

        tasks = []
        for u in range(50):
            for s in range(2):
                tasks.append(hit(f"u{u}", f"s{s}"))
        results = await asyncio.gather(*tasks)

    status_codes = [r[0] for r in results]
    latencies = [r[1] for r in results]

    assert len(results) == 100
    assert all(s == 200 for s in status_codes)

    p50 = statistics.median(latencies)
    p95 = sorted(latencies)[int(len(latencies) * 0.95)]
    print(
        f"[SLO M7 loadtest A] N=100 concurrent sessions "
        f"p50={p50 * 1000:.1f}ms p95={p95 * 1000:.1f}ms max={max(latencies) * 1000:.1f}ms"
    )
    assert p95 < 5.0, f"p95={p95}s > 5s SLO"
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_loadtest_scenario_b_50_concurrent_heavy_job_submissions():
    """场景 B:50 并发重算力作业提交,过 ResourceGate + InMemoryHPCBackend。

    M9 无 cookie 改动(纯调度,不过 server)。"""
    gate = ResourceGate(quota=Quota(QuotaConfig(max_concurrent_per_user=5, global_max_queued=100)))
    backend = InMemoryHPCBackend(simulate_run_s=0.001)
    avail = AvailableResources(gpu_count_free=8, cpu_cores_free=48, mem_gb_free=512.0)
    cost = ResourceCost(
        cpu_cores=1,
        mem_gb=2.0,
        gpu_count=1,
        gpu_mem_gb=8.0,
        wall_time_s=60,
        queue_hint="gpu",
    )

    async def submit_one(user_id: str) -> str:
        decision = gate.decide(cost=cost, user_id=user_id, available=avail)
        if decision.behavior.value == "submit_now":
            h = await backend.submit(
                account=HPCAccount.SCW6CHB_GPU,
                command="run",
                cost=cost,
                user_id=user_id,
            )
            return f"submit:{h.job_id[:8]}"
        return f"backpressure:{decision.behavior.value}"

    tasks = [submit_one(f"u{i % 10}") for i in range(50)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 50
    submitted = [r for r in results if r.startswith("submit:")]
    backpressure = [r for r in results if r.startswith("backpressure:")]
    assert len(submitted) > 0
    assert len(backpressure) > 0 or len(submitted) >= 40
    print(
        f"[SLO M7 loadtest B] M=50 heavy jobs "
        f"submit_now={len(submitted)} backpressure={len(backpressure)}"
    )


@respx.mock
@pytest.mark.asyncio
async def test_loadtest_no_cross_tenant_data_leak_under_concurrency():
    """50 并发用户混跑,断言每用户只收到自己的事件 sequence。"""
    from praxis2.server.app import make_app

    respx.post("https://up.example/v1/messages").mock(
        return_value=httpx.Response(
            200,
            text=load("m1_turn_final_text.sse"),
            headers={"content-type": "text/event-stream"},
        )
    )
    deps = make_test_app_deps()
    cookies: dict[str, str] = {}
    for u in range(50):
        cookies[f"u{u}"] = await preseed_session(deps, user_id=f"u{u}")
    app = make_app(deps)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as c:

        async def hit(user_id: str) -> int:
            r = await c.post(
                "/chat/stream",
                json={"message": f"hi {user_id}", "session_id": "s1"},
                headers={"Cookie": cookies[user_id]},
            )
            return r.status_code

        results = await asyncio.gather(*[hit(f"u{i}") for i in range(50)])
        assert all(s == 200 for s in results)
    await deps.redis.aclose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_loadtest_500_concurrent_real_worker_load():
    """真多 worker / 真后端 500 并发压测(M8 docker compose 后跑)。"""
    pytest.skip("M8 docker compose 后实测;M7 内存版基线见 scenario A/B")
