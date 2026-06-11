"""§5⑨ M5 整合不变量:大脑检索/五模式/审核/依赖报告/可观测。
不引入新生产码,只在真实 store + 真实 permission 上组合 T1-T12。"""

from praxis2.agents.loader import AgentMode, resolve_agent
from praxis2.brains.migrate import DISCIPLINE_SLUGS, build_fixture_brain
from praxis2.brains.retrieve import retrieve_brain
from praxis2.brains.retrieve_first import retrieve_first
from praxis2.brains.store import list_brain_docs
from praxis2.core.rmcp import Phase, get_phase
from praxis2.core.state import State
from praxis2.memory.extract import ExtractCandidate, persist_candidates
from praxis2.memory.review import BrainCacheRegistry, approve, list_pending, reject
from praxis2.skills.deps import probe_dependencies
from praxis2.skills.executor import choose_env
from praxis2.skills.loader import SkillManifest
from praxis2.store.base import Namespace
from praxis2.store.memory import InMemoryStore


# ① 大脑检索 retrieve-first 命中 + bare 降级
def test_inv1_retrieve_hit_vs_bare_degrade():
    st = State()
    sel = resolve_agent("Cryo", user_query="冷冻电镜")
    hit = retrieve_first(st, sel, domain_docs=build_fixture_brain("Cryo"),
                         common_docs=build_fixture_brain("_common"),
                         user_query="冷冻电镜 三维重构")
    assert hit.degraded_to_bare is False
    assert get_phase(st) is Phase.RETRIEVE
    st2 = State()
    bare = retrieve_first(st2, sel, domain_docs=build_fixture_brain("Cryo"),
                          common_docs=build_fixture_brain("_common"),
                          user_query="无关烹饪")
    assert bare.degraded_to_bare is True
    assert get_phase(st2) is Phase.INIT  # bare 降级不推进相位


# ② 五种 agent 模式选择与合成(v2.0.2:Synth 落地,13 学科 lowercase 单源)
def test_inv2_five_modes_selection_and_synthesis():
    assert len(DISCIPLINE_SLUGS) == 13  # v2.0.2:Synth 真盘落地,13 学科
    for slug in DISCIPLINE_SLUGS:
        s = resolve_agent(slug, user_query="x")
        assert s.mode is AgentMode.DISCIPLINE
        assert s.brain_slugs == ["_common", slug]  # 单源 lowercase
        assert s.is_discipline is True
    assert resolve_agent("general", user_query="x").mode is AgentMode.GENERAL
    assert resolve_agent("bare", user_query="x").brain_slugs == ["_common"]
    oaa = resolve_agent("one-above-all", user_query="CRISPR sgRNA 脱靶")
    assert oaa.mode is AgentMode.ONE_ABOVE_ALL and "crispr" in oaa.brain_slugs
    assert oaa.max_turns <= 5
    y = resolve_agent("yourself", user_query="我做 Enzyme 与 Dock")
    assert y.readonly is True and "enzyme" in y.brain_slugs


# ③ 审核流:未审不进检索 / approve promote+热加载 / reject 记因
async def test_inv3_review_flow_full():
    store = InMemoryStore()
    ns = Namespace(user_id="u1", scope="session")
    reg = BrainCacheRegistry()
    reg.mark_loaded("Cryo")
    # 候选文本须与 BM25-lite 口径一致:中文关键词空格分隔(T6 第一版局限,
    # 总纲校准②,与 T11 _SLUG_CASE_HINTS 同口径;v2 向量检索绕开)
    await persist_candidates(store, ns, [
        ExtractCandidate(id="k1", text="冷冻电镜 新经验 doi:10.1/x",
                         trigger="manual"),
        ExtractCandidate(id="k2", text="待拒经验", trigger="manual"),
    ])
    # 未审 → 不在大脑检索
    assert await list_brain_docs(store, "u1", "Cryo") == []
    assert len(await list_pending(store, ns)) == 2
    # approve → promote + 热加载失效
    await approve(store, ns, "k1", brain_slug="Cryo", cache=reg)
    assert reg.is_loaded("Cryo") is False
    docs = await list_brain_docs(store, "u1", "Cryo")
    assert any("冷冻电镜" in d.text and "新经验" in d.text for d in docs)
    # promote 后大脑检索可命中(后续会话,空格分隔故 BM25-lite 命中)
    r = retrieve_brain(docs, "冷冻电镜 新经验", top_k=1)
    assert r.degraded_to_bare is False
    # reject → 记因、不 promote
    await reject(store, ns, "k2", reason="证据不足")
    assert (await store.kv_get(ns, "_reject/k2")) is not None
    assert len(await list_pending(store, ns)) == 0


# ④ 依赖缺失产结构化报告而非裸失败
def test_inv4_missing_deps_structured_report():
    r = probe_dependencies(["torch", "rdkit"], env="e1", available={"torch"})
    assert r.ok is False and r.missing == ["rdkit"]
    p = r.to_tool_result_payload()
    assert p["is_error"] is True and "rdkit" in p["content"]
    # 不裸失败:probe 返回报告对象,未抛异常(上面调用未 try/except 即证)


# ⑤ §12 可观测:路由依据 / env 选择 / 审核审计写 transcript
def test_inv5_observability_route_and_env_to_transcript():
    rec: list[dict] = []
    resolve_agent("one-above-all", user_query="Protein 结构预测 折叠",
                  transcript_sink=rec.append)
    # B.3:agent_route.chosen 是 lowercase slug(对齐真盘 brain:protein)
    assert any(e["type"] == "agent_route" and e["chosen"] == "protein"
               for e in rec)
    rec2: list[dict] = []
    m = SkillManifest(name="s", description="d", when_to_use="w")
    m.skill_env = "cryo-gpu"
    choose_env(m, agent_env=None, available_envs={"cryo-gpu"},
               transcript_sink=rec2.append)
    assert any(e["type"] == "env_choice" and e["env"] == "cryo-gpu"
               for e in rec2)
