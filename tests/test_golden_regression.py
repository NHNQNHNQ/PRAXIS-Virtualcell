from praxis2.brains.retrieve import retrieve_brain
from praxis2.brains.store import BrainDoc, list_brain_docs, put_brain_doc
from praxis2.core.rmcp import Phase, set_phase
from praxis2.core.seams import PermissionDecision, StopDecision
from praxis2.core.state import State
from praxis2.hooks.builtin import doi_required, make_rmcp_stop_gate
from praxis2.store.memory import InMemoryStore
from praxis2.tools.permission import PhaseAwarePermission, RulePermissionPolicy


class _StubExecTool:
    name = "Bash"
    rmcp_op = "call_skill"


def test_golden_1_rmcp_force_retrieve_first():

    state = State()
    set_phase(state, Phase.INIT)

    policy = PhaseAwarePermission(RulePermissionPolicy([]))
    r = policy.check(tool=_StubExecTool(), payload={}, state=state)
    assert r.decision is PermissionDecision.DENY
    assert r.reason is not None
    assert "retrieve" in r.reason


def test_golden_2_doi_required_on_tool_result():

    state = State()

    ok_blk = {
        "type": "tool_result",
        "tool_use_id": "t1",
        "is_error": False,
        "content": "\u7ed3\u8bba doi:10.1/x",
    }
    bad_blk = {
        "type": "tool_result",
        "tool_use_id": "t2",
        "is_error": False,
        "content": "\u7ed3\u8bba\u65e0\u6eaf\u6e90",
    }
    assert doi_required(None, {}, ok_blk, state) is None
    replaced = doi_required(None, {}, bad_blk, state)
    assert replaced is not None
    assert replaced["is_error"] is True
    assert "DOI" in replaced["content"] or "doi" in replaced["content"].lower()


def test_golden_3_evidence_chain_seal_blocks_premature_stop():

    state = State()

    gate = make_rmcp_stop_gate()
    decision = gate(state)
    assert isinstance(decision, StopDecision)
    assert decision.veto is True
    assert "Evidence chain" in decision.message or "seal" in decision.message.lower()


async def test_golden_4_brain_retrieve_first_hits_cryo_slug():

    store = InMemoryStore()
    user = "u1"

    await put_brain_doc(
        store,
        user,
        BrainDoc(
            slug="cryo",
            kind="cases",
            stem="c1",
            text="cryo-EM \u5355\u9897\u7c92\u91cd\u6784\u6d41\u7a0b,RELION CTF \u77eb\u6b63",
        ),
    )
    await put_brain_doc(
        store,
        user,
        BrainDoc(
            slug="md",
            kind="cases",
            stem="m1",
            text="GROMACS \u5206\u5b50\u52a8\u529b\u5b66\u6a21\u62df\u6d41\u7a0b",
        ),
    )

    candidates: list[BrainDoc] = []
    for slug in ("cryo", "md", "dock"):
        candidates.extend(await list_brain_docs(store, user, slug))

    r = retrieve_brain(
        candidates,
        query="\u5982\u4f55\u505a cryo-EM \u5355\u9897\u7c92\u91cd\u6784\u548c CTF \u77eb\u6b63",
        top_k=3,
    )
    assert not r.degraded_to_bare
    assert len(r.hits) >= 1
    assert r.hits[0].slug == "cryo"
