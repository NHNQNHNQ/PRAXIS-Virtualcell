"""§7.5.5 M7 扩 TaskState submitted/timeout + 跃迁补(零回归 M6 5 态)。"""

import pytest

from praxis2.runtime.tasks import TaskRegistry, TaskState


def test_taskstate_has_seven_values_including_submitted_timeout():
    # M6 5 态 + M7 2 态 = 7 态(submitted/timeout 新增,零回归 5 态)
    assert {s.value for s in TaskState} == {
        "pending", "queued", "submitted", "running",
        "completed", "failed", "killed", "timeout",
    }


async def test_queued_to_submitted_then_running_heavy_path():
    # 重算力路径:queued → submitted(经 hpc_submit) → running(HPC 起跑)
    reg = TaskRegistry()
    tid = await reg.create(user_id="u1", session_id="s1", kind="hpc_af3")
    await reg.transition("u1", tid, TaskState.QUEUED)
    await reg.transition("u1", tid, TaskState.SUBMITTED)
    await reg.transition("u1", tid, TaskState.RUNNING)
    await reg.transition("u1", tid, TaskState.COMPLETED)
    assert (await reg.get("u1", tid)).state is TaskState.COMPLETED


async def test_queued_to_running_light_path_still_legal_no_regression():
    # M6 轻量路径 queued → running 仍合法(零回归)
    reg = TaskRegistry()
    tid = await reg.create(user_id="u1", session_id="s1", kind="llm_chat")
    await reg.transition("u1", tid, TaskState.QUEUED)
    await reg.transition("u1", tid, TaskState.RUNNING)  # 不经 submitted
    await reg.transition("u1", tid, TaskState.COMPLETED)


async def test_submitted_to_killed_user_cancels_in_queue():
    # SUBMITTED 仍可被 cancel(SLURM scancel)→ KILLED
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
    with pytest.raises(ValueError, match="非法 Task 跃迁"):
        await reg.transition("u1", tid, TaskState.RUNNING)


async def test_pending_to_submitted_directly_illegal():
    # pending → submitted 非法(必须先 queued)
    reg = TaskRegistry()
    tid = await reg.create(user_id="u1", session_id="s1", kind="hpc_af3")
    with pytest.raises(ValueError, match="非法 Task 跃迁"):
        await reg.transition("u1", tid, TaskState.SUBMITTED)
