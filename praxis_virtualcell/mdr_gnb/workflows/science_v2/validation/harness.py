"""Phase 11 共享验证 harness(确定性纯函数)。包 api.service.predict,不重算科学。"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from praxis_virtualcell.mdr_gnb.api import service

# harness.py: praxis_virtualcell/mdr_gnb/workflows/science_v2/validation/harness.py
# parents[0]=validation parents[1]=science_v2 parents[2]=workflows parents[3]=mdr_gnb
# parents[4]=praxis_virtualcell parents[5]=仓库根(实测核对,别信空口数层数)
_REPORT_ROOT = Path(__file__).resolve().parents[5] / "reports" / "antibacterial" / "mdr_gnb" / "science_v2" / "phase11"


def run_query(raw: dict[str, Any]) -> dict[str, Any]:
    """跑一次预测,归一化成验证要用的扁平 dict(只读 service 输出,不改)。"""
    out = service.predict(raw)["response"]
    r = out["report"]
    return {
        "task_id": out["task_id"],
        "abstained": r["abstained"],
        "output_kind": r["output_kind"],
        "sir": r["sir"],
        "activity": r["activity"],
        "peptide_activity": r["peptide_activity"],
        "mechanism": r["mechanism"],
        "evidence": out["evidence"],
        "prediction_available": out["prediction_available"],
        "abstain_reasons": list(r["abstain_reasons"]),
    }


def trace_hash(raw: dict[str, Any]) -> str:
    """对完整 trace_record 做 sha256(确定性红线的可测锚)。"""
    rec = service.predict(raw)["trace_record"]
    blob = json.dumps(rec, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def classification_metrics(
    y_true: list, y_pred: list, abstained: list | None = None
) -> dict[str, Any]:
    """SIR 分类指标。VME=预测S实际R;ME=预测R实际S。仅未弃权样本进 accuracy/VME/ME。

    abstained=None 视作全未弃权(但仍滤掉 y_pred 里的 None)。暴露分母 n_R/n_S:
    VME=0.0 时能分清"真零错误"还是"没有 R 样本没法算"(本项目在 VME 上踩过坑,
    安全指标必须透出分母)。
    """
    n = len(y_true)
    abst = abstained if abstained is not None else [False] * n
    covered = [i for i in range(n) if not abst[i] and y_pred[i] is not None]
    coverage = len(covered) / n if n else 0.0
    n_R = sum(1 for i in covered if y_true[i] == "R")
    n_S = sum(1 for i in covered if y_true[i] == "S")
    if not covered:
        return {"n": n, "coverage": coverage, "accuracy": 0.0,
                "very_major_error": 0.0, "major_error": 0.0, "n_R": n_R, "n_S": n_S}
    correct = sum(1 for i in covered if y_pred[i] == y_true[i])
    vme = sum(1 for i in covered if y_true[i] == "R" and y_pred[i] == "S") / n_R if n_R else 0.0
    me = sum(1 for i in covered if y_true[i] == "S" and y_pred[i] == "R") / n_S if n_S else 0.0
    return {"n": n, "coverage": coverage, "accuracy": correct / len(covered),
            "very_major_error": vme, "major_error": me, "n_R": n_R, "n_S": n_S}


def regression_metrics(
    y_true: list, y_pred: list, abstained: list | None = None
) -> dict[str, Any]:
    """MIC 回归指标(log10 尺度传入)。MAE/RMSE/R²。

    仿 classification_metrics:先滤掉弃权(abstained[i] is True)或 y_pred 为 None 的样本,
    只对 covered 算指标。abstained=None 视作全未弃权(仍滤 None)。无可评样本时 mae/rmse/r2
    返回 None(不用 float('nan'),保证报告 JSON 恒标准);ss_tot=0 时 r2 也返回 None。
    """
    n = len(y_true)
    abst = abstained if abstained is not None else [False] * n
    covered = [i for i in range(n) if not abst[i] and y_pred[i] is not None]
    coverage = len(covered) / n if n else 0.0
    n_scored = len(covered)
    if n_scored == 0:
        return {"n": n, "n_scored": 0, "coverage": coverage,
                "mae": None, "rmse": None, "r2": None}
    err = [y_pred[i] - y_true[i] for i in covered]
    mae = sum(abs(e) for e in err) / n_scored
    rmse = math.sqrt(sum(e * e for e in err) / n_scored)
    ybar = sum(y_true[i] for i in covered) / n_scored
    ss_tot = sum((y_true[i] - ybar) ** 2 for i in covered)
    ss_res = sum(e * e for e in err)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else None
    return {"n": n, "n_scored": n_scored, "coverage": coverage,
            "mae": mae, "rmse": rmse, "r2": r2}


def load_golden(path, required: list[str]) -> list[dict[str, Any]]:
    """读 golden(csv);缺必需列即 raise(防不完整 golden 静默评分)。yaml 由调用方另读。"""
    p = Path(path)
    with p.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"golden 为空:{p}")
    missing = [c for c in required if c not in rows[0]]
    if missing:
        raise ValueError(f"golden 缺列 {missing}:{p}")
    return rows


def write_report(name: str, payload: dict[str, Any]) -> Path:
    """确定性写报告(json)。同 payload 逐字相等。"""
    _REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    j = _REPORT_ROOT / f"{name}.json"
    j.write_text(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return j
