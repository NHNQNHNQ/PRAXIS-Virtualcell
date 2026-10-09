import asyncio
from collections.abc import Awaitable, Callable
from typing import Any


class ParallelSubagentRunner:
    async def run_all(
        self,
        factories: list[Callable[[], Awaitable[Any]]],
        *,
        return_exceptions: bool = False,
    ) -> list[Any]:
        return await asyncio.gather(*(f() for f in factories), return_exceptions=return_exceptions)


class FileWriteSerialQueue:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def submit(self, write_fn: Callable[[], Awaitable[Any]]) -> Any:
        async with self._lock:
            return await write_fn()
