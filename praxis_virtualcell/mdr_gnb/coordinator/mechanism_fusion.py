"""B4 机制融合:化合物活性(QSAR)+ 虚拟细胞机制(GEM/FBA)同 report 分栏。

VirtualCell 血脉真实落点=机制层不是 MIC(spec §三):QSAR 出活性,GEM/FBA(iML1515 大肠杆菌
"虚拟细胞")出可证伪机制(代谢靶被抑制→growth 下降)。两者在同一 report 里**分栏**,互不冒充。

红线:
- **活性≠机制**:activity(QSAR MIC)与 mechanism(FBA growth 抑制)分栏,不拿 QSAR 数字当机制证据。
- **机制只在 G3 门后声称**:FBA 算出的 growth 抑制是真实可证伪的一阶原理模拟(照实报),但
  "这是已验证机制解释"仅当该 species×drug 过 G3 机理门才声称;未评估/未过 → claim_allowed=False,
  标"候选机制,G3 未验证"。
- **FBA 真跑或诚实 abstain**:非代谢靶/cobra 缺/GEM 缺 → available=False,绝不伪造通量。
- **请求完整性**:API 请求已捕获 model manifest 时，实际 sidecar 必须复用该
  catalog bytes/contract，不得另开一次隐式 manifest 观察。
- **确定性**:FBA 输出四舍五入(cobra LP 解有 ULP 噪声),报告逐字相等。
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable

from praxis_virtualcell.mdr_gnb.g3_anchors import G3_ANCHORS

FBA_ROUND = 4              # cobra LP 解有 ~1e-13 ULP 噪声,四舍五入到 4 位吸收,保报告确定性


def _default_g3_status(species: str, drug: str) -> str:
    """该 species×drug 的 G3 机理门状态:passed / failed / not_evaluated(诚实)。

    G3 锚点(g3_anchors.G3_ANCHORS)当前为 β-内酰胺机制(ceftriaxone/meropenem 的 ampC/ompK36),
    未覆盖 FBA 的代谢靶药(trimethoprim/sulfamethoxazole 叶酸通路)→ 这些药 not_evaluated。
    即:FBA 可算机制模拟,但 G3 门尚未对代谢靶药验证 → 机制作候选不作已证实解释(诚实)。
    """
    key = f"{species}__{drug.strip().lower()}"
    if key not in G3_ANCHORS:
        return "not_evaluated"          # 无 G3 锚点覆盖 → 未评估(不假装已验证)
    # 有锚点:真跑 gate 太重,此处保守返 not_evaluated;真 gate 决策经 run_g3_gate 单独产
    return "not_evaluated"


@lru_cache(maxsize=1)
def _default_predictor():
    """模块级缓存单例:GemFbaPredictor 的 _model_cache 跨查询复用,iML1515 只载一次(~2s→仅首次)。"""
    from praxis_virtualcell.mdr_gnb.predictors.mechanistic.gem_fba import GemFbaPredictor
    return GemFbaPredictor()


def _sidecar_contract(result: Any) -> dict[str, Any] | None:
    """Return the safe iML1515 identity attached by ``GemFbaPredictor``.

    FBA evidence also contains reaction data.  This extracts only the catalog
    contract and deliberately excludes its internal evidence ``kind`` wrapper so
    report and trace can make the executed sidecar identity explicit.
    """
    for evidence in getattr(result, "evidence", None) or []:
        if isinstance(evidence, dict) and evidence.get("kind") == "gem_sidecar_contract":
            return {key: value for key, value in evidence.items() if key != "kind"}
    return None


def fuse_mechanism(
    species: str,
    drug: str,
    *,
    predictor: Any | None = None,
    g3_status_fn: Callable[[str, str], str] | None = None,
    sidecar_manifest: Any | None = None,
) -> dict[str, Any]:
    """跑 GEM/FBA 出机制段(与 activity 分栏)。predictor/g3_status_fn 可注入(测试不真跑 cobra)。

    返回 mechanism 段:
      unavailable → {"available": False, "reason", "engine", "mechanism_claim": None}
      available   → {"available": True, "engine", "fba_simulation": {...}, "g3_gate": {...},
                     "mechanism_claim": <仅 G3 passed 才非 None>, "disclaimer"}
    """
    pred = predictor if predictor is not None else _default_predictor()
    # Keep injected fake predictors on their legacy two-argument contract.  The
    # production predictor alone accepts the private request manifest, preserving
    # its SHA-keyed SBML cache while preventing a fresh catalog observation.
    if predictor is None and sidecar_manifest is not None:
        r = pred.predict(species=species, drug=drug, sidecar_manifest=sidecar_manifest)
    else:
        r = pred.predict(species=species, drug=drug)
    sidecar_contract = _sidecar_contract(r)
    # 缺 growth 数值(abstain 或畸形 result)→ 诚实 unavailable,不伪造通量、不崩(防 round(None))
    gi, base, cons = (getattr(r, "growth_inhibition", None),
                      getattr(r, "baseline_growth", None),
                      getattr(r, "constrained_growth", None))
    if getattr(r, "abstained", True) or gi is None or base is None or cons is None:
        unavailable = {
            "available": False,
            "engine": "gem_fba",
            "reason": getattr(r, "abstain_reason", None) or "FBA 结果不完整,unavailable",
            "mechanism_claim": None,
        }
        if sidecar_contract is not None:
            unavailable["sidecar_contract"] = sidecar_contract
        return unavailable

    g3_fn = g3_status_fn or _default_g3_status
    status = g3_fn(species, drug)
    claim_allowed = (status == "passed")     # 红线:机制解释仅 G3 passed 才声称

    blocked = []
    for ev in (getattr(r, "evidence", None) or []):
        if ev.get("kind") == "fba":
            blocked = ev.get("reactions_blocked", [])
    fba = {
        "growth_inhibition": round(float(gi), FBA_ROUND),
        "baseline_growth": round(float(base), FBA_ROUND),
        "constrained_growth": round(float(cons), FBA_ROUND),
        "reactions_blocked": list(blocked),
        "note": "一阶原理代谢 FBA 模拟(iML1515):钳制代谢靶反应通量→估 growth 抑制(可证伪)",
    }
    fused = {
        "available": True,
        "engine": "gem_fba",
        "fba_simulation": fba,
        "g3_gate": {"status": status, "claim_allowed": claim_allowed},
        # 机制解释仅 G3 门后声称;否则 None(候选)
        "mechanism_claim": (r.mechanism if claim_allowed else None),
        "disclaimer": ("FBA 为可证伪机制模拟;G3 门"
                       + ("已验证,机制可作解释来源" if claim_allowed
                          else "未验证该药(候选机制,不作已证实解释)")),
    }
    if sidecar_contract is not None:
        fused["sidecar_contract"] = sidecar_contract
    return fused
