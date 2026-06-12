import os

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "llm: 需要真实 DEEPSEEK_API_KEY + 网络(无 key 自动 skip)")


def pytest_collection_modifyitems(config, items):
    from praxis_virtualcell.core.config import load_env
    load_env()  # 本地有 .env 则把 key 注入 env,llm 测试就能真跑
    if os.environ.get("DEEPSEEK_API_KEY"):
        return
    skip = pytest.mark.skip(reason="无 DEEPSEEK_API_KEY,跳过 llm 测试")
    for item in items:
        if "llm" in item.keywords:
            item.add_marker(skip)
