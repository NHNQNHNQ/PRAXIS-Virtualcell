"""异步执行单个 spawn task — 拉 LLM stream, 累积 text, 完成时扣费。

不走 query.py 完整 loop:spawn 是 one-shot 无 tool 调用。
错误处理 (Q8):任何异常 → status=failed + error 存。
取消:asyncio.CancelledError → status=cancelled, 不扣费(Q5)。
"""
from __future__ import annotations

import logging

from praxis2.accounting.ledger import Ledger
from praxis2.spawn.pricing import compute_cost_li
from praxis2.spawn.repo import SpawnRepo

log = logging.getLogger(__name__)


async def run_spawn_task(
    *,
    task_id: str,
    user_id: str,
    prompt: str,
    model: str,
    client,                       # LLMClient or FakeLLMClient (鸭子类型)
    repo: SpawnRepo,
    ledger: Ledger,
    pg_pool,                      # asyncpg.Pool — 显式传,不取 ledger._pool
    max_tokens: int,
    price_in_per_m: int,
    price_out_per_m: int,
    partial_flush_chunks: int,
    keep_last_per_user: int,
) -> None:
    """单条 spawn 任务执行体。被 asyncio.create_task 包,SpawnRegistry 管 cancel。

    不返结果(状态写 PG;handler poll 拿)。不抛(全捕,落库为 failed/cancelled)。
    """
    import asyncio
    await repo.update_running(task_id)

    chunks: list[str] = []
    flush_counter = 0
    tokens_in = 0
    tokens_out = 0
    try:
        messages = [{"role": "user", "content": prompt}]
        async for ev in client.stream_messages(
            model=model, messages=messages, max_tokens=max_tokens,
        ):
            etype = ev.get("type")
            if etype == "text":
                chunks.append(ev.get("text", ""))
                flush_counter += 1
                if flush_counter >= partial_flush_chunks:
                    await repo.update_partial(task_id, "".join(chunks))
                    flush_counter = 0
            elif etype == "message_stop":
                usage = ev.get("usage") or {}
                tokens_in = int(usage.get("input_tokens", 0) or 0)
                tokens_out = int(usage.get("output_tokens", 0) or 0)
                break

        final_answer = "".join(chunks)
        cost = compute_cost_li(
            tokens_in, tokens_out, price_in_per_m, price_out_per_m,
        )

        async with pg_pool.acquire() as conn:
            async with conn.transaction():
                await repo.update_done(
                    conn, task_id, final_answer, tokens_in, tokens_out, cost,
                )
                if cost > 0:
                    await ledger.record(
                        conn, user_id, -cost,
                        "spawn_consume",
                        "spawn_task", task_id,
                        {"tokens_in": tokens_in, "tokens_out": tokens_out},
                    )

        # TTL trim (Q7) — 事务外,不阻塞主流程
        await repo.trim_old(user_id, keep=keep_last_per_user)

    except asyncio.CancelledError:
        await repo.update_cancelled(task_id)
        raise
    except Exception as exc:
        log.exception("spawn task %s failed", task_id)
        await repo.update_failed(task_id, repr(exc))
