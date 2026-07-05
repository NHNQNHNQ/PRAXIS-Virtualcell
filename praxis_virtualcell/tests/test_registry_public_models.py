"""Phase 6:registry 公开模型声明(gears/scgpt)+ assets schema 校验。
铁律:ckpt 挪出硬编码 → registry assets 声明(filename + sha256 占位 + source_note);
assets 结构坏 → ValueError(fail-closed)。gears/scgpt 仍 planned(缺 torch/ckpt → broker fail-closed)。"""
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
    assert e["status"] == "planned"                  # 缺 torch/ckpt → 仍 planned,不静默 available
    assert e["wrapper"].endswith("scgpt_wrapper.ScgptWrapper")


def test_gears_and_scgpt_have_assets_declared(reg):
    for name in ("gears", "scgpt"):
        e = reg.get(name)
        assert e.get("assets"), f"{name} 缺 assets 声明(ckpt 须挪出硬编码进 registry)"
        for a in e["assets"]:
            assert "filename" in a and "sha256" in a  # sha256 可为 null 占位,但键必须在
            assert "source_note" in a                 # 远端获取路径(requires_manual_fetch 取数流程)


def test_gears_and_scgpt_have_provenance(reg):
    assert reg.get("gears")["provenance"]["metrics"]["pearson_de"] == pytest.approx(0.8392, abs=1e-4)
    sp = reg.get("scgpt")["provenance"]["metrics"]
    assert sp["delta_pearson"] == pytest.approx(0.4407, abs=1e-4)


def test_query_by_module_genetic_hub_includes_public_models(reg):
    names = {e["name"] for e in reg.by_module("genetic_hub")}
    assert {"gears", "scgpt"} <= names


def test_illegal_assets_shape_is_rejected(tmp_path):
    """assets 条目缺 filename/sha256 键 → ValueError(fail-closed)。"""
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
        "      - filename: w.pt\n"                    # 缺 sha256 键
        "        source_note: remote\n",
        encoding="utf-8")
    with pytest.raises(ValueError) as ei:
        ModelZooRegistry(registry_path=str(bad))
    assert "assets" in str(ei.value) or "sha256" in str(ei.value)
