import pytest

from praxis2.runtime.tasks import TaskRegistry, TaskState


def test_task_state_values_match_spec():

    assert {s.value for s in TaskState} == {
        "pending",
        "queued",
        "submitted",
        "running",
        "completed",
        "failed",
        "killed",
        "timeout",
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

    reg = TaskRegistry()
    tid = await reg.create(user_id="u1", session_id="s1", kind="llm_chat")
    with pytest.raises(ValueError, match="Invalid Task transition"):
        await reg.transition("u1", tid, TaskState.COMPLETED)


async def test_kill_running_task():
    reg = TaskRegistry()
    tid = await reg.create(user_id="u1", session_id="s1", kind="llm_chat")
    await reg.transition("u1", tid, TaskState.QUEUED)
    await reg.transition("u1", tid, TaskState.RUNNING)
    await reg.stop("u1", tid)
    assert (await reg.get("u1", tid)).state is TaskState.KILLED


async def test_list_tasks_is_user_scoped():

    reg = TaskRegistry()
    await reg.create(user_id="u1", session_id="s1", kind="llm_chat")
    await reg.create(user_id="u1", session_id="s2", kind="llm_chat")
    await reg.create(user_id="u2", session_id="s1", kind="llm_chat")
    assert len(await reg.list_tasks("u1")) == 2
    assert len(await reg.list_tasks("u2")) == 1


async def test_get_cross_tenant_denied():
    reg = TaskRegistry()
    tid = await reg.create(user_id="u1", session_id="s1", kind="llm_chat")
    assert await reg.get("u2", tid) is None


async def test_state_change_publishes_to_event_bus():

    from praxis2.runtime.pubsub import InMemoryEventBus

    bus = InMemoryEventBus()
    seen: list[dict] = []
    await bus.subscribe("s1", lambda ev: seen.append(ev))
    reg = TaskRegistry(event_bus=bus)
    tid = await reg.create(user_id="u1", session_id="s1", kind="llm_chat")
    await reg.transition("u1", tid, TaskState.QUEUED)
    assert any(e["type"] == "task_state" and e["state"] == "queued" for e in seen)
