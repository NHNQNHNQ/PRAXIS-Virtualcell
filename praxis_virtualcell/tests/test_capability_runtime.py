"""P6: capability-driven model planning and runtime plugin execution."""

from __future__ import annotations

import copy
import hashlib
import inspect
from pathlib import Path

import pytest
import yaml

from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.core.request import VirtualCellRequest
from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2
from praxis_virtualcell.data_packs.registry import PackRegistry
from praxis_virtualcell.model_zoo.cache import ModelCache
from praxis_virtualcell.model_zoo.capability_registry import (
    CapabilityRegistry,
    EnvironmentSnapshot,
    ExecutionStep,
    ModelCard,
)
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry
from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper
from praxis_virtualcell.workflows.predict_delta_expression import build_runtime

_MODEL_BYTES = b"p6-test-only-dummy-model\n"
_MODEL_SHA = hashlib.sha256(_MODEL_BYTES).hexdigest()
_DUMMY_NAME = "test_only_dummy_predictor"
_DUMMY_WRAPPER = (
    "praxis_virtualcell.tests.test_capability_runtime.DummyPredictor"
)
_PACK_ROOT = (
    Path(__file__).parent / "fixtures" / "data_packs" / "valid_tiny"
)


class DummyPredictor(ModelWrapper):
    """Test-only plugin loaded exclusively from a temporary model card."""

    name = "unbound_test_dummy"

    def declare_scope(self) -> dict:
        return {
            "species": ["human"],
            "module": "genetic_hub",
            "task": ["predict_delta_expression"],
            "perturbation": ["gene"],
        }

    def run_prediction(self, model_input: dict) -> dict:
        assert self.capability_assets["model.bin"].endswith("model.bin")
        return {
            "prediction": {"delta": [0.25]},
            "uncertainty": {"method": "deterministic_fixture"},
            "evidence": ["test_only_dummy"],
        }


class MalformedPredictor(ModelWrapper):
    """Test-only plugin returning an invalid result object."""

    name = "unbound_test_malformed"

    def declare_scope(self) -> dict:
        return {}

    def run_prediction(self, model_input: dict) -> dict:
        return []  # type: ignore[return-value]


class WrongOutputPredictor(ModelWrapper):
    """Test-only plugin whose output contradicts its model card."""

    name = "unbound_test_wrong_output"

    def declare_scope(self) -> dict:
        return {}

    def run_prediction(self, model_input: dict) -> dict:
        return {
            "prediction": {"absolute_expression": [0.25]},
            "uncertainty": {"method": "deterministic_fixture"},
        }


class NonJsonPredictor(ModelWrapper):
    """Test-only plugin returning a non-JSON nested provenance value."""

    name = "unbound_test_non_json"

    def declare_scope(self) -> dict:
        return {}

    def run_prediction(self, model_input: dict) -> dict:
        return {
            "prediction": {"delta": [0.25]},
            "uncertainty": {"method": "deterministic_fixture"},
            "provenance": {"invalid": object()},
        }


class RaisingPredictor(ModelWrapper):
    """Test-only plugin failing during capability-bound construction."""

    name = "unbound_test_raising"

    def __init__(self) -> None:
        raise RuntimeError("test-only constructor failure")

    def declare_scope(self) -> dict:
        return {}

    def run_prediction(self, model_input: dict) -> dict:
        raise AssertionError("unreachable")


def _card() -> dict:
    return {
        "schema_version": "vc.model-card.v1",
        "name": _DUMMY_NAME,
        "type": "public_model",
        "species": ["human"],
        "taxon": ["NCBITaxon:9606"],
        "module": "genetic_hub",
        "modality": [{"name": "scRNA", "ontology_id": "EFO:0008913"}],
        "assay": ["EFO:0008913"],
        "cell_domain": {
            "cell_type_ids": [],
            "cell_type_names": ["K562"],
            "tissue_ids": [],
            "tissue_names": [],
            "allow_unspecified": False,
        },
        "perturbation": ["gene"],
        "task": "predict_delta_expression",
        "output": ["delta_expression"],
        "feature_namespace": [
            {
                "name": "EnsemblGene",
                "version": "GRCh38",
                "id_format": "ensembl_gene",
            }
        ],
        "representation": ["asset:text/csv"],
        "source": "cache:test-only",
        "license": "CC0-1.0",
        "status": "available",
        "wrapper": _DUMMY_WRAPPER,
        "version": "dummy-v1",
        "requires": [],
        "assets": [
            {
                "filename": "model.bin",
                "sha256": _MODEL_SHA,
                "media_type": "application/octet-stream",
                "source_note": "generated in pytest tmp_path",
            }
        ],
        "resources": {
            "python_dependencies": [],
            "required": ["cpu"],
        },
        "uncertainty": {
            "required": True,
            "methods": ["deterministic_fixture"],
            "calibrated": False,
        },
        "ood": {
            "action": "abstain",
            "dimensions": [
                "taxon",
                "modality",
                "assay",
                "cell_domain",
                "perturbation",
                "task",
                "output",
                "feature_namespace",
                "representation",
            ],
        },
        "reliability_policy": "test_only",
        "provenance": {
            "training_data": "none; deterministic test fixture",
            "distributable": True,
        },
    }


