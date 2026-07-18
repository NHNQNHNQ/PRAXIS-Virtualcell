"""v0.6:统一 自然语言→报告 服务层(CLI / API / web 共用)。

流程:text →(LLM 解析 or 确定性 fallback)→ candidate_request →(deterministic validator)→
确认后的 VirtualCellRequest → 现有离线 runtime → structured report(+可选 narrative)+ trace + provenance + llm_metadata。

铁律(assert_llm_boundaries 守卫):LLM 只产 candidate/router-suggestion/critic-notes/narrative;
prediction / hard-rule / learned reliability / abstain-downgrade-accept 终决 / provenance 全由确定性 runtime 决定。
冲突:deterministic wins。默认 mode=OFFLINE 时**不调用任何 LLM**。
"""
from __future__ import annotations

import hashlib
import json
import math
import re

from praxis_virtualcell.core.config import RuntimeConfig, assert_llm_boundaries
from praxis_virtualcell.core.request import VirtualCellRequest

# 白名单(validator 用)
SUPPORTED_SPECIES = {"human", "mouse", "yeast", "bacteria"}
SUPPORTED_PERTURBATION = {"gene", "gene_combination", "drug", "medium", "ligand"}
SUPPORTED_TASKS = {"predict_delta_expression"}
ALLOWED_OUTPUTS = {"delta_expression", "pathway_response", "reliability_report",
                   "growth", "flux", "state", "communication"}
_REQUIRED = ("species", "perturbation_type", "perturbation_targets", "task_type")
_STRUCTURED_DESCRIPTION_MARKER = "结构化描述:"
_STRUCTURED_FIELDS = frozenset({
    "species", "cell_type", "perturbation_type", "perturbation_targets",
    "input_modality", "output_modality", "task_type", "requested_outputs",
})
_STRUCTURED_MARKER_RE = re.compile(rf"(?m)^{re.escape(_STRUCTURED_DESCRIPTION_MARKER)}")

_LLM_SYS = (
    "你把用户的虚拟细胞实验描述解析成 JSON,只输出 JSON 不要解释。字段:species(human/mouse/"
    "yeast/bacteria 小写)、cell_type、perturbation_type(gene/gene_combination/drug/medium/ligand)、"
    "perturbation_targets(数组)、task_type(predict_delta_expression)、requested_outputs(数组)、"
    "confidence(0-1)、missing_fields(数组)、assumptions(数组)。无法判断的字段留空或省略。"
)


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _is_utf8_safe(value: str) -> bool:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _response_safe_candidate(cand: dict) -> dict:
    """保留安全的 validator-invalid raw-like 候选；不安全时改为固定空壳。"""
    if not _is_json_response_safe(cand):
        return {"perturbation_targets": []}
    return cand


def _within_response_budget(value, *, max_depth: int = 64, max_nodes: int = 4096) -> bool:
    """Iterative structure budget keeps framework serializers away from depth overflows."""
    stack = [(value, 0)]
    seen_nodes = 0
    while stack:
        current, depth = stack.pop()
        seen_nodes += 1
        if depth > max_depth or seen_nodes > max_nodes:
            return False
        if isinstance(current, dict):
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, (list, tuple)):
            stack.extend((item, depth + 1) for item in current)
    return True


def _is_json_response_safe(value) -> bool:
    if not _within_response_budget(value):
        return False
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError):
        return False
    return len(encoded) <= 262_144


def _safe_text_list(value) -> list[str]:
    return [
        item
        for item in value
        if isinstance(item, str) and _is_utf8_safe(item)
    ] if isinstance(value, list) else []


