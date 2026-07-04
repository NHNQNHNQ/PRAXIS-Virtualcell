"""Phase 1:ModuleRegistry 查询。4×8 support matrix 可生成;support→verdict 映射;
unsupported 模块 reject/caution;生物学错配返回 verdict。"""
import pytest

from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.biological_modules.registry import ModuleRegistry


@pytest.fixture(scope="module")
def reg():
    return ModuleRegistry()  # 默认 brains_root


def test_matrix_is_four_by_eight(reg):
    mat = reg.matrix()
    assert set(mat.keys()) == {"human", "mouse", "yeast", "bacteria"}
    for species, row in mat.items():
        assert set(row.keys()) == set(M.MODULE_ORDER), f"{species} 行不是 8 模块"


def test_support_query_returns_level_and_reason(reg):
    rec = reg.support("yeast", "cytoplasmic_metabolism")
    assert rec["support"] == "strong"
    rec2 = reg.support("yeast", "genetic_hub")
    assert rec2["support"] == "weak"
    assert rec2["reason"]


def test_verdict_mapping(reg):
    # strong/medium → 可用(非弃权);weak → caution;unsupported → reject
    assert reg.default_verdict("yeast", "cytoplasmic_metabolism") == "accept"
    assert reg.default_verdict("yeast", "genetic_hub") == "caution"


def test_unknown_species_or_module_is_unsupported(reg):
    assert reg.support("martian", "genetic_hub")["support"] == "unsupported"
    assert reg.default_verdict("martian", "genetic_hub") == "reject"
    with pytest.raises(KeyError):
        reg.support("human", "no_such_module")


def test_biological_mismatch_lookup(reg):
    # 铁律:细菌自噬 → caution;酵母组织 niche → reject
    assert reg.biological_mismatch("bacteria", "bacteria_autophagy") == "caution"
    assert reg.biological_mismatch("yeast", "tissue_spatial_niche") == "reject"
    assert reg.biological_mismatch("human", "anything_normal") is None


def test_display_name_honors_bacteria_alias(reg):
    assert reg.display_name("bacteria", "mitochondrial_energy_metabolism") \
        == "Energy metabolism / redox module"
