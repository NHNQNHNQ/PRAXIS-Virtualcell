"""Phase 7:broker 对 self_trained 模型 fail-closed 纵深(红线 6)。
yeast_deletion_fitness(planned)→ status 关 fail-closed;self_trained source → source 关 fail-closed;
sha 占位 → assets 关 fail-closed。变异逮捕:self_trained + 依赖齐 + 落 assets sha 对 → available(关非空转)。
broker 五关不改,本 task 只加测试。

依赖修正(计划 Task 7.4 Step 2):norman_mean_baseline 条目 Task 7.5 才加,故
test_norman_mean_baseline_source_self_trained_fail_closed 移入 Task 7.5,本 task 保留其余 4 条
(只依赖现有 yeast_deletion_fitness 种子 + 临时 registry)。"""
import hashlib

from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.model_zoo.cache import ModelCache
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry


def _ask(name):
    return AgentMessage("q1", "Client", "ModelBrokerAgent", "model_request",
                        {"model_name": name}, "t1")


def _resolve_default(name, cache=None):
    bus = MessageBus()
    ModelBrokerAgent(cache=cache).handle(_ask(name), bus)
    return bus.latest("model_broker_result").payload


def test_yeast_deletion_fitness_planned_fail_closed():
    """种子 yeast_deletion_fitness status=planned → ②关 fail-closed,reason 点名 planned/not available。
    红线 6:无数据未训的自训模型不静默 accept。"""
    p = _resolve_default("yeast_deletion_fitness")
    assert p["available"] is False
    assert p["status"] == "planned"
    assert "planned" in p["reason"] or "not available" in p["reason"]
    # fail-closed 不等于隐藏:wrapper 类路径仍可见(可分发性声明)
    assert p["wrapper"].endswith("self_trained_wrapper.SelfTrainedWrapper")


def test_self_trained_source_requires_manual_fetch(tmp_path):
    """临时 registry:self_trained + status=available + 依赖齐 → source=self_trained:* 在④关拦
    (requires_manual_fetch,不静默 available)。证明 source 关对 self_trained 生效。"""
    import praxis_virtualcell.agents.model_broker_agent as mba
    reg_yaml = tmp_path / "reg.yaml"
    reg_yaml.write_text(
        "models:\n"
        "  st:\n"
        "    name: st\n    type: self_trained\n    species: [human]\n"
        "    module: genetic_hub\n    task: predict_delta_expression\n"
        "    source: 'self_trained:st'\n"            # self_trained source → source 关拦
        "    license: internal\n    status: available\n"   # 故意 available 让请求走到 source 关
        "    wrapper: x.Y\n    version: v1\n    requires: []\n"
        "    reliability_policy: ml_disagreement\n"
        "    training_card:\n"
        "      training_data: donor norman\n      split: seed split\n"
        "      baseline: naive\n      metrics: {delta_pearson: 0.4615}\n"
        "      provenance: scored on .53\n",
        encoding="utf-8")
    bus = MessageBus()
    mba.ModelBrokerAgent(registry=ModelZooRegistry(registry_path=str(reg_yaml))).handle(_ask("st"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is False
    assert "source" in p["reason"] or "manual" in p["reason"]


def test_self_trained_with_local_ckpt_and_sha_passes(tmp_path, monkeypatch):
    """变异逮捕:self_trained + status=available + 依赖齐 + source=local(resolved)+ assets sha 对
    → available(证明关非空转;若 self_trained 被无条件拦则此测试 FAIL)。
    用 source=cobra_bundled(resolved)绕过 self_trained: source 关,专验 assets 关放行。"""
    import praxis_virtualcell.agents.model_broker_agent as mba
    monkeypatch.setattr(mba, "_dep_available", lambda dep: True)

    payload = b"fake-mean-delta-tensor"
    sha = hashlib.sha256(payload).hexdigest()
    reg_yaml = tmp_path / "reg.yaml"
    reg_yaml.write_text(
        "models:\n"
        "  st:\n"
        "    name: st\n    type: self_trained\n    species: [human]\n"
        "    module: genetic_hub\n    task: predict_delta_expression\n"
        "    source: cobra_bundled_textbook\n"       # resolved(绕 self_trained: source 关,专验 assets)
        "    license: internal\n    status: available\n    wrapper: x.Y\n    version: v1\n"
        "    requires: []\n    reliability_policy: ml_disagreement\n"
        "    training_card:\n"
        "      training_data: donor norman\n      split: seed split\n"
        "      baseline: naive\n      metrics: {delta_pearson: 0.4615}\n"
        "      provenance: scored on .53\n"
        "    assets:\n"
        "      - filename: mean_delta.pt\n"
        f"        sha256: '{sha}'\n"
        "        source_note: local\n",
        encoding="utf-8")
    cache = ModelCache(root=str(tmp_path))
    ap = cache.asset_path("st", "mean_delta.pt")
    ap.parent.mkdir(parents=True, exist_ok=True)
    ap.write_bytes(payload)

    bus = MessageBus()
    mba.ModelBrokerAgent(registry=ModelZooRegistry(registry_path=str(reg_yaml)),
                         cache=cache).handle(_ask("st"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is True                    # self_trained 依赖齐+resolved+sha 对 → available(关非空转)


def test_self_trained_sha_placeholder_fail_closed(tmp_path, monkeypatch):
    """self_trained + sha=null 占位(ckpt 未训/未算 sha)→ assets 关 fail-closed(红线 6)。"""
    import praxis_virtualcell.agents.model_broker_agent as mba
    monkeypatch.setattr(mba, "_dep_available", lambda dep: True)

    reg_yaml = tmp_path / "reg.yaml"
    reg_yaml.write_text(
        "models:\n"
        "  st:\n"
        "    name: st\n    type: self_trained\n    species: [human]\n"
        "    module: genetic_hub\n    task: predict_delta_expression\n"
        "    source: cobra_bundled_textbook\n    license: internal\n    status: available\n"
        "    wrapper: x.Y\n    version: v1\n    requires: []\n    reliability_policy: ml_disagreement\n"
        "    training_card:\n"
        "      training_data: donor norman\n      split: seed split\n"
        "      baseline: naive\n      metrics: {pearson: null, note: planned}\n"
        "      provenance: planned; no weights yet\n"
        "    assets:\n"
        "      - filename: mean_delta.pt\n"
        "        sha256: null\n"                      # 占位未填 → requires_manual_fetch
        "        source_note: local\n",
        encoding="utf-8")
    cache = ModelCache(root=str(tmp_path))
    bus = MessageBus()
    mba.ModelBrokerAgent(registry=ModelZooRegistry(registry_path=str(reg_yaml)),
                         cache=cache).handle(_ask("st"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is False
    assert "manual_fetch" in p["reason"] or "sha256" in p["reason"] or "asset" in p["reason"]