def _request_payload() -> dict:
    return {
        "schema_version": "vc.request.v2",
        "request_id": "p6-dummy",
        "species": {
            "schema_version": "vc.species-ref.v1",
            "taxonomy_id": "NCBITaxon:9606",
            "scientific_name": "Homo sapiens",
            "common_name": "human",
        },
        "cell_context": {
            "schema_version": "vc.cell-context.v1",
            "cell_type_name": "K562",
            "cell_type_id": None,
            "tissue_name": None,
            "tissue_id": None,
            "attributes": {},
        },
        "input_modality": {
            "schema_version": "vc.modality.v1",
            "name": "scRNA",
            "ontology_id": "EFO:0008913",
            "unit": None,
            "feature_namespace": "EnsemblGene",
        },
        "output_modality": {
            "schema_version": "vc.modality.v1",
            "name": "delta_expression",
            "ontology_id": None,
            "unit": None,
            "feature_namespace": "EnsemblGene",
        },
        "perturbation": {
            "schema_version": "vc.perturbation.v1",
            "kind": "gene",
            "targets": ["AHR"],
            "dose_value": None,
            "dose_unit": None,
            "timepoint": None,
        },
        "task": {
            "schema_version": "vc.task.v1",
            "task_type": "predict_delta_expression",
            "requested_outputs": ["delta_expression"],
        },
        "baseline_context": None,
        "metadata": {},
        "constraints": {},
    }


def _legacy_request(*, cell_type: str = "K562") -> VirtualCellRequest:
    return VirtualCellRequest.from_dict(
        {
            "request_id": "p6-dummy",
            "species": "human",
            "cell_type": cell_type,
            "perturbation_type": "gene",
            "perturbation_targets": ["AHR"],
            "input_modality": "scRNA",
            "output_modality": "delta_expression",
            "task_type": "predict_delta_expression",
        }
    )


def _write_registry(tmp_path: Path, card: dict) -> ModelZooRegistry:
    path = tmp_path / "registry.yaml"
    path.write_text(
        yaml.safe_dump({"models": {card["name"]: card}}, sort_keys=False),
        encoding="utf-8",
    )
    return ModelZooRegistry(registry_path=str(path))


def _pack_registry() -> PackRegistry:
    registry = PackRegistry()
    registry.register(_PACK_ROOT)
    return registry


def _environment(*, dependencies=(), resources=("cpu",)) -> EnvironmentSnapshot:
    return EnvironmentSnapshot.from_dict(
        {
            "schema_version": "vc.environment.v1",
            "python_dependencies": list(dependencies),
            "resources": list(resources),
        }
    )


def _cache_with_model(tmp_path: Path, *, payload: bytes = _MODEL_BYTES) -> ModelCache:
    cache = ModelCache(root=str(tmp_path / "cache"))
    path = cache.asset_path(_DUMMY_NAME, "model.bin")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return cache


def _registry_stack(tmp_path: Path, card: dict | None = None):
    card = copy.deepcopy(card or _card())
    zoo = _write_registry(tmp_path, card)
    packs = _pack_registry()
    cache = _cache_with_model(tmp_path)
    capabilities = CapabilityRegistry(zoo, cache)
    return card, zoo, packs, cache, capabilities


