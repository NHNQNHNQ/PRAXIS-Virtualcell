"""Phase 1:物种特异生物学守卫(数据驱动)。铁律:
- bacteria 不能强行解释为自噬/线粒体 → mismatch caution
- yeast/bacteria 单细胞无组织 niche → mismatch reject
- 弱支持模块默认 caution,不静默 accept"""
import pytest

from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.biological_modules.registry import ModuleRegistry

reg = ModuleRegistry()

# (species, query, 期望 verdict)
_MISMATCH = [
    ("bacteria", "bacteria_autophagy", "caution"),
    ("bacteria", "mitochondria", "caution"),
    ("yeast", "tissue_spatial_niche", "reject"),
    ("yeast", "mammalian_cell_communication", "reject"),
]


@pytest.mark.parametrize("species,query,verdict", _MISMATCH,
                         ids=[f"{s}_{q}" for s, q, _ in _MISMATCH])
def test_biological_mismatch_verdict(species, query, verdict):
    assert reg.biological_mismatch(species, query) == verdict


def test_weak_modules_never_silently_accept():
    """所有 weak 模块默认裁决必须是 caution,不能是 accept(诚实:弱支持要带告警)。"""
    offenders = []
    for sp in ("human", "mouse", "yeast", "bacteria"):
        for mid in M.MODULE_ORDER:
            rec = reg.support(sp, mid)
            if rec["support"] == "weak" and reg.default_verdict(sp, mid) == "accept":
                offenders.append(f"{sp}/{mid}")
    assert offenders == [], f"弱支持模块被静默 accept: {offenders}"


def test_unsupported_modules_reject():
    """unsupported 模块默认 reject。"""
    for sp in ("human", "mouse", "yeast", "bacteria"):
        for mid in M.MODULE_ORDER:
            if reg.support(sp, mid)["support"] == "unsupported":
                assert reg.default_verdict(sp, mid) == "reject"


def test_bacteria_m3_not_called_mitochondria_in_display():
    """bacteria 的 M3 前端显示不得出现 'Mitochondrial'。"""
    name = reg.display_name("bacteria", "mitochondrial_energy_metabolism")
    assert "Mitochond" not in name