def _safe_llm_error(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and _is_utf8_safe(value):
        return value
    return "llm_error_not_response_safe"


def _safe_parse_failure(error: str = "parse_response_not_json_safe") -> dict:
    return {
        "candidate_request": {"perturbation_targets": []},
        "schema_valid": False,
        "missing_fields": [],
        "errors": [error],
        "clarification_required": True,
        "parser": "deterministic",
        "llm_used": False,
        "fallback_used": True,
        "assumptions": [],
        "llm_metadata": {},
    }


def _extract_structured_description(text: str) -> tuple[str, dict | None, list[str]]:
    """拆出行首显式结构化 JSON；只允许请求字段白名单，错误必须进入澄清态。"""
    matches = list(_STRUCTURED_MARKER_RE.finditer(text))
    if not matches:
        return text, None, []
    marker = matches[-1]
    natural_text = text[:marker.start()].rstrip()
    raw = text[marker.end():].strip()
    if not raw:
        return natural_text, None, ["structured_description_malformed"]
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError, RecursionError):
        return natural_text, None, ["structured_description_malformed"]
    if not isinstance(parsed, dict):
        return natural_text, None, ["structured_description_not_object"]
    errors = (["structured_description_unknown_fields"]
              if set(parsed) - _STRUCTURED_FIELDS else [])
    if "requested_outputs" in parsed:
        requested_outputs = parsed["requested_outputs"]
        if (
            not isinstance(requested_outputs, list)
            or not all(isinstance(item, str) for item in requested_outputs)
        ):
            errors.append("invalid_requested_outputs_type")
        elif any(item not in ALLOWED_OUTPUTS for item in requested_outputs):
            errors.append("unsupported_requested_outputs")
    if "perturbation_targets" in parsed and (
        not isinstance(parsed["perturbation_targets"], list)
        or not all(isinstance(item, str) for item in parsed["perturbation_targets"])
    ):
        errors.append("invalid_perturbation_targets_type")
    overlay = {key: parsed[key] for key in _STRUCTURED_FIELDS if key in parsed}
    return natural_text, overlay, errors


def coerce_str_list(value) -> list[str]:
    """未受信值 → `list[str]`(**两层**守卫:容器级 + 元素级),供消费 `parse_query`
    candidate 字段的 UI 层使用(§10 修正 12)。

    **为什么必须两层(§10 修正 9③ 的判据②,亦是 opus 建议的修法里的缺陷)**:
    只加**元素级** `isinstance(t, str)` **挡不住字符拆** —— 实测
    `[t for t in "AHR" if isinstance(t, str)] == ['A','H','R']`(**拆出来的字符本身就是 str**)。
    字符拆只能由**容器级** `isinstance(value, list)` 挡(C3 既有手法)。两者**各挡各的**:
    容器级挡字符拆、元素级挡 dict/None/int 混进来。

    **存在理由**:`parse_query` 在 validator 无 normalized 产物时按设计返回 response-safe、但
    **未做语义归一/值白名单**的 raw-like candidate,好让用户看到并修正 LLM 产物。最终
    `schema_valid=False` 也可能因 structured error 携带 normalized candidate,所以消费侧不能靠
    该布尔值猜字段形状,必须始终按声明类型读取。
    本函数是**共享**的消费侧守卫:任何新增的第三个消费者都应调它,而不是各自重写
    (C3 教训 #2「同型缺口未回填」:safety_contract 抄 llm_router 时修了漏洞却没回填原件)。

    fail-closed:非 list → `[]`(**不字符拆**);list → 只保留 str 元素(丢弃 dict/None/int,
    **不发明**、不抛 TypeError)。
    """
    return _safe_text_list(value)


def validate_candidate(cand: dict) -> dict:
    """确定性校验 + 归一。返回 {schema_valid, missing_fields, errors, normalized}。

    **C4 边界 try = public API 契约防线(defense-in-depth)**:fail-closed —— 捕获**已识别的
    4 类** → schema_valid=False + errors=["candidate_malformed"]:
    `TypeError`(混合类型 key)· `AttributeError` · `ValueError`(含 `UnicodeEncodeError`
    孤立代理项 与 循环引用 "Circular reference detected",实测二者均为其子类)·
    `RecursionError`(深嵌套 dict —— 它是 **RuntimeError 子类**,曾穿透原三元组,§10 修正 8)。

    **不声称捕获一切(设计上的有意取舍,非遗漏)**:**任何有限白名单都不可能兑现"绝不把
    异常透给调用方"** —— 全称主张 vs 枚举,量词就对不上。`MemoryError`、未来代码路径的
    未知异常类型均在白名单外;`except BaseException` 能兑现"绝不"却是**坏实践**(会吞掉
    `KeyboardInterrupt`/`SystemExit`,让进程杀不掉、真 bug 被静默)。故此处**只捕已识别 4 类**,
    并明示边界。**"绝不"一词已作废(§10 修正 8:本单元第 6 次未限定作用域的全称词)。**

    **定性必须精确**:validator 函数由 `/api/parse`、Streamlit 确认页与 `/api/jobs` 生产调用;
    后者把它作为 runner/save 前最终复验。具体异常形状的可达性仍不同:标准 HTTP JSON 的
    object key 恒为 string 且不能表达循环引用,而混合类型 key/循环/某些超深 Python dict 可由
    脚本、notebook 或直接调用触发。故本层既不是“生产不可达”,也不能把每一种捕获异常都写成
    HTTP 可构造。
    """
    try:
        return _validate_candidate_impl(cand)
    except (TypeError, AttributeError, ValueError, RecursionError):
        return {"schema_valid": False, "missing_fields": [],
                "errors": ["candidate_malformed"], "normalized": None}


