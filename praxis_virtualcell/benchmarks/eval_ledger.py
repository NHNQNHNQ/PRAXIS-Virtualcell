"""M1(v0.3):PRAXIS Eval Ledger —— 统一记录每次 communicative run 的逐样本治理信号。

阶段2 自研模型(MoE Router / OOD Classifier / Abstain Head)的**训练数据骨架**:把每个请求经
PRAXIS 通讯流跑出的 report 抽成结构化条目(参与/拒绝/失败的 predictor、ensemble 分歧、reliability、
abstain、caution、可选 ground-truth 误差与 seen/unseen OOD 标签),落 jsonl。

设计纪律(守 PRAXIS DNA):
- **只记录 report 里真实存在的字段**(report.py 的结构),不编造结论;缺失用 None。
- ground-truth 误差(delta_pearson)与 OOD 标签(seen_in_train)是**可选**外部信号,由调用方在评测时填;
  不填就是 None(诚实:没评测就没有误差)。
- 纯 Python、无 torch 依赖,Mac 可建/测;真实填充在远端 run_request_ml 后(阶段1 ③/④)。
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class LedgerEntry:
    request_id: str | None
    species: str | None
    cell_type: str | None
    perturbation_targets: list[str]
    # predictor 参与情况
    models_used: list[str]
    models_rejected: list[str]
    models_failed: list[str]
    # ensemble 分歧(§8.3,真 predictor 上才有意义)
    disagreement_score: float | None
    disagreement_triggered: bool
    disagreement_n_models: int | None
    disagreement_n_zero_pairs: int | None
    # reliability / abstain
    reliability: str | None
    abstain: bool
    abstain_reasons: list[str]
    downgrade_reasons: list[str]
    critic_violations: list = field(default_factory=list)
    caution_flags: dict = field(default_factory=dict)
    # 可选外部评测信号(有 ground-truth 时填;否则 None = 未评测)
    delta_pearson: float | None = None
    seen_in_train: bool | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def _entry_from_report(report: dict, *, request: dict | None = None,
                       delta_pearson: float | None = None,
                       seen_in_train: bool | None = None) -> LedgerEntry:
    req = request or {}
    md = report.get("model_disagreement") or {}
    return LedgerEntry(
        request_id=report.get("request_id") or req.get("request_id"),
        species=req.get("species"),
        cell_type=req.get("cell_type"),
        perturbation_targets=list(req.get("perturbation_targets") or []),
        models_used=list(report.get("models_used") or []),
        models_rejected=list(report.get("models_rejected") or []),
        models_failed=list(report.get("models_failed") or []),
        disagreement_score=md.get("score"),
        disagreement_triggered=bool(md.get("triggered", False)),
        disagreement_n_models=md.get("n_models"),
        disagreement_n_zero_pairs=md.get("n_zero_vector_pairs"),
        reliability=report.get("reliability"),
        abstain=bool(report.get("abstain", False)),
        abstain_reasons=list(report.get("abstain_reasons") or []),
        downgrade_reasons=list(report.get("downgrade_reasons") or []),
        critic_violations=list(report.get("critic_violations") or []),
        caution_flags=dict(report.get("caution_flags") or {}),
        delta_pearson=delta_pearson,
        seen_in_train=seen_in_train,
    )


class EvalLedger:
    """逐样本治理账本。record() 从 report 抽条目;to_jsonl/from_jsonl 持久化;summary() 聚合。"""

    def __init__(self) -> None:
        self.entries: list[LedgerEntry] = []

    def record(self, report: dict, *, request: dict | None = None,
               delta_pearson: float | None = None,
               seen_in_train: bool | None = None) -> LedgerEntry:
        e = _entry_from_report(report, request=request, delta_pearson=delta_pearson,
                               seen_in_train=seen_in_train)
        self.entries.append(e)
        return e

    def to_jsonl(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for e in self.entries:
                f.write(json.dumps(e.as_dict(), ensure_ascii=False) + "\n")

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "EvalLedger":
        led = cls()
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                led.entries.append(LedgerEntry(**json.loads(line)))
        return led

    def summary(self) -> dict:
        n = len(self.entries)
        if n == 0:
            return {"n": 0}
        n_abstain = sum(1 for e in self.entries if e.abstain)
        n_downgrade = sum(1 for e in self.entries if e.downgrade_reasons and not e.abstain)
        scores = [e.disagreement_score for e in self.entries if e.disagreement_score is not None]
        evaluated = [e.delta_pearson for e in self.entries if e.delta_pearson is not None]
        rel_counts: dict[str, int] = {}
        for e in self.entries:
            rel_counts[e.reliability] = rel_counts.get(e.reliability, 0) + 1
        return {
            "n": n,
            "abstain_rate": n_abstain / n,
            "downgrade_rate": n_downgrade / n,
            "disagreement_mean": (sum(scores) / len(scores)) if scores else None,
            "disagreement_triggered_rate": sum(1 for e in self.entries if e.disagreement_triggered) / n,
            "reliability_counts": rel_counts,
            "n_evaluated": len(evaluated),
            "delta_pearson_mean": (sum(evaluated) / len(evaluated)) if evaluated else None,
        }
