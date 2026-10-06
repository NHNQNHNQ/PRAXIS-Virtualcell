"""GemFbaPredictor:用 cobrapy 载各物种 GEM,仅对代谢靶抗生素估计 growth 抑制。

约束(D4):
- 只有作用于代谢/生物合成通路且能映射到 GEM 反应的药物才走 FBA;
  非代谢靶(碳青霉烯酶/外排/孔蛋白/DNA 旋切酶等)显式 abstain,交给
  MechanismStateModel。
- cobra 缺失、GEM 缺失、通路映射缺失,一律 fail-closed 返回结构化 abstain,
  绝不返回伪造数值,也不静默 skip。
"""
from __future__ import annotations

import gzip
import importlib.util
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from praxis_virtualcell.model_zoo.runtime_manifest import (
    ExperimentalSidecarContract,
    RuntimeModelManifest,
)

# 代谢靶药物 -> GEM 中被抑制的反应 id 列表(以 iML1515/BiGG 命名为准,冻结)
# trimethoprim 抑制 DHFR(反应 DHFR),sulfamethoxazole 抑制 DHPS(反应 DHPS2)。
METABOLIC_TARGET_REACTIONS: dict[str, list[str]] = {
    "trimethoprim": ["DHFR"],
    "sulfamethoxazole": ["DHPS2"],
    "trimethoprim-sulfamethoxazole": ["DHFR", "DHPS2"],
    "sulfamethoxazole-trimethoprim": ["DHFR", "DHPS2"],
    "fosfomycin": ["UAGDP"],  # MurA 类似步骤(近似;报告注明为近似映射)
}
METABOLIC_TARGET_DRUGS: frozenset[str] = frozenset(METABOLIC_TARGET_REACTIONS)

# GEM 库根:路径经 __file__ 解析(抗 CWD;裸相对路径在生产 ASGI/Docker 非 repo 根 CWD 下
# 会静默丢失 —— GEM 找不到 → 机制层退化成「无可用 GEM」abstain,报告不承认降级)。
# gem_fba.py: praxis_virtualcell/mdr_gnb/predictors/mechanistic/ → parents[4] = 仓库根
_GEMS_ROOT = Path(__file__).resolve().parents[4] / "data" / "mdr_gnb" / "gems"

# species -> GEM 文件(**绝对路径**);未列出 = 无 GEM。
# 值刻意存绝对 Path 而非相对字符串:消费者直接 .exists()/读取即正确,不可能再引入 CWD 依赖。
SPECIES_GEM: dict[str, Path] = {
    "escherichia_coli": _GEMS_ROOT / "iML1515.xml.gz",
    "klebsiella_pneumoniae": _GEMS_ROOT / "iYL1228.xml.gz",
    "pseudomonas_aeruginosa": _GEMS_ROOT / "iMO1086.xml.gz",
    "acinetobacter_baumannii": _GEMS_ROOT / "iCN718.xml.gz",
    "salmonella_enterica": _GEMS_ROOT / "STM_v1_0.xml.gz",
}
IML1515_MODEL_ID = "mechanism/escherichia_coli/iml1515"


@dataclass
class GemFbaResult:
    species: str
    drug: str
    abstained: bool
    abstain_reason: str | None = None
    growth_inhibition: float | None = None  # 1 - (被抑制通量约束下 growth / baseline)
    baseline_growth: float | None = None
    constrained_growth: float | None = None
    mechanism: str | None = None
    evidence: list[dict] = field(default_factory=list)


