import pytest

from praxis2.runtime.tasks import TaskRegistry, TaskState


def test_taskstate_has_seven_values_including_submitted_timeout():

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


async def test_queued_to_submitted_then_running_heavy_path():

    reg = TaskRegistry()
    tid = await reg.create(user_id="u1", session_id="s1", kind="hpc_af3")
    await reg.transition("u1", tid, TaskState.QUEUED)
    await reg.transition("u1", tid, TaskState.SUBMITTED)
    await reg.transition("u1", tid, TaskState.RUNNING)
    await reg.transition("u1", tid, TaskState.COMPLETED)
    assert (await reg.get("u1", tid)).state is TaskState.COMPLETED


async def test_queued_to_running_light_path_still_legal_no_regression():

    reg = TaskRegistry()
    tid = await reg.create(user_id="u1", session_id="s1", kind="llm_chat")
    await reg.transition("u1", tid, TaskState.QUEUED)
    await reg.transition("u1", tid, TaskState.RUNNING)
    await reg.transition("u1", tid, TaskState.COMPLETED)


async def test_submitted_to_killed_user_cancels_in_queue():

    reg = TaskRegistry()
    tid = await reg.create(user_id="u1", session_id="s1", kind="hpc_af3")
    await reg.transition("u1", tid, TaskState.QUEUED)
    await reg.transition("u1", tid, TaskState.SUBMITTED)
    await reg.stop("u1", tid)
    assert (await reg.get("u1", tid)).state is TaskState.KILLED


async def test_running_to_timeout_legal():
    reg = TaskRegistry()
    tid = await reg.create(user_id="u1", session_id="s1", kind="hpc_af3")
    await reg.transition("u1", tid, TaskState.QUEUED)
    await reg.transition("u1", tid, TaskState.SUBMITTED)
    await reg.transition("u1", tid, TaskState.RUNNING)
    await reg.transition("u1", tid, TaskState.TIMEOUT)
    assert (await reg.get("u1", tid)).state is TaskState.TIMEOUT


async def test_timeout_is_terminal_no_further_transitions():
    reg = TaskRegistry()
    tid = await reg.create(user_id="u1", session_id="s1", kind="hpc_af3")
    await reg.transition("u1", tid, TaskState.QUEUED)
    await reg.transition("u1", tid, TaskState.SUBMITTED)
    await reg.transition("u1", tid, TaskState.RUNNING)
    await reg.transition("u1", tid, TaskState.TIMEOUT)
    with pytest.raises(ValueError, match="Invalid Task transition"):
        await reg.transition("u1", tid, TaskState.RUNNING)


async def test_pending_to_submitted_directly_illegal():

    reg = TaskRegistry()
    tid = await reg.create(user_id="u1", session_id="s1", kind="hpc_af3")
    with pytest.raises(ValueError, match="Invalid Task transition"):
        await reg.transition("u1", tid, TaskState.SUBMITTED)
