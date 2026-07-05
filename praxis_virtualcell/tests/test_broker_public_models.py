"""Phase 6:broker 对公开模型(gears/scgpt)fail-closed 纵深。
铁律(红线 6):planned/缺 torch/缺 ckpt/sha 占位 → available=False + reason 点名缺什么,绝不静默 accept。
本地无 torch → gears/scgpt 在 requires 关就 fail-closed(reason 点名 torch/gpu)。
assets 关:即便依赖齐,ckpt 缺失/sha 占位/sha 不匹配 → 仍 available=False(第二道锁)。"""
import hashlib
import importlib.util

from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.model_zoo.cache import ModelCache

_HAS_TORCH = importlib.util.find_spec("torch") is not None


def _ask(name):
    return AgentMessage("q1", "Client", "ModelBrokerAgent", "model_request",
                        {"model_name": name}, "t1")


def _resolve(name, cache=None):
    bus = MessageBus()
    ModelBrokerAgent(cache=cache).handle(_ask(name), bus)
    return bus.latest("model_broker_result").payload


def test_gears_fail_closed_missing_torch_locally():
    """本地无 torch → gears requires[torch,gpu] 关 fail-closed,reason 点名依赖。不静默 accept。"""
    if _HAS_TORCH:
        import pytest
        pytest.skip("本地有 torch 时此断言不成立;缺 torch 断言见此路径")
    p = _resolve("gears")
    assert p["available"] is False
    assert p["status"] == "planned"
    assert "torch" in p["reason"] or "gpu" in p["reason"] or "planned" in p["reason"]


def test_scgpt_fail_closed_locally():
    p = _resolve("scgpt")
    assert p["available"] is False               # planned + 缺 torch/ckpt → 不静默 available
    assert p["reason"]


def test_wrapper_class_path_still_visible_when_unavailable():
    """fail-closed 不等于隐藏:registry 里 wrapper 类路径仍可见(可分发性声明),只是不可用。"""
    p = _resolve("scgpt")
    assert p["wrapper"].endswith("scgpt_wrapper.ScgptWrapper")
    assert p["available"] is False


