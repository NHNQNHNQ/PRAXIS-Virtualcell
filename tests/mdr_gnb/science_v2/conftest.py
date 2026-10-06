"""science_v2 测试共享:模型加载缓存隔离。

部分 pipeline 测试用 monkeypatch 把 `_MODELS_ROOT` 指向 tmp_path 并灌入微模型,再 cache_clear
以加载。但 `_load_sm_activity/_load_peptide_activity/_load_gsir` 是全局 lru_cache——若测试结束
不清缓存,tmp_path 微模型会泄漏进后续测试(如 tests/api 用真 artifact 的端到端测试会误取微模型
→ 环丙沙星等训练内化合物被判 OOD 弃权)。此 autouse fixture 在每个 science_v2 测试前后清缓存,
保证测试隔离(monkeypatch 恢复 _MODELS_ROOT 后,下次加载走真路径)。
"""
import pytest


@pytest.fixture(autouse=True)
def _clear_model_caches():
    import praxis_virtualcell.mdr_gnb.predictors.default_registry as dr

    def _clear():
        for loader in (dr._load_test_sm_activity, dr._load_test_peptide_activity, dr._load_test_gsir):
            loader.cache_clear()

    _clear()
    yield
    _clear()
