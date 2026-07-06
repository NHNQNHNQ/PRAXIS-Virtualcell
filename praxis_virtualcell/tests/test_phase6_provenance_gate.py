"""Phase 6 完成闸门:registry 声明 ↔ wrapper 声明 跨源一致 + 可分发性齐全 + fail-closed 纵深。
铁律:registry.provenance/scope 与 wrapper.declare_* 一致(防双真相源);每个公开模型
assets+source_note+provenance 齐(ckpt 挪出硬编码可指认);缺依赖/缺 ckpt → broker fail-closed。"""
import importlib

import pytest

from praxis_virtualcell.model_zoo.registry import ModelZooRegistry


def _wrapper_instance(class_path: str):
    mod, cls = class_path.rsplit(".", 1)
    return getattr(importlib.import_module(mod), cls)()


@pytest.fixture(scope="module")
def reg():
    return ModelZooRegistry()


@pytest.mark.parametrize("name", ["gears", "scgpt"])
def test_registry_module_matches_wrapper_scope(reg, name):
    """registry.module == wrapper.declare_scope()['module'](防双真相源)。"""
    e = reg.get(name)
    w = _wrapper_instance(e["wrapper"])
    assert w.declare_scope()["module"] == e["module"]
    assert set(e["species"]) <= set(w.declare_scope()["species"]) or \
           set(w.declare_scope()["species"]) <= set(e["species"])


@pytest.mark.parametrize("name", ["gears", "scgpt"])
def test_registry_anchor_matches_wrapper_provenance(reg, name):
    """registry.provenance 锚点 == wrapper.declare_provenance() 锚点(数字一致)。"""
    e = reg.get(name)
    w = _wrapper_instance(e["wrapper"])
    wp = w.declare_provenance()
    if name == "gears":
        assert wp["metrics"]["pearson_de"] == pytest.approx(
            e["provenance"]["metrics"]["pearson_de"], abs=1e-4)
        assert wp["not_comparable_to_donor_base"] is True
    else:
        assert wp["metrics"]["delta_pearson"] == pytest.approx(
            e["provenance"]["metrics"]["delta_pearson"], abs=1e-4)
        assert wp["not_comparable_to_donor_base"] is False


@pytest.mark.parametrize("name", ["gears", "scgpt"])
def test_distributability_declared(reg, name):
    """可分发性齐全:assets(含 source_note)+ provenance.distributable 标注,ckpt 可指认。"""
    e = reg.get(name)
    assert e["assets"] and all("source_note" in a for a in e["assets"])
    assert e["provenance"]["distributable"] is False   # 需 torch+GPU+ckpt,缺则 fail-closed


def test_public_models_wrapper_importable(reg):
    """wrapper 类路径可 import(可分发性:装了 wheel 的人能拿到类,即便模型 unavailable)。"""
    for name in ("gears", "scgpt"):
        w = _wrapper_instance(reg.get(name)["wrapper"])
        assert w.declare_scope()["module"] == "genetic_hub"


def test_broker_fail_closed_depth_for_public_models():
    """红线 6 纵深:本地 broker 对 gears/scgpt 全 available=False(缺 torch/ckpt),reason 非空。"""
    from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
    from praxis_virtualcell.core.bus import MessageBus
    from praxis_virtualcell.core.message import AgentMessage

    for name in ("gears", "scgpt"):
        bus = MessageBus()
        ModelBrokerAgent().handle(AgentMessage(
            "q", "C", "ModelBrokerAgent", "model_request", {"model_name": name}, "t"), bus)
        p = bus.latest("model_broker_result").payload
        assert p["available"] is False and p["reason"]
        assert p["wrapper"]                              # 不隐藏:类路径仍可见
