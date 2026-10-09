"""Phase 2:ModelZooRegistry —— 声明式模型注册表 schema + 查询 + 白名单校验。
铁律:module 必须 ∈ MODULE_ORDER;status 合法枚举;未知 name → KeyError(不静默返 None)。"""
import pytest

from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.model_zoo.registry import (
    LEGAL_STATUS,
    LEGAL_TYPES,
    ModelZooRegistry,
)


@pytest.fixture(scope="module")
def reg():
    return ModelZooRegistry()  # 默认读 model_zoo/registry.yaml


def test_seed_entries_present(reg):
    names = set(reg.names())
    # 至少三条种子:一条 available 真模型、一条 planned 公开模型、一条 self_trained
    assert {"ecoli_gem", "gears", "yeast_deletion_fitness"} <= names


def test_every_entry_schema_is_legal(reg):
    for name in reg.names():
        e = reg.get(name)
        assert e["name"] == name
        assert e["type"] in LEGAL_TYPES, f"{name} 非法 type: {e['type']}"
        assert e["status"] in LEGAL_STATUS, f"{name} 非法 status: {e['status']}"
        assert e["module"] in M.MODULE_ORDER, f"{name} module 越白名单: {e['module']}"
        assert isinstance(e.get("requires", []), list)
        assert e.get("species"), f"{name} 缺 species"
        assert e.get("wrapper"), f"{name} 缺 wrapper 类路径"


def test_query_by_module_and_species(reg):
    ecoli = reg.by_module("cytoplasmic_metabolism")
    assert "ecoli_gem" in {e["name"] for e in ecoli}
    bact = reg.by_species("bacteria")
    assert "ecoli_gem" in {e["name"] for e in bact}


def test_status_helpers(reg):
    assert reg.status("ecoli_gem") == "available"
    assert reg.status("gears") == "planned"
    assert reg.is_available("ecoli_gem") is True
    assert reg.is_available("gears") is False


def test_unknown_name_raises_keyerror(reg):
    with pytest.raises(KeyError):
        reg.get("no_such_model")
    with pytest.raises(KeyError):
        reg.status("no_such_model")


def test_illegal_module_in_yaml_is_rejected(tmp_path):
    """注册表加载时校验 module ∈ MODULE_ORDER;非法 module → ValueError(fail-closed)。"""
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "models:\n"
        "  broken:\n"
        "    name: broken\n"
        "    type: public_model\n"
        "    species: [human]\n"
        "    module: not_a_real_module\n"
        "    task: growth\n"
        "    source: local\n"
        "    license: MIT\n"
        "    status: available\n"
        "    wrapper: x.Y\n"
        "    version: '1'\n"
        "    requires: []\n"
        "    reliability_policy: gem_growth\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        ModelZooRegistry(registry_path=str(bad))