def test_model_card_has_complete_strict_contract_and_stable_fingerprint():
    card = ModelCard.from_dict(_card())

    assert card.schema_version == "vc.model-card.v1"
    assert card.taxon == ("NCBITaxon:9606",)
    assert card.modality[0].ontology_id == "EFO:0008913"
    assert card.assay == ("EFO:0008913",)
    assert card.cell_domain.cell_type_names == ("K562",)
    assert card.perturbation == ("gene",)
    assert card.task == "predict_delta_expression"
    assert card.output == ("delta_expression",)
    assert card.feature_namespace[0].name == "EnsemblGene"
    assert card.representation == ("asset:text/csv",)
    assert card.assets[0].sha256 == _MODEL_SHA
    assert card.resources.required == ("cpu",)
    assert card.uncertainty.methods == ("deterministic_fixture",)
    assert card.ood.action == "abstain"
    assert card.fingerprint() == ModelCard.from_dict(card.to_dict()).fingerprint()

    changed_version = copy.deepcopy(_card())
    changed_version["version"] = "dummy-v2"
    changed_asset = copy.deepcopy(_card())
    changed_asset["assets"][0]["sha256"] = hashlib.sha256(b"other").hexdigest()
    assert ModelCard.from_dict(changed_version).fingerprint() != card.fingerprint()
    assert ModelCard.from_dict(changed_asset).fingerprint() != card.fingerprint()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update({"unknown": True}),
        lambda value: value.pop("taxon"),
        lambda value: value.update({"taxon": ["human"]}),
        lambda value: value.update({"modality": []}),
        lambda value: value.update({"assay": []}),
        lambda value: value.update({"perturbation": ["gene", "gene"]}),
        lambda value: value.update({"output": []}),
        lambda value: value.update({"representation": []}),
        lambda value: value.update({"assets": [{"filename": "../x", "sha256": "0" * 64}]}),
        lambda value: value["assets"][0].update({"filename": "..\\outside"}),
        lambda value: value.update({"ood": {"action": "fallback", "dimensions": ["taxon"]}}),
        lambda value: value["ood"].update({"dimensions": ["taxon"]}),
        lambda value: value["cell_domain"].update({"allow_unspecified": 0}),
        lambda value: value["uncertainty"].update({"required": 1}),
    ],
)
def test_model_card_rejects_incomplete_ambiguous_or_noncanonical_contract(mutation):
    value = copy.deepcopy(_card())
    mutation(value)
    with pytest.raises(ValueError):
        ModelCard.from_dict(value)


def test_model_card_rejects_cache_path_escape_in_model_name():
    value = copy.deepcopy(_card())
    value["name"] = "../outside-cache"

    with pytest.raises(ValueError, match="name"):
        ModelCard.from_dict(value)


def test_self_trained_model_card_requires_complete_typed_training_card():
    value = copy.deepcopy(_card())
    value["type"] = "self_trained"
    value["training_card"] = {
        "training_data": "fixture",
        "split": "fixed",
        "baseline": "mean",
        "metrics": "not-an-object",
        "provenance": "fixture-only",
    }

    with pytest.raises(ValueError, match="training_card"):
        ModelCard.from_dict(value)


def test_model_zoo_rejects_duplicate_yaml_keys(tmp_path):
    path = tmp_path / "registry.yaml"
    path.write_text(
        "models:\n"
        "  duplicate:\n"
        "    name: one\n"
        "    name: two\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate"):
        ModelZooRegistry(registry_path=str(path))


def test_model_zoo_exposes_typed_card_without_mutable_normalization(tmp_path):
    raw = _card()
    zoo = _write_registry(tmp_path, raw)
    card = zoo.card(_DUMMY_NAME)

    assert isinstance(card, ModelCard)
    assert card.to_dict() == zoo.get(_DUMMY_NAME)
    assert zoo.capability_names() == [_DUMMY_NAME]
    with pytest.raises(TypeError):
        card.provenance["changed"] = True
    exported = zoo.get(_DUMMY_NAME)
    exported["status"] = "missing"
    assert zoo.get(_DUMMY_NAME)["status"] == "available"


def test_valid_request_pack_model_environment_produces_compatibility_report(tmp_path):
    _, _, packs, _, capabilities = _registry_stack(tmp_path)
    report = capabilities.evaluate(
        VirtualCellRequestV2.from_dict(_request_payload()),
        packs.record("tiny-human-scrna", "0.1.0"),
        _DUMMY_NAME,
        _environment(),
    )

    assert report.schema_version == "vc.compatibility-report.v1"
    assert report.pack_valid is True
    assert report.model_compatible is True
    assert report.environment_compatible is True
    assert report.assets_ready is True
    assert report.wrapper_ready is True
    assert report.executable is True
    assert report.scientifically_validated is False
    assert report.reasons == ()
    assert all(report.checks.values())
    assert len(report.model_fingerprint) == 64
    assert len(report.pack_fingerprint) == 64
    assert len(report.environment_fingerprint) == 64
    assert len(report.fingerprint()) == 64


