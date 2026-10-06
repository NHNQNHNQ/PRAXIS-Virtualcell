"""genotype_to_sir 直接分类器测试(NCBI-only 适配:无 MIC 两阶段折点)。"""
import numpy as np

from praxis_virtualcell.mdr_gnb.predictors.genotype_to_sir import GenotypeToSIR


def test_learns_simple_gene_signal():
    # 特征列0=耐药基因;带该基因→R,不带→S
    X = np.zeros((40, 3), dtype=np.float32)
    y = np.zeros(40, dtype=int)
    X[:20, 0] = 1.0
    y[:20] = 1
    clf = GenotypeToSIR().fit(X, y)
    p = clf.predict_proba_r(X)
    assert p[:20].mean() > p[20:].mean()  # 带基因的 P(R) 更高
    pred = clf.predict(X)
    assert (pred[:20] == 1).mean() > 0.8
    assert (pred[20:] == 0).mean() > 0.8


def test_single_class_constant_no_hallucination():
    # 训练集单类(全 R)→ 常数预测,不臆造
    X = np.zeros((5, 2), dtype=np.float32)
    y = np.ones(5, dtype=int)
    clf = GenotypeToSIR().fit(X, y)
    assert clf.predict(X).tolist() == [1, 1, 1, 1, 1]
    assert clf.predict_proba_r(X).tolist() == [1.0] * 5


def test_predict_threshold():
    X = np.zeros((40, 3), dtype=np.float32)
    y = np.zeros(40, dtype=int)
    X[:20, 0] = 1.0
    y[:20] = 1
    clf = GenotypeToSIR().fit(X, y)
    # 阈值越高判 R 越少
    n_hi = clf.predict(X, threshold=0.9).sum()
    n_lo = clf.predict(X, threshold=0.1).sum()
    assert n_lo >= n_hi


def test_rf_model_learns_signal():
    # RandomForest 变体也能学到简单基因信号
    X = np.zeros((40, 3), dtype=np.float32)
    y = np.zeros(40, dtype=int)
    X[:20, 0] = 1.0
    y[:20] = 1
    clf = GenotypeToSIR(model="rf").fit(X, y)
    p = clf.predict_proba_r(X)
    assert p[:20].mean() > p[20:].mean()
    assert (clf.predict(X)[:20] == 1).mean() > 0.8


# ---- 确定性(Phase11-T4 真 bug 回归)----

def _order_sensitive_rf() -> tuple[GenotypeToSIR, np.ndarray]:
    """构造叶概率为**非二进小数**的 RF,及其查询矩阵。

    为什么要刻意造不纯叶:干净可分数据下 RF 会把叶子训纯,叶概率恰为 0.0/1.0,300 棵树
    求和在 float64 里恒精确 → 任何累加顺序同值 → 测不出 ULP 噪声(试过,恒 1 个值)。
    只有叶概率是 7/23 这类非二进小数时,浮点加法不满足结合律,累加顺序才会改变末位——
    这正是部署 artifact(EC×ceftriaxone,20% 不纯叶)的处境。重复特征模式 + 冲突标签
    使叶子**必然**不纯:同一 X 行对应两种 y,树无法靠分裂把它们分开。
    """
    rng = np.random.default_rng(7)
    pats = rng.integers(0, 2, size=(24, 16)).astype(float)
    X = np.repeat(pats, 40, axis=0)
    y = rng.integers(0, 2, size=len(X))
    return GenotypeToSIR(model="rf").fit(X, y), pats


def test_rf_fixture_really_has_impure_leaves():
    """守卫:若 fixture 退化成纯叶,下面的确定性测试会变成空测(恒绿却什么都没验)。"""
    clf, pats = _order_sensitive_rf()
    j = list(clf._clf.classes_).index(1)
    per_tree = np.array([t.predict_proba(pats)[:, j] for t in clf._clf.estimators_])
    impure = (per_tree != 0.0) & (per_tree != 1.0)
    assert impure.mean() > 0.5, "叶概率几乎全是 0/1,累加顺序不敏感,确定性测试将失去意义"


def test_rf_predict_proba_r_bitwise_deterministic():
    """同一 X 重复预测必须**逐位**恒等 —— sir_prob 末位漂会让 trace_hash 变(T4 红线)。

    修复前红:sklearn RF 的 predict_proba 靠 n_jobs 并行把各树结果按**线程完成顺序**
    累加(_forest._accumulate_prediction 在锁里 out += prediction),顺序随调度变 → 末位 ULP 漂。
    """
    clf, pats = _order_sensitive_rf()
    seen = {tuple(v.hex() for v in clf.predict_proba_r(pats)) for _ in range(40)}
    assert len(seen) == 1, f"predict_proba_r 非确定性:40 次调用出现 {len(seen)} 个不同结果"


def test_rf_predict_proba_r_equals_fixed_order_tree_mean():
    """契约:实现就是"按 estimators_ 固定顺序逐树平均",不得回退到并行 predict_proba。"""
    clf, pats = _order_sensitive_rf()
    j = list(clf._clf.classes_).index(1)
    ref = np.mean([t.predict_proba(pats)[:, j] for t in clf._clf.estimators_], axis=0)
    got = clf.predict_proba_r(pats)
    assert [v.hex() for v in got] == [v.hex() for v in ref]


def test_rf_predict_proba_r_numerically_equals_sklearn():
    """只改求和顺序、不改科学:与 sklearn predict_proba 的差异必须只在 ULP 量级。"""
    clf, pats = _order_sensitive_rf()
    j = list(clf._clf.classes_).index(1)
    assert np.allclose(clf.predict_proba_r(pats),
                       clf._clf.predict_proba(pats)[:, j], atol=1e-12, rtol=0)


def test_logreg_path_unchanged_and_deterministic():
    """logreg 路径不受 RF 分支影响:仍逐字走 sklearn predict_proba,且重复调用逐位恒等。"""
    rng = np.random.default_rng(3)
    X = rng.random((60, 5))
    y = (X[:, 0] > 0.5).astype(int)
    clf = GenotypeToSIR().fit(X, y)
    j = list(clf._clf.classes_).index(1)
    assert [v.hex() for v in clf.predict_proba_r(X)] == \
           [v.hex() for v in clf._clf.predict_proba(X)[:, j]]
    seen = {tuple(v.hex() for v in clf.predict_proba_r(X)) for _ in range(10)}
    assert len(seen) == 1


def test_const_path_deterministic():
    """单类退化常数路径不受影响(无 _clf,不走逐树分支)。"""
    X = np.zeros((4, 2))
    clf = GenotypeToSIR().fit(X, np.ones(4, dtype=int))
    seen = {tuple(v.hex() for v in clf.predict_proba_r(X)) for _ in range(10)}
    assert seen == {("0x1.0000000000000p+0",) * 4}
