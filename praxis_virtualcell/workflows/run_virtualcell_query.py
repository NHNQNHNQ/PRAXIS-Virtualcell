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

_LLM_SYS = (
    "你把用户的虚拟细胞实验描述解析成 JSON,只输出 JSON 不要解释。字段:species(human/mouse/"
    "yeast/bacteria 小写)、cell_type、perturbation_type(gene/gene_combination/drug/medium/ligand)、"
    "perturbation_targets(数组)、task_type(predict_delta_expression)、requested_outputs(数组)、"
    "confidence(0-1)、missing_fields(数组)、assumptions(数组)。无法判断的字段留空或省略。"
)


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


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

    **定性必须精确 —— "可达"分两种,本层只占后一种**:
    - **当前两个已知消费点的正常路径不可达**(勘察实证):`/api/parse` → `parse_query` 的
      `cand` 只可能来自 `json.loads`(**JSON object key 恒为 str**)或 `_deterministic_parse`
      (固定 str key);`praxis_vc_web/app.py:75` 的 `cand` 来自 `json.loads` 产物或本函数自产
      normalized 二者之一(**schema_valid=False 时 `parse_query` 返的是未归一的原始 LLM JSON /
      `_deterministic_parse` 产物的展开** —— 页面 2 让用户补充/修正的常见路径),
      **两者 key 皆恒 str**。→ **本层不是当前生产 500 的防线**,那个由 `_validate_candidate_impl`
      里的元素级白名单管(C4 Task 1)。深嵌套那条**当前**亦生产不可达,但**依据更弱**:
      `llm_client.py:23` `max_tokens` **默认值** 1024(**可调默认参数,非结构不变量** ——
      与"JSON key 恒 str"这种格式级保证不同级)→ LLM 产不出所需深度;**调大到 128k 级则
      余量被吃穿**(§10 修正 8)。
    - **直接调用可达**(实测,故非死码):触发需**非 JSON 来源的 dict**(混合类型 key)→
      `json.dumps(d, sort_keys=True)` 抛 `TypeError: '<' not supported between 'str' and 'int'`;
      或深嵌套 dict → `RecursionError`。

    **真实价值** = public API 契约防线:防脚本 / notebook / 直接调用 / **未来第 3 个调用点**。
    定性对标 **C2 的 Gate B**(防御性完整性断言:字段恒由代码构造、正常路径不触发、防未来
    重构漏挂)—— 项目已接受的模式。**非死码,但也不得说成"生产可达"**(C4 §10 修正 7)。
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
    _raw_outputs = d.get("requested_outputs")
    # C4:`o in ALLOWED_OUTPUTS`(set)对 unhashable 元素抛 TypeError → /api/parse 500
    # (main 活 bug)。isinstance 短路在 `in` 之前 → 元素级畸形不再崩;值白名单同时保证
    # 输出 ⊆ ALLOWED_OUTPUTS。
    outputs = ([o for o in _raw_outputs if isinstance(o, str) and o in ALLOWED_OUTPUTS]
               if isinstance(_raw_outputs, list) else [])
    # C4:元素级类型过滤(原 list(x) 元素任意 → dict/list 原样进 normalized.metadata)。
    _raw_assumptions = d.get("assumptions")
    assumptions = ([a for a in _raw_assumptions if isinstance(a, str)]
                   if isinstance(_raw_assumptions, list) else [])

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
        "request_id": d.get("request_id") or "vc-" + _hash(json.dumps(d, sort_keys=True, ensure_ascii=False)),
        "species": species, "perturbation_type": ptype, "perturbation_targets": targets,
        "input_modality": d.get("input_modality") or "scRNA",
        "output_modality": d.get("output_modality") or "delta_expression",
        "task_type": task, "cell_type": d.get("cell_type"),
        "metadata": {"requested_outputs": outputs, "assumptions": assumptions},
    }
    schema_valid = not missing and not errors
    return {"schema_valid": schema_valid, "missing_fields": missing, "errors": errors,
            "normalized": normalized if schema_valid else None}


def _deterministic_parse(text: str) -> dict:
    """无 LLM 的关键词 fallback 解析(不臆造:只抓明确信号)。"""
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
    llm_used = fallback_used = False
    llm_metadata: dict = {}
    cand = None
    assumptions: list = []
    if cfg.llm_enabled:
        from praxis_virtualcell.agents_llm.llm_client import make_llm_client
        client = make_llm_client(cfg)
        res = client.complete([{"role": "system", "content": _LLM_SYS},
                               {"role": "user", "content": text}], json_mode=True)
        content = res.get("content")
        llm_metadata = {"provider": "deepseek", "model": cfg.deepseek_model,
                        "prompt_hash": _hash(_LLM_SYS + text),
                        "response_hash": _hash(content) if content else None,
                        "error": res.get("error"), "schema_valid": None, "fallback_used": False}
        if content:
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
                assumptions = [a for a in raw_assumptions if isinstance(a, str)] if isinstance(raw_assumptions, list) else []
            # C4 修正 9②:补 RecursionError —— `:184` 的 json.loads 与 Task 2 修前的边界 try
            # 是**同一形状的缺口**(C3 教训 #2「同型缺口未回填」的又一实例)。深嵌套 JSON →
            # json.loads 抛 RecursionError(**RuntimeError 子类**,不在前三者的继承链上)→
            # 原三元组捕不到 → 端到端实测 /api/parse **500**,且 Task 2 在 validate_candidate
            # 的边界 try 根本轮不到执行(json.loads 程序顺序在先)。
            # 限定表述(§10 修正 11 已更新:原写"是否还有第三处未捕,层1 无机械判据" ——
            # 那是当时诚实的不确定标注,**现在答案已确定**,不更新就从"诚实的不确定"变成
            # "已知而未更新"):经**机械枚举** json.loads/json.dumps 消费未受信 LLM JSON 的
            # 调用点(命令+输出见 §10 修正 11),当前清单 **7 处**(本处 + 边界 try :75 +
            # llm_critic:43 + llm_router:52 + cross_module_reasoner:48 + safety_contract:64 +
            # llm_input_interpreter:53)**已全部捕获 RecursionError**。
            # **仍不得**声称 /api/parse 或全仓"对 RecursionError 已全覆盖" —— **层1(哪些算
            # "未受信 LLM JSON")是语义判断、无机械判据**,残余风险照旧。
            except (json.JSONDecodeError, TypeError, AttributeError, RecursionError):
                cand = None
    if cand is None:
        cand = _deterministic_parse(text)
        fallback_used = True
        assumptions = list(cand.get("assumptions") or [])
    v = validate_candidate(cand)
    if llm_metadata:
        llm_metadata["schema_valid"] = v["schema_valid"]
        llm_metadata["fallback_used"] = fallback_used
    return {
        "candidate_request": v["normalized"] or {**cand, "perturbation_targets":
                                                 cand.get("perturbation_targets", [])},
        "schema_valid": v["schema_valid"], "missing_fields": v["missing_fields"],
        "errors": v["errors"], "clarification_required": not v["schema_valid"],
        "parser": "llm_with_validator" if llm_used else "deterministic",
        "llm_used": llm_used, "fallback_used": fallback_used,
        "assumptions": assumptions, "llm_metadata": llm_metadata,
    }


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
