"""MDR-GNB LLM 四模式编排(Phase 6,最后一相)。

VC 的 llm_orchestration 编排 **module 集**且依赖 agents.module_rules(MDR 无);MDR 编排的是
**每药 output_kind**(sir_class/mic_scalar/synergy)——领域分叉,故本模块自建,复用 VC 的
fail-closed / 候选过滤 / sanitize 模式(不 import VC 包、不动核心 config)。

四模式:
  OFFLINE                 —— 零 LLM/零 token,run_mdr_query 原样(字节等价)。
  LLM_PARSE_ONLY          —— LLM 仅在任务解析(现有 llm_assisted 语义);裁决不变。
  LLM_ORCHESTRATED_DRUGS  —— LLM 建议每药 output_kind(经 safety_contract 过滤成候选子集,
                             MIC 弱→clip SIR);只进 provenance.llm_orchestration,不改实际预测。
  LLM_ORCHESTRATED_STRICT —— 上者 + 跨物种 SIR/MIC 冲突 advisory(只进 provenance notes)。

硬红线(LLM 不裁决):三 flag modify_disposition / override_abstain / change_breakpoint **恒 False**
(enforce_boundaries 硬钉,即便 LLM 妄图置 True 也剔除);LLM 产物只进 provenance notes,绝不改
prediction/verdict/disposition/breakpoint。确定性:disabled client → content=None → fail-closed 回退。
"""
from __future__ import annotations

import json
from enum import Enum

from praxis_virtualcell.agents_llm.llm_client import LLMClient
from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query

# output_kind 全集与展示序(sir 最安全 fallback)
_SIR, _MIC, _SYN = "sir_class", "mic_scalar", "synergy"
_KIND_ORDER = (_MIC, _SIR, _SYN)

# LLM 不裁决:这三边界 flag 恒 False,任何 LLM 产物不得置 True(硬钉)
_BOUNDARY_FLAGS = ("modify_disposition", "override_abstain", "change_breakpoint")


class OrchestrationMode(str, Enum):
    OFFLINE = "offline"
    LLM_PARSE_ONLY = "llm_parse_only"
    LLM_ORCHESTRATED_DRUGS = "llm_orchestrated_drugs"
    LLM_ORCHESTRATED_STRICT = "llm_orchestrated_strict"


_LLM_MODES = (OrchestrationMode.LLM_PARSE_ONLY,
              OrchestrationMode.LLM_ORCHESTRATED_DRUGS,
              OrchestrationMode.LLM_ORCHESTRATED_STRICT)


# ---------------------------------------------------------------- 边界守卫
def enforce_boundaries(plan: dict) -> dict:
    """硬钉三边界 flag 恒 False(返回新 dict)。LLM 不改 disposition / 不翻 abstain / 不改 breakpoint。"""
    out = dict(plan)
    for f in _BOUNDARY_FLAGS:
        out[f] = False
    return out


def assert_orchestration_boundaries(plan: dict) -> None:
    """守卫:任一边界 flag 为真 → 拒绝(fail-closed)。入口处调用防误配置让 LLM 侵入裁决。"""
    bad = [f for f in _BOUNDARY_FLAGS if plan.get(f)]
    if bad:
        raise RuntimeError(f"LLM 编排边界被违反(必须恒 False): {bad}。LLM 绝不碰 disposition/abstain/breakpoint。")


# ---------------------------------------------------------------- 候选 output_kind
def build_candidate_outputs_for_drug(*, requested_outputs=None, mic_supported: bool = True,
                                     synergy: bool = False) -> dict:
    """确定性候选 output_kind 全集 + primary。
    SIR→sir_class、MIC→mic_scalar(仅 mic_supported)、组合→synergy;primary=MIC 可用则 mic_scalar 否则 sir_class。
    fail-closed:候选空 → [sir_class](MIC 弱自动 clip 到 SIR:mic 不支持时 mic_scalar 不入候选)。"""
    reqs = {str(o).strip().upper() for o in (requested_outputs or [])}
    cand: set[str] = set()
    if "SIR" in reqs or not reqs:
        cand.add(_SIR)
    if "MIC" in reqs and mic_supported:
        cand.add(_MIC)
    if synergy or "SYNERGY" in reqs or "COMBO" in reqs:
        cand.add(_SYN)
    if not cand:
        cand.add(_SIR)                                   # fail-closed 保底
    primary = _MIC if _MIC in cand else _SIR
    cand.add(primary)
    return {"candidates": sorted(cand, key=_KIND_ORDER.index), "primary": primary}


