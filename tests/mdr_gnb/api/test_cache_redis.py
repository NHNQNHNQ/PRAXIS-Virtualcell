"""9.3 真 Redis 集成测。@integration;缺 MDR_REDIS_URL/连接失败则 skip。Redis 走 53。"""
import os

import pytest

from praxis_virtualcell.mdr_gnb.api.cache import PredictionCache, make_redis_client

pytestmark = pytest.mark.integration


@pytest.fixture()
def redis_cache():
    url = os.environ.get("MDR_REDIS_URL")
    if not url:
        pytest.skip("MDR_REDIS_URL 未设:无本地 Redis,跳过 Redis 集成测")
    client = make_redis_client(url)
    try:
        client.ping()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Redis 连接失败:{e}")
    return PredictionCache(client)


def test_redis_roundtrip(redis_cache):
    resp = {"task_id": "mdr-it", "report": {"sir": "R"}}
    redis_cache.set("mdr-it", resp)
    assert redis_cache.get("mdr-it") == resp