def test_compatibility_and_plan_contracts_reject_malformed_bound_fingerprints(
    tmp_path,
):
    _, _, packs, _, capabilities = _registry_stack(tmp_path)
    plan = capabilities.plan(
        VirtualCellRequestV2.from_dict(_request_payload()),
        packs.record("tiny-human-scrna", "0.1.0"),
        _environment(),
    )
    bad_report = plan.reports[0].to_dict()
    bad_report["request_fingerprint"] = "not-a-sha256"
    bad_plan = plan.to_dict()
    bad_plan["pack_fingerprint"] = "not-a-sha256"

    with pytest.raises(ValueError, match="fingerprint"):
        type(plan.reports[0]).from_dict(bad_report)
    with pytest.raises(ValueError, match="fingerprint"):
        type(plan).from_dict(bad_plan)


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("species.taxonomy_id", "NCBITaxon:10090", "request.taxon"),
        ("input_modality.name", "protein", "request.modality"),
        ("input_modality.ontology_id", "EFO:9999999", "request.assay"),
        ("cell_context.cell_type_name", "HeLa", "request.cell_domain"),
        ("perturbation.kind", "drug", "request.perturbation"),
        ("task.task_type", "classify", "request.task"),
        ("output_modality.name", "state", "request.output"),
        ("input_modality.feature_namespace", "NCBIGene", "request.feature_namespace"),
    ],
)
def test_request_out_of_model_scope_fails_closed(tmp_path, field, value, reason):
    _, _, packs, _, capabilities = _registry_stack(tmp_path)
    payload = _request_payload()
    section, key = field.split(".")
    payload[section][key] = value
    if field == "task.task_type":
        payload["task"]["requested_outputs"] = []
    request = VirtualCellRequestV2.from_dict(payload)

    report = capabilities.evaluate(
        request,
        packs.record("tiny-human-scrna", "0.1.0"),
        _DUMMY_NAME,
        _environment(),
    )

    assert report.executable is False
    assert report.model_compatible is False
    assert reason in report.reasons


def test_duplicate_requested_outputs_fail_closed_without_silent_deduplication(tmp_path):
    _, _, packs, _, capabilities = _registry_stack(tmp_path)
    payload = _request_payload()
    payload["task"]["requested_outputs"] = [
        "delta_expression",
        "delta_expression",
    ]

    report = capabilities.evaluate(
        VirtualCellRequestV2.from_dict(payload),
        packs.record("tiny-human-scrna", "0.1.0"),
        _DUMMY_NAME,
        _environment(),
    )

    assert report.model_compatible is False
    assert report.executable is False
    assert "request.requested_outputs_duplicates" in report.reasons


def test_unspecified_tissue_cannot_enter_a_declared_tissue_domain(tmp_path):
    card = _card()
    card["cell_domain"]["tissue_names"] = ["bone marrow"]
    _, _, packs, _, capabilities = _registry_stack(tmp_path, card)
    pack = packs.record("tiny-human-scrna", "0.1.0")
    missing_tissue = capabilities.evaluate(
        VirtualCellRequestV2.from_dict(_request_payload()),
        pack,
        _DUMMY_NAME,
        _environment(),
    )
    payload = _request_payload()
    payload["cell_context"]["tissue_name"] = "bone marrow"
    declared_tissue = capabilities.evaluate(
        VirtualCellRequestV2.from_dict(payload),
        pack,
        _DUMMY_NAME,
        _environment(),
    )

    assert missing_tissue.model_compatible is False
    assert "request.cell_domain" in missing_tissue.reasons
    assert declared_tissue.model_compatible is True


def test_request_content_not_only_request_id_is_bound_into_plan_identity(tmp_path):
    _, _, packs, _, capabilities = _registry_stack(tmp_path)
    first_payload = _request_payload()
    second_payload = copy.deepcopy(first_payload)
    second_payload["perturbation"]["targets"] = ["TP53"]
    pack = packs.record("tiny-human-scrna", "0.1.0")

    first = capabilities.plan(
        VirtualCellRequestV2.from_dict(first_payload),
        pack,
        _environment(),
    )
    second = capabilities.plan(
        VirtualCellRequestV2.from_dict(second_payload),
        pack,
        _environment(),
    )

    assert first.request_id == second.request_id
    assert first.request_fingerprint != second.request_fingerprint
    assert first.plan_id != second.plan_id
    assert first.reports[0].request_fingerprint == first.request_fingerprint


def test_environment_detection_treats_missing_nested_module_as_absent(tmp_path):
    card = _card()
    card["resources"]["python_dependencies"] = ["missing_parent.child"]
    card["requires"] = ["missing_parent.child"]
    zoo = _write_registry(tmp_path, card)

    environment = EnvironmentSnapshot.detect((zoo.card(_DUMMY_NAME),))

    assert environment.python_dependencies == ()


