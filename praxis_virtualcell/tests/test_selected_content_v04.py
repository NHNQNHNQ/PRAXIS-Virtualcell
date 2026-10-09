"""Generic v0.4 selected-content contracts for direct-v2 input preparation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Clock, IdGen, RuntimeConfig
from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2
from praxis_virtualcell.core.runtime import AgentRuntime
from praxis_virtualcell.data_packs.errors import PackManifestError, PackRegistryError
from praxis_virtualcell.data_packs.registry import (
    PackRegistry,
    PreparedPackViewV2,
    SelectedContentRequestV1,
    validate_selected_content_receipt_binding,
)
from praxis_virtualcell.data_packs.selected_content import PreparedSelectedContentV1
from praxis_virtualcell.data_packs.validator import validate_pack
from praxis_virtualcell.io.job_store import JobStore
from praxis_virtualcell.model_zoo.adapter_sdk import (
    AdapterExecutionProvenance,
    AdapterInputContract,
    AdapterInputReceipt,
    AdapterInputReceiptV2,
    AdapterOutputContract,
    AdapterOutputEnvelope,
    AdapterRegistry,
    PreparedAdapterInput,
    VirtualCellModelAdapter,
)
from praxis_virtualcell.model_zoo.cache import ModelCache
from praxis_virtualcell.model_zoo.wrapper_registry import WrapperRegistry
from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper
from praxis_virtualcell.tests.test_capability_runtime import (
    _MODEL_BYTES,
    _TEST_ARTIFACT_SNAPSHOT_BUDGET,
    _card,
    _v2_registry_and_environment,
    _write_registry,
)
from praxis_virtualcell.workflows.submit_job import submit_direct_v2_job

_TAXON = "NCBITaxon:999999999"
_ASSEMBLY = "GCF_000001405.40"
_FEATURES = ("ENSG00000000001", "ENSG00000000002")
_MODEL_NAME = "test_only_selected_vector"


def _write_pack(root: Path) -> None:
    asset = root / "assets" / "profile.csv"
    asset.parent.mkdir(parents=True)
    asset.write_text(
        "record_id,split,ENSG00000000001,ENSG00000000002\ncontrol-1,train,0.0,1.0\nprofile-1,test,1.25,-0.5\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "vc.pack.v0.4",
        "pack_id": "test-only-selected-vector",
        "pack_version": "1.0.0",
        "taxon": {"ontology_id": _TAXON, "scientific_name": "test-only organism"},
        "assembly": {"name": "test-assembly", "accession": _ASSEMBLY},
        "identity": {"observation_key": "record_id", "feature_key": "value_columns"},
        "modality": {"name": "generic_profile", "ontology_id": "EFO:0000001"},
        "feature_namespace": {"name": "EnsemblGene", "version": _ASSEMBLY},
        "feature_semantics": {"id_source": "value_columns", "id_format": "ensembl_gene"},
        "assets": [
            {
                "id": "profile",
                "path": "assets/profile.csv",
                "media_type": "text/csv",
                "sha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
                "size_bytes": asset.stat().st_size,
            }
        ],
        "split": {
            "field": "split",
            "strategy": "predefined",
            "values": ["train", "test"],
            "name": "record_split",
            "leakage_guard": ["record_id"],
        },
        "selected_content": {
            "schema_version": "vc.pack-selected-csv.v1",
            "asset": "profile",
            "encoding": "utf-8",
            "delimiter": ",",
            "representation": "csv.record-vector.v1",
            "record_id_column": "record_id",
            "split_column": "split",
            "value_columns": list(_FEATURES),
            "unit": "count",
            "shape": [2, 2],
        },
        "provenance": {"source": "synthetic fixture", "created_by": "pytest", "citation": "none"},
        "license": {"id": "CC0-1.0", "name": "CC0 1.0 Universal"},
    }
    (root / "manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")


def _add_unrelated_declared_asset(root: Path) -> Path:
    asset = root / "assets" / "unrelated.csv"
    asset.write_text("fixture\nnot-a-runtime-input\n", encoding="utf-8")
    manifest_path = root / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"].append(
        {
            "id": "unrelated",
            "path": "assets/unrelated.csv",
            "media_type": "text/csv",
            "sha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
            "size_bytes": asset.stat().st_size,
        }
    )
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return asset


def _request() -> VirtualCellRequestV2:
    return VirtualCellRequestV2.from_dict(
        {
            "schema_version": "vc.request.v2",
            "request_id": "selected-content-v04",
            "species": {
                "schema_version": "vc.species-ref.v1",
                "taxonomy_id": _TAXON,
                "scientific_name": "test-only organism",
            },
            "cell_context": {"schema_version": "vc.cell-context.v1", "attributes": {}},
            "input_modality": {
                "schema_version": "vc.modality.v1",
                "name": "generic_profile",
                "ontology_id": "EFO:0000001",
                "unit": "count",
                "feature_namespace": "EnsemblGene",
            },
            "output_modality": {
                "schema_version": "vc.modality.v1",
                "name": "generic_score",
                "unit": "dimensionless",
            },
            "perturbation": {
                "schema_version": "vc.perturbation.v1",
                "kind": "gene",
                "targets": ["ENSG00000000001"],
            },
            "task": {
                "schema_version": "vc.task.v1",
                "task_type": "predict_generic_score",
                "requested_outputs": ["generic_score"],
            },
            "pack_input": {
                "schema_version": "vc.pack-input-selector.v1",
                "record_id": "profile-1",
            },
            "metadata": {},
            "constraints": {},
        }
    )


def _selector(
    *,
    model_id: str = _MODEL_NAME,
    model_version: str = "1.0.0",
) -> SelectedContentRequestV1:
    return SelectedContentRequestV1.from_dict(
        {
            "schema_version": "vc.selected-content-request.v1",
            "record_id": "profile-1",
            "feature_contract": {
                "schema_version": "vc.model-feature-contract.v1",
                "model_id": model_id,
                "model_version": model_version,
                "taxonomy_id": _TAXON,
                "assembly_accession": _ASSEMBLY,
                "modality": "generic_profile",
                "feature_namespace": {"name": "EnsemblGene", "version": _ASSEMBLY},
                "feature_id_format": "ensembl_gene",
                "feature_ids": list(_FEATURES),
                "reorder": False,
                "drop": [],
                "fill": [],
            },
        }
    )


def _with_forged_receipt(
    content: PreparedSelectedContentV1,
    receipt,
) -> PreparedSelectedContentV1:
    model_input = dict(content.model_input)
    model_input["selected_content_receipt_fingerprint"] = receipt.fingerprint()
    return replace(content, receipt=receipt, model_input=model_input)


def _record_split_fingerprint(receipt, record_split: str) -> str:
    def field(name: str):
        return receipt[name] if isinstance(receipt, dict) else getattr(receipt, name)

    return hashlib.sha256(
        json.dumps(
            {
                "schema_version": "vc.selected-content-record-split.v1",
                "selection_fingerprint": field("selection_fingerprint"),
                "split_name": field("split_name"),
                "record_split": record_split,
                "split_fingerprint": field("split_fingerprint"),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def test_v04_materializes_one_exact_hashed_record_without_leaking_values_or_paths(
    tmp_path: Path,
) -> None:
    root = tmp_path / "pack"
    _write_pack(root)
    packs = PackRegistry()
    packs.register(root)
    record = packs.record("test-only-selected-vector", "1.0.0")
    view = packs.issue_execution_view(record)
    assert type(view) is PreparedPackViewV2

    content = packs.materialize_selected_content(
        record,
        request=_request(),
        selection=_selector(),
        pack_view=view,
    )

    assert content.values == (1.25, -0.5)
    assert content.alignment_report.source_shape == (1, 2)
    assert content.alignment_report.target_shape == (2,)
    assert content.receipt.source_asset_id == "profile"
    assert content.receipt.observation_count == 1
    assert content.receipt.model_id == _MODEL_NAME
    assert content.receipt.model_version == "1.0.0"
    assert content.receipt.split_name == "record_split"
    assert content.receipt.record_split == "test"
    assert validate_selected_content_receipt_binding(content.receipt, view.receipt)
    forged = content.receipt.model_copy(update={"source_asset_sha256": "0" * 64})
    assert not validate_selected_content_receipt_binding(forged, view.receipt)
    public = json.dumps(content.receipt.to_dict(), sort_keys=True)
    assert "profile-1" not in public
    assert "1.25" not in public
    assert str(root) not in public
    assert "assets/profile.csv" not in public


def test_v04_selector_rejects_free_payload_or_non_exact_record() -> None:
    value = _selector().to_dict()
    value["values"] = [999.0]
    with pytest.raises(ValueError, match="SelectedContentRequestV1"):
        SelectedContentRequestV1.from_dict(value)

    value = _selector().to_dict()
    value["record_id"] = "unknown"
    selector = SelectedContentRequestV1.from_dict(value)
    assert selector.record_id == "unknown"


@pytest.mark.parametrize(
    "contents, reason",
    [
        ("unexpected,header\nvalue,1\n", "header"),
        (
            "record_id,split,ENSG00000000001,ENSG00000000002\ncontrol-1,train,0.0,1.0\nprofile-1,test,nan,-0.5\n",
            "finite vector",
        ),
        (
            "record_id,split,ENSG00000000001,ENSG00000000002\nprofile-1,train,0.0,1.0\nprofile-1,test,1.25,-0.5\n",
            "duplicate record",
        ),
        (
            "record_id,split,ENSG00000000001,ENSG00000000002\ncontrol-1,train,0.0,1.0\nprofile-1,test,1_000,-0.5\n",
            "finite vector",
        ),
        (
            'record_id,split,ENSG00000000001,ENSG00000000002\ncontrol-1,train,0.0,1.0\nprofile-1,test,"1.25",-0.5\n',
            "unquoted",
        ),
    ],
)
def test_v04_registration_rejects_a_hashed_but_malformed_csv(
    tmp_path: Path,
    contents: str,
    reason: str,
) -> None:
    root = tmp_path / "pack"
    _write_pack(root)
    asset = root / "assets" / "profile.csv"
    asset.write_text(contents, encoding="utf-8")
    manifest_path = root / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"][0]["sha256"] = hashlib.sha256(asset.read_bytes()).hexdigest()
    manifest["assets"][0]["size_bytes"] = asset.stat().st_size
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

    with pytest.raises(PackRegistryError, match=reason):
        validate_pack(root)
    with pytest.raises(PackRegistryError, match=reason):
        PackRegistry().register(root)


def test_v04_requires_the_record_key_as_its_only_leakage_guard(tmp_path: Path) -> None:
    root = tmp_path / "pack"
    _write_pack(root)
    manifest_path = root / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["split"]["leakage_guard"] = ["unbound-group"]
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

    with pytest.raises(PackManifestError, match="leakage_guard"):
        PackRegistry().register(root)


class _VectorAdapter(VirtualCellModelAdapter):
    adapter_id = "test-only-selected-vector"
    version = "1.0.0"
    input_contract = AdapterInputContract(
        schema_version="vc.adapter-input-contract.v1",
        task="predict_generic_score",
        output="generic_score",
        value_type="float",
        shape=(2,),
        unit="count",
        pack_data_required=True,
        alignment_required=True,
    )
    output_contract = AdapterOutputContract(
        schema_version="vc.adapter-output-contract.v1",
        task="predict_generic_score",
        output="generic_score",
        value_type="float",
        shape=(1,),
        unit="dimensionless",
        uncertainty_required=False,
        ood_required=False,
        abstain_allowed=True,
    )

    def __init__(self) -> None:
        self.prepare_calls = 0
        self.seen_content = None

    def select_content(self, request, *, pack=None, compatibility_report=None, **kwargs):
        assert type(pack) is PreparedPackViewV2
        assert not hasattr(pack, "root")
        assert compatibility_report is not None
        assert not kwargs
        return _selector()

    def prepare_input(self, request, *, pack=None, compatibility_report=None, **kwargs):
        self.prepare_calls += 1
        content = kwargs.pop("selected_content", None)
        assert type(pack) is PreparedPackViewV2
        assert type(content) is PreparedSelectedContentV1
        assert not hasattr(content, "root")
        assert not kwargs
        self.seen_content = content
        return PreparedAdapterInput(
            schema_version="vc.prepared-adapter-input.v1",
            adapter_fingerprint=self.fingerprint(),
            input_contract_fingerprint=self.input_contract.fingerprint(),
            task=self.input_contract.task,
            output=self.input_contract.output,
            request_fingerprint=hashlib.sha256(
                json.dumps(request.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            pack_fingerprint=pack.fingerprint,
            compatibility_fingerprint=compatibility_report.fingerprint(),
            model_input=content.model_input,
            values=content.values,
            shape=(len(content.values),),
            unit=content.receipt.unit,
            feature_contract=content.feature_contract,
            feature_contract_fingerprint=content.feature_contract.fingerprint(),
            alignment_report=content.alignment_report,
        )

    def adapt_output(self, prepared, raw_output):
        assert raw_output == {"value": 0.75}
        return AdapterOutputEnvelope(
            schema_version="vc.adapter-output-envelope.v1",
            task=self.output_contract.task,
            output=self.output_contract.output,
            shape=(1,),
            unit=self.output_contract.unit,
            values=(0.75,),
            uncertainty=None,
            ood=None,
            abstain=False,
            abstain_reasons=(),
            projection_metadata={"fixture": "selected-content-v04"},
            provenance=AdapterExecutionProvenance(
                schema_version="vc.adapter-execution-provenance.v1",
                adapter_fingerprint=self.fingerprint(),
                input_fingerprints=(prepared.fingerprint(),),
                input_contract_fingerprint=self.input_contract.fingerprint(),
                output_contract_fingerprint=self.output_contract.fingerprint(),
                request_fingerprints=(prepared.request_fingerprint,),
                pack_fingerprints=(prepared.pack_fingerprint,),
                compatibility_fingerprints=(prepared.compatibility_fingerprint,),
            ),
        )


class _WrongModelContractAdapter(_VectorAdapter):
    def select_content(self, request, *, pack=None, compatibility_report=None, **kwargs):
        return _selector(model_id="other-generic-model", model_version="9.9.9")


class _PathlessCompatibilityVectorAdapter(_VectorAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.selector_asset_paths: dict[str, str] | None = None
        self.prepared_asset_paths: dict[str, str] | None = None

    def select_content(self, request, *, pack=None, compatibility_report=None, **kwargs):
        self.selector_asset_paths = dict(compatibility_report.asset_paths)
        return super().select_content(
            request,
            pack=pack,
            compatibility_report=compatibility_report,
            **kwargs,
        )

    def prepare_input(self, request, *, pack=None, compatibility_report=None, **kwargs):
        self.prepared_asset_paths = dict(compatibility_report.asset_paths)
        return super().prepare_input(
            request,
            pack=pack,
            compatibility_report=compatibility_report,
            **kwargs,
        )


class _VectorWrapper(ModelWrapper):
    run_calls = 0
    artifact_snapshot_supported = True

    def __init__(self) -> None:
        self.calls = 0

    def declare_scope(self) -> dict:
        return {}

    def run_prediction(self, model_input: dict) -> dict:
        self.calls += 1
        type(self).run_calls += 1
        assert model_input["values"] == (1.25, -0.5)
        assert model_input["feature_ids"] == _FEATURES
        return {"value": 0.75}


def _direct_v04_runtime(
    tmp_path: Path,
    adapter: _VectorAdapter,
    *,
    extra_asset: bool = False,
) -> tuple[AgentRuntime, object, Path]:
    root = tmp_path / "pack"
    _write_pack(root)
    if extra_asset:
        _add_unrelated_declared_asset(root)
    packs = PackRegistry()
    packs.register(root)
    pack = packs.record("test-only-selected-vector", "1.0.0")
    card = _card()
    card.update(
        {
            "name": _MODEL_NAME,
            "species": ["test-only"],
            "taxon": [_TAXON],
            "module": "genetic_hub",
            "modality": [{"name": "generic_profile", "ontology_id": "EFO:0000001"}],
            "assay": ["EFO:0000001"],
            "cell_domain": {
                "cell_type_ids": [],
                "cell_type_names": [],
                "tissue_ids": [],
                "tissue_names": [],
                "allow_unspecified": True,
            },
            "task": "predict_generic_score",
            "output": ["generic_score"],
            "feature_namespace": [{"name": "EnsemblGene", "version": _ASSEMBLY, "id_format": "ensembl_gene"}],
            "wrapper": f"{__name__}._VectorWrapper",
            "version": "1.0.0",
        }
    )
    registry_v2, environment = _v2_registry_and_environment(
        card,
        pack.fingerprint,
        promoted=False,
        runtime_adapter=adapter,
        research_execution_authorized=True,
        runtime_tasks=("predict_generic_score",),
        runtime_outputs=("generic_score",),
        snapshot_budget=_TEST_ARTIFACT_SNAPSHOT_BUDGET,
    )
    zoo = _write_registry(tmp_path, card, registry_v2=registry_v2)
    cache = ModelCache(root=str(tmp_path / "cache"))
    asset_path = cache.asset_path(card["name"], "model.bin")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(_MODEL_BYTES)
    wrappers = WrapperRegistry()
    wrappers.register(card["wrapper"], _VectorWrapper)
    runtime = AgentRuntime(RuntimeConfig(), bus=MessageBus(), clock=Clock(), idgen=IdGen())
    runtime.register_agent(
        ModelBrokerAgent(
            registry=zoo,
            cache=cache,
            pack_registry=packs,
            environment=environment,
            adapter_registry=AdapterRegistry([adapter]),
            wrapper_registry=wrappers,
        )
    )
    _VectorWrapper.run_calls = 0
    return runtime, pack, root / "assets" / "profile.csv"


def test_direct_v2_executes_only_core_materialized_v04_content(tmp_path: Path) -> None:
    adapter = _VectorAdapter()
    runtime, pack, _ = _direct_v04_runtime(tmp_path, adapter)

    report = runtime.run_workflow_v2(
        _request(),
        pack_id=pack.manifest.pack_id,
        pack_version=pack.manifest.pack_version,
    )

    assert report["abstain"] is False
    assert adapter.prepare_calls == 1
    assert adapter.seen_content.values == (1.25, -0.5)
    receipt = report["provenance"]["adapter_input_receipts"][_MODEL_NAME]
    assert receipt["schema_version"] == "vc.adapter-input-receipt.v2"
    public = json.dumps(receipt, sort_keys=True)
    assert "profile-1" not in public
    assert "1.25" not in public


def test_direct_v2_data_required_adapter_never_receives_compatibility_asset_paths(tmp_path: Path) -> None:
    adapter = _PathlessCompatibilityVectorAdapter()
    runtime, pack, _ = _direct_v04_runtime(tmp_path, adapter)

    report = runtime.run_workflow_v2(
        _request(),
        pack_id=pack.manifest.pack_id,
        pack_version=pack.manifest.pack_version,
    )

    raw_plan = runtime.bus.latest("execution_plan_ready").payload["execution_plan"]
    assert raw_plan["reports"][0]["asset_paths"]
    assert report["abstain"] is False
    assert adapter.selector_asset_paths == {}
    assert adapter.prepared_asset_paths == {}


def test_direct_v2_v04_requires_an_exact_request_record_selector(tmp_path: Path) -> None:
    adapter = _VectorAdapter()
    runtime, pack, _ = _direct_v04_runtime(tmp_path, adapter)

    report = runtime.run_workflow_v2(
        _request().model_copy(update={"pack_input": None}),
        pack_id=pack.manifest.pack_id,
        pack_version=pack.manifest.pack_version,
    )

    assert report["abstain"] is True
    assert "pack.selected_content_unavailable" in report["abstain_reasons"]
    assert adapter.prepare_calls == 0
    assert _VectorWrapper.run_calls == 0


class _DriftAfterPrepareAdapter(_VectorAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.asset_to_drift: Path | None = None

    def prepare_input(self, *args, **kwargs):
        prepared = super().prepare_input(*args, **kwargs)
        assert self.asset_to_drift is not None
        self.asset_to_drift.write_text(
            "record_id,split,ENSG00000000001,ENSG00000000002\ncontrol-1,train,0.0,1.0\nprofile-1,test,9.0,-0.5\n",
            encoding="utf-8",
        )
        return prepared


class _TamperingAdapter(_VectorAdapter):
    def prepare_input(self, *args, **kwargs):
        prepared = super().prepare_input(*args, **kwargs)
        return prepared.model_copy(update={"values": (9.0, -0.5)})


@pytest.mark.parametrize("adapter_type", [_DriftAfterPrepareAdapter, _TamperingAdapter])
def test_direct_v2_v04_rejects_pack_or_adapter_drift_before_wrapper_execution(
    tmp_path: Path,
    adapter_type,
) -> None:
    adapter = adapter_type()
    runtime, pack, asset = _direct_v04_runtime(tmp_path, adapter)
    if isinstance(adapter, _DriftAfterPrepareAdapter):
        adapter.asset_to_drift = asset

    report = runtime.run_workflow_v2(
        _request(),
        pack_id=pack.manifest.pack_id,
        pack_version=pack.manifest.pack_version,
    )

    assert report["abstain"] is True
    assert "pack.selected_content_unavailable" in report["abstain_reasons"]
    assert adapter.prepare_calls == 1
    assert _VectorWrapper.run_calls == 0


def test_direct_v2_v04_rejects_a_feature_contract_for_another_model(tmp_path: Path) -> None:
    adapter = _WrongModelContractAdapter()
    runtime, pack, _ = _direct_v04_runtime(tmp_path, adapter)

    report = runtime.run_workflow_v2(
        _request(),
        pack_id=pack.manifest.pack_id,
        pack_version=pack.manifest.pack_version,
    )

    assert report["abstain"] is True
    assert "pack.selected_content_unavailable" in report["abstain_reasons"]
    assert adapter.prepare_calls == 0
    assert _VectorWrapper.run_calls == 0


def test_direct_v2_v04_runtime_rejects_private_data_execution_without_content(
    tmp_path: Path,
) -> None:
    adapter = _VectorAdapter()
    runtime, pack, _ = _direct_v04_runtime(tmp_path, adapter)
    broker = runtime._agents["ModelBrokerAgent"]
    dispatch = runtime._dispatch_collect_direct_v2

    def forge_v1_execution(message):
        planned = dispatch(message)
        plan_id = planned.payload["execution_plan"]["plan_id"]
        execution = broker._prepared_v2[plan_id][_MODEL_NAME]
        planned.payload["adapter_input_receipts"][_MODEL_NAME] = AdapterInputReceipt.from_prepared(
            execution["adapter_input"]
        ).to_dict()
        execution.pop("selected_content")
        return planned

    runtime._dispatch_collect_direct_v2 = forge_v1_execution
    report = runtime.run_workflow_v2(
        _request(),
        pack_id=pack.manifest.pack_id,
        pack_version=pack.manifest.pack_version,
    )

    assert report["abstain"] is True
    assert "prepared_execution_invalid" in report["abstain_reasons"]
    assert _VectorWrapper.run_calls == 0


def test_direct_v2_v04_runtime_rejects_a_selected_receipt_outside_the_pack_view(
    tmp_path: Path,
) -> None:
    adapter = _VectorAdapter()
    runtime, pack, _ = _direct_v04_runtime(tmp_path, adapter)
    broker = runtime._agents["ModelBrokerAgent"]
    dispatch = runtime._dispatch_collect_direct_v2

    def forge_asset_receipt(message):
        planned = dispatch(message)
        plan_id = planned.payload["execution_plan"]["plan_id"]
        execution = broker._prepared_v2[plan_id][_MODEL_NAME]
        content = execution["selected_content"]
        forged = _with_forged_receipt(
            content,
            content.receipt.model_copy(update={"source_asset_sha256": "0" * 64}),
        )
        execution["selected_content"] = forged
        execution["adapter_input"] = execution["adapter_input"].model_copy(update={"model_input": forged.model_input})
        planned.payload["adapter_input_receipts"][_MODEL_NAME] = AdapterInputReceiptV2.from_prepared(
            execution["adapter_input"], forged
        ).to_dict()
        return planned

    runtime._dispatch_collect_direct_v2 = forge_asset_receipt
    report = runtime.run_workflow_v2(
        _request(),
        pack_id=pack.manifest.pack_id,
        pack_version=pack.manifest.pack_version,
    )

    assert report["abstain"] is True
    assert "prepared_execution_invalid" in report["abstain_reasons"]
    assert _VectorWrapper.run_calls == 0


def test_direct_v2_v04_runtime_rejects_a_tampered_selected_record_split(
    tmp_path: Path,
) -> None:
    adapter = _VectorAdapter()
    runtime, pack, _ = _direct_v04_runtime(tmp_path, adapter)
    broker = runtime._agents["ModelBrokerAgent"]
    dispatch = runtime._dispatch_collect_direct_v2

    def forge_split_receipt(message):
        planned = dispatch(message)
        plan_id = planned.payload["execution_plan"]["plan_id"]
        execution = broker._prepared_v2[plan_id][_MODEL_NAME]
        content = execution["selected_content"]
        forged = _with_forged_receipt(
            content,
            content.receipt.model_copy(
                update={
                    "record_split": "train",
                    "record_split_fingerprint": _record_split_fingerprint(
                        content.receipt,
                        "train",
                    ),
                }
            ),
        )
        execution["selected_content"] = forged
        execution["adapter_input"] = execution["adapter_input"].model_copy(update={"model_input": forged.model_input})
        planned.payload["adapter_input_receipts"][_MODEL_NAME] = AdapterInputReceiptV2.from_prepared(
            execution["adapter_input"], forged
        ).to_dict()
        return planned

    runtime._dispatch_collect_direct_v2 = forge_split_receipt
    report = runtime.run_workflow_v2(
        _request(),
        pack_id=pack.manifest.pack_id,
        pack_version=pack.manifest.pack_version,
    )

    assert report["abstain"] is True
    assert "prepared_execution_invalid" in report["abstain_reasons"]
    assert _VectorWrapper.run_calls == 0


def test_direct_v2_v04_runtime_rejects_another_declared_pack_asset(
    tmp_path: Path,
) -> None:
    adapter = _VectorAdapter()
    runtime, pack, profile_asset = _direct_v04_runtime(tmp_path, adapter, extra_asset=True)
    unrelated = profile_asset.with_name("unrelated.csv")
    broker = runtime._agents["ModelBrokerAgent"]
    dispatch = runtime._dispatch_collect_direct_v2

    def forge_another_asset(message):
        planned = dispatch(message)
        plan_id = planned.payload["execution_plan"]["plan_id"]
        execution = broker._prepared_v2[plan_id][_MODEL_NAME]
        content = execution["selected_content"]
        forged = _with_forged_receipt(
            content,
            content.receipt.model_copy(
                update={
                    "source_asset_id": "unrelated",
                    "source_asset_sha256": hashlib.sha256(unrelated.read_bytes()).hexdigest(),
                    "source_asset_size_bytes": unrelated.stat().st_size,
                }
            ),
        )
        execution["selected_content"] = forged
        execution["adapter_input"] = execution["adapter_input"].model_copy(update={"model_input": forged.model_input})
        planned.payload["adapter_input_receipts"][_MODEL_NAME] = AdapterInputReceiptV2.from_prepared(
            execution["adapter_input"], forged
        ).to_dict()
        return planned

    runtime._dispatch_collect_direct_v2 = forge_another_asset
    report = runtime.run_workflow_v2(
        _request(),
        pack_id=pack.manifest.pack_id,
        pack_version=pack.manifest.pack_version,
    )

    assert report["abstain"] is True
    assert "prepared_execution_invalid" in report["abstain_reasons"]
    assert _VectorWrapper.run_calls == 0


def test_direct_v2_v04_job_store_keeps_selected_values_out_of_public_replay_bytes(
    tmp_path: Path,
) -> None:
    adapter = _VectorAdapter()
    runtime, pack, root = _direct_v04_runtime(tmp_path, adapter)
    store = JobStore(str(tmp_path / "runs"))

    submitted = submit_direct_v2_job(
        _request(),
        runtime=runtime,
        pack_id=pack.manifest.pack_id,
        pack_version=pack.manifest.pack_version,
        job_store=store,
        job_id="selected-content-v04",
    )
    loaded = store.load(submitted["job_id"])

    assert loaded["execution_identity"]["schema_version"] == "vc.job-execution-identity.v4"
    assert loaded["report"]["abstain"] is False
    rendered = json.dumps(loaded, sort_keys=True)
    assert "1.25" not in rendered
    assert str(root) not in rendered
    assert all("payload" not in message for message in loaded["trace"])
    receipt = loaded["provenance"]["adapter_input_receipts"][_MODEL_NAME]
    assert "profile-1" not in json.dumps(receipt, sort_keys=True)


def test_direct_v2_v04_job_store_rejects_a_tampered_selected_asset_receipt(
    tmp_path: Path,
) -> None:
    adapter = _VectorAdapter()
    runtime, pack, _ = _direct_v04_runtime(tmp_path, adapter)
    store = JobStore(str(tmp_path / "runs"))
    submitted = submit_direct_v2_job(
        _request(),
        runtime=runtime,
        pack_id=pack.manifest.pack_id,
        pack_version=pack.manifest.pack_version,
        job_store=store,
        job_id="selected-content-v04-tamper",
    )
    directory = tmp_path / "runs" / submitted["job_id"]
    for filename, path in (
        ("provenance.json", ("adapter_input_receipts", _MODEL_NAME)),
        ("report.json", ("provenance", "adapter_input_receipts", _MODEL_NAME)),
    ):
        payload = json.loads((directory / filename).read_text(encoding="utf-8"))
        target = payload
        for key in path:
            target = target[key]
        target["selected_content_receipt"]["source_asset_sha256"] = "0" * 64
        (directory / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    loaded = store.load(submitted["job_id"])

    assert loaded["execution_identity"] == {
        "schema_version": None,
        "available": False,
        "reason": "unsupported_or_invalid_execution_identity",
    }


def test_direct_v2_v04_job_store_rejects_a_rehashed_selected_record_split(
    tmp_path: Path,
) -> None:
    adapter = _VectorAdapter()
    runtime, pack, _ = _direct_v04_runtime(tmp_path, adapter)
    store = JobStore(str(tmp_path / "runs"))
    submitted = submit_direct_v2_job(
        _request(),
        runtime=runtime,
        pack_id=pack.manifest.pack_id,
        pack_version=pack.manifest.pack_version,
        job_store=store,
        job_id="selected-content-v04-split-tamper",
    )
    directory = tmp_path / "runs" / submitted["job_id"]
    for filename, path in (
        ("provenance.json", ("adapter_input_receipts", _MODEL_NAME)),
        ("report.json", ("provenance", "adapter_input_receipts", _MODEL_NAME)),
    ):
        payload = json.loads((directory / filename).read_text(encoding="utf-8"))
        target = payload
        for key in path:
            target = target[key]
        receipt = target["selected_content_receipt"]
        receipt["record_split"] = "train"
        receipt["record_split_fingerprint"] = _record_split_fingerprint(receipt, "train")
        (directory / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    loaded = store.load(submitted["job_id"])

    assert loaded["execution_identity"] == {
        "schema_version": None,
        "available": False,
        "reason": "unsupported_or_invalid_execution_identity",
    }


def test_direct_v2_v04_job_store_rejects_another_declared_selected_asset(
    tmp_path: Path,
) -> None:
    adapter = _VectorAdapter()
    runtime, pack, profile_asset = _direct_v04_runtime(tmp_path, adapter, extra_asset=True)
    unrelated = profile_asset.with_name("unrelated.csv")
    store = JobStore(str(tmp_path / "runs"))
    submitted = submit_direct_v2_job(
        _request(),
        runtime=runtime,
        pack_id=pack.manifest.pack_id,
        pack_version=pack.manifest.pack_version,
        job_store=store,
        job_id="selected-content-v04-other-asset-tamper",
    )
    directory = tmp_path / "runs" / submitted["job_id"]
    for filename, path in (
        ("provenance.json", ("adapter_input_receipts", _MODEL_NAME)),
        ("report.json", ("provenance", "adapter_input_receipts", _MODEL_NAME)),
    ):
        payload = json.loads((directory / filename).read_text(encoding="utf-8"))
        target = payload
        for key in path:
            target = target[key]
        receipt = target["selected_content_receipt"]
        receipt["source_asset_id"] = "unrelated"
        receipt["source_asset_sha256"] = hashlib.sha256(unrelated.read_bytes()).hexdigest()
        receipt["source_asset_size_bytes"] = unrelated.stat().st_size
        (directory / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    loaded = store.load(submitted["job_id"])

    assert loaded["execution_identity"] == {
        "schema_version": None,
        "available": False,
        "reason": "unsupported_or_invalid_execution_identity",
    }