class _GemSidecarContractError(RuntimeError):
    """Internal machine-readable denial raised before an experimental SBML load."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


def _cobra_present() -> bool:
    return importlib.util.find_spec("cobra") is not None


class GemFbaPredictor:
    def __init__(
        self,
        cobra_available: bool | None = None,
        *,
        sidecar_manifest: RuntimeModelManifest | None = None,
    ) -> None:
        # 允许测试注入 False;默认按环境探测
        self._cobra = _cobra_present() if cobra_available is None else cobra_available
        # The model cache key includes the verified SHA.  If an operator replaces the
        # artifact and updates the catalog in a live process, the old in-memory SBML
        # cannot be reused under the new catalog identity.
        self._model_cache: dict[tuple[Path, str | None], object] = {}
        # Resolve the generated catalog lazily in the guarded load path.  A malformed
        # catalog must become a machine-readable abstention, not crash construction of
        # the predictor or an API worker before it can report the failure.
        self._sidecar_manifest = sidecar_manifest

    def predict(
        self,
        *,
        species: str,
        drug: str,
        sidecar_manifest: RuntimeModelManifest | None = None,
    ) -> GemFbaResult:
        """Run one bounded FBA request under an optional captured catalog manifest.

        ``sidecar_manifest`` is supplied by the API request context.  It must take
        precedence over the compatibility constructor value so a long-lived cached
        predictor never opens a fresh catalog while serving a request that already
        has a cache/provenance identity.
        """
        drug = drug.strip().lower()
        # 1) 非代谢靶 -> abstain
        if drug not in METABOLIC_TARGET_DRUGS:
            return GemFbaResult(
                species=species,
                drug=drug,
                abstained=True,
                abstain_reason="非代谢靶抗生素,FBA 不适用,交由 MechanismStateModel 处理",
            )
        # 2) cobra 缺失 -> fail-closed abstain
        if not self._cobra:
            return GemFbaResult(
                species=species,
                drug=drug,
                abstained=True,
                abstain_reason="cobra 不可用,FBA 无法运行(fail-closed)",
            )
        # 3) 无 GEM -> abstain
        gem_path = SPECIES_GEM.get(species)
        if gem_path is None or not gem_path.exists():
            return GemFbaResult(
                species=species,
                drug=drug,
                abstained=True,
                abstain_reason=f"物种 {species} 无可用 GEM(需先入库),FBA abstain",
            )
        try:
            if sidecar_manifest is None:
                # Preserve the direct compatibility seam used by existing callers
                # and test doubles; the constructor-level manifest remains active.
                model, sidecar_contract = self._load_model_with_contract(gem_path)
            else:
                model, sidecar_contract = self._load_model_with_contract(
                    gem_path,
                    sidecar_manifest=sidecar_manifest,
                )
        except _GemSidecarContractError as exc:
            return GemFbaResult(
                species=species,
                drug=drug,
                abstained=True,
                abstain_reason=f"gem_sidecar_contract_failed:{exc.reason_code}",
            )
        except Exception as exc:  # noqa: BLE001 - SBML/solver errors must fail closed
            return GemFbaResult(
                species=species,
                drug=drug,
                abstained=True,
                abstain_reason=f"gem_load_failed:{type(exc).__name__}",
            )
        rxn_ids = METABOLIC_TARGET_REACTIONS[drug]
        try:
            result = self._run_fba(model, species, drug, rxn_ids)
        except Exception as exc:  # noqa: BLE001 - solver faults must not escape the workflow
            evidence = []
            if sidecar_contract is not None:
                evidence.append(
                    {
                        "kind": "gem_sidecar_contract",
                        **sidecar_contract.as_dict(),
                    }
                )
            return GemFbaResult(
                species=species,
                drug=drug,
                abstained=True,
                abstain_reason=f"gem_fba_execution_failed:{type(exc).__name__}",
                evidence=evidence,
            )
        if sidecar_contract is not None:
            result.evidence.insert(
                0,
                {
                    "kind": "gem_sidecar_contract",
                    **sidecar_contract.as_dict(),
                },
            )
        return result

    def _load_model(
        self,
        gem_path: Path,
        *,
        sidecar_manifest: RuntimeModelManifest | None = None,
    ):
        """Compatibility loader that still applies the sidecar contract before SBML I/O."""
        model, _ = self._load_model_with_contract(
            gem_path,
            sidecar_manifest=sidecar_manifest,
        )
        return model

    def _load_model_with_contract(
        self,
        gem_path: Path,
        *,
        sidecar_manifest: RuntimeModelManifest | None = None,
    ) -> tuple[object, ExperimentalSidecarContract | None]:
        """Load one GEM only after rechecking the iML1515 sidecar contract.

        Both ``predict`` and the compatibility ``_load_model`` use this method, so an
        accidental future direct caller cannot bypass catalog path/SHA/dependency
        verification.  The returned contract is attached to the public FBA evidence.
        """
        resolved_path = gem_path.resolve()
        iml1515_path = SPECIES_GEM["escherichia_coli"].resolve()
        contract: ExperimentalSidecarContract | None = None
        if resolved_path == iml1515_path:
            try:
                # API callers supply the exact catalog bytes captured before cache
                # lookup.  Direct compatibility calls keep the old local manifest
                # fallback, but request-scoped work must never silently re-open it.
                manifest = (
                    sidecar_manifest
                    if sidecar_manifest is not None
                    else self._sidecar_manifest or RuntimeModelManifest()
                )
                contract = manifest.inspect_experimental_sidecar(
                    IML1515_MODEL_ID,
                    loader_path=resolved_path,
                )
            except Exception as exc:  # noqa: BLE001 - preserve a stable API denial code
                raise _GemSidecarContractError("sidecar_contract_exception") from exc
            if not contract.operational:
                raise _GemSidecarContractError(contract.reason_code)
        cache_key = (resolved_path, contract.expected_sha256 if contract is not None else None)
        if cache_key in self._model_cache:
            return self._model_cache[cache_key], contract
        import cobra  # 局部导入,避免无 cobra 环境 import 期崩

        if resolved_path.suffix == ".gz":
            # COBRApy reads an uncompressed SBML path.  A scoped directory makes the
            # temporary XML recoverable even when gzip/SBML parsing raises.
            with tempfile.TemporaryDirectory(prefix="praxis-gem-") as temporary_directory:
                temporary_sbml = Path(temporary_directory) / "model.xml"
                with gzip.open(resolved_path, "rb") as source, temporary_sbml.open("wb") as sink:
                    shutil.copyfileobj(source, sink)
                model = cobra.io.read_sbml_model(str(temporary_sbml))
        else:
            model = cobra.io.read_sbml_model(str(resolved_path))
        self._model_cache[cache_key] = model
        return model, contract

    def _run_fba(self, model, species: str, drug: str, rxn_ids: list[str]) -> GemFbaResult:
        # baseline growth
        baseline = float(model.slim_optimize(error_value=0.0) or 0.0)
        present = [r for r in rxn_ids if r in {rx.id for rx in model.reactions}]
        missing = [r for r in rxn_ids if r not in {rx.id for rx in model.reactions}]
        if not present:
            return GemFbaResult(
                species=species,
                drug=drug,
                abstained=True,
                abstain_reason=f"GEM 中缺目标反应 {rxn_ids},通路映射不可用,abstain",
            )
        # 用 context 管理器临时把目标反应通量钳到 0(模拟酶被抑制),不污染 model
        with model:
            for rid in present:
                rx = model.reactions.get_by_id(rid)
                rx.bounds = (0.0, 0.0)
            constrained = float(model.slim_optimize(error_value=0.0) or 0.0)
        if baseline <= 0.0:
            return GemFbaResult(
                species=species,
                drug=drug,
                abstained=True,
                abstain_reason="baseline growth 为 0,FBA 结果不可信,abstain",
            )
        inhibition = max(0.0, min(1.0, 1.0 - constrained / baseline))
        mech = f"抑制 {drug} 代谢靶反应 {present} → growth 下降(叶酸/folate 或对应通路)"
        return GemFbaResult(
            species=species,
            drug=drug,
            abstained=False,
            growth_inhibition=inhibition,
            baseline_growth=baseline,
            constrained_growth=constrained,
            mechanism=mech,
            evidence=[
                {"kind": "fba", "reactions_blocked": present, "reactions_missing": missing},
            ],
        )
