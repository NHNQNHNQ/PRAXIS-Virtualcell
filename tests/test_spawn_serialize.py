"""v0.15.0 顺手修(playwright e2e 暴露老 bug):
repo 返回字段(id/prompt/tokens_in/completed_at)与 FE SpawnModal
+ SpawnTask interface 期望(task_id/message/in_tokens/finished_at)错位,
任务非空时 t.message.slice() 在 FE 崩。

handler 加 _serialize_task wrap 后,FE 字段全对齐。
"""
from __future__ import annotations

from praxis2.spawn.handlers import _serialize_task


def test_serialize_task_renames_to_fe_contract():
    """repo dict → FE 期望 key,缺失字段默认值不让 FE 崩。"""
    row = {
        "id": "t-1",
        "user_id": "u-1",
        "model": "deepseek-v4-pro",
        "prompt": "print(1)",
        "status": "done",
        "answer": "1",
        "tokens_in": 5,
        "tokens_out": 3,
        "cost_li": 12,
        "error": None,
        "created_at": "2026-06-01 08:00:00",
        "started_at": "2026-06-01 08:00:01",
        "completed_at": "2026-06-01 08:00:02",
    }
    out = _serialize_task(row)
    # FE 期望 key 全在
    assert out["task_id"] == "t-1"
    assert out["message"] == "print(1)"
    assert out["in_tokens"] == 5
    assert out["out_tokens"] == 3
    assert out["finished_at"] == "2026-06-01 08:00:02"
    # repo 未存的字段给默认值,不让 FE undefined.slice 崩
    assert out["agent"] == "spawn"
    assert out["label"] is None
    assert out["exit_code"] is None


def test_serialize_task_empty_prompt_returns_empty_string():
    """prompt 为 None 时 message 必须是 '',让 FE slice() 安全。"""
    row = {"id": "t-2", "prompt": None, "status": "starting"}
    out = _serialize_task(row)
    assert out["message"] == ""  # 不能是 None
    # FE 后续做 message.slice(0, 80) 必不崩


def test_serialize_task_zero_tokens_default():
    """tokens_in / tokens_out 缺失 → 默认 0,FE 数字渲染不崩。"""
    row = {"id": "t-3", "status": "pending"}
    out = _serialize_task(row)
    assert out["in_tokens"] == 0
    assert out["out_tokens"] == 0
