import os

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "llm: 需要真实 DEEPSEEK_API_KEY + 网络(无 key 自动 skip)")
    config.addinivalue_line(
        "markers", "remote: 需远端 GPU + torch + donor(Mac 无 torch 时 skip)")


def pytest_collection_modifyitems(config, items):
    from praxis_virtualcell.core.config import load_env
    load_env()  # 本地有 .env 则把 key 注入 env,llm 测试就能真跑

    # remote:无 torch(Mac 本地)则 skip ml 测试。
    # 须放在 llm 的 early-return 之前 —— 否则 Mac .env 有 key 时会提前 return,remote 跳不到。
    try:
        import torch  # noqa: F401
        has_torch = True
    except Exception:
        has_torch = False
    if not has_torch:
        skip_remote = pytest.mark.skip(reason="无 torch(Mac 本地),跳过 remote 标记测试")
        for item in items:
            if "remote" in item.keywords:
                item.add_marker(skip_remote)

    # llm:无 key 则 skip
    if os.environ.get("DEEPSEEK_API_KEY"):
        return
    skip = pytest.mark.skip(reason="无 DEEPSEEK_API_KEY,跳过 llm 测试")
    for item in items:
        if "llm" in item.keywords:
            item.add_marker(skip)
