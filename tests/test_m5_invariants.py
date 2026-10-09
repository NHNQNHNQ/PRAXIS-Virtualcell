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


def test_inv1_retrieve_hit_vs_bare_degrade():
    st = State()
    sel = resolve_agent("Virtualcell", user_query="\u51b7\u51bb\u7535\u955c")
    hit = retrieve_first(
        st,
        sel,
        domain_docs=build_fixture_brain("Virtualcell"),
        common_docs=build_fixture_brain("_common"),
        user_query="Virtualcell \u9886\u57df",
    )
    assert hit.degraded_to_bare is False
    assert get_phase(st) is Phase.RETRIEVE
    st2 = State()
    bare = retrieve_first(
        st2,
        sel,
        domain_docs=build_fixture_brain("Virtualcell"),
        common_docs=build_fixture_brain("_common"),
        user_query="\u65e0\u5173\u70f9\u996a",
    )
    assert bare.degraded_to_bare is True
    assert get_phase(st2) is Phase.INIT


def test_inv2_five_modes_selection_and_synthesis():
    assert len(DISCIPLINE_SLUGS) == 1
    for slug in DISCIPLINE_SLUGS:
        s = resolve_agent(slug, user_query="x")
        assert s.mode is AgentMode.DISCIPLINE
        assert s.brain_slugs == ["_common", slug]
        assert s.is_discipline is True
    assert resolve_agent("general", user_query="x").mode is AgentMode.GENERAL
    assert resolve_agent("bare", user_query="x").brain_slugs == ["_common"]
    oaa = resolve_agent("one-above-all", user_query="Norman perturbation perturbation")
    assert oaa.mode is AgentMode.ONE_ABOVE_ALL and "virtualcell" in oaa.brain_slugs
    assert oaa.max_turns <= 5
    y = resolve_agent("yourself", user_query="\u6211\u505a\u57fa\u56e0perturbation perturbation Norman")
    assert y.readonly is True and "virtualcell" in y.brain_slugs


async def test_inv3_review_flow_full():
    store = InMemoryStore()
    ns = Namespace(user_id="u1", scope="session")
    reg = BrainCacheRegistry()
    reg.mark_loaded("Virtualcell")

    await persist_candidates(
        store,
        ns,
        [
            ExtractCandidate(id="k1", text="\u51b7\u51bb\u7535\u955c \u65b0\u7ecf\u9a8c doi:10.1/x", trigger="manual"),
            ExtractCandidate(id="k2", text="\u5f85\u62d2\u7ecf\u9a8c", trigger="manual"),
        ],
    )

    assert await list_brain_docs(store, "u1", "Virtualcell") == []
    assert len(await list_pending(store, ns)) == 2

    await approve(store, ns, "k1", brain_slug="Virtualcell", cache=reg)
    assert reg.is_loaded("Virtualcell") is False
    docs = await list_brain_docs(store, "u1", "Virtualcell")
    assert any("\u51b7\u51bb\u7535\u955c" in d.text and "\u65b0\u7ecf\u9a8c" in d.text for d in docs)

    r = retrieve_brain(docs, "\u51b7\u51bb\u7535\u955c \u65b0\u7ecf\u9a8c", top_k=1)
    assert r.degraded_to_bare is False

    await reject(store, ns, "k2", reason="\u8bc1\u636e\u4e0d\u8db3")
    assert (await store.kv_get(ns, "_reject/k2")) is not None
    assert len(await list_pending(store, ns)) == 0


def test_inv4_missing_deps_structured_report():
    r = probe_dependencies(["torch", "rdkit"], env="e1", available={"torch"})
    assert r.ok is False and r.missing == ["rdkit"]
    p = r.to_tool_result_payload()
    assert p["is_error"] is True and "rdkit" in p["content"]


def test_inv5_observability_route_and_env_to_transcript():
    rec: list[dict] = []
    resolve_agent(
        "one-above-all", user_query="Norman perturbation perturbation\u9884\u6d4b", transcript_sink=rec.append
    )

    assert any(e["type"] == "agent_route" and e["chosen"] == "virtualcell" for e in rec)
    rec2: list[dict] = []
    m = SkillManifest(name="s", description="d", when_to_use="w")
    m.skill_env = "cryo-gpu"
    choose_env(m, agent_env=None, available_envs={"cryo-gpu"}, transcript_sink=rec2.append)
    assert any(e["type"] == "env_choice" and e["env"] == "cryo-gpu" for e in rec2)
