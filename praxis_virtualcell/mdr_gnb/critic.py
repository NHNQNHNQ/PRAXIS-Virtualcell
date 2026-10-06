"""GNB critic 不变量(确定性,只记 violation 不改预测)。审 trace 诚实性:
  1 retrieve-before-predict:brain_retrieved 须在 predictor_result 之前
  2 无预测不得声称(有 ensemble 却无 models_used 且未 abstain)
  3 abstain 与预测互斥(abstain=True 却残留 ensemble)
  4 breakpoint 版本一致(结论所用折点源须与请求声明版本一致)
  5 基因型与结论一致(判 R 却基因型无任何耐药机制 = 矛盾)
  6 provenance 完整(非 abstain 须有检索规则、catalog 与治理快照等必要 provenance)
  7 机理声明须 G3 通过(mechanism_claimed=True 而 g3_passed=False = 越权机制话术)

violations 用裸标签(供精确匹配/审计计数),具体涉及药物等详情记入 notes。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CriticInput:
    trace_types: list[str]
    abstain: bool
    reasons: list[str]
    models_used: list[str]
    ensemble: dict[str, Any] | None
    rules_referenced: list[str]
    breakpoint_sources: dict[str, str]          # drug -> source string
    request_breakpoint_version: str
    genotype: dict[str, Any]
    conclusion_sir: dict[str, str]              # drug -> S/I/R
    provenance: dict[str, Any]
    mechanism_claimed: bool
    g3_passed: bool


@dataclass
class CriticResult:
    violations: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _has_required_provenance(provenance: dict[str, Any]) -> bool:
    """Return whether a non-abstained production conclusion is replay-bindable.

    A truthy free-form dict is not evidence.  The MDR production path must bind
    its route, catalog identity, mutable-governance identity and the trace/critic
    contract versions.  This deliberately remains a structural check: it does
    not infer scientific validation from a ready artifact or a hash.
    """
    capability = provenance.get("capability")
    governance = provenance.get("governance_snapshot")
    return (
        isinstance(provenance.get("route"), str)
        and bool(provenance["route"])
        and isinstance(capability, dict)
        and _is_sha256(capability.get("catalog_digest"))
        and isinstance(governance, dict)
        and _is_sha256(governance.get("governance_digest"))
        and isinstance(provenance.get("trace_schema_version"), str)
        and bool(provenance["trace_schema_version"])
        and isinstance(provenance.get("critic_policy_version"), str)
        and bool(provenance["critic_policy_version"])
    )


def check_invariants(ci: CriticInput) -> CriticResult:
    v: list[str] = []
    notes: list[str] = []
    t = ci.trace_types

    # 1 retrieve-before-predict
    if "predictor_result" in t:
        if "brain_retrieved" not in t or t.index("brain_retrieved") > t.index("predictor_result"):
            v.append("predict_before_retrieve")
    # 2 无预测无 abstain(有结论 ensemble 却既无 model 又未 abstain)
    if ci.ensemble is not None and not ci.models_used and not ci.abstain:
        v.append("prediction_without_predictor")
    # 3 abstain 与预测互斥
    if ci.abstain and ci.ensemble is not None:
        v.append("abstain_inconsistent_with_prediction")
    # 4 breakpoint 版本一致
    mismatch = sorted(d for d, src in ci.breakpoint_sources.items()
                      if ci.request_breakpoint_version not in src)
    if mismatch:
        v.append("breakpoint_version_mismatch")
        notes.append(f"breakpoint_version_mismatch drugs={mismatch}")
    # 5 基因型与结论一致(判 R 需至少一个耐药机制标记为真)
    if not ci.abstain:
        has_mech = any(bool(x) for x in ci.genotype.values())
        wrong_r = sorted(d for d, s in ci.conclusion_sir.items() if s == "R") if not has_mech else []
        if wrong_r:
            v.append("genotype_conclusion_contradiction")
            notes.append(f"genotype_conclusion_contradiction drugs={wrong_r}")
    # 6 provenance 完整。规则引用只是检索链的一部分；任意 truthy dict 不能掩盖
    # catalog/governance/contract identity 的缺失，否则缓存或回放会误把不同决策当同一条。
    if not ci.abstain and (
        not ci.rules_referenced or not _has_required_provenance(ci.provenance)
    ):
        v.append("missing_provenance")
    # 7 机理声明须 G3 通过
    if ci.mechanism_claimed and not ci.g3_passed:
        v.append("mechanism_claim_without_g3")

    notes.append(f"checked 7 GNB invariants; n_violations={len(v)}")
    return CriticResult(violations=v, notes=notes)