def test_environment_detection_fails_closed_when_dependency_probe_raises(
    tmp_path,
    monkeypatch,
):
    card = _card()
    card["resources"]["python_dependencies"] = ["broken_dependency"]
    card["requires"] = ["broken_dependency"]
    zoo = _write_registry(tmp_path, card)

    def _broken_probe(_name):
        raise RuntimeError("test-only dependency probe failure")

    monkeypatch.setattr(
        "praxis_virtualcell.model_zoo.capability_registry.importlib.util.find_spec",
        _broken_probe,
    )

    environment = EnvironmentSnapshot.detect((zoo.card(_DUMMY_NAME),))

    assert environment.python_dependencies == ()


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("assay", ["EFO:9999999"], "pack.assay"),
        (
            "feature_namespace",
            [{"name": "NCBIGene", "version": "GRCh38", "id_format": "ncbi_gene_curie"}],
            "pack.feature_namespace",
        ),
        ("representation", ["matrix:X"], "pack.representation"),
    ],
)
def test_pack_out_of_model_scope_fails_closed(tmp_path, field, value, reason):
    card = _card()
    card[field] = value
    _, _, packs, _, capabilities = _registry_stack(tmp_path, card)

    report = capabilities.evaluate(
        VirtualCellRequestV2.from_dict(_request_payload()),
        packs.record("tiny-human-scrna", "0.1.0"),
        _DUMMY_NAME,
        _environment(),
    )

    assert report.executable is False
    assert report.model_compatible is False
    assert reason in report.reasons


def test_model_scope_cannot_hide_requested_modality_absent_from_pack(tmp_path):
    card = _card()
    card["modality"].append(
        {"name": "protein", "ontology_id": "PRAXISASSAY:protein"}
    )
    card["assay"].append("PRAXISASSAY:protein")
    _, _, packs, _, capabilities = _registry_stack(tmp_path, card)
    payload = _request_payload()
    payload["input_modality"]["name"] = "protein"
    payload["input_modality"]["ontology_id"] = "PRAXISASSAY:protein"

    report = capabilities.evaluate(
        VirtualCellRequestV2.from_dict(payload),
        packs.record("tiny-human-scrna", "0.1.0"),
        _DUMMY_NAME,
        _environment(),
    )

    assert report.model_compatible is False
    assert "request_pack.modality" in report.reasons


def test_model_scope_cannot_hide_requested_namespace_absent_from_pack(tmp_path):
    card = _card()
    card["feature_namespace"].append(
        {
            "name": "NCBIGene",
            "version": "GRCh38",
            "id_format": "ncbi_gene_curie",
        }
    )
    _, _, packs, _, capabilities = _registry_stack(tmp_path, card)
    payload = _request_payload()
    payload["input_modality"]["feature_namespace"] = "NCBIGene"

    report = capabilities.evaluate(
        VirtualCellRequestV2.from_dict(payload),
        packs.record("tiny-human-scrna", "0.1.0"),
        _DUMMY_NAME,
        _environment(),
    )

    assert report.model_compatible is False
    assert "request_pack.feature_namespace" in report.reasons


def test_missing_asset_fails_closed(tmp_path):
    card = _card()
    zoo = _write_registry(tmp_path, card)
    packs = _pack_registry()
    capabilities = CapabilityRegistry(zoo, ModelCache(root=str(tmp_path / "empty")))

    report = capabilities.evaluate(
        VirtualCellRequestV2.from_dict(_request_payload()),
        packs.record("tiny-human-scrna", "0.1.0"),
        _DUMMY_NAME,
        _environment(),
    )

    assert report.assets_ready is False
    assert report.environment_compatible is False
    assert report.executable is False
    assert "asset.missing:model.bin" in report.reasons


def test_bad_asset_hash_fails_closed(tmp_path):
    _, _, packs, _, capabilities = _registry_stack(tmp_path)
    cache = _cache_with_model(tmp_path, payload=b"tampered")
    capabilities = CapabilityRegistry(
        _write_registry(tmp_path, _card()),
        cache,
    )

    report = capabilities.evaluate(
        VirtualCellRequestV2.from_dict(_request_payload()),
        packs.record("tiny-human-scrna", "0.1.0"),
        _DUMMY_NAME,
        _environment(),
    )

    assert report.assets_ready is False
    assert report.executable is False
    assert "asset.sha256:model.bin" in report.reasons