def _filter_to(llm_list, candidates: list[str]) -> list[str]:
    """只保留 ∈ candidates 的项,去重,按 candidates 序(复刻 LLMRouter 越界剔除)。"""
    sel = set(llm_list or [])
    return [c for c in candidates if c in sel]


def sanitize_llm_orchestration_plan(raw_content: str | None, candidates: list[str],
                                    *, primary: str) -> dict:
    """解析 LLM JSON {selected_outputs, reasoning_summary, risk_flags} → 合法结构(fail-closed)。
    越候选剔除;primary 保底;content 空→llm_unavailable;解析失败→llm_parse_failed;三 flag 硬钉 False。"""
    out = {"selected_outputs": [], "reasoning_summary": "", "risk_flags": [],
           "candidates": list(candidates)}
    fb = [primary] if primary in candidates else list(candidates[:1])
    if not raw_content:
        out["risk_flags"] = ["llm_unavailable"]
        out["selected_outputs"] = fb
        return enforce_boundaries(out)
    try:
        d = json.loads(raw_content)
        sel = _filter_to(d.get("selected_outputs") or [], candidates)
        if primary in candidates and primary not in sel:
            sel = [primary] + sel                        # primary 保底(LLM 不可删 primary)
        rf = d.get("risk_flags")
        out["selected_outputs"] = sel
        out["reasoning_summary"] = str(d.get("reasoning_summary", ""))[:500]
        out["risk_flags"] = list(rf) if isinstance(rf, list) else []
    except (json.JSONDecodeError, TypeError, AttributeError):
        out["risk_flags"] = ["llm_parse_failed"]
        out["selected_outputs"] = fb
    return enforce_boundaries(out)                        # 三 flag 恒 False(丢弃 LLM 任何 flag 妄图)


_ORCH_SYS = (
    "你给耐药革兰阴性菌的药物给出 output_kind 编排建议。只输出 JSON:"
    '{"selected_outputs":[],"reasoning_summary":"","risk_flags":[]}。'
    "selected_outputs 必须来自给定 candidates(sir_class/mic_scalar/synergy),不发明新类、不选候选外。"
    "你只挑 output_kind,不给数值预测、不改 SIR/MIC 裁决、不改折点。只输出 JSON。"
)


def orchestrate_outputs(request: dict, *, client=None) -> dict:
    """LLM 建议每药 output_kind(经 candidates 过滤,MIC 弱→clip SIR)。三 flag 恒 False。"""
    mic_supported = bool(request.get("mic_supported", True))
    cc = build_candidate_outputs_for_drug(requested_outputs=request.get("requested_outputs"),
                                          mic_supported=mic_supported)
    candidates, primary = cc["candidates"], cc["primary"]
    content = None
    if client is not None and getattr(client, "enabled", False):
        user = json.dumps({"request": request, "candidates": candidates,
                           "deterministic_primary": primary}, ensure_ascii=False)
        res = client.complete([{"role": "system", "content": _ORCH_SYS},
                               {"role": "user", "content": user}], json_mode=True)
        content = res.get("content")
    plan = sanitize_llm_orchestration_plan(content, candidates, primary=primary)
    # MIC 弱→clip(候选已排除 mic,此处兜底 selected 里若混入 mic 也替 sir)
    if not mic_supported and _MIC in plan["selected_outputs"]:
        plan["selected_outputs"] = [_SIR if k == _MIC else k for k in plan["selected_outputs"]]
        plan["risk_flags"] = sorted(set(plan["risk_flags"]) | {"mic_weak_clip_to_sir"})
    return plan


# ---------------------------------------------------------------- 跨物种 SIR/MIC 冲突(advisory)
def detect_sir_mic_conflict(sir, mic_call) -> bool:
    """确定性:SIR 分类与 MIC 折点判读不一致(如 SIR=R 但 MIC 落 S 区)。缺任一 → 无冲突。"""
    if not sir or not mic_call:
        return False
    return str(sir) != str(mic_call)


