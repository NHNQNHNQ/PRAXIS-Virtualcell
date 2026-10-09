"""cell_type 越界判据(Gate C)。独立复用 reliability.py 的 declaring/unsupported 逻辑
(不 import reliability,避免耦合裁决路径)。窄门:仅'有声明 supported_cell_types 的 used
predictor 且全部越界'才判 violation —— 与 reliability downgrade 同源,避免误伤无声明 predictor。
reliability 已 abstain 时不触发,与 reliability not-abstain 守卫镜像(reliability.py:113 短路)。
Gate C 在 reliability 已有 downgrade 之上叠加'全越界→对外 abstain';reliability 数值不变。"""
from __future__ import annotations


def check_cell_type_domain(request: dict, brain_context: dict, models_used: list,
                           *, reliability_abstained: bool = False) -> list[str]:
    """返回越界(声明了 supported_cell_types 且 req cell_type 不在其中)的 used predictor 清单。
    空 = 不触发(reliability 已 abstain / 无 cell_type / 无 used / 无声明 / 在库 / 部分声明未全越界)。"""
    if reliability_abstained:      # 镜像 reliability.py:113 的 not-abstain 守卫:reliability 已因其它
        return []                  # 原因 abstain 时不算 cell_type downgrade,Gate C 也不独立触发(保持同源)
    req_ct = request.get("cell_type")
    if not req_ct or not models_used:
        return []
    appmap = brain_context.get("model_applicability") or {}
    declaring = [n for n in models_used
                 if appmap.get(n, {}).get("supported_cell_types") is not None]
    unsupported = [n for n in declaring if req_ct not in appmap[n]["supported_cell_types"]]
    if declaring and len(unsupported) == len(declaring):
        return unsupported
    return []