def _validate_candidate_impl(cand: dict) -> dict:
    """validate_candidate 的实现体(**已识别的 4 类**异常由外层边界 try 兜 —— 非"一切异常",
    见其 docstring)。"""
    errors, missing = [], []
    d = dict(cand or {})
    serialized = json.dumps(d, sort_keys=True, ensure_ascii=False)
    try:
        serialized.encode("utf-8")
    except UnicodeEncodeError:
        return {"schema_valid": False, "missing_fields": [],
                "errors": ["candidate_not_utf8_safe"], "normalized": None}
    species = str(d.get("species", "")).strip().lower()
    # C3 全入口守卫(fresh 复审补漏):cand 来自未受信 LLM JSON —— 只接受 list/dict,
    # 绝不把字符串逐字符拆(perturbation_targets:"AHR" → ['A','H','R'] 会带着
    # schema_valid=True 返给前端用户,内核随后真按 ['A','H','R'] 跑);标量/非 dict 亦不得
    # 让 /api/parse(无 try/except)因未捕获异常 500。手法同 llm_critic.py/safety_contract.py。
    _perturbation = d.get("perturbation")
    _perturbation = _perturbation if isinstance(_perturbation, dict) else {}
    ptype = str(d.get("perturbation_type") or _perturbation.get("type", "")).strip().lower()
    targets = d.get("perturbation_targets")
    if targets is None and _perturbation:
        targets = _perturbation.get("targets")
    # C4 元素级白名单:容器级 isinstance 只守了"targets 是不是 list",没守元素 ——
    # 原 `str(t).strip()` 对**任何**对象都成功,把 [None,'AHR'] 变成 ['NONE','AHR']
    # (凭空发明基因 NONE)、[['AHR']] 变成 ["['AHR']"],且带 schema_valid=True 返给前端,
    # 用户确认后内核真按假基因名跑。**try/except 兜不住这一类**(str() 不抛异常)。
    # 修法跟随 llm_router.py 的值白名单先例:只接受契约内类型(str),其余丢弃 ——
    # 畸形类型全集无需枚举,因为"其余"是补集。
    targets = ([t.strip() for t in targets if isinstance(t, str) and t.strip()]
               if isinstance(targets, list) else [])
    task = str(d.get("task_type") or d.get("task", "")).strip().lower() or "predict_delta_expression"
    raw_output_modality = d.get("output_modality")
    if raw_output_modality in (None, ""):
        output_modality = "delta_expression"
    elif isinstance(raw_output_modality, str):
        output_modality = raw_output_modality.strip().lower()
        if output_modality not in ALLOWED_OUTPUTS:
            errors.append(f"unsupported_output_modality:{output_modality}")
    else:
        output_modality = ""
        errors.append("invalid_output_modality_type")
    raw_input_modality = d.get("input_modality")
    if raw_input_modality in (None, ""):
        input_modality = "scRNA"
    elif isinstance(raw_input_modality, str):
        input_modality = raw_input_modality.strip()
    else:
        input_modality = ""
        errors.append("invalid_input_modality_type")
    raw_cell_type = d.get("cell_type")
    if raw_cell_type is None:
        cell_type = None
    elif isinstance(raw_cell_type, str):
        cell_type = raw_cell_type.strip() or None
    else:
        cell_type = None
        errors.append("invalid_cell_type_type")
    raw_request_id = d.get("request_id")
    if raw_request_id in (None, ""):
        request_id = "vc-" + _hash(serialized)
    elif isinstance(raw_request_id, str) and raw_request_id.strip():
        request_id = raw_request_id.strip()
    else:
        request_id = ""
        errors.append("invalid_request_id_type")
    raw_metadata = d.get("metadata")
    if raw_metadata is None:
        metadata = {}
    elif isinstance(raw_metadata, dict):
        metadata = dict(raw_metadata)
        if not _is_json_response_safe(metadata):
            errors.append("invalid_metadata_value")
            metadata = {}
    else:
        errors.append("invalid_metadata_type")
        metadata = {}
    _raw_outputs = (
        d.get("requested_outputs")
        if "requested_outputs" in d
        else metadata.get("requested_outputs")
    )
    # C4:`o in ALLOWED_OUTPUTS`(set)对 unhashable 元素抛 TypeError → /api/parse 500
    # (main 活 bug)。isinstance 短路在 `in` 之前 → 元素级畸形不再崩;值白名单同时保证
    # 输出 ⊆ ALLOWED_OUTPUTS。
    outputs = ([o for o in _raw_outputs if isinstance(o, str) and o in ALLOWED_OUTPUTS]
               if isinstance(_raw_outputs, list) else [])
    # C4:元素级类型过滤(原 list(x) 元素任意 → dict/list 原样进 normalized.metadata)。
    _raw_assumptions = (
        d.get("assumptions") if "assumptions" in d else metadata.get("assumptions")
    )
    assumptions = _safe_text_list(_raw_assumptions)
    metadata["requested_outputs"] = outputs
    metadata["assumptions"] = assumptions

    raw_tissue = d.get("tissue")
    if raw_tissue is None:
        tissue = None
    elif isinstance(raw_tissue, str):
        tissue = raw_tissue.strip() or None
    else:
        tissue = None
        errors.append("invalid_tissue_type")
    raw_perturbation_time = d.get("perturbation_time")
    if raw_perturbation_time is None:
        perturbation_time = None
    elif isinstance(raw_perturbation_time, str):
        perturbation_time = raw_perturbation_time.strip() or None
    else:
        perturbation_time = None
        errors.append("invalid_perturbation_time_type")
    raw_dose = d.get("perturbation_dose")
    if raw_dose is None:
        perturbation_dose = None
    else:
        perturbation_dose = None
        if isinstance(raw_dose, (int, float)) and not isinstance(raw_dose, bool):
            try:
                normalized_dose = float(raw_dose)
            except (OverflowError, TypeError, ValueError):
                normalized_dose = math.nan
            if math.isfinite(normalized_dose):
                perturbation_dose = normalized_dose
        if perturbation_dose is None:
            errors.append("invalid_perturbation_dose")
    raw_baseline = d.get("baseline_context")
    if raw_baseline is None:
        baseline_context = raw_baseline
    elif isinstance(raw_baseline, dict) and _is_json_response_safe(raw_baseline):
        baseline_context = raw_baseline
    else:
        baseline_context = None
        errors.append("invalid_baseline_context")
    raw_constraints = d.get("constraints")
    if raw_constraints is None:
        constraints = {}
    elif isinstance(raw_constraints, dict) and _is_json_response_safe(raw_constraints):
        constraints = raw_constraints
    else:
        constraints = {}
        errors.append("invalid_constraints")

    if not species:
        missing.append("species")
    elif species not in SUPPORTED_SPECIES:
        errors.append(f"unsupported_species:{species}")
    if not ptype:
        missing.append("perturbation_type")
    elif ptype not in SUPPORTED_PERTURBATION:
        errors.append(f"unsupported_perturbation_type:{ptype}")
    if ptype != "medium" and not targets:
        missing.append("perturbation_targets")
    if task not in SUPPORTED_TASKS:
        errors.append(f"unsupported_task:{task}")

    # gene/ligand 归一大写、drug 小写(与 species_schema 一致)
    if ptype in ("gene", "gene_combination", "ligand"):
        targets = [t.upper() for t in targets]
    elif ptype == "drug":
        targets = [t.lower() for t in targets]

    normalized = {
        "request_id": request_id,
        "species": species, "perturbation_type": ptype, "perturbation_targets": targets,
        "input_modality": input_modality,
        "output_modality": output_modality,
        "task_type": task, "cell_type": cell_type,
        "tissue": tissue,
        "perturbation_dose": perturbation_dose,
        "perturbation_time": perturbation_time,
        "baseline_context": baseline_context,
        "metadata": metadata,
        "constraints": constraints,
    }
    schema_valid = not missing and not errors
    return {"schema_valid": schema_valid, "missing_fields": missing, "errors": errors,
            "normalized": normalized if schema_valid else None}


