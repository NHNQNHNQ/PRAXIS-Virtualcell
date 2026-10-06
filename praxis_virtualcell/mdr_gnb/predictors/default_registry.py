"""默认注册装配:把 M2 各 species×drug 模型 + M3 机理层包成 PredictorSpec 注册进 registry。

设计:registry 只持有**能力声明** + 惰性 predict 闭包,不在注册期加载 artifact。
全景铺开:genotype→SIR 注册在已入库物种;MIC 回归组合仅占位(NCBI-only 无定量 MIC);
其余组合仅规则基线兜底(sir_class)。机理 spec 的 requires 带 'g3_passed',critic 据此把关。

**predict 接线现状(2026-07-05)**:
- genotype_to_sir:**已接线真加载**(M2-artifact 工作块)。按 species+drug 加载
  data/mdr_gnb/models/<species>/genotype_to_sir__<safe_drug>.joblib(RF,自包含 feature_names),
  把 amr_profile 转 gene=/mut= one-hot 出 {sir,sir_prob};artifact 缺→fail-closed abstain。
- **mic_regressor:恒 fail-closed abstain**(NCBI-only 无定量 MIC,不训 MIC 回归,诚实不伪造)。
- **sm_activity_model(线B B1):已接线真加载**。按 species 加载
  data/mdr_gnb/models/<species>/sm_activity__mic.joblib(Morgan+RF QSAR,B0.1 验证 R²=0.565),
  从 ctx['smiles'] 出 log10-MIC;缺 smiles/缺 artifact/invalid/化学 OOD → fail-closed abstain。
- mechanism_state/gem_fba:fail-closed(机理层经 run_g3_gate 单独产报告,不进 SIR/MIC ensemble)。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from praxis_virtualcell.mdr_gnb.predictors.registry import (
    PredictorRegistry, PredictorSpec,
)

# 磁盘 model artifact 根(测试可 monkeypatch)。
# 路径经 __file__ 解析(抗 CWD;裸相对路径在生产 ASGI/Docker 非 repo 根 CWD 下会静默丢失
# —— 且 _load_* 是 lru_cache,None 会被永久钉住,事后 chdir 回仓库根也不恢复)。
# default_registry.py: praxis_virtualcell/mdr_gnb/predictors/ → parents[3] = 仓库根
_MODELS_ROOT = Path(__file__).resolve().parents[3] / "data" / "mdr_gnb" / "models"
_DEFAULT_MODELS_ROOT = _MODELS_ROOT


def _fail_closed_predict(name: str, output_kind: str):
    """惰性 fail-closed predict 闭包:artifact 缺/不适用时诚实 abstain,不伪造。"""
    def _predict(ctx: dict[str, Any]) -> dict[str, Any]:
        reason = (
            "NCBI-only 无定量 MIC,mic_regressor 不训、恒 abstain(诚实不伪造)"
            if output_kind == "mic_scalar"
            else f"{name} 不进 SIR/MIC ensemble(机理层经 run_g3_gate 单独产报告)"
        )
        return {"abstained": True, "predictor": name,
                "output_kind": output_kind, "abstain_reason": reason}
    return _predict


# --- genotype_to_sir 真加载接线 -----------------------------------------------

def _safe_drug(drug: str) -> str:
    return drug.replace("/", "_").replace(" ", "_")


@lru_cache(maxsize=None)
def _load_test_gsir(models_root: str, species: str, safe_drug: str):
    """Cache only explicit non-production test roots by their resolved path."""
    from praxis_virtualcell.mdr_gnb.predictors.genotype_to_sir import GenotypeToSIR

    path = Path(models_root) / species / f"genotype_to_sir__{safe_drug}.joblib"
    if not path.exists():
        return None
    return GenotypeToSIR.load(path)


def _load_gsir(
    species: str,
    safe_drug: str,
    *,
    runtime_manifest: Any | None = None,
):
    """Load a verified SIR adapter without a logical-name production cache.

    Production requests must reach ``RuntimeModelManifest.load_ready_model`` so
    its SHA-keyed adapter cache, not an unversioned ``species×drug`` cache,
    governs reuse.  Explicit monkeypatched model roots retain a small test-only
    cache to keep existing fixture ergonomics.
    """
    if _MODELS_ROOT == _DEFAULT_MODELS_ROOT:
        from praxis_virtualcell.model_zoo.runtime_manifest import get_runtime_manifest

        try:
            manifest = runtime_manifest or get_runtime_manifest()
            return manifest.load_ready_model(f"sir/{species}/{safe_drug}")
        except ValueError:
            if runtime_manifest is not None:
                raise
            return None

    return _load_test_gsir(str(_MODELS_ROOT.resolve()), species, safe_drug)


def _amr_to_X(amr_profile: dict[str, Any], feature_names: list[str]) -> np.ndarray:
    """amr_profile{基因/突变名:True} → 按 feature_names 的 gene=/mut=/mech= one-hot 行向量。
    机制聚合 token(mech=)仅当模型词表含时生效 → 基线特征模型行为不变(向后兼容)。

    API 的 AMR profile 契约是 ``marker -> bool``。只有显式 ``True`` 才是阳性
    marker；例如字符串 ``"false"`` 或整数 ``1`` 不能静默变成耐药证据。"""
    from praxis_virtualcell.mdr_gnb.predictors.mechanism_features import mechanism_tokens
    idx = {n: i for i, n in enumerate(feature_names)}
    X = np.zeros((1, len(feature_names)), dtype=float)
    tokens: set[str] = set()
    for key, val in (amr_profile or {}).items():
        if val is True:
            marker = str(key)
            tokens.add(f"gene={marker}")
            tokens.add(f"mut={marker}")
    genotype_str = ",".join(str(k) for k, v in (amr_profile or {}).items() if v is True)
    tokens |= mechanism_tokens(genotype_str)      # 机制聚合(carbapenem_R_pathway 等)
    for tok in tokens:
        j = idx.get(tok)
        if j is not None:
            X[0, j] = 1.0
    return X


def _has_recognized_amr_feature(amr_profile: dict[str, Any], feature_names: list[str]) -> bool:
    """输入是否命中该 artifact 的实际训练特征。

    这不是 ``bool(amr_profile)``：某个键只有在生产投影后命中当前
    species×drug 模型的 ``feature_names`` 才能作为预测依据。"""
    return bool(np.any(_amr_to_X(amr_profile, feature_names)))


# --- sm_activity(化合物结构→活性 QSAR)真加载接线(线B B1)---------------------

@lru_cache(maxsize=None)
def _load_test_sm_activity(models_root: str, species: str):
    from praxis_virtualcell.mdr_gnb.predictors.small_molecule_model import SmallMoleculeModel

    path = Path(models_root) / species / "sm_activity__mic.joblib"
    if not path.exists():
        return None
    return SmallMoleculeModel.load(path)


def _load_sm_activity(
    species: str,
    *,
    runtime_manifest: Any | None = None,
):
    """按 species 加载 SmallMoleculeModel artifact(sm_activity__mic.joblib);缺则 None。

    artifact 是 B0.1 验证过的 Morgan+RF QSAR(scaffold split R²=0.565)固化件,由
    workflows/science_v2/qsar_train.py 在真 ChEMBL MIC 上训出(joblib gitignore,留本地/53)。
    """
    if _MODELS_ROOT == _DEFAULT_MODELS_ROOT:
        from praxis_virtualcell.model_zoo.runtime_manifest import get_runtime_manifest

        try:
            manifest = runtime_manifest or get_runtime_manifest()
            return manifest.load_ready_model(
                f"activity/{species}/small_molecule"
            )
        except ValueError:
            if runtime_manifest is not None:
                raise
            return None

    return _load_test_sm_activity(str(_MODELS_ROOT.resolve()), species)


def _sm_activity_predict(
    ctx: dict[str, Any],
    *,
    runtime_manifest: Any | None = None,
) -> dict[str, Any]:
    """化合物 SMILES → log10-MIC。fail-closed:缺 smiles/缺 artifact/invalid/化学 OOD → abstain。

    OOD(对训练集最大 Tanimoto<阈)不预测,置 ood=True 供上游把 drug_in_training_dist 判 False
    → 报告经 abstain 硬规则出 drug_out_of_training_distribution(诚实不伪造 OOD 数字)。
    """
    species = ctx.get("species", "")
    smiles = ctx.get("smiles")
    if not smiles:
        return {"abstained": True, "predictor": "sm_activity_model",
                "output_kind": "sm_activity", "reason_code": "compound_smiles_missing",
                "abstain_reason": "无 smiles 输入(化合物查询须提供结构)"}
    try:
        model = _load_sm_activity(species, runtime_manifest=runtime_manifest)
    except ValueError as exc:
        return {"abstained": True, "predictor": "sm_activity_model",
                "output_kind": "sm_activity", "reason_code": str(exc),
                "abstain_reason": "模型工件完整性在执行前发生漂移，fail-closed 弃权"}
    if model is None:
        return {"abstained": True, "predictor": "sm_activity_model",
                "output_kind": "sm_activity", "reason_code": "sm_activity_model_unavailable",
                "abstain_reason": f"无 {species} sm_activity artifact(fail-closed,不伪造)"}
    r = model.predict_one(smiles)
    if not r.get("ok"):
        from praxis_virtualcell.mdr_gnb.predictors.small_molecule_model import GATE_REASON_MESSAGES
        reason = r.get("reason")
        if reason in GATE_REASON_MESSAGES:
            # Phase 12 加法方向结构 sanity gate 触发:保留专属 reason_code(不混进"特征化失败"),
            # 让报告级弃权透出准确原因(结构规模/组分,独立于 Tanimoto)。
            return {"abstained": True, "predictor": "sm_activity_model",
                    "output_kind": "sm_activity", "reason_code": reason,
                    "abstain_reason": f"{GATE_REASON_MESSAGES[reason]},fail-closed 弃权"}
        return {"abstained": True, "predictor": "sm_activity_model",
                "output_kind": "sm_activity", "reason_code": "compound_featurization_failed",
                "abstain_reason": f"化合物特征化失败:{reason}"}
    if r["is_ood"]:
        return {"abstained": True, "predictor": "sm_activity_model",
                "output_kind": "sm_activity", "ood": True,
                "reason_code": "drug_out_of_training_distribution",
                "max_tanimoto": r["max_tanimoto"],
                "abstain_reason": (f"化学空间外(对训练集最大 Tanimoto={r['max_tanimoto']:.3f}"
                                   f"<{model.ood_threshold}),fail-closed 弃权")}
    return {"abstained": False, "predictor": "sm_activity_model",
            "output_kind": "sm_activity",
            "log10_mic": r["log10_mic"], "mic_ug_ml": r["mic_ug_ml"],
            "max_tanimoto": r["max_tanimoto"], "is_ood": False,
            "uncertainty": {"sigma": round(r["std"], 4)}}


# --- peptide_activity(肽序列→活性 QSAR)真加载接线(线B B5)-----------------------

@lru_cache(maxsize=None)
def _load_test_peptide_activity(models_root: str, species: str):
    from praxis_virtualcell.mdr_gnb.predictors.peptide_activity_model import PeptideActivityModel

    path = Path(models_root) / species / "peptide_activity__mic.joblib"
    if not path.exists():
        return None
    return PeptideActivityModel.load(path)


def _load_peptide_activity(
    species: str,
    *,
    runtime_manifest: Any | None = None,
):
    """按 species 加载 PeptideActivityModel artifact(peptide_activity__mic.joblib);缺则 None。

    artifact 是 B5 验证过的 理化+组成+RF QSAR(序列相似度连通分量防泄漏 R²=0.29)固化件,由
    workflows/science_v2/peptide_train.py 在真 DBAASP MIC 上训出(joblib gitignore,留本地)。
    """
    if _MODELS_ROOT == _DEFAULT_MODELS_ROOT:
        from praxis_virtualcell.model_zoo.runtime_manifest import get_runtime_manifest

        try:
            manifest = runtime_manifest or get_runtime_manifest()
            return manifest.load_ready_model(f"activity/{species}/peptide")
        except ValueError:
            if runtime_manifest is not None:
                raise
            return None

    return _load_test_peptide_activity(str(_MODELS_ROOT.resolve()), species)


def _peptide_activity_predict(
    ctx: dict[str, Any],
    *,
    runtime_manifest: Any | None = None,
) -> dict[str, Any]:
    """肽序列 → log10-MIC(µM)。fail-closed:缺 sequence/缺 artifact/invalid/序列 OOD → abstain。

    序列 OOD(对训练集最大 k-mer Jaccard<阈)不预测,置 ood=True 供上游把 drug_in_training_dist
    判 False → 报告出 drug_out_of_training_distribution(诚实不伪造 OOD 数字)。
    """
    species = ctx.get("species", "")
    sequence = ctx.get("sequence")
    if not sequence:
        return {"abstained": True, "predictor": "peptide_activity_model",
                "output_kind": "peptide_activity", "reason_code": "peptide_sequence_missing",
                "abstain_reason": "无 sequence 输入(肽查询须提供序列)"}
    try:
        model = _load_peptide_activity(species, runtime_manifest=runtime_manifest)
    except ValueError as exc:
        return {"abstained": True, "predictor": "peptide_activity_model",
                "output_kind": "peptide_activity", "reason_code": str(exc),
                "abstain_reason": "模型工件完整性在执行前发生漂移，fail-closed 弃权"}
    if model is None:
        return {"abstained": True, "predictor": "peptide_activity_model",
                "output_kind": "peptide_activity", "reason_code": "peptide_activity_model_unavailable",
                "abstain_reason": f"无 {species} peptide_activity artifact(fail-closed,不伪造)"}
    r = model.predict_one(sequence)
    if not r.get("ok"):
        from praxis_virtualcell.mdr_gnb.predictors.peptide_activity_model import PEP_LEN_MAX
        reason = r.get("reason")
        if reason == "peptide_length_out_of_range":
            # Phase 12 加法方向长度 sanity gate 触发:保留专属 reason_code(独立于 k-mer Jaccard)。
            return {"abstained": True, "predictor": "peptide_activity_model",
                    "output_kind": "peptide_activity", "reason_code": reason,
                    "abstain_reason": f"序列长度超训练范围(长度 > {PEP_LEN_MAX}),fail-closed 弃权"}
        return {"abstained": True, "predictor": "peptide_activity_model",
                "output_kind": "peptide_activity", "reason_code": "peptide_featurization_failed",
                "abstain_reason": f"肽特征化失败:{reason}"}
    if r["is_ood"]:
        return {"abstained": True, "predictor": "peptide_activity_model",
                "output_kind": "peptide_activity", "ood": True,
                "reason_code": "drug_out_of_training_distribution",
                "max_jaccard": r["max_jaccard"],
                "abstain_reason": (f"序列空间外(对训练集最大 Jaccard={r['max_jaccard']:.3f}"
                                   f"<{model.ood_threshold}),fail-closed 弃权")}
    return {"abstained": False, "predictor": "peptide_activity_model",
            "output_kind": "peptide_activity",
            "log10_mic": r["log10_mic"], "mic_um": r["mic_um"],
            "max_jaccard": r["max_jaccard"], "is_ood": False,
            "uncertainty": {"sigma": round(r["std"], 4)}}


def _genotype_sir_predict(
    ctx: dict[str, Any],
    *,
    runtime_manifest: Any | None = None,
) -> dict[str, Any]:
    """真加载 genotype_to_sir artifact 出 SIR;artifact 缺 fail-closed abstain。"""
    species = ctx.get("species", "")
    drug = ctx.get("drug", "")
    readiness = None
    if _MODELS_ROOT == _DEFAULT_MODELS_ROOT:
        from praxis_virtualcell.model_zoo.runtime_manifest import get_runtime_manifest

        manifest = runtime_manifest or get_runtime_manifest()
        readiness = manifest.inspect_sir(species, drug, probe=True)
        if not readiness.ready:
            return {
                "abstained": True,
                "predictor": "genotype_to_sir",
                "output_kind": "sir_class",
                "reason_code": readiness.reason_code,
                "abstain_reason": "SIR artifact runtime readiness 未通过，fail-closed 弃权",
            }
    try:
        clf = _load_gsir(
            species,
            _safe_drug(drug),
            runtime_manifest=runtime_manifest,
        )
    except ValueError as exc:
        return {"abstained": True, "predictor": "genotype_to_sir",
                "output_kind": "sir_class", "reason_code": str(exc),
                "abstain_reason": "SIR 工件完整性在执行前发生漂移，fail-closed 弃权"}
    if clf is None:
        return {"abstained": True, "predictor": "genotype_to_sir",
                "output_kind": "sir_class",
                "reason_code": "sir_artifact_unavailable",
                "abstain_reason": f"无 {species}×{drug} SIR artifact(fail-closed,不伪造)"}
    feature_names = list(clf.feature_names) if clf.feature_names is not None else []
    if not feature_names:
        return {"abstained": True, "predictor": "genotype_to_sir",
                "output_kind": "sir_class",
                "reason_code": "sir_artifact_feature_schema_missing",
                "abstain_reason": "SIR artifact 缺 feature_names，无法验证输入 schema，fail-closed 弃权"}
    X = _amr_to_X(ctx.get("amr_profile") or {}, feature_names)
    if not np.any(X):
        # 零向量在训练时可能与 S 或 R 相关，但运行时无法区分“完整的阴性 callset”与
        # “漏传/无关/词表外 profile”。当前请求 schema 没有完整性证书，故不得把它解释成敏感。
        return {"abstained": True, "predictor": "genotype_to_sir",
                "output_kind": "sir_class",
                "reason_code": "amr_profile_no_recognized_features",
                "abstain_reason": "AMR profile 未命中该模型训练特征，无法作为 SIR 预测依据，fail-closed 弃权"}
    p = float(clf.predict_proba_r(X)[0])
    sir = "R" if p >= 0.5 else "S"
    return {"abstained": False, "predictor": "genotype_to_sir",
            "output_kind": "sir_class",
            "sir_prob": {"S": 1.0 - p, "I": 0.0, "R": p}, "sir": sir,
            "uncertainty": {"sigma": round(1.0 - abs(2 * p - 1.0), 4)}}  # 越靠 0.5 越不确定


# G2 判定为 pass 的 species×drug_class(MIC 组合;NCBI-only 下 mic 恒 abstain,保留声明)。
_PASS_MIC_COMBOS: list[tuple[str, str]] = [
    ("escherichia_coli", "carbapenems"),
    ("escherichia_coli", "beta_lactams"),
    ("klebsiella_pneumoniae", "carbapenems"),
    ("klebsiella_pneumoniae", "beta_lactams"),
]
# G3 通过(消融显示机理层做功,见 reports/mechanistic/)的 species。
_G3_PASSED_SPECIES: list[str] = ["escherichia_coli", "klebsiella_pneumoniae"]
# 线B:有 sm_activity(化合物→活性 QSAR)artifact 的 species(B0.1 先做 EC;KP 留 B0.2)。
# drug_class=["*"]:化合物本身即被测药,不限已知药类(novel_compound 也走通)。
_SM_ACTIVITY_SPECIES: list[str] = ["escherichia_coli"]
# 线B B5:有 peptide_activity(肽序列→活性 QSAR)artifact 的 species(先做 EC;DBAASP R²=0.29)。
_PEPTIDE_ACTIVITY_SPECIES: list[str] = ["escherichia_coli"]
# 全景注册 genotype_to_sir 的物种(全 9 有 NCBI 数据物种;各 species×drug 有 artifact 才真出,
# 缺则 predict fail-closed abstain。固有耐药稀疏物种多数 drug 无 artifact,诚实降级)。
_GENOTYPE_SIR_SPECIES: list[str] = [
    "escherichia_coli", "klebsiella_pneumoniae", "pseudomonas_aeruginosa",
    "acinetobacter_baumannii", "salmonella_enterica", "enterobacter_cloacae",
    "serratia_marcescens", "stenotrophomonas_maltophilia", "morganella_morganii",
]


def _sir_runtime_ready(
    ctx: dict[str, Any],
    *,
    runtime_manifest: Any | None = None,
) -> tuple[bool, str]:
    from praxis_virtualcell.model_zoo.runtime_manifest import get_runtime_manifest

    manifest = runtime_manifest or get_runtime_manifest()
    status = manifest.inspect_sir(
        str(ctx.get("species", "")), str(ctx.get("drug", "")), probe=True
    )
    return status.ready, status.reason_code


def _catalog_runtime_ready(model_id: str, *, runtime_manifest: Any | None = None):
    def _check(_ctx: dict[str, Any]) -> tuple[bool, str]:
        from praxis_virtualcell.model_zoo.runtime_manifest import get_runtime_manifest

        manifest = runtime_manifest or get_runtime_manifest()
        status = manifest.inspect(model_id, probe=True)
        return status.ready, status.reason_code

    return _check


def _declared_only(reason_code: str):
    def _check(_ctx: dict[str, Any]) -> tuple[bool, str]:
        return False, reason_code

    return _check


def build_default_registry(*, runtime_manifest: Any | None = None) -> PredictorRegistry:
    """Build the production registry bound to one optional runtime manifest.

    ``run_mdr_query`` supplies the same request-scoped manifest used by the
    response-cache integrity preflight.  Readiness, provenance and adapter load
    then describe one catalog/artifact observation rather than independently
    reopening a mutable global resolver at each stage.
    """
    reg = PredictorRegistry()

    # 1) 通配规则基线(SIR):全物种全药类兜底(predict 待接 rule_baseline,当前 fail-closed)
    reg.register(PredictorSpec(
        name="rule_baseline_sir", version="amrfinder-2025-07-16.1",
        species=["*"], drug_class=["*"], output_kind="sir_class",
        artifact_path="praxis_virtualcell/mdr_gnb/predictors/rules/amrfinder_sir_rules.yaml",
        requires=["species", "drug", "amr_profile"],
        predict=_fail_closed_predict("rule_baseline_sir", "sir_class"),
        readiness=_declared_only("rule_baseline_not_runtime_predictor"),
    ))

    # 2) genotype→SIR 分类器(全 9 有数据物种)——**已接线真加载**
    for species in _GENOTYPE_SIR_SPECIES:
        reg.register(PredictorSpec(
            name="genotype_to_sir", version=f"m2-{species}",
            species=[species], drug_class=["*"], output_kind="sir_class",
            artifact_path=f"data/mdr_gnb/models/{species}/genotype_to_sir__<drug>.joblib",
            requires=["amr_profile", "drug"],
            predict=lambda ctx, _manifest=runtime_manifest: _genotype_sir_predict(
                ctx, runtime_manifest=_manifest
            ),
            readiness=lambda ctx, _manifest=runtime_manifest: _sir_runtime_ready(
                ctx, runtime_manifest=_manifest
            ),
        ))

    # 3) MIC 回归(NCBI-only 无定量 MIC → 恒 fail-closed abstain,保留能力声明)
    for species, dc in _PASS_MIC_COMBOS:
        reg.register(PredictorSpec(
            name="mic_regressor", version=f"m2-{species}-{dc}",
            species=[species], drug_class=[dc], output_kind="mic_scalar",
            artifact_path=f"data/mdr_gnb/models/{species}/mic_{dc}.joblib",
            requires=["features", "drug"],
            predict=_fail_closed_predict("mic_regressor", "mic_scalar"),
            readiness=_declared_only("quantitative_mic_model_unavailable"),
        ))

    # 3b) 线B:sm_activity(化合物结构→活性 QSAR)——已接线真加载(artifact 缺→fail-closed)
    for species in _SM_ACTIVITY_SPECIES:
        reg.register(PredictorSpec(
            name="sm_activity_model", version=f"b1-{species}",
            species=[species], drug_class=["*"], output_kind="sm_activity",
            artifact_path=f"data/mdr_gnb/models/{species}/sm_activity__mic.joblib",
            requires=["smiles"],
            predict=lambda ctx, _manifest=runtime_manifest: _sm_activity_predict(
                ctx, runtime_manifest=_manifest
            ),
            readiness=_catalog_runtime_ready(
                f"activity/{species}/small_molecule",
                runtime_manifest=runtime_manifest,
            ),
        ))

    # 3c) 线B B5:peptide_activity(肽序列→活性 QSAR)——已接线真加载(artifact 缺→fail-closed)
    for species in _PEPTIDE_ACTIVITY_SPECIES:
        reg.register(PredictorSpec(
            name="peptide_activity_model", version=f"b5-{species}",
            species=[species], drug_class=["*"], output_kind="peptide_activity",
            artifact_path=f"data/mdr_gnb/models/{species}/peptide_activity__mic.joblib",
            requires=["sequence"],
            predict=lambda ctx, _manifest=runtime_manifest: _peptide_activity_predict(
                ctx, runtime_manifest=_manifest
            ),
            readiness=_catalog_runtime_ready(
                f"activity/{species}/peptide",
                runtime_manifest=runtime_manifest,
            ),
        ))

    # 4) M3 机理层:状态模型 + 代谢靶 FBA(requires 带 g3_passed,critic 据此把关机制声明)
    for species in _G3_PASSED_SPECIES:
        reg.register(PredictorSpec(
            name="mechanism_state_model", version=f"m3-{species}",
            species=[species], drug_class=["*"], output_kind="mechanism_state",
            artifact_path=f"data/mdr_gnb/models/{species}/mechanism_state.joblib",
            requires=["amr_profile", "assay_context", "g3_passed"],
            predict=_fail_closed_predict("mechanism_state_model", "mechanism_state"),
            readiness=_declared_only("mechanism_state_model_unavailable"),
        ))
        reg.register(PredictorSpec(
            name="gem_fba", version=f"m3-{species}",
            species=[species], drug_class=["beta_lactams", "carbapenems"],
            output_kind="mechanism_state",
            artifact_path=f"data/mdr_gnb/gems/{species}.xml.gz",
            requires=["amr_profile", "drug", "g3_passed"],
            predict=_fail_closed_predict("gem_fba", "mechanism_state"),
            readiness=_declared_only("experimental_gem_not_runtime_predictor"),
        ))
    return reg


# Compatibility for existing focused fixtures.  Only explicitly monkeypatched
# test-root loaders retain logical-path caching; production adapter reuse lives
# in RuntimeModelManifest and is keyed by a verified artifact SHA-256.
_load_gsir.cache_clear = _load_test_gsir.cache_clear  # type: ignore[attr-defined]
_load_sm_activity.cache_clear = _load_test_sm_activity.cache_clear  # type: ignore[attr-defined]
_load_peptide_activity.cache_clear = _load_test_peptide_activity.cache_clear  # type: ignore[attr-defined]
