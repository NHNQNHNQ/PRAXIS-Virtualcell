"""§7.5.4 普通 subagent 真并行执行编排 + file-write 串行队列。

多普通 subagent 可并行(asyncio.gather);**文件写操作必须串行**
(单一 asyncio.Lock 串行化写,防并发冲突)。读不阻塞。M5 已落子 agent
隔离三层设施(agents/agent_tool)与递归约束;本模块只做并行/串行编排,
不另起子 agent 执行栈(子 agent 复用同一 query(),§7.5.0)。"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any


class ParallelSubagentRunner:
    """普通 subagent 并行执行(§7.5.4)。各 subagent 隔离(异常不互拖,
    return_exceptions 透传 asyncio.gather 语义)。"""

    async def run_all(
        self,
        factories: list[Callable[[], Awaitable[Any]]],
        *,
        return_exceptions: bool = False,
    ) -> list[Any]:
        return await asyncio.gather(
            *(f() for f in factories), return_exceptions=return_exceptions
        )


class FileWriteSerialQueue:
    """§7.5.4 文件写串行队列:并发提交,执行严格串行(单 Lock),
    防多 subagent 并发写同一产物/transcript 冲突。"""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def submit(self, write_fn: Callable[[], Awaitable[Any]]) -> Any:
        async with self._lock:  # 串行化:同一时刻只一个写在跑
            return await write_fn()
