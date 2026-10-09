"""Task 5 integration tests — spawn worker: happy path + error path。"""
import pytest

from praxis2.accounting.ledger import Ledger
from praxis2.spawn.repo import SpawnRepo
from praxis2.spawn.worker import run_spawn_task
from tests._llm_fakes import FakeLLMClient

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
]


async def test_happy_path_done_and_debit(pg_pool, fake_user_id):
    """跑通 → status=done + answer 完整 + ledger 扣费 + 余额减少。"""
    repo = SpawnRepo(pg_pool)
    ledger = Ledger(pg_pool)
    async with pg_pool.acquire() as conn:
        tid = await repo.create(conn, fake_user_id, "你好", "deepseek-v4-pro")

    # FakeLLMClient: 25 个 text chunk + message_stop
    client = FakeLLMClient(turns=[[
        *[{"type": "text", "text": f"chunk{i}"} for i in range(25)],
        {"type": "message_stop", "stop_reason": "end_turn",
         "usage": {"input_tokens": 1000, "output_tokens": 500}},
    ]])

    await run_spawn_task(
        task_id=tid, user_id=fake_user_id,
        prompt="你好", model="deepseek-v4-pro",
        client=client, repo=repo, ledger=ledger, pg_pool=pg_pool,
        max_tokens=1024,
        price_in_per_m=1500, price_out_per_m=6000,
        partial_flush_chunks=20, keep_last_per_user=100,
    )

    row = await repo.get(tid)
    assert row["status"] == "done"
    assert row["answer"] == "".join(f"chunk{i}" for i in range(25))
    assert row["tokens_in"] == 1000
    assert row["tokens_out"] == 500
    # cost = ceil((1000*1500 + 500*6000) / 1e6) = ceil(4.5) = 5
    assert row["cost_li"] == 5

    # ledger 有一条 -5 spawn_consume
    entries = await ledger.recent(fake_user_id, limit=5)
    debit = [e for e in entries if e["kind"] == "spawn_consume"]
    assert len(debit) == 1
    assert debit[0]["amount_li"] == -5
    assert debit[0]["ref_id"] == tid


async def test_llm_error_marks_failed(pg_pool, fake_user_id):
    from tests._llm_fakes import RaisingLLMClient
    repo = SpawnRepo(pg_pool)
    ledger = Ledger(pg_pool)
    async with pg_pool.acquire() as conn:
        tid = await repo.create(conn, fake_user_id, "p", "m")

    client = RaisingLLMClient(RuntimeError("upstream 500"))
    await run_spawn_task(
        task_id=tid, user_id=fake_user_id, prompt="p", model="m",
        client=client, repo=repo, ledger=ledger, pg_pool=pg_pool,
        max_tokens=1024, price_in_per_m=1500, price_out_per_m=6000,
        partial_flush_chunks=20, keep_last_per_user=100,
    )

    row = await repo.get(tid)
    assert row["status"] == "failed"
    assert "upstream 500" in row["error"]
    entries = await ledger.recent(fake_user_id, limit=5)
    assert not any(e["kind"] == "spawn_consume" for e in entries)
