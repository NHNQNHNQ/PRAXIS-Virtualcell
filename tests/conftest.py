import os

import pytest


def _docker_pg_redis_available() -> bool:
    # 仅当显式声明可用时才跑集成测试;否则 skip(本机无 docker 不阻塞 M0)
    return os.environ.get("PRAXIS_INTEGRATION") == "1"


def pytest_collection_modifyitems(config, items):
    if _docker_pg_redis_available():
        return
    skip = pytest.mark.skip(reason="integration: set PRAXIS_INTEGRATION=1 with docker PG/Redis")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
