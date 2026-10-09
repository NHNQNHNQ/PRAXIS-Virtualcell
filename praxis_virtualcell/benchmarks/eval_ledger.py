"""Per-sample governance ledger for communicative runs. Extract only fields present in reports; missing values
remain None. Optional delta_pearson and seen_in_train are caller-supplied evaluation labels, never inferred
without measurement. Plain Python serialization supports local construction; real model reports come from remote
execution.
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

    models_used: list[str]
    models_rejected: list[str]
    models_failed: list[str]

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

    delta_pearson: float | None = None
    per_predictor_delta_pearson: dict | None = None
    seen_in_train: bool | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def _entry_from_report(report: dict, *, request: dict | None = None,
                       delta_pearson: float | None = None,
                       per_predictor_delta_pearson: dict | None = None,
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
        per_predictor_delta_pearson=per_predictor_delta_pearson,
        seen_in_train=seen_in_train,
    )


class EvalLedger:
    """Per-sample governance ledger: record reports, persist to/from JSONL, and aggregate summaries."""

    def __init__(self) -> None:
        self.entries: list[LedgerEntry] = []

    def record(self, report: dict, *, request: dict | None = None,
               delta_pearson: float | None = None,
               per_predictor_delta_pearson: dict | None = None,
               seen_in_train: bool | None = None) -> LedgerEntry:
        e = _entry_from_report(report, request=request, delta_pearson=delta_pearson,
                               per_predictor_delta_pearson=per_predictor_delta_pearson,
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
    def from_jsonl(cls, path: str | Path) -> EvalLedger:
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
