"""Tests for registry public models."""
import pytest

from praxis_virtualcell.model_zoo.registry import ModelZooRegistry


@pytest.fixture(scope="module")
def reg():
    return ModelZooRegistry()


def test_scgpt_entry_present_and_planned(reg):
    e = reg.get("scgpt")
    assert e["type"] == "public_model"
    assert e["module"] == "genetic_hub"
    assert "human" in e["species"]
    assert e["status"] == "planned"
    assert e["wrapper"].endswith("scgpt_wrapper.ScgptWrapper")


def test_gears_and_scgpt_have_assets_declared(reg):
    for name in ("gears", "scgpt"):
        e = reg.get(name)
        assert e.get("assets"), f"{name} missing assets declaration; checkpoints belong in the registry"
        for a in e["assets"]:
            assert "filename" in a and "sha256" in a
            assert "source_note" in a


def test_gears_and_scgpt_have_provenance(reg):
    assert reg.get("gears")["provenance"]["metrics"]["pearson_de"] == pytest.approx(0.8392, abs=1e-4)
    sp = reg.get("scgpt")["provenance"]["metrics"]
    assert sp["delta_pearson"] == pytest.approx(0.4407, abs=1e-4)


def test_query_by_module_genetic_hub_includes_public_models(reg):
    names = {e["name"] for e in reg.by_module("genetic_hub")}
    assert {"gears", "scgpt"} <= names


def test_gears_and_scgpt_assets_sha256_backfilled(reg):
    """Verify gears and scgpt assets sha256 backfilled."""
    import re
    hex64 = re.compile(r"^[0-9a-f]{64}$")
    for name in ("gears", "scgpt"):
        for a in reg.get(name)["assets"]:
            assert a["sha256"] is not None, f"{name}/{a['filename']} sha256 must not be null"
            assert hex64.match(a["sha256"]), f"{name}/{a['filename']} sha256 must contain 64 hexadecimal characters"
    gears_files = {a["filename"] for a in reg.get("gears")["assets"]}
    assert gears_files == {"model.pt", "config.pkl"}, "GEARS assets must be the actual artifacts produced by GEARS save"
    assert reg.get("gears")["status"] == "planned"


def test_illegal_assets_shape_is_rejected(tmp_path):
    """Verify illegal assets shape is rejected."""
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "models:\n"
        "  m:\n"
        "    name: m\n"
        "    type: public_model\n"
        "    species: [human]\n"
        "    module: genetic_hub\n"
        "    task: t\n"
        "    source: 'remote:x'\n"
        "    license: MIT\n"
        "    status: planned\n"
        "    wrapper: x.Y\n"
        "    version: v1\n"
        "    requires: [torch]\n"
        "    reliability_policy: ml_disagreement\n"
        "    assets:\n"
        "      - filename: w.pt\n"
        "        source_note: remote\n",
        encoding="utf-8")
    with pytest.raises(ValueError) as ei:
        ModelZooRegistry(registry_path=str(bad))
    assert "assets" in str(ei.value) or "sha256" in str(ei.value)
