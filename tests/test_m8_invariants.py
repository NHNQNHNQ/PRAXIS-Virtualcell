"""§6⑦ M8 切换判据 9 项横向不变量(单文件可读兜底)。"""

from pathlib import Path

import pytest

from praxis2.config import ConfigError, Settings
from praxis2.runtime.tasks import TaskState
from praxis2.scheduler.hpc_submit import HPCAccount
from praxis2.scheduler.resource_gate import GateBehavior
from praxis2.server.sse import SSE_EVENT_TYPES
from scripts.migrate_brains import _LEGACY_SLUGS


def test_inv1_config_settings_required_fields_no_default():
    # §6⑤ fail-fast 配置单一源
    with pytest.raises(TypeError):
        Settings()
    assert issubclass(ConfigError, RuntimeError)


def test_inv2_brains_legacy_slugs_constant_13():
    # v2.0.2:Synth carry 落地(brains/synth/)→ 13 学科
    assert len(_LEGACY_SLUGS) == 13


def test_inv3_sse_event_set_13_unchanged_from_m6():
    # §5⑥ SSE 13 集合 M6 已锁,M8 零回归
    assert SSE_EVENT_TYPES == {
        "text_delta", "tool_start", "tool_end", "tool_progress",
        "stream_event", "phase_change", "compact_boundary",
        "control_request", "control_cancel_request", "auth_status",
        "final", "error", "queue_position",
    }


def test_inv4_task_state_8_values_m7_unchanged():
    # §7.5.5 8 态(M7 已扩),M8 零回归
    assert {s.value for s in TaskState} == {
        "pending", "queued", "submitted", "running",
        "completed", "failed", "killed", "timeout",
    }


def test_inv5_resource_gate_behavior_5_values_m7_unchanged():
    # §7.3.9 五分支(M7 已落)
    assert {b.value for b in GateBehavior} == {
        "submit_now", "enqueue", "downscale", "cpu_fallback", "reject",
    }


def test_inv6_hpc_account_case_sensitive_m7_unchanged():
    # §11.7 严区分大小写(M7 已落)
    assert HPCAccount.SCW6CHB_GPU.value != HPCAccount.SCW6CHB_CPU.value


def test_inv7_deploy_artifacts_exist():
    # §6⑤ deploy/ 必备文件(M8 Task 3-5)
    root = Path(__file__).resolve().parent.parent / "deploy"
    for name in (
        "docker-compose.yml", "Dockerfile", "gunicorn.conf.py",
        "push_backend.sh", "push_frontend.sh",
        "hpc_submit_account.example.toml", "README.md",
    ):
        assert (root / name).is_file(), f"deploy/{name} 缺失"


def test_inv8_migrate_brains_script_callable():
    # M8 校准⑤ + §5⑨ migrate_brains 真灌入脚本可 import
    from scripts.migrate_brains import migrate_all  # noqa: F401


def test_inv9_make_app_default_factory_for_gunicorn():
    # §11.1 gunicorn CMD 入口存在(M8 Task 4)
    from praxis2.server.app import make_app_default  # noqa: F401
