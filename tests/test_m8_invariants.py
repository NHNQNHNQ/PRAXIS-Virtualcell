from praxis2.runtime.tasks import TaskState
from praxis2.scheduler.resource_gate import GateBehavior
from praxis2.server.sse import SSE_EVENT_TYPES
from scripts.migrate_brains import _LEGACY_SLUGS


def test_inv2_brains_legacy_slugs_constant_13():

    assert len(_LEGACY_SLUGS) == 1


def test_inv3_sse_event_set_13_unchanged_from_m6():

    assert SSE_EVENT_TYPES == {
        "text_delta",
        "tool_start",
        "tool_end",
        "tool_progress",
        "stream_event",
        "phase_change",
        "compact_boundary",
        "control_request",
        "control_cancel_request",
        "auth_status",
        "final",
        "error",
        "queue_position",
    }


def test_inv4_task_state_8_values_m7_unchanged():

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


def test_inv5_resource_gate_behavior_5_values_m7_unchanged():

    assert {b.value for b in GateBehavior} == {
        "submit_now",
        "enqueue",
        "downscale",
        "cpu_fallback",
        "reject",
    }


def test_inv8_migrate_brains_script_callable():

    from scripts.migrate_brains import migrate_all  # noqa: F401
