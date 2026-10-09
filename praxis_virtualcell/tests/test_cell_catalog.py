"""Tests for cell catalog."""
from praxis_virtualcell.catalogs import load_cell_presets
from praxis_virtualcell.workflows.run_virtualcell_query import SUPPORTED_SPECIES


def test_presets_loaded_min_count():
    presets = load_cell_presets()
    assert len(presets) >= 10, f"Too few presets: {len(presets)}"


def test_preset_fields_and_species_in_whitelist():
    for p in load_cell_presets():
        assert p.get("id") and p.get("cell_type") and p.get("label"), f"Missing fields: {p}"
        assert p["species"] in SUPPORTED_SPECIES, f"Preset species is outside the allowlist: {p['species']}"


def test_all_four_species_covered():
    species = {p["species"] for p in load_cell_presets()}
    assert species == SUPPORTED_SPECIES, f"Incomplete species coverage: {species} != {SUPPORTED_SPECIES}"


def test_preset_ids_unique():
    ids = [p["id"] for p in load_cell_presets()]
    assert len(ids) == len(set(ids)), f"Duplicate preset IDs: {ids}"


def test_preset_modules_within_whitelist():
    """Verify preset modules within whitelist."""
    from praxis_virtualcell.biological_modules.modules import MODULE_ORDER
    for p in load_cell_presets():
        mods = p.get("modules") or []
        assert isinstance(mods, list), f"{p['id']} modules must be a list"
        for m in mods:
            assert m in MODULE_ORDER, f"{p['id']} module is outside the allowlist: {m}"


def test_every_preset_has_modules():
    """Verify every preset has modules."""
    for p in load_cell_presets():
        assert p.get("modules"), f"{p['id']} missing modules declaration"
