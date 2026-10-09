"""Phase 1:八模块规范定义。测 8 模块齐全、code M1-M8、engines 合法、bacteria M3 术语别名。"""
from praxis_virtualcell.agents.route_table import ENGINES
from praxis_virtualcell.biological_modules import modules as M


def test_eight_modules_in_stable_order():
    assert len(M.MODULE_ORDER) == 8
    assert M.MODULE_ORDER == [
        "membrane_system", "genetic_hub", "mitochondrial_energy_metabolism",
        "cytoplasmic_metabolism", "biosynthetic_network", "cytoskeletal_framework",
        "stress_processor", "degradation_machinery",
    ]


def test_each_module_has_m_code():
    for i, mid in enumerate(M.MODULE_ORDER, start=1):
        assert M.MODULES[mid]["code"] == f"M{i}"


def test_module_engines_are_known_engines():
    known = set(ENGINES)
    for mid in M.MODULE_ORDER:
        for eng in M.MODULES[mid]["engines"]:
            assert eng in known, f"{mid} 引用未知 engine: {eng}"


def test_bacteria_m3_display_alias():
    # 铁律:bacteria 不叫线粒体,前端显示 energy/redox
    assert M.display_name("mitochondrial_energy_metabolism", species="bacteria") \
        == "Energy metabolism / redox module"
    # 其它物种保留原名
    assert "Mitochond" in M.display_name("mitochondrial_energy_metabolism", species="yeast")


def test_module_ids_helper():
    assert set(M.module_ids()) == set(M.MODULE_ORDER)
    assert M.module("genetic_hub")["code"] == "M2"
