"""gpu_pool — mock ssh_run 返 check_gpus.sh 的 JSON。"""
import json
from unittest.mock import AsyncMock, patch

import pytest

from praxis2.md.gpu_pool import fetch_gpu_pool
from praxis2.md.ssh import SshConfig


def _cfg() -> SshConfig:
    return SshConfig(host="x", user="x", key_path="/tmp/fake-key")


@pytest.mark.asyncio
async def test_parses_check_gpus_json():
    fake_json = json.dumps({
        "total_slots": 8, "busy_slots": 3, "free_slots": 5,
        "hosts": ["bio000071", "bio000072"],
        "gpus": [
            {"host":"bio000071","gpu_id":0,"name":"RTX4090","mem_mb":"100/24000",
             "util_pct":2,"busy":False,"busy_label":None},
            {"host":"bio000071","gpu_id":1,"name":"RTX4090","mem_mb":"22000/24000",
             "util_pct":95,"busy":True,"busy_label":"in_use"},
        ],
    })
    with patch("praxis2.md.gpu_pool.ssh_run",
               AsyncMock(return_value=fake_json)):
        result = await fetch_gpu_pool(cfg=_cfg(), script_path="~/check_gpus.sh")
    assert result["total_slots"] == 8
    assert result["busy_slots"] == 3
    assert len(result["gpus"]) == 2


@pytest.mark.asyncio
async def test_ssh_failure_returns_empty_pool():
    """ssh_run 抛 → 返回 stub 空 pool(不阻塞 FE)。"""
    with patch("praxis2.md.gpu_pool.ssh_run",
               AsyncMock(side_effect=RuntimeError("ssh_failed timeout"))):
        result = await fetch_gpu_pool(cfg=_cfg(), script_path="~/check_gpus.sh")
    assert result == {
        "total_slots": 0, "busy_slots": 0, "free_slots": 0,
        "hosts": [], "gpus": [],
    }


@pytest.mark.asyncio
async def test_malformed_json_returns_empty_pool():
    with patch("praxis2.md.gpu_pool.ssh_run",
               AsyncMock(return_value="not json")):
        result = await fetch_gpu_pool(cfg=_cfg(), script_path="~/check_gpus.sh")
    assert result["total_slots"] == 0