def _deterministic_parse(text: str) -> dict:
    """无 LLM 的关键词 fallback(不臆造:只抓明确信号)。"""
    t = text.lower()
    species = next((s for s in ("human", "mouse", "yeast", "bacteria") if s in t), "")
    for zh, en in (("人", "human"), ("小鼠", "mouse"), ("酵母", "yeast"), ("细菌", "bacteria"),
                   ("大肠杆菌", "bacteria"), ("e. coli", "bacteria"), ("e.coli", "bacteria")):
        if not species and zh in t:
            species = en
    ptype = "drug" if ("drug" in t or "药" in t) else "gene"
    # 抓大写基因符号(2-8 位字母数字,首字母大写)—— 仅从原文
    genes = re.findall(r"\b[A-Z][A-Z0-9]{1,7}\b", text)
    genes = [g for g in genes if g not in ("K562", "T", "DNA", "RNA", "AND", "OR")][:4]
    return {"species": species, "perturbation_type": ptype, "perturbation_targets": genes,
            "task_type": "predict_delta_expression", "assumptions": ["deterministic keyword parse"]}


def parse_query(text: str, *, config: RuntimeConfig | None = None) -> dict:
    """自然语言 → candidate_request + 校验结果 + parser 元数据。OFFLINE 不调 LLM。"""
    cfg = config or RuntimeConfig.from_env()
    assert_llm_boundaries(cfg)                # C3 全入口守卫(此前只有 run_query/free-text 覆盖)
    if not _is_utf8_safe(text):
        return {
            "candidate_request": {"perturbation_targets": []},
            "schema_valid": False, "missing_fields": [],
            "errors": ["query_not_utf8_safe"], "clarification_required": True,
            "parser": "deterministic", "llm_used": False, "fallback_used": True,
            "assumptions": [], "llm_metadata": {},
        }

    natural_text, structured_overlay, structured_errors = _extract_structured_description(text)
    llm_used = fallback_used = False
    llm_metadata: dict = {}
    cand = None
    assumptions: list = []
    if cfg.llm_enabled:
        from praxis_virtualcell.agents_llm.llm_client import make_llm_client
        client = make_llm_client(cfg)
        res = client.complete([{"role": "system", "content": _LLM_SYS},
                               {"role": "user", "content": natural_text}], json_mode=True)
        content = res.get("content")
        content_is_safe = isinstance(content, str) and _is_utf8_safe(content)
        safe_model = (cfg.deepseek_model if isinstance(cfg.deepseek_model, str)
                      and _is_utf8_safe(cfg.deepseek_model) else "unknown")
        llm_metadata = {"provider": "deepseek", "model": safe_model,
                        "prompt_hash": _hash(_LLM_SYS + natural_text),
                        "response_hash": _hash(content) if content and content_is_safe else None,
                        "error": _safe_llm_error(res.get("error")),
                        "schema_valid": None, "fallback_used": False}
        if content and content_is_safe:
            try:
                cand = json.loads(content)
                # C3 全入口守卫(opus 终审补漏):cand.get 要求 cand 是 dict——JSON 顶层为
                # list/数字/字符串/bool/None 时(注入/畸形产物)天然抛 AttributeError,
                # 与下方 assumptions 的 isinstance 守卫共用同一 except,fail-closed 落回
                # _deterministic_parse,不让 /api/parse 端点因未捕获异常 500。
                raw_assumptions = cand.get("assumptions")
                llm_used = True
                # 只接受 list(非 list 丢弃置 [],绝不把字符串逐字符拆成 ['a','b','c']
                # 直接返给前端用户,复刻 llm_critic.py/safety_contract.py 同一手法)。
                # C4 Task 3 元素级白名单:本处与 validate_candidate 内那处**是两处独立代码**,
                # Task 1 的收紧保护不到这里。原 list(x) 元素任意 → 返回 →
                # ParseOut.assumptions: list[str] → pydantic 对 dict/list/None/int 全抛
                # ValidationError → /api/parse **HTTP 500**(第二个活 bug,端到端实测)。
                # 包着本行的 try 捕不到(list() 不抛,ValidationError 在 return 之后)。
                assumptions = _safe_text_list(raw_assumptions)
            # C4 修正 9②:补 RecursionError —— `:184` 的 json.loads 与 Task 2 修前的边界 try
            # 是**同一形状的缺口**(C3 教训 #2「同型缺口未回填」的又一实例)。深嵌套 JSON →
            # json.loads 抛 RecursionError(**RuntimeError 子类**,不在前三者的继承链上)→
            # 原三元组捕不到 → 端到端实测 /api/parse **500**,且 Task 2 在 validate_candidate
            # 的边界 try 根本轮不到执行(json.loads 程序顺序在先)。
            # 限定表述(§10 修正 11 已更新:原写"是否还有第三处未捕,层1 无机械判据" ——
            # 那是当时诚实的不确定标注,**现在答案已确定**,不更新就从"诚实的不确定"变成
            # "已知而未更新"):经**机械枚举** json.loads/json.dumps 消费未受信 LLM JSON 的
            # 调用点(命令+输出见 §10 修正 11),原清单 7 处仍捕获;加上 2026-07-18 新增的
            # response-safe json.dumps,按原 LLM JSON 口径当前登记 **8 处**。显式 structured
            # user JSON 的 json.loads 另计 +1,也在边界内捕获。
            # **仍不得**声称 /api/parse 或全仓"对 RecursionError 已全覆盖" —— **层1(哪些算
            # "未受信 LLM JSON")是语义判断、无机械判据**,残余风险照旧。
            except (json.JSONDecodeError, TypeError, AttributeError, RecursionError):
                cand = None
        elif content:
            llm_metadata["error"] = "response_not_utf8_safe"
    if cand is None:
        cand = _deterministic_parse(natural_text)
        fallback_used = True
        assumptions = coerce_str_list(cand.get("assumptions"))
    else:
        cand = dict(cand)
        # parser 产生的 request_id 永远由本服务生成，LLM 不能指定审计标识。
        cand.pop("request_id", None)
    if structured_overlay is not None:
        cand = {**cand, **structured_overlay}

    v = validate_candidate(cand)
    errors = [*structured_errors, *v["errors"]]
    schema_valid = v["schema_valid"] and not structured_errors
    if llm_metadata:
        llm_metadata["schema_valid"] = schema_valid
        llm_metadata["fallback_used"] = fallback_used
    raw_candidate = {**cand, "perturbation_targets": cand.get("perturbation_targets", [])}
    result = {
        "candidate_request": v["normalized"] or _response_safe_candidate(raw_candidate),
        "schema_valid": schema_valid, "missing_fields": v["missing_fields"],
        "errors": errors, "clarification_required": not schema_valid,
        "parser": "llm_with_validator" if llm_used else "deterministic",
        "llm_used": llm_used, "fallback_used": fallback_used,
        "assumptions": assumptions, "llm_metadata": llm_metadata,
    }
    return result if _is_json_response_safe(result) else _safe_parse_failure()