def test_assets_sha_placeholder_gates_requires_manual_fetch(tmp_path):
    """assets sha256=null(占位未填)→ 即便前三关齐(status=available/requires 空/source resolved)
    也判 requires_manual_fetch(不静默 available)。用 status=available 的临时 registry,让请求真正
    走到 assets 关(真实 scgpt status=planned 会在②关拦下,到不了 assets 关,故不可用它验此分支)。
    关键:此处**故意落一个真文件**(sha=null 却权重在位),以证明"占位未锁即拦"是靠 sha=null
    这道 gates 拦的,而非靠文件缺失——若删掉 sha=null gates 分支,会 fallthrough 到
    cache.check(sha256=None) 且文件在位 → available=True,本测试即 FAIL(变异被逮住,非空转)。"""
    import praxis_virtualcell.agents.model_broker_agent as mba
    from praxis_virtualcell.model_zoo.registry import ModelZooRegistry

    reg_yaml = tmp_path / "reg.yaml"
    reg_yaml.write_text(
        "models:\n"
        "  tm:\n"
        "    name: tm\n"
        "    type: public_model\n"
        "    species: [human]\n"
        "    module: genetic_hub\n"
        "    task: t\n"
        "    source: cobra_bundled_textbook\n"   # source 关放行(resolved)
        "    license: MIT\n"
        "    status: available\n"                 # available 才走到 assets 关
        "    wrapper: x.Y\n"
        "    version: v1\n"
        "    requires: []\n"                       # requires 空 → ③关放行,无需 monkeypatch
        "    reliability_policy: p\n"
        "    assets:\n"
        "      - filename: w.pt\n"
        "        sha256: null\n"                   # sha256 占位未填 → 应判 requires_manual_fetch
        "        source_note: local\n",
        encoding="utf-8")
    cache = ModelCache(root=str(tmp_path))
    ap = cache.asset_path("tm", "w.pt")
    ap.parent.mkdir(parents=True, exist_ok=True)
    ap.write_bytes(b"weights-present-but-sha-unregistered")  # 文件在位,但 sha 未登记 → 仍须拦

    bus = MessageBus()
    mba.ModelBrokerAgent(registry=ModelZooRegistry(registry_path=str(reg_yaml)),
                         cache=cache).handle(_ask("tm"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is False               # sha=null → 即便权重在位也不静默 available
    assert "asset" in p["reason"] or "manual_fetch" in p["reason"] or "sha256" in p["reason"]


def test_assets_present_and_sha_match_passes_asset_gate(tmp_path, monkeypatch):
    """assets 齐 + sha 对 → assets 关放行(证明关不是恒 False 空转)。用临时 registry + 真文件 sha。"""
    import praxis_virtualcell.agents.model_broker_agent as mba
    from praxis_virtualcell.model_zoo.registry import ModelZooRegistry
    monkeypatch.setattr(mba, "_dep_available", lambda dep: True)

    payload = b"fake-weights"
    sha = hashlib.sha256(payload).hexdigest()
    reg_yaml = tmp_path / "reg.yaml"
    reg_yaml.write_text(
        "models:\n"
        "  tm:\n"
        "    name: tm\n"
        "    type: public_model\n"
        "    species: [human]\n"
        "    module: genetic_hub\n"
        "    task: t\n"
        "    source: cobra_bundled_textbook\n"   # source 关放行(resolved)
        "    license: MIT\n"
        "    status: available\n"                 # available 才走到 assets 关
        "    wrapper: x.Y\n"
        "    version: v1\n"
        "    requires: []\n"
        "    reliability_policy: p\n"
        "    assets:\n"
        "      - filename: w.pt\n"
        f"        sha256: '{sha}'\n"
        "        source_note: local\n",
        encoding="utf-8")
    cache = ModelCache(root=str(tmp_path))
    ap = cache.asset_path("tm", "w.pt")
    ap.parent.mkdir(parents=True, exist_ok=True)
    ap.write_bytes(payload)                       # 落真文件,sha 对

    bus = MessageBus()
    mba.ModelBrokerAgent(registry=ModelZooRegistry(registry_path=str(reg_yaml)),
                         cache=cache).handle(_ask("tm"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is True                 # 依赖齐 + source resolved + assets sha 对 → available


def test_assets_sha_mismatch_fail_closed(tmp_path, monkeypatch):
    """assets sha 不匹配(篡改/版本错)→ available=False(fail-closed,红线 6)。"""
    import praxis_virtualcell.agents.model_broker_agent as mba
    from praxis_virtualcell.model_zoo.registry import ModelZooRegistry
    monkeypatch.setattr(mba, "_dep_available", lambda dep: True)

    wrong_sha = hashlib.sha256(b"expected").hexdigest()
    reg_yaml = tmp_path / "reg.yaml"
    reg_yaml.write_text(
        "models:\n"
        "  tm:\n"
        "    name: tm\n    type: public_model\n    species: [human]\n"
        "    module: genetic_hub\n    task: t\n    source: cobra_bundled_textbook\n"
        "    license: MIT\n    status: available\n    wrapper: x.Y\n    version: v1\n"
        "    requires: []\n    reliability_policy: p\n"
        "    assets:\n"
        "      - filename: w.pt\n"
        f"        sha256: '{wrong_sha}'\n"
        "        source_note: local\n",
        encoding="utf-8")
    cache = ModelCache(root=str(tmp_path))
    ap = cache.asset_path("tm", "w.pt")
    ap.parent.mkdir(parents=True, exist_ok=True)
    ap.write_bytes(b"actual-different-bytes")     # sha 不匹配

    bus = MessageBus()
    mba.ModelBrokerAgent(registry=ModelZooRegistry(registry_path=str(reg_yaml)),
                         cache=cache).handle(_ask("tm"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is False
    assert "sha256" in p["reason"] or "asset" in p["reason"]