def test_missing_dependency_and_resource_fail_closed(tmp_path):
    card = _card()
    card["resources"] = {
        "python_dependencies": ["definitely_missing_p6_dependency"],
        "required": ["cpu", "gpu"],
    }
    card["requires"] = ["definitely_missing_p6_dependency", "gpu"]
    _, _, packs, _, capabilities = _registry_stack(tmp_path, card)

    report = capabilities.evaluate(
        VirtualCellRequestV2.from_dict(_request_payload()),
        packs.record("tiny-human-scrna", "0.1.0"),
        _DUMMY_NAME,
        _environment(),
    )

    assert report.environment_compatible is False
    assert report.executable is False
    assert "environment.dependency:definitely_missing_p6_dependency" in report.reasons
    assert "environment.resource:gpu" in report.reasons


def test_wrapper_probe_failure_is_reported_instead_of_crashing(
    tmp_path,
    monkeypatch,
):
    _, _, packs, _, capabilities = _registry_stack(tmp_path)

    def _broken_wrapper_probe(_card):
        raise RuntimeError("test-only wrapper probe failure")

    monkeypatch.setattr(capabilities, "_wrapper_class", _broken_wrapper_probe)

    report = capabilities.evaluate(
        VirtualCellRequestV2.from_dict(_request_payload()),
        packs.record("tiny-human-scrna", "0.1.0"),
        _DUMMY_NAME,
        _environment(),
    )

    assert report.wrapper_ready is False
    assert report.environment_compatible is False
    assert report.executable is False
    assert "model.wrapper" in report.reasons


def test_runtime_environment_rejects_task_without_an_execution_adapter(tmp_path):
    card = _card()
    card["task"] = "growth"
    card["output"] = ["growth"]
    _, _, packs, _, capabilities = _registry_stack(tmp_path, card)
    payload = _request_payload()
    payload["task"]["task_type"] = "growth"
    payload["task"]["requested_outputs"] = ["growth"]
    payload["output_modality"]["name"] = "growth"

    report = capabilities.evaluate(
        VirtualCellRequestV2.from_dict(payload),
        packs.record("tiny-human-scrna", "0.1.0"),
        _DUMMY_NAME,
        _environment(),
    )

    assert report.model_compatible is True
    assert report.environment_compatible is False
    assert report.executable is False
    assert "environment.runtime_task:growth" in report.reasons
    assert "environment.runtime_output:growth" in report.reasons


def test_plan_is_deterministic_and_contains_only_executable_models(tmp_path):
    _, _, packs, _, capabilities = _registry_stack(tmp_path)
    request = VirtualCellRequestV2.from_dict(_request_payload())
    pack = packs.record("tiny-human-scrna", "0.1.0")
    environment = _environment()

    first = capabilities.plan(request, pack, environment)
    second = capabilities.plan(request, pack, environment)

    assert first == second
    assert first.schema_version == "vc.execution-plan.v1"
    assert first.executable is True
    assert [step.model_name for step in first.steps] == [_DUMMY_NAME]
    assert first.steps[0].agent_name == _DUMMY_NAME
    assert first.steps[0].asset_paths["model.bin"].endswith("model.bin")
    assert first.fingerprint() == second.fingerprint()


def test_plugin_delta_rejects_unrepresentable_integer_without_crashing(tmp_path):
    _, _, packs, _, capabilities = _registry_stack(tmp_path)
    plan = capabilities.plan(
        VirtualCellRequestV2.from_dict(_request_payload()),
        packs.record("tiny-human-scrna", "0.1.0"),
        _environment(),
    )
    predictor = capabilities.instantiate(plan.steps[0], plan.reports[0])

    status, reason = predictor._result_status(
        {
            "prediction": {"delta": [10**10000]},
            "uncertainty": {"method": "deterministic_fixture"},
        }
    )

    assert status == "rejected"
    assert reason == "prediction_contract_delta"


def test_instantiation_rejects_tampered_execution_step_asset_path(tmp_path):
    _, _, packs, _, capabilities = _registry_stack(tmp_path)
    plan = capabilities.plan(
        VirtualCellRequestV2.from_dict(_request_payload()),
        packs.record("tiny-human-scrna", "0.1.0"),
        _environment(),
    )
    value = plan.steps[0].to_dict()
    value["asset_paths"]["model.bin"] = "/tmp/unverified-model.bin"
    tampered = ExecutionStep.from_dict(value)

    with pytest.raises(ValueError, match="execution step"):
        capabilities.instantiate(tampered, plan.reports[0])


def test_instantiation_rechecks_asset_hash_after_planning(tmp_path):
    _, _, packs, cache, capabilities = _registry_stack(tmp_path)
    plan = capabilities.plan(
        VirtualCellRequestV2.from_dict(_request_payload()),
        packs.record("tiny-human-scrna", "0.1.0"),
        _environment(),
    )
    cache.asset_path(_DUMMY_NAME, "model.bin").write_bytes(b"tampered-after-plan")

    with pytest.raises(ValueError, match="asset"):
        capabilities.instantiate(plan.steps[0], plan.reports[0])


