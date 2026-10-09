"""§5⑦ M8 校准⑤ 4 个 v1 代表性科研场景 golden 测试。
RMCP 强制 / DOI 必需 / 证据链未签封 / 大脑命中——PRAXIS-2 行为等价 v1。

implementer note(签名对齐):
- `retrieve_first` 真实签名为 `(state, selection, *, domain_docs, common_docs,
  user_query, top_k=3, ...)`,不接受 store/user_id/slugs 形参;故本 Task ④
  改走 `put_brain_doc + list_brain_docs + retrieve_brain` 等价端到端
  (顺序:灌→按 slug 取→BM25-lite 命中),断言 hits[0].slug == 'cryo'。
- `evidence_chain_seal_gate` 不存在;真实 API 是工厂
  `make_rmcp_stop_gate()`(返回 (state)->StopDecision),故本 Task ③ 调
  该工厂取 gate 后跑。
- `doi_required(tool, blk, result, state)`/`PhaseAwarePermission` API 与
  spec 一致;`result` 须含 tool_use_id 键(`_veto` 透传)。
"""

from praxis2.brains.retrieve import retrieve_brain
from praxis2.brains.store import BrainDoc, list_brain_docs, put_brain_doc
from praxis2.core.rmcp import Phase, set_phase
from praxis2.core.seams import PermissionDecision, StopDecision
from praxis2.core.state import State
from praxis2.hooks.builtin import doi_required, make_rmcp_stop_gate
from praxis2.store.memory import InMemoryStore
from praxis2.tools.permission import PhaseAwarePermission, RulePermissionPolicy


class _StubExecTool:
    """模拟 EXECUTE 相位工具:rmcp_op='call_skill'(真实 v1 op);
    INIT 相位 ALLOWED_OPS 为空,任何 rmcp_op 都被 PhaseAwarePermission 拒。"""

    name = "Bash"
    rmcp_op = "call_skill"


def test_golden_1_rmcp_force_retrieve_first():
    """§5⑦① RMCP 强制:相位未完成 retrieve,execute 类工具被 Permission 拒。"""
    # 初态:相位 INIT(未 retrieve)
    state = State()
    set_phase(state, Phase.INIT)
    # 规则层无 deny,但相位门拒 execute 类
    policy = PhaseAwarePermission(RulePermissionPolicy([]))
    r = policy.check(tool=_StubExecTool(), payload={}, state=state)
    assert r.decision is PermissionDecision.DENY
    assert r.reason is not None
    assert "retrieve" in r.reason  # 提示模型先 retrieve(§4① 自救)


def test_golden_2_doi_required_on_tool_result():
    """§5⑦② DOI 必需:工具结果不含 DOI/PMID → PostToolUse hook 否决。"""
    state = State()
    # tool_result 含 'doi:...' → 放行;不含 → 被 doi_required 替换为 is_error
    ok_blk = {
        "type": "tool_result",
        "tool_use_id": "t1",
        "is_error": False,
        "content": "结论 doi:10.1/x",
    }
    bad_blk = {
        "type": "tool_result",
        "tool_use_id": "t2",
        "is_error": False,
        "content": "结论无溯源",
    }
    assert doi_required(None, {}, ok_blk, state) is None  # 放行
    replaced = doi_required(None, {}, bad_blk, state)
    assert replaced is not None
    assert replaced["is_error"] is True
    assert "DOI" in replaced["content"] or "doi" in replaced["content"].lower()


def test_golden_3_evidence_chain_seal_blocks_premature_stop():
    """§5⑦③ 证据链不完整:Stop hook 否决终答,强制再走一轮。"""
    state = State()
    # 默认 tool_use_context 空 → 缺 evidence_ok/anti_filter_ok → veto
    gate = make_rmcp_stop_gate()
    decision = gate(state)
    assert isinstance(decision, StopDecision)
    assert decision.veto is True
    assert "证据链" in decision.message or "seal" in decision.message.lower()


async def test_golden_4_brain_retrieve_first_hits_cryo_slug():
    """§5⑦④ 大脑命中:用户问 cryo-EM,跨 slug 检索命中 cryo 排第一。

    端到端等价(按真实签名拆):put_brain_doc 灌 → list_brain_docs 取 →
    retrieve_brain 跑 BM25-lite → 断言 hits[0].slug == 'cryo'。
    """
    store = InMemoryStore()
    user = "u1"

    # 灌 cryo + md 两 slug 候选(text 含查询关键词重合度差异)
    await put_brain_doc(store, user, BrainDoc(
        slug="cryo", kind="cases", stem="c1",
        text="cryo-EM 单颗粒重构流程,RELION CTF 矫正",
    ))
    await put_brain_doc(store, user, BrainDoc(
        slug="md", kind="cases", stem="m1",
        text="GROMACS 分子动力学模拟流程",
    ))

    # 跨 slug 聚合候选(模拟 retrieve_first 选 cryo+md 两 slug 后并表)
    candidates: list[BrainDoc] = []
    for slug in ("cryo", "md", "dock"):
        candidates.extend(await list_brain_docs(store, user, slug))

    # cryo-EM 问题 → BM25-lite 命中 cryo(text 含 cryo/CTF 关键词)
    r = retrieve_brain(
        candidates,
        query="如何做 cryo-EM 单颗粒重构和 CTF 矫正",
        top_k=3,
    )
    assert not r.degraded_to_bare
    assert len(r.hits) >= 1
    assert r.hits[0].slug == "cryo"  # 第一名命中 cryo
