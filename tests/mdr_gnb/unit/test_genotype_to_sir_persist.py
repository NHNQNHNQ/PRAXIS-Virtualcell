"""GenotypeToSIR 持久化:save/load 往返后 predict 一致(含单类 _const 与 feature_names)。"""
import numpy as np

from praxis_virtualcell.mdr_gnb.predictors.genotype_to_sir import GenotypeToSIR


def _signal_data():
    X = np.zeros((40, 3), dtype=np.float32)
    y = np.zeros(40, dtype=int)
    X[:20, 0] = 1.0
    y[:20] = 1
    return X, y


def test_save_load_roundtrip(tmp_path):
    X, y = _signal_data()
    clf = GenotypeToSIR(model="rf").fit(X, y)
    p = clf.predict_proba_r(X)
    path = tmp_path / "m.joblib"
    clf.save(path)
    loaded = GenotypeToSIR.load(path)
    assert np.allclose(loaded.predict_proba_r(X), p)
    assert (loaded.predict(X) == clf.predict(X)).all()


def test_save_load_single_class_const(tmp_path):
    X = np.zeros((5, 2), dtype=np.float32)
    y = np.ones(5, dtype=int)
    clf = GenotypeToSIR().fit(X, y)  # _const=1
    path = tmp_path / "c.joblib"
    clf.save(path)
    loaded = GenotypeToSIR.load(path)
    assert loaded.predict(X).tolist() == [1, 1, 1, 1, 1]
    assert loaded._const == 1


def test_save_load_preserves_feature_names(tmp_path):
    X, y = _signal_data()
    clf = GenotypeToSIR().fit(X, y)
    clf.feature_names = ["blaKPC", "gyrA_S83L", "sul1"]
    path = tmp_path / "f.joblib"
    clf.save(path)
    loaded = GenotypeToSIR.load(path)
    assert loaded.feature_names == ["blaKPC", "gyrA_S83L", "sul1"]
