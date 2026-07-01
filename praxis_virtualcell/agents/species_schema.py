"""W1.1(v0.4):species-aware request schema —— 结构化请求 + 对象归一。

把 v0.2/v0.3 的 gene→delta_expression 请求词汇,扩到代表物种 × 代表应用所需的:
  perturbation_object: gene / gene_combination / drug / medium / ligand
  target_output:       expression / growth / flux / state / communication

职责边界:**只做 schema 校验与对象归一,不含任何预测**(预测由 route_table 决定路由后的
下游模型/工具完成)。非法或缺字段一律抛 SchemaError,不静默补默认(诚实优先,避免把错误输入
悄悄"洗"成合法请求)。
"""
from __future__ import annotations

# 代表物种(v0.4 scope;unknown → 拒,不臆造支持)
SPECIES = {"human", "mouse", "yeast", "bacteria"}

# 扰动对象类型
PERTURBATION_OBJECTS = {"gene", "gene_combination", "drug", "medium", "ligand"}

# 目标输出(把输出从 delta_expression 扩到 growth/flux/state/communication)
TARGET_OUTPUTS = {"expression", "growth", "flux", "state", "communication"}

# gene 类对象需要非空 targets;medium 类可由 medium 字段承载
_GENE_LIKE = {"gene", "gene_combination"}


class SchemaError(ValueError):
    """请求不合 schema(未知词汇 / 缺必需字段 / 空 targets)。"""


def _norm_target(obj: str, t: str) -> str:
    """按对象类型归一单个 target 标识。"""
    s = str(t).strip()
    if obj in _GENE_LIKE or obj == "ligand":
        return s.upper()          # 基因/配体符号:大写
    if obj == "drug":
        return s.lower()          # 药名:小写(与 LINCS/化合物库习惯一致)
    return s                       # medium 等:保留原样(去空格)


def normalize_request(raw: dict) -> dict:
    """校验 + 归一 → 结构化请求 dict。

    必需字段:species, perturbation_object, target_output;
    gene/gene_combination/drug/ligand 需非空 perturbation_targets(medium 例外)。
    可选字段:cell_type, medium, dose(原样透传,仅去空格)。
    """
    if not isinstance(raw, dict):
        raise SchemaError(f"request 必须是 dict,得到 {type(raw).__name__}")

    species = str(raw.get("species", "")).strip().lower()
    obj = str(raw.get("perturbation_object", "")).strip().lower()
    out = str(raw.get("target_output", "")).strip().lower()

    if species not in SPECIES:
        raise SchemaError(f"未知 species={species!r}(支持:{sorted(SPECIES)})")
    if obj not in PERTURBATION_OBJECTS:
        raise SchemaError(f"未知 perturbation_object={obj!r}(支持:{sorted(PERTURBATION_OBJECTS)})")
    if out not in TARGET_OUTPUTS:
        raise SchemaError(f"未知 target_output={out!r}(支持:{sorted(TARGET_OUTPUTS)})")

    targets_raw = raw.get("perturbation_targets")
    if obj != "medium":
        if not targets_raw:
            raise SchemaError(f"perturbation_object={obj} 需要非空 perturbation_targets")
        targets = [_norm_target(obj, t) for t in targets_raw]
    else:
        targets = [_norm_target(obj, t) for t in (targets_raw or [])]

    req: dict = {
        "species": species,
        "perturbation_object": obj,
        "target_output": out,
        "perturbation_targets": targets,
    }
    # 可选上下文字段(原样,仅去空格)——保留供下游 GEM/药物模型审查 medium/dose/context
    for k in ("cell_type", "medium", "dose"):
        if raw.get(k) is not None:
            req[k] = str(raw[k]).strip()
    return req
