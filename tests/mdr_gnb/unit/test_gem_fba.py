"""GemFbaPredictor:代谢靶给 growth 抑制,非代谢靶/无 GEM/无 cobra 一律显式 abstain。"""
from __future__ import annotations

import gzip
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import praxis_virtualcell.mdr_gnb.predictors.mechanistic.gem_fba as gem_fba_module
import praxis_virtualcell.model_zoo.runtime_manifest as runtime_manifest_module
from praxis_virtualcell.mdr_gnb.predictors.mechanistic.gem_fba import (
    METABOLIC_TARGET_DRUGS,
    GemFbaPredictor,
    GemFbaResult,
)
from praxis_virtualcell.model_zoo.runtime_manifest import DEFAULT_CATALOG, RuntimeModelManifest


# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts

_HAS_COBRA = importlib.util.find_spec("cobra") is not None
_REPO_ROOT = Path(__file__).resolve().parents[3]
_GEM_ECOLI = _REPO_ROOT / "data" / "mdr_gnb" / "gems" / "iML1515.xml.gz"
_IML1515_MODEL_ID = "mechanism/escherichia_coli/iml1515"


def _manifest_with_iml1515_mutation(tmp_path: Path, mutate) -> RuntimeModelManifest:
    """Build a one-off catalog so the production boundary is tested without disk mutation."""
    catalog = yaml.safe_load(Path(DEFAULT_CATALOG).read_text(encoding="utf-8"))
    mutate(catalog["models"][_IML1515_MODEL_ID])
    catalog_path = tmp_path / "registry_mdr_gnb.yaml"
    catalog_path.write_text(
        yaml.safe_dump(catalog, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return RuntimeModelManifest(catalog_path, repo_root=_REPO_ROOT)


def test_non_metabolic_target_always_abstains():
    p = GemFbaPredictor()
    r = p.predict(species="escherichia_coli", drug="meropenem")
    assert isinstance(r, GemFbaResult)
    assert r.abstained is True
    assert "非代谢靶" in r.abstain_reason
    assert r.growth_inhibition is None


def test_missing_gem_species_abstains():
    p = GemFbaPredictor()
    # proteus 无 GEM,即便给代谢靶药也 abstain
    drug = next(iter(METABOLIC_TARGET_DRUGS))
    r = p.predict(species="proteus_mirabilis", drug=drug)
    assert r.abstained is True
    assert "GEM" in r.abstain_reason


@pytest.mark.skipif(
    not (_HAS_COBRA and _GEM_ECOLI.exists()),
    reason="需要 cobra 与 iML1515;缺失时该功能路径由 abstain 分支覆盖",
)
def test_metabolic_target_returns_growth_inhibition():
    p = GemFbaPredictor()
    r = p.predict(species="escherichia_coli", drug="trimethoprim-sulfamethoxazole")
    assert r.abstained is False
    assert r.growth_inhibition is not None
    assert 0.0 <= r.growth_inhibition <= 1.0
    # 抑制叶酸通路后 growth 相对野生型应下降
    assert r.baseline_growth is not None and r.baseline_growth > 0
    assert "folate" in (r.mechanism or "").lower() or "叶酸" in (r.mechanism or "")
    contract = next(item for item in r.evidence if item["kind"] == "gem_sidecar_contract")
    assert contract["contract_version"] == "mdr-gem-sidecar-v1"
    assert contract["model_id"] == _IML1515_MODEL_ID
    assert contract["dependency_versions"] == {
        "cobra": "0.31.1",
        "optlang": "1.9.1",
        "swiglpk": "5.0.13",
    }
    lifecycle = RuntimeModelManifest().inspect(_IML1515_MODEL_ID)
    assert lifecycle.declared is True
    assert lifecycle.ready is False
    assert lifecycle.reason_code == "experimental_not_routeable"


def test_no_cobra_reports_abstain_not_crash(monkeypatch):
    # 强制模拟 cobra 不可用:predictor 须 fail-closed 返回 abstain
    p = GemFbaPredictor(cobra_available=False)
    drug = next(iter(METABOLIC_TARGET_DRUGS))
    r = p.predict(species="escherichia_coli", drug=drug)
    assert r.abstained is True
    assert "cobra" in r.abstain_reason.lower()


@pytest.mark.skipif(not _GEM_ECOLI.exists(), reason="需要 iML1515 artifact")
def test_iml1515_catalog_path_mismatch_fails_closed_before_fba(tmp_path):
    manifest = _manifest_with_iml1515_mutation(
        tmp_path,
        lambda model: model["asset"].__setitem__("path", "data/mdr_gnb/gems/README.md"),
    )

    result = GemFbaPredictor(cobra_available=True, sidecar_manifest=manifest).predict(
        species="escherichia_coli", drug="trimethoprim"
    )

    assert result.abstained is True
    assert result.abstain_reason == "gem_sidecar_contract_failed:artifact_path_mismatch"


@pytest.mark.skipif(not _GEM_ECOLI.exists(), reason="需要 iML1515 artifact")
def test_iml1515_catalog_sha_mismatch_fails_closed_before_fba(tmp_path):
    manifest = _manifest_with_iml1515_mutation(
        tmp_path,
        lambda model: model["asset"].__setitem__("sha256", "0" * 64),
    )

    result = GemFbaPredictor(cobra_available=True, sidecar_manifest=manifest).predict(
        species="escherichia_coli", drug="trimethoprim"
    )

    assert result.abstained is True
    assert result.abstain_reason == "gem_sidecar_contract_failed:artifact_sha256_mismatch"


@pytest.mark.skipif(not _GEM_ECOLI.exists(), reason="需要 iML1515 artifact")
def test_direct_iml1515_loader_cannot_bypass_catalog_sha_contract(tmp_path):
    manifest = _manifest_with_iml1515_mutation(
        tmp_path,
        lambda model: model["asset"].__setitem__("sha256", "0" * 64),
    )
    predictor = GemFbaPredictor(cobra_available=True, sidecar_manifest=manifest)

    with pytest.raises(RuntimeError, match="artifact_sha256_mismatch"):
        predictor._load_model(_GEM_ECOLI)


@pytest.mark.skipif(not _GEM_ECOLI.exists(), reason="需要 iML1515 artifact")
def test_iml1515_missing_solver_dependency_fails_closed_before_fba(tmp_path, monkeypatch):
    real_find_spec = importlib.util.find_spec

    def without_optlang(name: str, package: str | None = None):
        if name == "optlang":
            return None
        return real_find_spec(name, package)

    monkeypatch.setattr(runtime_manifest_module.importlib.util, "find_spec", without_optlang)
    manifest = _manifest_with_iml1515_mutation(tmp_path, lambda model: None)

    result = GemFbaPredictor(cobra_available=True, sidecar_manifest=manifest).predict(
        species="escherichia_coli", drug="trimethoprim"
    )

    assert result.abstained is True
    assert result.abstain_reason == "gem_sidecar_contract_failed:dependency_missing:optlang"


@pytest.mark.skipif(not _GEM_ECOLI.exists(), reason="需要 iML1515 artifact")
def test_iml1515_solver_version_mismatch_fails_closed_before_fba(tmp_path):
    def mutate(model: dict) -> None:
        model["runtime"]["dependency_versions"]["swiglpk"] = "0.0.0"

    manifest = _manifest_with_iml1515_mutation(tmp_path, mutate)
    result = GemFbaPredictor(cobra_available=True, sidecar_manifest=manifest).predict(
        species="escherichia_coli", drug="trimethoprim"
    )

    assert result.abstained is True
    assert result.abstain_reason == "gem_sidecar_contract_failed:dependency_version_mismatch:swiglpk"


@pytest.mark.skipif(not _GEM_ECOLI.exists(), reason="需要 iML1515 artifact")
def test_catalog_parser_exception_is_machine_readable_and_fail_closed(monkeypatch):
    def fail_manifest_load():
        raise ValueError("simulated malformed catalog")

    monkeypatch.setattr(gem_fba_module, "RuntimeModelManifest", fail_manifest_load)
    result = GemFbaPredictor(cobra_available=True).predict(
        species="escherichia_coli", drug="trimethoprim"
    )

    assert result.abstained is True
    assert result.abstain_reason == "gem_sidecar_contract_failed:sidecar_contract_exception"


def test_fba_execution_exception_is_machine_readable_and_fail_closed(monkeypatch):
    predictor = GemFbaPredictor(cobra_available=True)

    monkeypatch.setattr(predictor, "_load_model_with_contract", lambda path: (object(), None))

    def fail_fba(*args, **kwargs):
        raise RuntimeError("simulated solver fault")

    monkeypatch.setattr(predictor, "_run_fba", fail_fba)
    result = predictor.predict(species="escherichia_coli", drug="trimethoprim")

    assert result.abstained is True
    assert result.abstain_reason == "gem_fba_execution_failed:RuntimeError"


def test_gzip_model_load_cleans_temporary_xml(tmp_path, monkeypatch):
    """A failed or successful SBML load may not leave an unbounded temp XML behind."""
    artifact = tmp_path / "sidecar.xml.gz"
    with gzip.open(artifact, "wb") as handle:
        handle.write(b"<sbml />")

    observed_paths: list[Path] = []

    class FakeCobraIO:
        @staticmethod
        def read_sbml_model(path: str):
            temporary_path = Path(path)
            assert temporary_path.is_file()
            observed_paths.append(temporary_path)
            return object()

    monkeypatch.setitem(sys.modules, "cobra", SimpleNamespace(io=FakeCobraIO()))
    predictor = GemFbaPredictor(cobra_available=True)
    try:
        predictor._load_model(artifact)
        assert observed_paths
        assert all(not path.exists() for path in observed_paths)
    finally:
        for path in observed_paths:
            path.unlink(missing_ok=True)
