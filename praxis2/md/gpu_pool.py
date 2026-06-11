"""GPU 池状态查询 — 调 .53 上 ~/check_gpus.sh,解析 JSON。

ssh 错 / 解析失败 → 返 stub 空 pool,FE 不挂(M11.2 carry: 加 caching)。
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from praxis2.md.ssh import SshConfig

log = logging.getLogger(__name__)


_EMPTY: dict[str, Any] = {
    "total_slots": 0, "busy_slots": 0, "free_slots": 0,
    "hosts": [], "gpus": [],
}


async def fetch_gpu_pool(*, cfg: "SshConfig", script_path: str) -> dict[str, Any]:
    """跑 .53 上 check_gpus.sh,返 GpuPoolStatus dict。"""
    from praxis2.md.ssh import ssh_run  # noqa: PLC0415
    try:
        out = await ssh_run(cfg, f"bash {script_path}")
    except Exception:  # noqa: BLE001
        log.exception("gpu_pool ssh failed")
        return dict(_EMPTY)
    try:
        result = json.loads(out)
    except ValueError:
        log.warning("gpu_pool: malformed JSON: %r", out[:200])
        return dict(_EMPTY)
    for k, v in _EMPTY.items():
        result.setdefault(k, v)
    return result
