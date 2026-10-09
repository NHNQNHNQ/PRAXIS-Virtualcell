import asyncio

from praxis2.runtime.parallel import FileWriteSerialQueue, ParallelSubagentRunner


async def test_subagents_run_concurrently():

    async def sub(tag: str) -> str:
        await asyncio.sleep(0.05)
        return f"done-{tag}"

    runner = ParallelSubagentRunner()
    t0 = asyncio.get_event_loop().time()
    results = await runner.run_all(
        [
            lambda: sub("a"),
            lambda: sub("b"),
            lambda: sub("c"),
        ]
    )
    elapsed = asyncio.get_event_loop().time() - t0
    assert sorted(results) == ["done-a", "done-b", "done-c"]
    assert elapsed < 0.12


async def test_file_writes_serialized_even_under_concurrency():

    q = FileWriteSerialQueue()
    log: list[str] = []

    async def do_write(tag: str) -> None:
        log.append(f"{tag}-start")
        await asyncio.sleep(0.01)
        log.append(f"{tag}-end")

    await asyncio.gather(
        q.submit(lambda: do_write("w1")),
        q.submit(lambda: do_write("w2")),
        q.submit(lambda: do_write("w3")),
    )

    for i in range(0, len(log), 2):
        tag = log[i].split("-")[0]
        assert log[i] == f"{tag}-start"
        assert log[i + 1] == f"{tag}-end"


async def test_parallel_reads_with_serial_writes_mixed():

    q = FileWriteSerialQueue()
    runner = ParallelSubagentRunner()
    order: list[str] = []

    async def reader(tag: str) -> str:
        await asyncio.sleep(0.02)
        order.append(f"r{tag}")
        return tag

    async def writer(tag: str) -> None:
        order.append(f"w{tag}-s")
        await asyncio.sleep(0.01)
        order.append(f"w{tag}-e")

    reads = runner.run_all([lambda: reader("1"), lambda: reader("2")])
    writes = asyncio.gather(q.submit(lambda: writer("A")), q.submit(lambda: writer("B")))
    rres, _ = await asyncio.gather(reads, writes)
    assert sorted(rres) == ["1", "2"]

    wa = order.index("wA-s")
    assert order[wa + 1] == "wA-e" or order.index("wA-e") == wa + 1


async def test_subagent_exception_isolated():

    async def good() -> str:
        return "ok"

    async def bad() -> str:
        raise RuntimeError("\u5b50 agent \u70b8")

    runner = ParallelSubagentRunner()
    results = await runner.run_all([lambda: good(), lambda: bad()], return_exceptions=True)
    assert "ok" in results
    assert any(isinstance(r, RuntimeError) for r in results)
