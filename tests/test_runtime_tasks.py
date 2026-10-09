import pytest

from praxis2.runtime.tasks import TaskRegistry, TaskState


def test_task_state_values_match_spec():
    # §7.5.5 完整生命周期(M6 5 态 + M7 重算力 submitted/timeout 扩,共 8 值)
    assert {s.value for s in TaskState} == {
        "pending", "queued", "submitted", "running",
        "completed", "failed", "killed", "timeout",
    }


async def test_task_lifecycle_happy_path():
    reg = TaskRegistry()
    tid = await reg.create(user_id="u1", session_id="s1", kind="llm_chat")
    rec = await reg.get("u1", tid)
    assert rec.state is TaskState.PENDING
    await reg.transition("u1", tid, TaskState.QUEUED)
    await reg.transition("u1", tid, TaskState.RUNNING)
    await reg.transition("u1", tid, TaskState.COMPLETED)
    rec = await reg.get("u1", tid)
    assert rec.state is TaskState.COMPLETED


async def test_illegal_transition_rejected():
    # 非法跃迁抛(状态机硬约束,体例同 M3 rmcp PhaseError)
    reg = TaskRegistry()
    tid = await reg.create(user_id="u1", session_id="s1", kind="llm_chat")
    with pytest.raises(ValueError, match="非法 Task 跃迁"):
        await reg.transition("u1", tid, TaskState.COMPLETED)  # pending→completed 非法


async def test_kill_running_task():
    reg = TaskRegistry()
    tid = await reg.create(user_id="u1", session_id="s1", kind="llm_chat")
    await reg.transition("u1", tid, TaskState.QUEUED)
    await reg.transition("u1", tid, TaskState.RUNNING)
    await reg.stop("u1", tid)  # 主动停止 → killed
    assert (await reg.get("u1", tid)).state is TaskState.KILLED


async def test_list_tasks_is_user_scoped():
    # §11.6 多租户:list 只返回本 user 的 task
    reg = TaskRegistry()
    await reg.create(user_id="u1", session_id="s1", kind="llm_chat")
    await reg.create(user_id="u1", session_id="s2", kind="llm_chat")
    await reg.create(user_id="u2", session_id="s1", kind="llm_chat")
    assert len(await reg.list_tasks("u1")) == 2
    assert len(await reg.list_tasks("u2")) == 1


async def test_get_cross_tenant_denied():
    reg = TaskRegistry()
    tid = await reg.create(user_id="u1", session_id="s1", kind="llm_chat")
    assert await reg.get("u2", tid) is None  # u2 读不到 u1 的 task(§11.6)


async def test_state_change_publishes_to_event_bus():
    # §7.5.5 状态变化经 pub/sub 路由(M6 内存 EventBus,Redis 版 integration)
    from praxis2.runtime.pubsub import InMemoryEventBus

    bus = InMemoryEventBus()
    seen: list[dict] = []
    await bus.subscribe("s1", lambda ev: seen.append(ev))
    reg = TaskRegistry(event_bus=bus)
    tid = await reg.create(user_id="u1", session_id="s1", kind="llm_chat")
    await reg.transition("u1", tid, TaskState.QUEUED)
    assert any(e["type"] == "task_state" and e["state"] == "queued"
               for e in seen)
