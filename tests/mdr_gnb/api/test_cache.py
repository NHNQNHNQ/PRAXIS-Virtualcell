"""9.3 Redis 缓存/状态(可选,不做科学证据来源)。fakeredis DI → 常规套件跑。
缓存的是已算好的确定性响应:命中返回逐字相等,不改科学结论。"""
import fakeredis

from praxis_virtualcell.mdr_gnb.api.cache import PredictionCache


def _cache():
    return PredictionCache(fakeredis.FakeStrictRedis())


def test_cache_set_get_roundtrip():
    c = _cache()
    resp = {"task_id": "mdr-x", "report": {"sir": "R"}, "warnings": []}
    c.set("mdr-x", resp)
    assert c.get("mdr-x") == resp


def test_cache_miss_returns_none():
    assert _cache().get("nope") is None


def test_cache_roundtrip_byte_identical():
    """缓存不得改内容:取回逐字等于存入。"""
    c = _cache()
    resp = {"task_id": "mdr-y", "sir_prob": {"S": 0.2, "I": 0.0, "R": 0.8}}
    c.set("mdr-y", resp)
    assert c.get("mdr-y") == resp


def test_status_set_get():
    """轻量 job 状态(临时):enqueued → done。"""
    c = _cache()
    c.set_status("job1", "enqueued")
    assert c.get_status("job1") == "enqueued"
    c.set_status("job1", "done")
    assert c.get_status("job1") == "done"


def test_status_missing_none():
    assert _cache().get_status("ghost") is None
