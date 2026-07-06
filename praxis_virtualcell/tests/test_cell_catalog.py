"""cell catalog 预设测试:只读展示层,species 不得越白名单(防与单一真相源漂移)。"""
from praxis_virtualcell.catalogs import load_cell_presets
from praxis_virtualcell.workflows.run_virtualcell_query import SUPPORTED_SPECIES


def test_presets_loaded_min_count():
    presets = load_cell_presets()
    assert len(presets) >= 10, f"预设过少:{len(presets)}"


def test_preset_fields_and_species_in_whitelist():
    for p in load_cell_presets():
        assert p.get("id") and p.get("cell_type") and p.get("label"), f"字段缺失:{p}"
        assert p["species"] in SUPPORTED_SPECIES, f"预设 species 越白名单:{p['species']}"


def test_all_four_species_covered():
    species = {p["species"] for p in load_cell_presets()}
    assert species == SUPPORTED_SPECIES, f"物种覆盖不全:{species} != {SUPPORTED_SPECIES}"


def test_preset_ids_unique():
    ids = [p["id"] for p in load_cell_presets()]
    assert len(ids) == len(set(ids)), f"预设 id 重复:{ids}"


def test_preset_modules_within_whitelist():
    """预设若声明 modules,每个必须 ∈ MODULE_ORDER(防展示层与单一真相源漂移)。"""
    from praxis_virtualcell.biological_modules.modules import MODULE_ORDER
    for p in load_cell_presets():
        mods = p.get("modules") or []
        assert isinstance(mods, list), f"{p['id']} modules 非 list"
        for m in mods:
            assert m in MODULE_ORDER, f"{p['id']} module 越白名单: {m}"


def test_every_preset_has_modules():
    """本 Phase 起每个预设都标注 supported_modules(前端 module_context 步消费)。"""
    for p in load_cell_presets():
        assert p.get("modules"), f"{p['id']} 缺 modules 标注"