_XS_SYS = (
    "你复核耐药菌 SIR 分类与 MIC 判读的一致性,只给观察与风险标记,"
    "不改任何 SIR/MIC 裁决、不改折点、不给数值。只输出 JSON:{\"notes\":[],\"flags\":[]}。"
)


def cross_species_review(pairs: list[dict], *, client=None) -> dict:
    """检出 SIR/MIC 冲突(确定性)+ 可选 LLM advisory notes。三 flag 恒 False,不碰裁决。"""
    conflicts = [p for p in (pairs or [])
                 if detect_sir_mic_conflict(p.get("sir"), p.get("mic_call"))]
    notes = [f"sir_mic_conflict:{p.get('species')}:{p.get('drug')} "
             f"sir={p.get('sir')} mic={p.get('mic_call')}" for p in conflicts]
    flags = ["sir_mic_conflict"] if conflicts else []
    if client is not None and getattr(client, "enabled", False):
        res = client.complete([{"role": "system", "content": _XS_SYS},
                               {"role": "user", "content": json.dumps(pairs, ensure_ascii=False)}],
                              json_mode=True)
        content = res.get("content")
        if content:
            try:
                d = json.loads(content)
                notes = notes + [str(x) for x in (d.get("notes") or [])]
                flags = sorted(set(flags) | {str(x) for x in (d.get("flags") or [])})
            except (json.JSONDecodeError, TypeError, AttributeError):
                flags = sorted(set(flags) | {"llm_parse_failed"})
    out = {"notes": notes, "conflicts": conflicts, "flags": flags}
    return enforce_boundaries(out)


# ---------------------------------------------------------------- client 工厂
def make_orchestration_client(mode: OrchestrationMode, *, api_key: str = "",
                              base_url: str = "https://api.deepseek.com",
                              model: str = "deepseek-chat") -> LLMClient:
    """enabled iff 编排/解析模式 且 有 api_key。OFFLINE 恒 disabled(零 token)。"""
    enabled = mode in _LLM_MODES and bool(api_key)
    return LLMClient(enabled=enabled, api_key=api_key, base_url=base_url, model=model)


# ---------------------------------------------------------------- 四模式 harness
def _mic_supported(result: dict) -> bool:
    """从确定性 result 判 MIC 是否可用(output_kind==mic_scalar 才算真出了 MIC)。"""
    return (result.get("report") or {}).get("output_kind") == _MIC


def run_query_with_mode(raw: dict, *, mode: OrchestrationMode = OrchestrationMode.OFFLINE,
                        seed_task_id: str, registry=None, client=None) -> dict:
    """四模式端到端。OFFLINE 原样返回(零 token 字节等价);LLM 模式跑确定性 run_mdr_query 后,
    只把 LLM advisory 挂到 report.provenance.llm_*,**裁决字段逐字不变**(返回新 report 不 mutate)。"""
    result = run_mdr_query(raw, seed_task_id=seed_task_id, registry=registry)
    if mode == OrchestrationMode.OFFLINE:
        return result                                    # 零 token:client 绝不触碰

    report = result["report"]
    prov = dict(report.get("provenance") or {})
    prov["llm_mode"] = mode.value

    if mode in (OrchestrationMode.LLM_ORCHESTRATED_DRUGS, OrchestrationMode.LLM_ORCHESTRATED_STRICT):
        request = {"requested_outputs": raw.get("requested_outputs"),
                   "mic_supported": _mic_supported(result),
                   "drug": report.get("drug")}
        orch = orchestrate_outputs(request, client=client)
        assert_orchestration_boundaries(orch)            # 入口守卫:三 flag 必 False
        prov["llm_orchestration"] = orch

    if mode == OrchestrationMode.LLM_ORCHESTRATED_STRICT:
        pairs = [{"species": raw.get("species"), "drug": report.get("drug"),
                  "sir": report.get("sir"), "mic_call": report.get("mic_call")}]
        xs = cross_species_review(pairs, client=client)
        assert_orchestration_boundaries(xs)
        prov["llm_cross_species"] = xs

    new_report = dict(report)                            # 裁决字段逐字复制,只换 provenance
    new_report["provenance"] = prov
    return {**result, "report": new_report}
