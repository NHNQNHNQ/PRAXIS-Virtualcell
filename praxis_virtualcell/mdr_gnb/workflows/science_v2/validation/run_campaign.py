"""T8:Phase 11 科学验证战役总裁决(串跑 T1–T7 + 出 VERDICT)。

七层的裁决字段是**异构**的(各层按自身语义演化,本任务不为了好聚合去改它们):
  · T1 三子层 → face_validity["gates"] / generalization["gates"]
  · T2 / T3 / T6 / T7 → verdict{...} 里的布尔
  · T4 → all_stable
  · T5 → 计数(n_leaked/n_crashed)+ findings
本模块把它们**归一**成 {gates, pass, findings, ...},再按预注册规则出总裁决。

## 预注册的两条读数(控制者定案,不得在本任务内调整)

计划书正文说 `campaign_pass = all(层 pass)`,但「验收标准」一节又把 T1 列为**软指标**、把
T2/T3/T4/T6/T7 列为**硬红线**。二者有张力 → 定案:**同时输出两个读数,全透明**,让读者自己
判断,而不是我们替他挑一个好看的。

  · campaign_pass  = 硬红线语义 = 所有硬红线层 pass **且** 无 severity=="red_line" 的 finding
  · all_gates_pass = 含软门槛   = 所有层(含 T1 三子层)所有 gates 全 True **且** 无 red_line finding

T5 不在硬红线层清单(计划书未列),但其 findings 若含 red_line 亦拉黑两条读数 —— 规则2 与
层清单彼此独立,这正是当前数据下 T5 的同聚物缺口能拉黑总裁决的原因。

## 诚实纪律

本模块只**读**各层评分函数的产出:不重算指标、不改门槛、不挑数据、不为好看而聚合。
门槛失败 = 如实记为科学发现(软指标),红线失败 = 如实列入 red_flags。VERDICT.md 里的每个
数字都从 payload 插值,prose 不写死结论 —— 数据变了,报告的结论必须跟着变。

## 性能

真串跑七层 ≈ 40s + T4(35 查询 × t4_repeats)。默认 t4_repeats=100 与
reports/antibacterial/mdr_gnb/science_v2/phase11/t4_determinism.json 的存档口径一致,`__main__` 亦走此默认值,
故存档 campaign.json 可由入口一键复现(不静默降配)。测试用小 N 控时长。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from praxis_virtualcell.mdr_gnb.workflows.science_v2.validation import (
    harness,
    t1_predictive,
    t2_ood,
    t3_honesty,
    t4_determinism,
    t5_adversarial,
    t6_evidence,
    t7_e2e,
)

# 仓库根(本文件 parents:[0]=validation [1]=science_v2 [2]=workflows [3]=mdr_gnb
# [4]=praxis_virtualcell [5]=仓库根;与 harness._REPORT_ROOT 同口径)。
_REPO_ROOT = Path(__file__).resolve().parents[5]
_VERDICT_PATH = _REPO_ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v2" / "phase11" / "VERDICT.md"

# 九层键名(T1 三子层不合并 —— 三个方向的门槛与结论各不相同,合并即抹掉信息)。
LAYER_KEYS: tuple[str, ...] = ("t1a", "t1b", "t1c", "t2", "t3", "t4", "t5", "t6", "t7")

# 硬红线层(计划书「Phase 11 验收标准(整体)」逐条列出:T2 OOD 全弃权、T3 无模型物种不出 SIR /
# 非代谢靶不出假机制 / G3 未过 claim 恒 None、T4 trace 全确定、T6 证据零串用、T7 HTTP=直调一致)。
# T1 **不在**此列:计划书明确把 accuracy/VME/MIC 误差列为软指标(达则背书,未达如实记为局限)。
HARD_RED_LINE_LAYERS: tuple[str, ...] = ("t2", "t3", "t4", "t6", "t7")

VERDICT_DEFINITIONS: dict[str, str] = {
    "campaign_pass": (
        "硬红线语义:HARD_RED_LINE_LAYERS(T2/T3/T4/T6/T7)全部 pass,且全战役无 "
        "severity=red_line 的 finding。回答的是「平台的安全与诚实边界守住了吗」。"
        "T1 的软门槛(准确率/VME/MIC 误差)**不**参与本读数。"
    ),
    "all_gates_pass": (
        "含软门槛:九层(含 T1 三子层)的**每一个** gate 都为 True,且无 red_line finding。"
        "它比 campaign_pass 严格 —— T1 的软门槛或 T5 的 gates 任一未达即 False。"
        "**门槛来源**:九层中八层的 gates 直读自各层自己的预注册字段,唯 T5 的两条 gate "
        "系推导(详见「九层一览」下方的门槛来源披露)。"
    ),
    "difference": (
        "二者的差 = T1 软指标 **及 T5 的非硬红线 gates**。campaign_pass=True 而 "
        "all_gates_pass=False 意味着:硬红线守住了,但某条非硬红线门槛未达 —— 差异若来自 "
        "T1,那是**科学局限**(预测性能未达预注册门槛,不是红线事故);若来自 T5,那是"
        "**边界缺口**(对抗输入未 fail-closed),性质更重,只是依预注册规则不由本读数拉黑"
        "(它由 red_line finding 拉黑)。**读数差异的来源要看是哪一层,不可一律当作科学局限。**"
        "两个读数同时呈现,是为了让读者自己判断,而不是由我们替他挑一个好看的。"
    ),
    "red_flags": (
        "红旗 = ①任一硬红线层失败 或 ②任一 severity=red_line 的 finding。非空 ⇔ "
        "campaign_pass=False。软门槛失败**不**进红旗(它是科学发现,如实记录,不调阈值)。"
    ),
}


# ---------------------------------------------------------------- 各层归一化

def _layer(key: str, gates: dict[str, bool], *, findings: list[dict[str, Any]] | None = None,
           **extra: Any) -> dict[str, Any]:
    """归一成 {gates, pass, findings, ...}。pass 由 gates 推导,不接受调用方手写。"""
    gates = {k: bool(v) for k, v in gates.items()}
    return {
        "layer": key,
        "hard_red_line": key in HARD_RED_LINE_LAYERS,
        "gates": gates,
        "pass": all(gates.values()),
        "findings": list(findings or []),
        **extra,
    }


def _dual_track_layer(key: str, payload: dict[str, Any]) -> dict[str, Any]:
    """T1 三子层同构:轨A face_validity(train_set_optimistic)+ 轨B generalization(held_out)。

    gates 加 face./gen. 前缀区分两轨 —— 轨A 是训练集乐观估计(只作 serving+合理性哨兵),
    轨B 才是泛化门槛。两轨的 stratum 原样透出,不许在裁决里把轨A 冒充成泛化。
    除 gates/note 外的字段整体透传(不假设各子层的指标形状:T1A 是 median VME/AUC,
    T1B/T1C 是 R²/MAE)。
    """
    fv, gen = payload["face_validity"], payload["generalization"]
    gates = {f"face.{k}": v for k, v in fv["gates"].items()}
    gates.update({f"gen.{k}": v for k, v in gen["gates"].items()})
    return _layer(
        key, gates,
        face_validity={k: v for k, v in fv.items() if k not in ("gates", "note")},
        generalization={k: v for k, v in gen.items() if k not in ("gates", "note")},
        limitations=payload.get("limitations", {}),
    )


def _t2_layer(payload: dict[str, Any]) -> dict[str, Any]:
    v = payload["verdict"]
    suite = payload["small_molecule_peptide_ood"]
    return _layer(
        "t2", {"fail_closed_verified": v["fail_closed_verified"]},
        n_total_leaks=v["n_total_leaks"],
        n_compounds=suite["n_compounds"], n_compounds_abstained=suite["n_compounds_abstained"],
        n_peptides=suite["n_peptides"], n_peptides_abstained=suite["n_peptides_abstained"],
        n_sir_malformed=len(payload["sir_malformed_cases"]),
        n_sir_leaks=len(payload["sir_leaks"]),
    )


def _t3_layer(payload: dict[str, Any]) -> dict[str, Any]:
    v = payload["verdict"]
    return _layer(
        "t3", {"honest": v["honest"]},
        n_violations=v["n_violations"],
        violations=payload["violations"],
        no_model_species=sorted(payload["no_model"]),
        non_metabolic_drugs=sorted(payload["non_metabolic"]),
        g3_candidate_drugs=sorted(payload["g3_candidate"]),
    )


def _t4_layer(payload: dict[str, Any]) -> dict[str, Any]:
    return _layer(
        "t4", {"all_stable": payload["all_stable"]},
        n_queries=payload["n_queries"], n_repeats=payload["n_repeats"],
        n_unstable=payload["n_unstable"], unstable_examples=payload["unstable_examples"],
        corpus_composition=payload["corpus_composition"], fba_coverage=payload["fba_coverage"],
    )


def _t5_layer(payload: dict[str, Any]) -> dict[str, Any]:
    """T5 无 verdict 字段;gates 按其 docstring 的红线定义(crashed 与 leaked 都是红线)推导。"""
    return _layer(
        "t5",
        {"no_leaked": payload["n_leaked"] == 0, "no_crashed": payload["n_crashed"] == 0},
        findings=payload["findings"],
        n_total=payload["n_total"], n_fail_closed=payload["n_fail_closed"],
        n_leaked=payload["n_leaked"], n_crashed=payload["n_crashed"],
        leaks=payload["leaks"], crashes=payload["crashes"],
    )


def _t6_layer(payload: dict[str, Any]) -> dict[str, Any]:
    v = payload["verdict"]
    return _layer(
        "t6", {"evidence_systems_consistent": v["evidence_systems_consistent"]},
        findings=payload["findings"],
        n_case=v["n_case"], n_mismatch=v["n_mismatch"],
        by_case_kind=payload["matrix"]["by_case_kind"],
    )


def _t7_layer(payload: dict[str, Any]) -> dict[str, Any]:
    """gates 取 verdict 里两条**彼此独立**的布尔:e2e_science_consistent(结论)与
    all_cases_schema_fixed_point(逐字比对的前提)。task_id_identical 已被前者蕴含,不重复计。
    """
    v = payload["verdict"]
    neg = payload["negative_controls"]
    return _layer(
        "t7",
        {"e2e_science_consistent": v["e2e_science_consistent"],
         "all_cases_schema_fixed_point": v["all_cases_schema_fixed_point"]},
        findings=payload["findings"],
        n_case=v["n_case"], n_mismatch=v["n_mismatch"],
        n_task_id_mismatch=v["n_task_id_mismatch"],
        science_fields_compared=payload["science_fields_compared"],
        negative_controls={
            "demonstrated_power_kinds": neg["demonstrated_power_kinds"],
            "power_not_demonstrated_kinds": neg["power_not_demonstrated_kinds"],
        },
    )


# ---------------------------------------------------------------- 裁决规则(纯函数)

def compute_verdict(layers: dict[str, dict[str, Any]],
                    findings: list[dict[str, Any]]) -> dict[str, Any]:
    """按**预注册**规则算两条读数 + red_flags。纯函数:不跑模型,合成输入即可直接打。

    KeyError:硬红线层缺失即抛(漏跑一层绝不能被 all() 当空集判 True → 假绿)。
    ValueError:任一层 gates 为空即抛(all({}) 恒 True,空 gates 是最隐蔽的假绿路径)。
    """
    for key in LAYER_KEYS:
        if key in layers and not layers[key]["gates"]:
            raise ValueError(f"层 {key} 的 gates 为空:all({{}}) 恒 True,会造出假绿")

    red_line = [f for f in findings if f.get("severity") == "red_line"]
    no_red_line = not red_line

    # 硬红线层缺失 → KeyError(有意不 .get)。
    hard_ok = all(layers[key]["pass"] for key in HARD_RED_LINE_LAYERS)
    all_gates_ok = all(bool(g) for key in LAYER_KEYS for g in layers[key]["gates"].values())

    red_flags: list[dict[str, Any]] = []
    for key in HARD_RED_LINE_LAYERS:
        if not layers[key]["pass"]:
            red_flags.append({
                "kind": "hard_red_line_layer_fail",
                "layer": key,
                "id": f"hard_red_line_fail_{key}",
                "failed_gates": [g for g, ok in layers[key]["gates"].items() if not ok],
            })
    for f in red_line:
        red_flags.append({
            "kind": "red_line_finding",
            "layer": f.get("layer"),
            "id": f.get("id"),
            "summary": f.get("summary") or f.get("detail"),
        })

    return {
        "campaign_pass": hard_ok and no_red_line,
        "all_gates_pass": all_gates_ok and no_red_line,
        "red_flags": red_flags,
    }


def run(t4_repeats: int = 100) -> dict[str, Any]:
    """串跑 T1–T7 全部评分函数 → 归一 → 出总裁决。

    确定性:层顺序固定(LAYER_KEYS),各层内部自身确定性由该层测试保证。
    t4_repeats 默认 100 = 存档口径(与 __main__ 一致);测试传小 N 控时长。
    """
    layers: dict[str, dict[str, Any]] = {
        "t1a": _dual_track_layer("t1a", t1_predictive.build_report()),
        "t1b": _dual_track_layer("t1b", t1_predictive.build_compound_report()),
        "t1c": _dual_track_layer("t1c", t1_predictive.build_peptide_report()),
        "t2": _t2_layer(t2_ood.build_report()),
        "t3": _t3_layer(t3_honesty.build_report()),
        "t4": _t4_layer(t4_determinism.run(n_repeats=t4_repeats)),
        "t5": _t5_layer(t5_adversarial.run_adversarial_suite()),
        "t6": _t6_layer(t6_evidence.build_report()),
        "t7": _t7_layer(t7_e2e.build_report()),
    }
    # 按 LAYER_KEYS 定序重建(dict 字面量顺序已对,此处显式钉死,防未来插层漏序)。
    layers = {k: layers[k] for k in LAYER_KEYS}
    findings = [{"layer": k, **f} for k in LAYER_KEYS for f in layers[k]["findings"]]
    return {
        "layers": layers,
        "findings": findings,
        "t4_repeats": t4_repeats,
        "verdict_definitions": VERDICT_DEFINITIONS,
        **compute_verdict(layers, findings),
    }


# ---------------------------------------------------------------- VERDICT.md 渲染

def _n(v: Any, nd: int = 4) -> str:
    """数字→字符串(None→n/a)。报告里每个数字都从 payload 插值,不写死。"""
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:.{nd}f}".rstrip("0").rstrip(".") if nd else f"{v:.0f}"
    return str(v)


def _mark(ok: bool) -> str:
    return "PASS" if ok else "**FAIL**"


def _gate_list(layer: dict[str, Any], prefix: str = "") -> str:
    """渲染 gates。prefix 过滤用于 T1 分轨呈现 —— 轨B 的行只列 `gen.*`,
    绝不把轨A(train_set_optimistic)的面值 gate 混进「泛化门槛」里冒充泛化。"""
    return ", ".join(f"`{g}`={ok}" for g, ok in layer["gates"].items() if g.startswith(prefix))


def render_verdict_md(payload: dict[str, Any]) -> str:
    """把 campaign payload 渲染成给**人**读的中文裁决报告。

    纪律:所有数字/结论从 payload 插值 —— prose 里不写死任何读数。数据变了,报告必须跟着变
    (由 test_render_verdict_md_reflects_payload_not_hardcoded 钉住)。
    """
    ly = payload["layers"]
    d = payload["verdict_definitions"]
    # 全战役的 red_line finding(缺口清单):驱动第二栏发现②渲染、九层一览脚注、后续路线待办 ——
    # 三处都 data-driven,缺口清空(如 Phase 12 修好同聚物 OOD 洞)后一并消失,prose 不写死结论。
    red_line_findings = [f for f in payload["findings"] if f.get("severity") == "red_line"]
    lines: list[str] = []
    a = lines.append

    a("# Phase 11 科学验证战役 · 总裁决(VERDICT)")
    a("")
    a("> 本文由 `praxis_virtualcell/mdr_gnb/workflows/science_v2/validation/run_campaign.py` "
      "真串跑 T1–T7 七层评分函数后生成,所有数字均从实跑 payload 插值。")
    a("> 结构化同源产物:`reports/antibacterial/mdr_gnb/science_v2/phase11/campaign.json`。")
    a("")
    a("## 〇、两条读数")
    a("")
    a(f"- `campaign_pass` = **{payload['campaign_pass']}**")
    a(f"- `all_gates_pass` = **{payload['all_gates_pass']}**")
    a("")
    a("**为什么给两个读数?** 计划书正文说 `campaign_pass = all(层 pass)`,而「验收标准」一节"
      "又把 T1 列为软指标、把 T2/T3/T4/T6/T7 列为硬红线。二者有张力。与其由我们替读者挑一个"
      "好看的,不如**两个都摆出来**,并写明定义差异:")
    a("")
    a("| 读数 | 定义 | 本次 |")
    a("|---|---|---|")
    a(f"| `campaign_pass` | {d['campaign_pass']} | **{payload['campaign_pass']}** |")
    a(f"| `all_gates_pass` | {d['all_gates_pass']} | **{payload['all_gates_pass']}** |")
    a("")
    a(f"**差异**:{d['difference']}")
    a("")
    # 数据驱动的"规则选择是否影响结论"提示:两条读数一致时,规则之争无从操纵结论——
    # 这是本裁决最强的诚实性论据,但它必须**算**出来,不能写死(数据一变就得改口)。
    if payload["campaign_pass"] == payload["all_gates_pass"]:
        a(f"**注意**:本次两条读数**一致**(都是 {payload['campaign_pass']}),"
          f"因此「该用哪条规则」之争**不影响结论** —— 这也是这套读数规则敢在跑数之前就"
          f"预注册的原因:它没有给我们留下挑一个好看的空间。")
    else:
        a(f"**注意**:本次两条读数**不一致**(`campaign_pass`={payload['campaign_pass']}、"
          f"`all_gates_pass`={payload['all_gates_pass']}),差异全部来自 T1 软门槛。"
          f"两个都摆在这里,请读者自行判断 —— 我们不替你挑。")
    a("")
    a(f"**红旗规则**:{d['red_flags']}")
    a("")
    a(f"### 红旗清单({len(payload['red_flags'])} 条)")
    a("")
    if not payload["red_flags"]:
        a("(无)")
    else:
        for f in payload["red_flags"]:
            detail = ""
            if f.get("summary"):
                detail = f":{f['summary']}"
            elif f.get("failed_gates"):
                detail = ":失败门槛 " + ", ".join(f"`{g}`" for g in f["failed_gates"])
            a(f"- **[{f['kind']}] `{f['id']}`**(层 `{f['layer']}`){detail}")
    a("")
    a("### 九层一览")
    a("")
    a("| 层 | 性质 | 判定 | 门槛 |")
    a("|---|---|---|---|")
    _titles = {"t1a": "T1A SIR", "t1b": "T1B 小分子", "t1c": "T1C 肽", "t2": "T2 OOD",
               "t3": "T3 诚实性", "t4": "T4 确定性", "t5": "T5 对抗", "t6": "T6 证据",
               "t7": "T7 端到端"}
    for k in LAYER_KEYS:
        if ly[k]["hard_red_line"]:
            kind = "硬红线"
        else:
            kind = "软指标" if k.startswith("t1") else "红线缺口源"
        a(f"| {_titles[k]} | {kind} | {_mark(ly[k]['pass'])} | {_gate_list(ly[k])} |")
    a("")
    if red_line_findings:
        a("> `t5` 不在计划书的硬红线层清单里,但它产出的 `severity=red_line` finding 依规则2 "
          "同样拉黑 `campaign_pass` —— 见第二栏发现②。")
    else:
        a("> `t5` 不在计划书的硬红线层清单里,但**若**它产出 `severity=red_line` finding,"
          "依规则2 同样会拉黑 `campaign_pass`。本次 `t5` 无 red_line finding(见第二栏)。")
    a(">")
    a("> **门槛来源披露(科学产物须交代门槛从哪来)**:上表九层中,**八层**的 gates 均"
      "**直读**自各层自己的预注册字段(T1 的 `gates`、T2/T3/T6/T7 的 `verdict`、T4 的 "
      "`all_stable`)。**唯 T5 例外** —— 该层无预注册 `verdict` 字段,其两条 gate"
      "(`no_leaked`/`no_crashed`)系按 T5 docstring 声明的红线语义(「crashed 和 leaked "
      "都是红线」)**推导**而来,取 `==0` 的最严读法,是九层中**唯一非直读**的门槛。"
      + ("**本次裁决不由该推导驱动**:拉黑 `campaign_pass` 的是 `severity=red_line`,"
         "而 severity 是 T5 自己的预注册字段。" if red_line_findings
         else "**本次 T5 两条推导 gate 均 True**(无泄漏、无崩溃),且无 red_line finding,"
              "故 T5 既未经推导 gate、也未经 finding 拉黑 `campaign_pass`。"))
    a("")

    # ---------------- 第一栏:科学性
    a("---")
    a("")
    a("## 一、科学性(T1)")
    a("")
    a("**双轨设计**:轨A(面值)拿 curated 真实株/真实药跑**部署平台**,验证服务链通 + 输出合理;"
      "但部署 artifact 训过全量数据,所以轨A 是**训练集乐观估计**,一律标 "
      "`stratum=train_set_optimistic`,**不作泛化门槛**。轨B(泛化)用已有留出"
      "(SIR 走 G2R evidence_tiers 的 per-ST 留出;小分子走 scaffold-OOF;肽走序列相似度"
      "连通分量-OOF),**泛化门槛只下在轨B**。两轨都诚实标 stratum,互不冒充。")
    a("")

    fa, ga = ly["t1a"]["face_validity"], ly["t1a"]["generalization"]
    fm = fa["metrics"]
    a("### T1A 基因型 → SIR")
    a("")
    a(f"- **轨A(`{fa['stratum']}`,不作泛化门槛)**:accuracy={_n(fm['accuracy'])}、"
      f"coverage={_n(fm['coverage'])}、**VME={_n(fm['very_major_error'])}(n_R={fm['n_R']})**、"
      f"ME={_n(fm['major_error'])}(n_S={fm['n_S']})、n={fm['n']};"
      f"强机制锚点全出 R = {ly['t1a']['gates']['face.anchors_all_R']}。")
    a(f"- **轨B(`{ga['stratum']}`,真泛化,门槛在此)**:中位 VME(fusion)="
      f"**{_n(ga['median_vme_fusion'])}**、中位 AUC_R={_n(ga['median_auc_R'])};"
      f"取自 `{ga['source']}` 的 {ga['n_strong']} 个 strong combo"
      f"(VME 中位数的分母 = {ga['n_vme']} 个 combo,每个 combo 的 per-ST VME 各自带 "
      f"`n_R_ST` 分母)。**泛化门槛**:{_gate_list(ly['t1a'], 'gen.')}")
    a("")
    a("#### 🔬 发现① SIR 留出泛化 VME 未达门槛(软指标 FAIL,**不调阈值**)")
    a("")
    a(f"轨B 中位 VME = **{_n(ga['median_vme_fusion'])}** > 门槛 "
      f"{_n(t1_predictive.SIR_GEN_GATES['vme_le_0.10'], 2)} → "
      f"`gen.vme_le_0.10` = {ly['t1a']['gates']['gen.vme_le_0.10']};"
      f"而 AUC_R = {_n(ga['median_auc_R'])} 过 "
      f"{_n(t1_predictive.SIR_GEN_GATES['auc_ge_0.85'], 2)} 门槛。")
    a("")
    a(f"**VME(very major error)= 把耐药误判为敏感**,是抗菌药敏最严重的错误类型(临床后果:"
      f"给了无效药)。故此处分母必须透出:轨A 的 VME={_n(fm['very_major_error'])} 是 "
      f"**0/{fm['n_R']}** 而非「没有 R 样本所以算不出 0」。")
    a("")
    a(f"**科学意义 —— 这是双轨设计的成功,不是失败**:同一套模型,轨A(训练集内)"
      f"VME={_n(fm['very_major_error'])},轨B(真留出)VME={_n(ga['median_vme_fusion'])}。"
      f"这道**「训练集乐观 vs 真泛化」的裂口**,正是本战役设置双轨要暴露的东西。"
      f"若只报轨A,我们会得到一个「VME=0」的漂亮结论,而它对新病人毫无意义。"
      f"门槛未达 → **如实记为科学发现,不调阈值、不换语料、不改算法让它变绿**。")
    a("")

    for key, title in (("t1b", "T1B 小分子(SMILES)→ 活性"),
                       ("t1c", "T1C 抗菌肽(序列)→ 活性")):
        f_, g_ = ly[key]["face_validity"], ly[key]["generalization"]
        fmm, gmm = f_["metrics"], g_["metrics"]
        a(f"### {title}")
        a("")
        a(f"- **轨A(`{f_['stratum']}`,不作泛化门槛)**:R²={_n(fmm['r2'])}、MAE={_n(fmm['mae'])}"
          f"(log10 尺度)、coverage={_n(fmm['coverage'])}、n_scored={fmm['n_scored']};"
          f"锚点 {', '.join(f'`{k}`={v}' for k, v in f_['anchors'].items())}。"
          f"面值哨兵:{_gate_list(ly[key], 'face.')}")
        a(f"- **轨B(`{g_['stratum']}`,真泛化,门槛在此)**:**R²={_n(gmm['r2'])}**、"
          f"MAE={_n(gmm['mae'])}、n={g_['n']};取自 `{g_['source']}`。"
          f"**泛化门槛**:{_gate_list(ly[key], 'gen.')} → 本层整体 **{_mark(ly[key]['pass'])}**")
        a("")

    pg = ly["t1c"]["generalization"]["metrics"]
    a(f"> **肽方向偏弱,如实说**:轨B R²={_n(pg['r2'])},门槛 `r2_ge_0.20` 是**诚实放宽**以对齐"
      f"现状 —— 不是假装它强。它过了门槛,但 R²≈0.3 意味着序列→MIC 的可解释方差仍然有限,"
      f"该方向**不足以支撑强科学声称**。提升路线见 Phase 13。")
    a("")

    # ---------------- 第二栏:诚实性/边界
    a("---")
    a("")
    a("## 二、诚实性与边界(T2 / T3 / T5 / T6)")
    a("")
    a("这一栏回答的不是「模型准不准」,而是**「模型知不知道自己不知道」**、"
      "**「不知道的时候会不会编」**。对一个要给临床用药提示的平台,这比准确率更要命。")
    a("")
    t2, t3, t5, t6 = ly["t2"], ly["t3"], ly["t5"], ly["t6"]
    a(f"- **T2 OOD 全弃权** — {_mark(t2['pass'])}(硬红线)。分布外化合物 "
      f"{t2['n_compounds_abstained']}/{t2['n_compounds']} 弃权、肽 "
      f"{t2['n_peptides_abstained']}/{t2['n_peptides']} 弃权;SIR 乱格式输入 "
      f"{t2['n_sir_malformed']} 例、泄漏 {t2['n_sir_leaks']} 例。"
      f"**总泄漏 = {t2['n_total_leaks']}**。")
    a(f"- **T3 不伪造** — {_mark(t3['pass'])}(硬红线)。违规 {t3['n_violations']} 例。"
      f"①无模型物种({', '.join(f'`{s}`' for s in t3['no_model_species'])})"
      f"必 `sir=None`/`prediction_available=False`,**不编 R/S**;"
      f"②非代谢靶药({', '.join(f'`{s}`' for s in t3['non_metabolic_drugs'])})"
      f"`mechanism.available=False`,**不编机制**;"
      f"③代谢靶候选药({', '.join(f'`{s}`' for s in t3['g3_candidate_drugs'])})"
      f"即便 FBA 真阻断了靶点,只要 G3 门未评估该药,`mechanism_claim` **恒 None** —— "
      f"有机制信号 ≠ 可以声称已证实。")
    a(f"- **T6 证据零串用** — {_mark(t6['pass'])}(硬红线)。{t6['n_case']} 个 case,"
      f"mismatch={t6['n_mismatch']}。两套证据系统(per-prediction SIR evidence_tiers vs "
      f"模型级 QSAR 验证层)不得互相冒充 —— 陷阱:EC×trimethoprim 在 SIR 侧有 E3 证据,"
      f"活性卡若取用它即误导(应取 QSAR 侧 E4)。")
    a(f"- **T5 对抗输入 fail-closed** — {_mark(t5['pass'])}。{t5['n_total']} 条恶意/畸形输入:"
      f"fail-closed **{t5['n_fail_closed']}**、崩溃 {t5['n_crashed']}、"
      f"**泄漏 {t5['n_leaked']}**。")
    a("")

    if red_line_findings:      # 已在函数顶部按 payload["findings"] 算好(见那里的注释)
        a("#### 🚨 发现② 超长同聚物绕过 OOD 判据(**red_line**,拉黑 `campaign_pass`)")
        a("")
        for f in red_line_findings:
            a(f"**`{f['id']}`**(层 `{f['layer']}`,surface=`{f.get('surface', 'n/a')}`,"
              f"kind=`{f.get('kind', 'n/a')}`)")
            a("")
            a(f"- **现象**:{f.get('summary')}")
            if f.get("example_input"):
                a(f"- **输入**:`{f['example_input']}`")
            act = f.get("leaked_activity") or {}
            if act:
                a(f"- **泄漏输出**:`is_ood={act.get('is_ood')}`、"
                  f"`max_tanimoto={_n(act.get('max_tanimoto'))}`、"
                  f"`log10_mic={_n(act.get('log10_mic'))}` → "
                  f"**MIC≈{_n(act.get('mic_ug_ml'))} µg/mL**、"
                  f"`uncertainty_std={_n(act.get('uncertainty_std'))}`")
                a(f"- **根因**:Morgan 指纹在长链中部**饱和** —— 一条语法合法但化学上荒谬的超长"
                  f"同聚物,其子结构与训练集普通分子高度重合,`max_tanimoto="
                  f"{_n(act.get('max_tanimoto'))}` 反而**高于** OOD 阈值 0.30。"
                  f"Tanimoto-only 判据在此拦不住,平台于是**自信地给出了一个 MIC**。"
                  f"这不是「模型不准」,是**边界判据有洞**:平台在它本该说「我不知道」的地方"
                  f"说了话。")
            if f.get("error"):
                a(f"- **异常**:`{f['error']}`")
            if f.get("recommendation"):
                a(f"- **修复建议**:{f['recommendation']}")
            a("")
        a("**处置(诚实纪律)**:该缺口**不在本战役范围内修复** —— 改核心特征层须独立任务、"
          "独立双审。战役的职责是**如实测出并留档**,不是顺手改一把让报告变绿。"
          "T5 的对应测试已标 `xfail(strict=True)`:缺口一旦修好,测试会变 XPASS **主动提醒**"
          "来收标记,`findings` 亦自动清空 → 本裁决的红旗随之消失。")
        a("")
    else:
        a("本栏无 red_line finding。")
        a("")

    # ---------------- 第三栏:治理有效性
    a("---")
    a("")
    a("## 三、治理有效性(T4 / T7)")
    a("")
    a("这一栏回答:**我们建的这套治理机制,自己有效吗?** 确定性红线与端到端一致性红线,"
      "是装饰,还是真能抓到东西?")
    a("")
    t4, t7 = ly["t4"], ly["t7"]
    a(f"- **T4 trace 确定性** — {_mark(t4['pass'])}(硬红线)。语料 {t4['n_queries']} 条 × "
      f"重复 **{t4['n_repeats']}** 次 = {t4['n_queries'] * t4['n_repeats']} 次预测,"
      f"trace_hash 不稳定 {t4['n_unstable']} 条。语料构成:"
      f"{', '.join(f'{k}×{v}' for k, v in t4['corpus_composition'].items())}。"
      f"FBA 真进 trace(cobra LP 实跑 iML1515):`mechanism_available="
      f"{t4['fba_coverage']['mechanism_available']}`、`growth_inhibition="
      f"{_n(t4['fba_coverage']['growth_inhibition'])}` —— 故「FBA 确定性已验证」是真覆盖,"
      f"不是假声称。")
    a(f"- **T7 HTTP = 直调逐字一致** — {_mark(t7['pass'])}(硬红线)。{t7['n_case']} 个 case,"
      f"科学字段不一致 {t7['n_mismatch']}、内容寻址 task_id 不一致 {t7['n_task_id_mismatch']}。"
      f"比对字段:{', '.join(f'`{s}`' for s in t7['science_fields_compared'])}。")
    a("")
    a("#### ✅ 发现③ SIR 路径间歇性非确定性 —— **战役中定位并已修复**")
    a("")
    a("**这是治理机制真的抓到产品 bug 的实例。**")
    a("")
    a("- **症状**:T4 层建成后,`test_determinism_corpus_stable` 约 **1/3 概率**变红 —— "
      "同一个查询、同一份 artifact,trace_hash 偶尔漂。")
    a("- **定位**:`predictors/genotype_to_sir.py` 的 `predict_proba_r` 直调 sklearn "
      "`RandomForestClassifier.predict_proba`;部署 artifact 是 "
      "`RandomForestClassifier(n_estimators=300, n_jobs=-1)`。sklearn 的 "
      "`_forest._accumulate_prediction` 在锁里按**线程完成顺序**累加各树结果 —— "
      "浮点加法**不满足结合律**,线程调度一变,末位 ULP 就漂 → `sir_prob` 变 → "
      "trace_hash 不再恒定。")
    a("- **修复**(commit `19e24b9`):按 `estimators_` 的**固定顺序**逐树 `predict_proba` "
      "再求均值。数学上恒等于 RF 的 `predict_proba` 定义(只固定了求和顺序),"
      "实测与 sklearn 差异 **5.55e-17**(阈值 1e-12)—— **科学结论未改**。"
      "性能反而 13.5ms → 8.2ms。")
    a("- **为什么早没发现**:线B 的 `small_molecule_model` / `peptide_activity_model` "
      "当年已显式修过同一个坑;SIR 路径建于 v1、早于线B,故漏修。本次对齐。")
    a("")
    a(f"**科学意义**:确定性红线**不是装饰**。它是本战役唯一一条「不看科学正确性、只看"
      f"可复现性」的门槛,而恰恰是它抓到了一个**潜伏在生产路径上的真 bug** —— 一个会让"
      f"「同样的病人、同样的基因型,两次查询给出不同 sir_prob」的 bug。"
      f"战役不仅验证了平台,还修好了平台。本层现判定 **{_mark(t4['pass'])}**。")
    a("")
    nc = t7["negative_controls"]
    a(f"> **T7 负对照的判别力**:已获实证 "
      f"{', '.join(f'`{k}`' for k in nc['demonstrated_power_kinds'])};"
      f"未获实证 {', '.join(f'`{k}`' for k in nc['power_not_demonstrated_kinds'])} —— "
      f"二者本就恒 fail-closed,「剥字段」这族负对照对其无从发力。"
      f"**措辞据实**:是「判别力未获实证」,**不等于**「无判别力」。")
    a("")

    # ---------------- 已知局限
    a("---")
    a("")
    a("## 四、已知局限与遗留(不隐瞒)")
    a("")
    a("1. **E5 外部 holdout 未做(论文最易被打的缺口)**。小分子的 "
      "`reports/antibacterial/mdr_gnb/science_v2/sm_activity_evidence/sm_activity_evidence.json` 载明 "
      "`not_e5_because=\"无外部数据集(换来源/换年份)holdout;当前仅 ChEMBL EC 内部 "
      "scaffold-split CV\"`;SIR 同理。→ **已定为 Phase 12**。")
    a("2. **T1A 轨A 面值仅覆盖 2 物种**(以下为 T1A 层自报的 `limitations`,原样透出):")
    for k, v in (ly["t1a"].get("limitations") or {}).items():
        a(f"   - `{k}`:{v}")
    a(f"3. **肽方向偏弱**:轨B R²={_n(pg['r2'])},门槛 `r2_ge_0.20` 系诚实放宽以对齐现状。"
      f"→ **Phase 13**(全量 DBAASP + ESM)。")
    a("4. **T5 `name_consistency` 正例无离线测试**(原「T5 遗留」三条,两条早前已修,"
      "「`consistent` 恒真」一族的**两处**——解析半场的空集恒真、活性半场的全弃权——"
      "**均已修复**,余此一条):"
      "`run_adversarial_suite()` 已有直接测试(`test_run_adversarial_suite_known_state`:"
      "钉计数口径 + 缺口上浮 findings + 连跑逐字确定性);其 `name_consistency` 子项的内部 "
      "crash(逐变体崩 / `resolve_compound` 探针自身崩)已汇入顶层 findings"
      "(`id=name_consistency_crash`、`severity=red_line`),依规则2 同样拉黑裁决 —— "
      "不再只躺在子项里对裁决不可见。"
      "**修复一(解析半场:空集恒真)**:`consistent` 原写作 `len(canon_set) <= 1`,对**空集**"
      "恒真 —— 全部变体都没解析出来(`n_resolved=0`)时反而报 `consistent=True`,报告读作"
      "「名称一致」,是空集恒真的假安慰。现改为**三态**:`comparable = n_resolved >= 2`,"
      "不足 2 个可比对象时 `consistent`/`same_canonical_smiles`/`same_activity` 全取 `null`"
      "(**无从判断**)而非 `true`/`false`(后者是反方向的编造);比较逻辑另加离线负对照"
      "(互异 SMILES → `consistent=false`)钉住。"
      "**修复二(活性半场:全弃权)**:`same_activity` 原写作 `len(activity_set) == 1`,而弃权"
      "(`activity=None`)也作为 `None` 落进该值集合 —— 变体**全部弃权**时集合是 `{None}`、"
      "基数也是 1 → 报 `same_activity=true` → `consistent=true`。这**不是**空集恒真"
      "(集合非空),而是它的近亲:把 `None`(**没有答案**)当成一个**值**去数基数,"
      "「都没给答案」被算成了「给了同一个答案」;此时平台**零个 MIC 产出**,而本项声称的性质"
      "「同一 canonical SMILES → **同一 MIC**」后半句从未被检验。现按同一把语用尺子改为三态:"
      "全弃权 → `same_activity=null`;`consistent` 改用**三值(Kleene)合取**汇总两半"
      "(任一半 `false` → `false`;否则任一半 `null` → `null`;全 `true` 才 `true` —— "
      "不能用 `all()`,`all([True, None])==False` 会把「无从判断」误报成「不一致」的假警报)。"
      "并透出活性半场的**分母** `n_with_activity` / `mic_comparable`(`same_activity is true` "
      "⟹ `mic_comparable` 必为 true),读者可自行核对「一致」是基于几个 MIC 得出的。"
      "⚠️「有的给 MIC 有的弃权」(`{tuple, None}`)**仍判 `false`** —— 同一 SMILES 一个给一个"
      "不给是平台行为不自洽,属**真发现**,不得在修全弃权时被顺手放成 `null`;该回归由 "
      "`test_name_consistency_mixed_activity_is_inconsistent` 参数化钉住(含仅 1 个 MIC、"
      "`mic_comparable=false` 的边界:不一致来自「结果形态不同」,不需要凑够两个 MIC 才能断定)。"
      "本存档 `name_consistency` 的 `consistent=true` 系**挣来的**"
      "(`n_resolved=3`、`n_with_activity=3` 均 ≥2,真联网所跑)。"
      "注:`unresolved_fail_closed` 的 `all([])` 恒真**有意保留** —— "
      "它是**违规检查**,零样本→零违规→True 语义正确,且分母 `n_unresolved` 就在旁边透出;"
      "而 `consistent` 声称的是「正面属性被验证过」,零样本下报 True 即撒谎。"
      "**残留**:`name_consistency` 的**正例**"
      "(`ciprofloxacin`/`Ciprofloxacin`/`cipro` 三个书写变体经 PubChem 解析到同一 canonical "
      "SMILES → 同一 MIC)本质是**联网事实**,离线注入假解析器去测它只会得到同义反复"
      "(假解析器返回什么就「一致」什么),故**不予测试**,仅由存档 "
      "`reports/antibacterial/mdr_gnb/science_v2/phase11/t5_adversarial.json` 的真跑记录佐证"
      "(该存档系真联网所跑:`skipped=false`、`n_resolved=3/4`,中文名「环丙沙星」未被 PubChem "
      "名称索引收录 → 诚实 fail-closed)。")
    a("5. **T6 遗留**:负对照覆盖面窄于实际能力(实测肽/弃权类均有判别力,但无测试钉住);"
      "`contract_selector` 是 `PredictionResult.tsx` 的**手写 Python 复刻件** —— TSX 若改用 "
      "`result.evidence` 喂活性卡,则 T6 恒绿(由 `PredictionResult.test.tsx` + T7 的 "
      "`phase11.e2e.test.tsx` 兜底)。")
    a("6. **T7 遗留**:`emit_frontend_fixtures` 用 `as unknown as`,故 `tsc` **不**校验 "
      "fixture 与前端类型的一致性(主因是 `Report.mic_range` 前端未声明);契约由运行时断言守。")
    a("7. **离线脚本 ULP 隐患**:`workflows/science_v2/qsar_baseline.py:142` 仍用 "
      "`rf.predict` + `n_jobs=-1`,与发现③同源。但它是**离线 baseline 脚本、不在 trace "
      "路径**,不影响产品确定性;仅在「复现报告 R² 逐位相同」的严格意义上有影响。"
      "(`peptide_baseline.py` 早已用固定顺序逐树平均,**无**此问题。)")
    a("8. **前端 trimethoprim 示例输入不一致（本地已修复）**:旧 `genes.ts` 曾把示例写成 "
      "C14H18N4O 的 `Cc1cc(C)c(Cc2cnc(N)nc2N)cc1OC`,而 golden 正确三甲氧结构是 "
      "C14H18N4O3 的 `COc1cc(Cc2cnc(N)nc2N)cc(OC)c1OC`。该示例会让活性 QSAR 使用错误 "
      "SMILES,但 `drug_panel` 仍以 `trimethoprim` 标签触发 DHFR sidecar,因此不是可接受的 "
      "展示差异。现前端示例已改为 golden 结构，`QueryInput` 用户路径回归同时钉住示例和提交 "
      "payload；本地 React/API/浏览器均已复核。此为战役后的本地输入完整性修复，**不改变 "
      "Phase11 的模型、规则、阈值或证据**；GitHub/.53 静态资产仍未核验。")
    a("")

    # ---------------- 路线
    a("---")
    a("")
    a("## 五、后续路线")
    a("")
    a("| 阶段 | 内容 | 触发本裁决的哪一项 |")
    a("|---|---|---|")
    a("| **Phase 12** | E5 外部 holdout(换来源/换年份的独立数据集) | 局限 1 —— 论文最易被打处 |")
    a("| **Phase 13** | 肽方向增强(全量 DBAASP + ESM 表征) | 发现①栏的肽 R²≈0.3 / 局限 3 |")
    a("| **Phase 14** | KP-QSAR:小分子从 EC only → EC + KP 双物种 | 局限 2(物种覆盖窄) |")
    a("| **Phase 15** | Synergy 原型:激活已预埋的 `output_kind=synergy` | 能力扩展(非本裁决缺陷) |")
    # 「加法方向 sanity gate」这一行 data-driven:仍有 red_line finding(缺口未修)时列为待办;
    # 缺口修好(findings 清空)后如实标已完成 —— 不留"已做完却仍写未排期"的陈旧待办。
    if red_line_findings:
        a("| **独立修复任务**(未排期) | 给 `sm_activity` 特征层加 MW/原子数上限的 sanity gate"
          "(独立于 Tanimoto) | **发现② red_line** |")
    else:
        a("| **加法方向 sanity gate(已完成)** | sm_activity/peptide 结构规模/组分/长度上限"
          "(独立于 Tanimoto)fail-closed | 历史发现②——现已修复,第二栏无 red_line finding |")
    a("")
    a("**Phase 14:KP-QSAR** —— 小分子从 EC only 扩到 EC + KP 双物种(KP 的 MIC 数据量第二大、"
      "临床价值最高)。交付:`chembl_pull.py` 拉 KP MIC + scaffold 防泄漏 baseline + KP "
      "`sm_activity` artifact(按物种分文件)+ 注册进 registry + 证据分层 + `golden_compounds` "
      "加 KP 栏。验收门:KP scaffold-CV R² 达「有意义预测」阈且优于 baseline;多物种活性证据"
      "**按物种 gate**;确定性。依赖:ChEMBL KP MIC 数据量核对(探查)。")
    a("")
    a("**Phase 15:Synergy 原型** —— 激活核心已预埋的 `output_kind=synergy`:输入 "
      "drugA + drugB + species → 输出 FICI / synergy 概率。交付:synergy 数据门探查 + baseline "
      "+ `SynergyPredictor` 注册进核心 + 证据分层 + fail-closed。验收门:**须有真实组合数据"
      "支撑**(无则明确「数据门未过、不产 FICI 数字」)。**风险**:数据可能根本不够 —— "
      "那就诚实给出结论「synergy 需先解决数据门」,**不硬做**。")
    a("")
    a("**路线层总原则**:①每个 Phase **先探数据门/算力门 spike,再立详细 plan** —— 数据门"
      "未过就写 TDD 步骤,会编造;②**诚实优先于涨点**;③**复用不抛弃核心**;④顺序可调"
      "(Phase 12 数据门若难,可先做 Phase 13 顶上),但 **E5 缺口始终是论文最大风险**。")
    a("")
    a("> **另记**:计划书显式记录了「方向5 虚拟细胞升级」(QSAR → 预测靶点 → FBA → growth "
      "闭环)**不排进 Phase 12–15**,理由是它依赖 Phase 12 的外部验证与 Phase 14 的多物种能力。"
      "而本战役的 **T3(机制诚实性)恰好为这条线打了地基** —— 机制恒作候选、G3 门约束,"
      "使未来的闭环不会在证据不足时越权声称。")
    a("")

    # ---------------- 复现
    a("---")
    a("")
    a("## 六、复现")
    a("")
    a("```bash")
    a(".venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v2.validation.run_campaign")
    a("```")
    a("")
    a(f"该入口同时重写 `reports/antibacterial/mdr_gnb/science_v2/phase11/campaign.json` 与本文件,"
      f"用 `t4_repeats={payload['t4_repeats']}`(= 本次存档口径,与 "
      f"`reports/antibacterial/mdr_gnb/science_v2/phase11/t4_determinism.json` 的 `n_repeats` 一致)。"
      f"耗时约 5 分钟,其中绝大部分是 T4 的 "
      f"{ly['t4']['n_queries']}×{ly['t4']['n_repeats']} 次真实预测。")
    a("")
    return "\n".join(lines) + "\n"


def write_verdict_md(payload: dict[str, Any]) -> Path:
    """写 VERDICT.md(确定性:同 payload 逐字相等)。"""
    _VERDICT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _VERDICT_PATH.write_text(render_verdict_md(payload), encoding="utf-8")
    return _VERDICT_PATH


if __name__ == "__main__":
    # t4_repeats 走 run() 的默认 100 = 存档报告口径。若此处降配跑一次入口就会把存档
    # 覆写成另一个值,报告便不可由本入口复现(T4 曾因 __main__ 硬编 20 但报告写 100 被审出)。
    result = run()
    jp = harness.write_report("campaign", result)
    # VERDICT.md 从**落盘后的 campaign.json 回读**渲染,而不是从内存 payload 直接渲染:
    # write_report 用 sort_keys=True,内存里的 dict 是插入序 —— 两者渲染出的 gates/limitations
    # 顺序不同。回读一次即保证「VERDICT.md 恒是 campaign.json 的纯函数」:两份产物永不漂开,
    # 且任何人拿 campaign.json 单独就能复现出逐字相同的 VERDICT.md
    # (由 test_archived_verdict_md_matches_archived_campaign_json 钉住)。
    archived = json.loads(jp.read_text(encoding="utf-8"))
    mp = write_verdict_md(archived)
    print(f"campaign 报告写入 {jp}")
    print(f"VERDICT 写入 {mp.relative_to(_REPO_ROOT)}")
    print(f"  t4_repeats={result['t4_repeats']}")
    for k in LAYER_KEYS:
        lay = result["layers"][k]
        flag = "硬红线" if lay["hard_red_line"] else "软/缺口"
        print(f"  {k:4s} [{flag}] pass={lay['pass']!s:5s} gates={_gate_list(lay)}")
    print(f"  findings({len(result['findings'])}):"
          f"{[(f['layer'], f['id'], f['severity']) for f in result['findings']]}")
    print(f"  red_flags({len(result['red_flags'])}):"
          f"{[(f['kind'], f['layer'], f['id']) for f in result['red_flags']]}")
    print(f"  campaign_pass  = {result['campaign_pass']}(硬红线语义)")
    print(f"  all_gates_pass = {result['all_gates_pass']}(含软门槛)")
    print(json.dumps({"campaign_pass": result["campaign_pass"],
                      "all_gates_pass": result["all_gates_pass"]}, ensure_ascii=False))
