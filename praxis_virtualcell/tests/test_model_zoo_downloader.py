"""Phase 2:下载契约(远端 gated)。铁律:Phase 2 不真下载大模型。
- 本地资产(cobra_bundled_* / local:)→ resolved(直接指认)
- 远端(remote:...)→ requires_manual_fetch(不假装下载成功,不静默)
- 缺 source → ValueError"""
import pytest

from praxis_virtualcell.model_zoo.downloader import resolve_source


def test_cobra_bundled_source_is_resolved():
    r = resolve_source({"name": "ecoli_gem", "source": "cobra_bundled_textbook", "requires": ["cobra"]})
    assert r["status"] == "resolved"
    assert r["fetch"] == "none"           # 本地自带,无需下载


def test_local_data_source_is_resolved():
    r = resolve_source({"name": "yeast_gem", "source": "local:data/gems/iMM904.xml.gz",
                        "requires": ["cobra"]})
    assert r["status"] == "resolved"
    assert "data/gems/iMM904.xml.gz" in r["path"]


def test_remote_source_is_gated_not_silently_ok():
    """铁律:远端权重 → requires_manual_fetch,绝不假装下载成功。"""
    r = resolve_source({"name": "gears", "source": "remote:gears_ckpt", "requires": ["torch", "gpu"]})
    assert r["status"] == "requires_manual_fetch"
    assert r["available"] is False
    assert "torch" in r["reason"] or "manual" in r["reason"] or "remote" in r["reason"]


def test_missing_source_raises():
    with pytest.raises(ValueError):
        resolve_source({"name": "broken", "requires": []})
