"""Audit ledger columns, extract inference-only features, and create perturbation-level splits.
delta_pearson/per_predictor_delta_pearson are training labels, never runtime features. INFERENCE_FEATURES holds
available prediction-time signals; LABELS holds accuracy targets; DIAGNOSTIC holds rule decisions for baseline
comparison. One ledger row is one perturbation.
"""
from __future__ import annotations

INFERENCE_FEATURES = (
    "disagreement_score",
    "disagreement_n_zero_pairs",
    "disagreement_n_models",
    "seen_in_train",
    "n_models_used",
)


LABELS = (
    "delta_pearson",
    "per_predictor_delta_pearson",
)


DIAGNOSTIC = ("reliability", "abstain", "abstain_reasons", "downgrade_reasons")


def _row(entry) -> dict:
    """Extract only INFERENCE_FEATURES from LedgerEntry; encode seen_in_train as 0/1 and missing values as None."""
    d = entry.as_dict() if hasattr(entry, "as_dict") else dict(entry)
    out = {}
    for f in INFERENCE_FEATURES:
        if f == "n_models_used":
            out[f] = len(d.get("models_used") or [])
        elif f == "seen_in_train":
            v = d.get("seen_in_train")
            out[f] = None if v is None else int(bool(v))
        else:
            out[f] = d.get(f)
    return out


def extract_features(entries) -> list[dict]:
    """Return inference feature rows and assert that no LABEL column is present."""
    assert not (set(INFERENCE_FEATURES) & set(LABELS)), "features and labels must not overlap (leakage)"
    return [_row(e) for e in entries]


def reliability_target(entry) -> float | None:
    """Reliability regression target: perturbation-level delta_pearson, a label rather than a feature."""
    d = entry.as_dict() if hasattr(entry, "as_dict") else dict(entry)
    return d.get("delta_pearson")


def router_label(entry) -> str | None:
    """Router label: argmax of per_predictor_delta_pearson; the best predictor is a training label."""
    d = entry.as_dict() if hasattr(entry, "as_dict") else dict(entry)
    pp = d.get("per_predictor_delta_pearson")
    if not pp:
        return None
    return max(pp, key=pp.get)


def leave_perturbation_out_folds(entries, k: int = 5) -> list[tuple[list[int], list[int]]]:
    """Deterministic perturbation-level k-fold split by index modulo k; return (train_idx, test_idx) pairs."""
    n = len(entries)
    folds = []
    for f in range(k):
        test = [i for i in range(n) if i % k == f]
        train = [i for i in range(n) if i % k != f]
        if test and train:
            folds.append((train, test))
    return folds


def audit_columns() -> dict:
    """Return the inference/label/diagnostic column audit classification."""
    return {"inference_features": list(INFERENCE_FEATURES),
            "labels": list(LABELS),
            "diagnostic": list(DIAGNOSTIC)}
