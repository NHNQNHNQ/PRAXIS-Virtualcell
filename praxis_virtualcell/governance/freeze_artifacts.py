"""M2.1 Step6:冻结 learned reliability/abstain artifact(可复现导出)。

全量(151 ledger)训练 reliability ridge → 冻结 weights/normalization;由训练预测分布定 abstain/downgrade 阈值;
记 training ledger sha256 + version + finding 引用。写 governance/artifacts/{reliability_model,abstain_head,feature_schema}_v0_3.json。

用法:python -m praxis_virtualcell.governance.freeze_artifacts
"""  # noqa: E501
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from praxis_virtualcell.benchmarks.eval_ledger import EvalLedger
from praxis_virtualcell.governance import ledger_features as lf
from praxis_virtualcell.governance import reliability_model as rm

LEDGER = "docs/findings/m1_ledger_151.jsonl"
ART = Path(__file__).parent / "artifacts"
SCHEMA = "v0.3.0"


def _quantile(vals, q):
    s = sorted(v for v in vals if v == v)
    return s[max(0, min(len(s) - 1, int(q * (len(s) - 1))))]


def main():
    ART.mkdir(parents=True, exist_ok=True)
    led = EvalLedger.from_jsonl(LEDGER)
    params = rm.fit_full(led.entries)
    # 用 ledger_features 抽真实推理特征(与 runtime 一致)再预测 → 训练预测分布定阈值
    rows = lf.extract_features(led.entries)
    preds = [rm.predict_dp(params, r) for r in rows]
    abstain_thr = _quantile(preds, 0.15)
    downgrade_thr = _quantile(preds, 0.35)
    ledger_sha = hashlib.sha256(Path(LEDGER).read_bytes()).hexdigest()

    rel = {
        "model_version": "reliability_v0.3.0", "feature_schema_version": SCHEMA,
        "features": params["features"], "mean": params["mean"], "std": params["std"],
        "weights": params["weights"], "lam": params["lam"],
        "training_ledger": LEDGER, "training_ledger_sha256": ledger_sha, "n_train": len(led.entries),
        "finding": "docs/findings/finding_w9_m2_reliability_model.md",
        "metrics_oof": {"reg_corr": 0.701, "bad_auroc": 0.907},
    }
    # 自校验:content hash 覆盖模型内容(features/mean/std/weights/lam);runtime 验证不符 → 篡改 → fallback
    content = {k: rel[k] for k in ("features", "mean", "std", "weights", "lam")}
    rel["content_sha256"] = hashlib.sha256(
        json.dumps(content, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    ab = {
        "model_version": "abstain_v0.3.0", "feature_schema_version": SCHEMA,
        "uses_reliability": "reliability_v0.3.0",
        "abstain_threshold_dp": abstain_thr, "downgrade_threshold_dp": downgrade_thr,
        "operating_point": "abstain<=15pct / downgrade<=35pct of training predicted dp",
        "finding": "docs/findings/finding_w9_m2_abstain_head.md", "risk_coverage_auc": 0.746,
    }
    schema = {
        "feature_schema_version": SCHEMA,
        "model_features": params["features"],
        "inference_features_audited": list(lf.INFERENCE_FEATURES),
        "labels_forbidden": list(lf.LABELS),
        "note": "runtime 只可用 model_features(推理期可得);labels_forbidden 严禁进入 runtime 特征(防泄漏)",
    }
    (ART / "reliability_model_v0_3.json").write_text(json.dumps(rel, ensure_ascii=False, indent=2), encoding="utf-8")
    (ART / "abstain_head_v0_3.json").write_text(json.dumps(ab, ensure_ascii=False, indent=2), encoding="utf-8")
    (ART / "feature_schema_v0_3.json").write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    print("froze artifacts:", abstain_thr, downgrade_thr, "ledger_sha", ledger_sha[:12])


if __name__ == "__main__":
    main()