def run_query(request_dict: dict, *, config: RuntimeConfig | None = None,
              enable_llm_report: bool = False) -> dict:
    """已确认的 request → 离线 runtime 执行 → structured report + trace + provenance + narrative。"""
    cfg = config or RuntimeConfig.from_env()
    assert_llm_boundaries(cfg)               # 铁律守卫
    from praxis_virtualcell.workflows.predict_delta_expression import build_runtime

    rt = build_runtime(cfg)
    req = dict(request_dict)
    if not req.get("request_id"):
        req["request_id"] = "vc-" + _hash(json.dumps(req, sort_keys=True, ensure_ascii=False))
    report = rt.run_workflow(VirtualCellRequest.from_dict(req))
    _tr = getattr(rt.bus, "trace", None)
    _msgs = _tr() if callable(_tr) else (_tr if isinstance(_tr, list) else getattr(rt.bus, "_trace", []))
    trace = [{"message_id": m.message_id, "sender": m.sender, "receiver": m.receiver,
              "message_type": m.message_type, "timestamp": m.timestamp,
              "schema_version": m.schema_version, "trace_id": m.trace_id,
              "task_id": m.task_id} for m in _msgs]
    return {
        "structured_report": {k: v for k, v in report.items() if k != "narrative"},
        "narrative": report.get("narrative"),
        "trace": trace,
        "provenance": report.get("provenance", {}),
        "reliability_decision": {"abstain": report.get("abstain"),
                                 "reliability": report.get("reliability"),
                                 "learned_reliability": report.get("learned_reliability")},
        "llm_used_for_prediction": False,        # 恒 False:LLM 不碰预测
        "mode": cfg.mode.value, "llm_enabled": cfg.llm_enabled,
    }


def run_full_query(text: str, *, config: RuntimeConfig | None = None,
                   enable_llm_report: bool = False) -> dict:
    """一步式:text → parse → (仅当 schema_valid)run。web 的 confirm 流程用 parse_query + run_query 分离。"""
    parsed = parse_query(text, config=config)
    if not parsed["schema_valid"]:
        return {"stage": "clarification_required", **parsed}
    out = run_query(parsed["candidate_request"], config=config, enable_llm_report=enable_llm_report)
    return {"stage": "done", "parsed": parsed, **out}