def test_incompatible_model_never_enters_execution_plan(tmp_path):
    _, _, packs, _, capabilities = _registry_stack(tmp_path)
    payload = _request_payload()
    payload["cell_context"]["cell_type_name"] = "HeLa"

    plan = capabilities.plan(
        VirtualCellRequestV2.from_dict(payload),
        packs.record("tiny-human-scrna", "0.1.0"),
        _environment(),
    )

    assert plan.executable is False
    assert plan.steps == ()
    assert plan.reports[0].executable is False
    assert "request.cell_domain" in plan.reports[0].reasons


def test_model_broker_message_emits_compatibility_and_prepared_plan(tmp_path):
    _, zoo, packs, cache, _ = _registry_stack(tmp_path)
    broker = ModelBrokerAgent(
        registry=zoo,
        cache=cache,
        pack_registry=packs,
        environment=_environment(),
    )
    bus = MessageBus()
    broker.handle(
        AgentMessage(
            "p6-plan",
            "client",
            "ModelBrokerAgent",
            "execution_plan_request",
            {
                "request": _request_payload(),
                "pack_id": "tiny-human-scrna",
                "pack_version": "0.1.0",
            },
            "t1",
        ),
        bus,
    )

    result = bus.latest("execution_plan_ready")
    assert result is not None
    assert result.payload["execution_plan"]["executable"] is True
    assert result.payload["execution_plan"]["steps"][0]["model_name"] == _DUMMY_NAME
    prepared = broker.take_prepared(result.payload["execution_plan"]["plan_id"])
    assert len(prepared) == 1
    assert prepared[0].name == _DUMMY_NAME
    assert broker.take_prepared(result.payload["execution_plan"]["plan_id"]) == []


def test_model_broker_removes_step_when_wrapper_construction_fails(tmp_path):
    card = _card()
    card["name"] = "test_only_raising_predictor"
    card["wrapper"] = (
        "praxis_virtualcell.tests.test_capability_runtime.RaisingPredictor"
    )
    card["assets"] = []
    zoo = _write_registry(tmp_path, card)
    packs = _pack_registry()
    broker = ModelBrokerAgent(
        registry=zoo,
        cache=ModelCache(root=str(tmp_path / "empty")),
        pack_registry=packs,
        environment=_environment(),
    )
    bus = MessageBus()

    broker.handle(
        AgentMessage(
            "p6-raising",
            "client",
            "ModelBrokerAgent",
            "execution_plan_request",
            {
                "request": _request_payload(),
                "pack_id": "tiny-human-scrna",
                "pack_version": "0.1.0",
            },
            "t1",
        ),
        bus,
    )

    plan = bus.latest("execution_plan_ready").payload["execution_plan"]
    assert plan["executable"] is False
    assert plan["steps"] == []
    assert "model.wrapper_initialization" in plan["reports"][0]["reasons"]
    assert broker.take_prepared(plan["plan_id"]) == []


def test_build_runtime_registers_broker_once():
    runtime = build_runtime()
    assert isinstance(runtime._agents["ModelBrokerAgent"], ModelBrokerAgent)


