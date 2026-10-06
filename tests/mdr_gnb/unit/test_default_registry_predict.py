"""default_registry predict 接线:genotype_to_sir 真加载出 sir_prob;mic_scalar 保持 abstain。"""
import numpy as np

import praxis_virtualcell.mdr_gnb.predictors.default_registry as dr
from praxis_virtualcell.mdr_gnb.coordinator.mdr_router import route_mdr
from praxis_virtualcell.mdr_gnb.predictors.default_registry import build_default_registry
from praxis_virtualcell.mdr_gnb.predictors.genotype_to_sir import GenotypeToSIR
from praxis_virtualcell.model_zoo.runtime_manifest import ModelReadiness


def _train_and_save(path, feature_names):
    # 小模型:feature[0](碳青霉烯酶)→R,其余无信号
    X = np.zeros((40, len(feature_names)), dtype=np.float32)
    y = np.zeros(40, dtype=int)
    X[:20, 0] = 1.0
    y[:20] = 1
    clf = GenotypeToSIR(model="logreg").fit(X, y)
    clf.feature_names = feature_names
    clf.save(path)


def test_genotype_sir_predict_real(tmp_path, monkeypatch):
    monkeypatch.setattr(dr, "_MODELS_ROOT", tmp_path)
    dr._load_test_gsir.cache_clear()
    fn = ["gene=blaKPC-2", "gene=blaSHV-12", "mut=gyrA_S83L"]
    p = tmp_path / "klebsiella_pneumoniae" / "genotype_to_sir__meropenem.joblib"
    p.parent.mkdir(parents=True)
    _train_and_save(p, fn)

    r = dr._genotype_sir_predict({"species": "klebsiella_pneumoniae", "drug": "meropenem",
                                  "amr_profile": {"blaKPC-2": True}})
    assert r["abstained"] is False
    assert r["output_kind"] == "sir_class"
    assert r["sir_prob"]["R"] > 0.5 and r["sir"] == "R"

    # 无碳青霉烯酶 → R 概率显著更低
    r0 = dr._genotype_sir_predict({"species": "klebsiella_pneumoniae", "drug": "meropenem",
                                   "amr_profile": {"blaSHV-12": True}})
    assert r0["sir_prob"]["R"] < r["sir_prob"]["R"]


def test_genotype_sir_predict_missing_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(dr, "_MODELS_ROOT", tmp_path)
    dr._load_test_gsir.cache_clear()
    r = dr._genotype_sir_predict({"species": "escherichia_coli", "drug": "nonexistent_drug",
                                  "amr_profile": {}})
    assert r["abstained"] is True


def test_genotype_sir_predict_rejects_empty_or_unrecognized_amr_profile(tmp_path, monkeypatch):
    """不能把缺失/词表外 AMR 输入的全零向量解释成 S（非 R）。"""
    monkeypatch.setattr(dr, "_MODELS_ROOT", tmp_path)
    dr._load_test_gsir.cache_clear()
    p = tmp_path / "klebsiella_pneumoniae" / "genotype_to_sir__meropenem.joblib"
    p.parent.mkdir(parents=True)
    _train_and_save(p, ["gene=blaKPC-2"])

    for profile in ({}, {"unrelated_locus": True}):
        r = dr._genotype_sir_predict({
            "species": "klebsiella_pneumoniae", "drug": "meropenem",
            "amr_profile": profile,
        })
        assert r["abstained"] is True
        assert r["reason_code"] == "amr_profile_no_recognized_features"
        assert "sir" not in r and "sir_prob" not in r


def test_mic_regressor_still_abstains():
    reg = build_default_registry()
    specs = reg.discover(species="escherichia_coli", drug_class="carbapenems",
                         output_kind="mic_scalar")
    assert specs
    r = specs[0].predict({"species": "escherichia_coli", "drug": "meropenem",
                          "amr_profile": {}})
    assert r["abstained"] is True  # NCBI 无定量 MIC,mic_scalar 恒 abstain


def test_injected_runtime_context_loads_the_selected_adapter_not_logical_cache():
    """Production closures must use the request context's verified loader."""

    class _Adapter:
        feature_names = ["gene=blaKPC-2"]

        @staticmethod
        def predict_proba_r(_X):
            return np.asarray([0.9])

    class _Context:
        def __init__(self):
            self.loaded: list[str] = []

        @staticmethod
        def inspect_sir(_species, _drug, *, probe=False):
            assert probe is True
            return ModelReadiness(
                model_id="sir/klebsiella_pneumoniae/meropenem",
                declared=True,
                ready=True,
                validated=False,
                validation_status="limited",
                reason_code="ready",
                execution="predict",
                artifact_path="test://context.joblib",
                expected_sha256="a" * 64,
                catalog_digest="b" * 64,
            )

        def load_ready_model(self, model_id):
            self.loaded.append(model_id)
            return _Adapter()

    context = _Context()
    registry = build_default_registry(runtime_manifest=context)
    route = route_mdr(
        {
            "species": "klebsiella_pneumoniae",
            "drug": "meropenem",
            "drug_class": "carbapenems",
            "requested_outputs": ["SIR"],
        },
        registry,
    )
    predictor = next(spec for spec in route.candidates if spec.name == "genotype_to_sir")
    result = predictor.predict(
        {
            "species": "klebsiella_pneumoniae",
            "drug": "meropenem",
            "amr_profile": {"blaKPC-2": True},
        }
    )

    assert result["abstained"] is False
    assert result["sir"] == "R"
    assert context.loaded == ["sir/klebsiella_pneumoniae/meropenem"]


def test_injected_runtime_context_reports_inflight_artifact_drift_fail_closed():
    class _DriftedContext:
        @staticmethod
        def inspect_sir(_species, _drug, *, probe=False):
            assert probe is True
            return ModelReadiness(
                model_id="sir/klebsiella_pneumoniae/meropenem",
                declared=True,
                ready=True,
                validated=False,
                validation_status="limited",
                reason_code="ready",
                execution="predict",
                artifact_path="test://context.joblib",
                expected_sha256="a" * 64,
                catalog_digest="b" * 64,
            )

        @staticmethod
        def load_ready_model(_model_id):
            raise ValueError("request_artifact_integrity_drift")

    result = dr._genotype_sir_predict(
        {
            "species": "klebsiella_pneumoniae",
            "drug": "meropenem",
            "amr_profile": {"blaKPC-2": True},
        },
        runtime_manifest=_DriftedContext(),
    )

    assert result["abstained"] is True
    assert result["reason_code"] == "request_artifact_integrity_drift"
