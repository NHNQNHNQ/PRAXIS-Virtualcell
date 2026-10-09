"""Phase 2:model zoo 本地缓存 + 版本锁(sha256)。铁律:资产缺失/sha 不匹配 → unavailable(fail-closed),
绝不 silent accept。测:命中 / 未命中 / sha 不匹配 / 版本锁行为。"""
import hashlib

from praxis_virtualcell.model_zoo.cache import ModelCache


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_missing_asset_is_unavailable(tmp_path):
    cache = ModelCache(root=str(tmp_path))
    st = cache.check("gears", "weights.pt")
    assert st.available is False
    assert "not_found" in st.reason or "missing" in st.reason


def test_present_asset_without_lock_is_available(tmp_path):
    cache = ModelCache(root=str(tmp_path))
    p = cache.asset_path("ecoli_gem", "model.xml")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"SBML")
    st = cache.check("ecoli_gem", "model.xml")            # 无 sha 锁 → 存在即可用
    assert st.available is True


def test_sha256_lock_match_is_available(tmp_path):
    cache = ModelCache(root=str(tmp_path))
    p = cache.asset_path("m", "w.bin")
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = b"hello-weights"
    p.write_bytes(payload)
    st = cache.check("m", "w.bin", sha256=_sha256(payload))
    assert st.available is True


def test_sha256_mismatch_is_unavailable(tmp_path):
    """铁律:sha 不匹配 → unavailable(可能被篡改/版本错),绝不 silent accept。"""
    cache = ModelCache(root=str(tmp_path))
    p = cache.asset_path("m", "w.bin")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"actual-bytes")
    st = cache.check("m", "w.bin", sha256=_sha256(b"expected-different"))
    assert st.available is False
    assert "sha256_mismatch" in st.reason


def test_asset_path_is_namespaced_by_model(tmp_path):
    cache = ModelCache(root=str(tmp_path))
    pa = cache.asset_path("model_a", "f.pt")
    pb = cache.asset_path("model_b", "f.pt")
    assert pa != pb
    assert "model_a" in str(pa) and "model_b" in str(pb)