def test_dummy_plugin_runs_without_model_specific_runtime_or_legacy_dispatch_edits(tmp_path):
    _, zoo, packs, cache, _ = _registry_stack(tmp_path)
    runtime = build_runtime(
        model_registry=zoo,
        model_cache=cache,
        pack_registry=packs,
        environment=_environment(),
    )

    report = runtime.run_workflow(
        _legacy_request(),
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert report["abstain"] is False
    assert report["prediction"] == {"delta": [0.25]}
    assert report["models_used"] == [_DUMMY_NAME]
    assert report["provenance"]["execution_plan"]["steps"][0]["model_name"] == _DUMMY_NAME
    assert report["provenance"]["compatibility_reports"][0]["executable"] is True
    assert runtime.bus.has_message_type("execution_plan_request")
    assert runtime.bus.has_message_type("execution_plan_ready")

    from praxis_virtualcell.agents import route_table
    from praxis_virtualcell.predictors import case_dispatch
    from praxis_virtualcell.workflows import predict_delta_expression

    for source in (
        inspect.getsource(predict_delta_expression.build_runtime),
        inspect.getsource(route_table),
        inspect.getsource(case_dispatch),
    ):
        assert _DUMMY_NAME not in source


def test_pack_aware_runtime_never_falls_back_to_mock_when_asset_missing(tmp_path):
    card = _card()
    zoo = _write_registry(tmp_path, card)
    packs = _pack_registry()
    runtime = build_runtime(
        model_registry=zoo,
        model_cache=ModelCache(root=str(tmp_path / "empty")),
        pack_registry=packs,
        environment=_environment(),
    )

    report = runtime.run_workflow(
        _legacy_request(),
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert report["abstain"] is True
    assert report["prediction"] is None
    assert report["models_used"] == []
    assert not any(name.startswith("Mock") for name in report["models_rejected"])
    reasons = report["provenance"]["compatibility_reports"][0]["reasons"]
    assert "asset.missing:model.bin" in reasons


def test_pack_aware_runtime_never_falls_back_to_mock_when_out_of_scope(tmp_path):
    _, zoo, packs, cache, _ = _registry_stack(tmp_path)
    runtime = build_runtime(
        model_registry=zoo,
        model_cache=cache,
        pack_registry=packs,
        environment=_environment(),
    )

    report = runtime.run_workflow(
        _legacy_request(cell_type="HeLa"),
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert report["abstain"] is True
    assert report["prediction"] is None
    assert report["models_used"] == []
    assert report["provenance"]["execution_plan"]["steps"] == []
    assert "request.cell_domain" in (
        report["provenance"]["compatibility_reports"][0]["reasons"]
    )


def test_malformed_plugin_output_fails_closed_instead_of_crashing_runtime(tmp_path):
    card = _card()
    card["name"] = "test_only_malformed_predictor"
    card["wrapper"] = (
        "praxis_virtualcell.tests.test_capability_runtime.MalformedPredictor"
    )
    card["assets"] = []
    zoo = _write_registry(tmp_path, card)
    packs = _pack_registry()
    runtime = build_runtime(
        model_registry=zoo,
        model_cache=ModelCache(root=str(tmp_path / "empty")),
        pack_registry=packs,
        environment=_environment(),
    )

    report = runtime.run_workflow(
        _legacy_request(),
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert report["abstain"] is True
    assert report["prediction"] is None
    assert report["models_used"] == []
    assert report["models_failed"] == ["test_only_malformed_predictor"]


def test_plugin_output_shape_must_match_declared_delta_contract(tmp_path):
    card = _card()
    card["name"] = "test_only_wrong_output_predictor"
    card["wrapper"] = (
        "praxis_virtualcell.tests.test_capability_runtime.WrongOutputPredictor"
    )
    card["assets"] = []
    zoo = _write_registry(tmp_path, card)
    packs = _pack_registry()
    runtime = build_runtime(
        model_registry=zoo,
        model_cache=ModelCache(root=str(tmp_path / "empty")),
        pack_registry=packs,
        environment=_environment(),
    )

    report = runtime.run_workflow(
        _legacy_request(),
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert report["abstain"] is True
    assert report["models_used"] == []
    assert report["models_rejected"] == ["test_only_wrong_output_predictor"]


def test_plugin_nested_non_json_output_fails_closed(tmp_path):
    card = _card()
    card["name"] = "test_only_non_json_predictor"
    card["wrapper"] = (
        "praxis_virtualcell.tests.test_capability_runtime.NonJsonPredictor"
    )
    card["assets"] = []
    zoo = _write_registry(tmp_path, card)
    packs = _pack_registry()
    runtime = build_runtime(
        model_registry=zoo,
        model_cache=ModelCache(root=str(tmp_path / "empty")),
        pack_registry=packs,
        environment=_environment(),
    )

    report = runtime.run_workflow(
        _legacy_request(),
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert report["abstain"] is True
    assert report["prediction"] is None
    assert report["models_used"] == []
    assert report["models_failed"] == ["test_only_non_json_predictor"]


def test_no_pack_is_explicit_legacy_adapter_and_does_not_consult_broker():
    runtime = build_runtime()
    report = runtime.run_workflow(_legacy_request())

    assert report["models_used"]
    assert not runtime.bus.has_message_type("execution_plan_request")
    assert "execution_plan" not in report["provenance"]


def test_partial_pack_identity_is_rejected_before_any_model_runs(tmp_path):
    _, zoo, packs, cache, _ = _registry_stack(tmp_path)
    runtime = build_runtime(
        model_registry=zoo,
        model_cache=cache,
        pack_registry=packs,
        environment=_environment(),
    )

    with pytest.raises(ValueError, match="pack_id and pack_version"):
        runtime.run_workflow(_legacy_request(), pack_id="tiny-human-scrna")
