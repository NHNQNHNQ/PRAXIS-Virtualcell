"""M1/M5/M8 gene-set 加载与命中(P10.B4 rule-based advisory 数据层)。

确定性、零 LLM、lazy 缓存。gene-set 为公开策展真实基因符号(GO/Reactome-style),
仅用于让休眠模块 M1/M5/M8 在相关基因扰动时进 module_plan 并挂 rule_based/evidence_limited
advisory —— 不产任何数值 delta(gene-set 成员只能给定性 advisory,数值预测=过度声称)。
"""
from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from praxis_virtualcell.biological_modules import modules as M

# gene-set 数据目录:仓库根 data/(与 data/gems、data/drug_signatures、data/cellstate 同源约定)
_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "module_gene_sets"

# gene-set 覆盖的模块 id(∈ MODULE_ORDER)→ 数据文件名。声明序 = M1,M5,M8。
_MODULE_FILES: dict[str, str] = {
    "membrane_system": "membrane_system.json",
    "biosynthetic_network": "biosynthetic_network.json",
    "degradation_machinery": "degradation_machinery.json",
}

# 供上层判「该 module 是否 gene-set advisory 模块」(公开只读集合)
GENE_SET_MODULES = frozenset(_MODULE_FILES)


@cache
def gene_set_of(module_id: str) -> frozenset[str]:
    """返回 module 的大写基因符号集(lazy 读 JSON,缓存)。非 gene-set 模块 → 空集。"""
    fname = _MODULE_FILES.get(module_id)
    if fname is None:
        return frozenset()
    doc = json.loads((_DATA_DIR / fname).read_text(encoding="utf-8"))
    return frozenset(str(g).strip().upper() for g in doc.get("gene_set", []))


def modules_hit_by(targets: list[str]) -> list[str]:
    """targets 命中的 module id(M1/M5/M8 子集),按 MODULE_ORDER 序、去重。
    精确大写归一匹配(防子串误命中,B3 IFNB2/IL-6 教训)。"""
    norm = {str(t).strip().upper() for t in (targets or []) if str(t).strip()}
    hits = [mid for mid in _MODULE_FILES if norm & gene_set_of(mid)]
    return sorted(hits, key=M.MODULE_ORDER.index)
