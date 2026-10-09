"""Generic direct-v2 runtime slice: empty plans stop before legacy execution."""

from __future__ import annotations

import hashlib
import json
import shutil
import threading

import pytest

import praxis_virtualcell.model_zoo.cache as cache_module
from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Clock, IdGen, RuntimeConfig
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2, require_v2_request
from praxis_virtualcell.core.runtime import AgentRuntime
from praxis_virtualcell.data_packs.registry import (
    PackRegistry,
    PackViewAssetV1,
    PackViewReceiptV1,
    PreparedPackViewV1,
)
from praxis_virtualcell.model_zoo.adapter_sdk import (
    AdapterExecutionProvenance,
    AdapterInputContract,
    AdapterInputReceipt,
    AdapterOutputContract,
    AdapterOutputEnvelope,
    AdapterRegistry,
    AdapterUncertainty,
    PreparedAdapterInput,
    VirtualCellModelAdapter,
)
from praxis_virtualcell.model_zoo.cache import ArtifactSnapshot, ModelCache
from praxis_virtualcell.model_zoo.capability_registry import (
    CompatibilityReportV2,
    ExecutionPlanV2,
    ExecutionStepV2,
)
from praxis_virtualcell.model_zoo.wrapper_registry import WrapperRegistry
from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper
from praxis_virtualcell.tests.test_capability_runtime import (
    _MODEL_BYTES,
    _PACK_ROOT,
    _TEST_ARTIFACT_SNAPSHOT_BUDGET,
    _card,
    _pack_registry,
    _v2_registry_and_environment,
    _write_registry,
)
from praxis_virtualcell.tests.test_direct_v2_public_contracts import _request


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


_PACK_ID = "test-only-direct-v2-pack"
_PACK_VERSION = "1.0.0"
_PACK_FINGERPRINT = _fingerprint("test-only-direct-v2-pack")
_MODEL_FINGERPRINT = _fingerprint("test-only-direct-v2-model")
_RELEASE_FINGERPRINT = _fingerprint("test-only-direct-v2-release")
_CAPABILITY_FINGERPRINT = _fingerprint("test-only-direct-v2-capability")
_ARTIFACT_FINGERPRINT = _fingerprint("test-only-direct-v2-artifact")
_ENVIRONMENT_FINGERPRINT = _fingerprint("test-only-direct-v2-environment")
_ENVIRONMENT_SNAPSHOT_FINGERPRINT = _fingerprint("test-only-direct-v2-snapshot")
_EVIDENCE_FINGERPRINT = _fingerprint("test-only-direct-v2-evidence")
_POLICY_FINGERPRINT = _fingerprint("test-only-direct-v2-policy")
_MODEL_NAME = "test_only_direct_v2_scalar"


class _ScalarAdapter(VirtualCellModelAdapter):
    adapter_id = "test-only-direct-v2-scalar"
    version = "1.0.0"
    input_contract = AdapterInputContract(
        schema_version="vc.adapter-input-contract.v1",
        task="test_scalar_task",
        output="test_output",
        value_type="float",
        shape=(1,),
        unit="dimensionless",
        pack_data_required=False,
        alignment_required=False,
    )
    output_contract = AdapterOutputContract(
        schema_version="vc.adapter-output-contract.v1",
        task="test_scalar_task",
        output="test_output",
        value_type="float",
        shape=(1,),
        unit="dimensionless",
        uncertainty_required=False,
        ood_required=False,
        abstain_allowed=True,
    )

    def prepare_input(
        self,
        request: VirtualCellRequestV2,
        *,
        pack=None,
        compatibility_report=None,
        **kwargs,
    ) -> PreparedAdapterInput:
        if kwargs:
            raise AssertionError("the adapter must not accept caller-provided features")
        if not isinstance(request, VirtualCellRequestV2):
            raise TypeError("request must be VirtualCellRequestV2")
        if pack is None or compatibility_report is None:
            raise AssertionError("the Broker must bind the exact Pack and report")
        return PreparedAdapterInput(
            schema_version="vc.prepared-adapter-input.v1",
            adapter_fingerprint=self.fingerprint(),
            input_contract_fingerprint=self.input_contract.fingerprint(),
            task=self.input_contract.task,
            output=self.input_contract.output,
            request_fingerprint=_fingerprint(request.to_dict()),
            pack_fingerprint=pack.fingerprint,
            compatibility_fingerprint=compatibility_report.fingerprint(),
            model_input={"request_id": request.request_id, "sealed": True},
            values=None,
            shape=None,
            unit=self.input_contract.unit,
            feature_contract=None,
            feature_contract_fingerprint=None,
            alignment_report=None,
        )

    def adapt_output(
        self,
        prepared: PreparedAdapterInput,
        raw_output: dict,
    ) -> AdapterOutputEnvelope:
        if raw_output != {"value": 0.25}:
            raise AssertionError("the synthetic wrapper returned an unexpected output")
        return AdapterOutputEnvelope(
            schema_version="vc.adapter-output-envelope.v1",
            task=self.output_contract.task,
            output=self.output_contract.output,
            shape=(1,),
            unit=self.output_contract.unit,
            values=(0.25,),
            uncertainty=None,
            ood=None,
            abstain=False,
            abstain_reasons=(),
            projection_metadata={"fixture": "test-only"},
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


class _PathlessPackAdapter(_ScalarAdapter):
    """Synthetic adapter proving direct-v2 never receives a Pack filesystem root."""

    def __init__(self) -> None:
        self.seen_pack = None

    def prepare_input(
        self,
        request: VirtualCellRequestV2,
        *,
        pack=None,
        compatibility_report=None,
        **kwargs,
    ) -> PreparedAdapterInput:
        assert type(pack) is PreparedPackViewV1
        assert not hasattr(pack, "root")
        assert pack.asset_ids
        assert all(pack.asset(asset_id).sha256 for asset_id in pack.asset_ids)
        self.seen_pack = pack
        return super().prepare_input(
            request,
            pack=pack,
            compatibility_report=compatibility_report,
            **kwargs,
        )


class _PathlessCompatibilityAdapter(_PathlessPackAdapter):
    """Synthetic adapter recording its private compatibility projection."""

    def __init__(self) -> None:
        super().__init__()
        self.seen_compatibility_asset_paths: dict[str, str] | None = None

    def prepare_input(
        self,
        request: VirtualCellRequestV2,
        *,
        pack=None,
        compatibility_report=None,
        **kwargs,
    ) -> PreparedAdapterInput:
        assert isinstance(compatibility_report, CompatibilityReportV2)
        self.seen_compatibility_asset_paths = dict(compatibility_report.asset_paths)
        return super().prepare_input(
            request,
            pack=pack,
            compatibility_report=compatibility_report,
            **kwargs,
        )


class _DataRequiredPackAdapter(_PathlessPackAdapter):
    adapter_id = "test-only-direct-v2-data-required"
    input_contract = AdapterInputContract(
        schema_version="vc.adapter-input-contract.v1",
        task="test_scalar_task",
        output="test_output",
        value_type="float",
        shape=(1,),
        unit="dimensionless",
        pack_data_required=True,
        alignment_required=False,
    )

    def __init__(self) -> None:
        super().__init__()
        self.prepare_calls = 0

    def prepare_input(self, *args, **kwargs) -> PreparedAdapterInput:
        self.prepare_calls += 1
        return super().prepare_input(*args, **kwargs)


class _ScalarWrapper(ModelWrapper):
    artifact_snapshot_supported = True

    def __init__(self) -> None:
        self.calls = 0

    def declare_scope(self) -> dict:
        return {}

    def run_prediction(self, model_input: dict) -> dict:
        self.calls += 1
        assert model_input["request_id"] == "direct-v2-public-contract"
        return {"value": 0.25}


class _SnapshotScalarWrapper(_ScalarWrapper):
    """Synthetic direct-v2 wrapper that consumes only Broker-sealed bytes."""

    def __init__(self) -> None:
        super().__init__()
        self.seen_asset_bytes: dict[str, bytes] | None = None

    def run_prediction(self, model_input: dict) -> dict:
        self.seen_asset_bytes = self.capability_asset_bytes
        assert self.capability_assets == {}
        assert self.seen_asset_bytes == {"model.bin": _MODEL_BYTES}
        return super().run_prediction(model_input)


class _PathlessCompatibilityWrapper(_ScalarWrapper):
    """Synthetic wrapper recording its private compatibility projection."""

    seen_compatibility_asset_paths: list[dict[str, str]] = []

    def run_prediction(self, model_input: dict) -> dict:
        compatibility_report = self._compatibility_report
        assert isinstance(compatibility_report, CompatibilityReportV2)
        type(self).seen_compatibility_asset_paths.append(dict(compatibility_report.asset_paths))
        return super().run_prediction(model_input)


class _UnsupportedSnapshotWrapper(_ScalarWrapper):
    artifact_snapshot_supported = False


class _UnadaptedSnapshotWrapper(_ScalarWrapper):

    @classmethod
    def from_capability(
        cls,
        *,
        card,
        compatibility_report,
        runtime_adapter,
        prepared_input,
        artifact_snapshot,
        **_kwargs,
    ):
        """Deliberately bypass the base-class declaration check for this regression test."""

        instance = cls()
        instance.name = card.name
        instance.model_version = card.version
        instance._capability_card = card
        instance._compatibility_report = compatibility_report
        instance._capability_assets = {}
        instance._capability_artifact_snapshot = artifact_snapshot
        instance._runtime_adapter = runtime_adapter
        instance._prepared_adapter_input = prepared_input
        return instance


def _plan_and_prepared(request):
    adapter = _ScalarAdapter()
    report = CompatibilityReportV2(
        schema_version="vc.compatibility-report.v2",
        request_id=request.request_id,
        request_fingerprint=_fingerprint(request.to_dict()),
        model_name=_MODEL_NAME,
        model_version="1.0.0",
        model_fingerprint=_MODEL_FINGERPRINT,
        release_fingerprint=_RELEASE_FINGERPRINT,
        capability_fingerprint=_CAPABILITY_FINGERPRINT,
        pack_id=_PACK_ID,
        pack_version=_PACK_VERSION,
        pack_fingerprint=_PACK_FINGERPRINT,
        environment_fingerprint=_ENVIRONMENT_FINGERPRINT,
        environment_snapshot_fingerprint=_ENVIRONMENT_SNAPSHOT_FINGERPRINT,
        artifact_fingerprints=(_ARTIFACT_FINGERPRINT,),
        adapter_fingerprints=(adapter.fingerprint(),),
        evidence_fingerprints=(_EVIDENCE_FINGERPRINT,),
        policy_fingerprint=_POLICY_FINGERPRINT,
        cataloged=True,
        artifact_ready=True,
        revoked=False,
        superseded_by=None,
        pack_valid=True,
        model_compatible=True,
        environment_compatible=True,
        adapter_compatible=True,
        assets_ready=True,
        wrapper_ready=True,
        benchmark_passed=False,
        scientifically_validated=False,
        promotion_eligible=False,
        policy_present=True,
        production_promoted=False,
        research_execution_authorized=True,
        research_execution_scope="research_only",
        executable=True,
        checks={},
        reasons=(),
        asset_paths={},
    )
    step = ExecutionStepV2(
        schema_version="vc.execution-step.v2",
        model_name=report.model_name,
        model_version=report.model_version,
        model_fingerprint=report.model_fingerprint,
        release_fingerprint=report.release_fingerprint,
        capability_fingerprint=report.capability_fingerprint,
        artifact_fingerprints=report.artifact_fingerprints,
        environment_fingerprint=report.environment_fingerprint,
        adapter_fingerprints=report.adapter_fingerprints,
        evidence_fingerprints=report.evidence_fingerprints,
        policy_fingerprint=report.policy_fingerprint,
        compatibility_fingerprint=report.fingerprint(),
        wrapper=f"{_ScalarWrapper.__module__}.{_ScalarWrapper.__qualname__}",
        agent_name=report.model_name,
        asset_paths={},
    )
    plan = ExecutionPlanV2.build(
        request_id=request.request_id,
        request_fingerprint=report.request_fingerprint,
        pack_id=_PACK_ID,
        pack_version=_PACK_VERSION,
        pack_fingerprint=_PACK_FINGERPRINT,
        environment_snapshot_fingerprint=_ENVIRONMENT_SNAPSHOT_FINGERPRINT,
        reports=(report,),
        steps=(step,),
    )
    prepared = PreparedAdapterInput(
        schema_version="vc.prepared-adapter-input.v1",
        adapter_fingerprint=adapter.fingerprint(),
        input_contract_fingerprint=adapter.input_contract.fingerprint(),
        task="test_scalar_task",
        output="test_output",
        request_fingerprint=report.request_fingerprint,
        pack_fingerprint=_PACK_FINGERPRINT,
        compatibility_fingerprint=report.fingerprint(),
        model_input={"request_id": request.request_id, "sealed": True},
        values=None,
        shape=None,
        unit="dimensionless",
        feature_contract=None,
        feature_contract_fingerprint=None,
        alignment_report=None,
    )
    return plan, adapter, prepared


def _two_step_plan(request) -> ExecutionPlanV2:
    first_plan, _adapter, _prepared = _plan_and_prepared(request)
    first_report = first_plan.reports[0]
    first_step = first_plan.steps[0]
    second_report_value = first_report.to_dict()
    second_report_value.update(
        {
            "model_name": "test_only_direct_v2_scalar_second",
            "model_fingerprint": _fingerprint("test-only-direct-v2-second-model"),
            "release_fingerprint": _fingerprint("test-only-direct-v2-second-release"),
            "capability_fingerprint": _fingerprint("test-only-direct-v2-second-capability"),
        }
    )
    second_report = CompatibilityReportV2.from_dict(second_report_value)
    second_step_value = first_step.to_dict()
    second_step_value.update(
        {
            "model_name": second_report.model_name,
            "model_fingerprint": second_report.model_fingerprint,
            "release_fingerprint": second_report.release_fingerprint,
            "capability_fingerprint": second_report.capability_fingerprint,
            "compatibility_fingerprint": second_report.fingerprint(),
            "agent_name": second_report.model_name,
        }
    )
    second_step = ExecutionStepV2.from_dict(second_step_value)
    return ExecutionPlanV2.build(
        request_id=first_plan.request_id,
        request_fingerprint=first_plan.request_fingerprint,
        pack_id=first_plan.pack_id,
        pack_version=first_plan.pack_version,
        pack_fingerprint=first_plan.pack_fingerprint,
        environment_snapshot_fingerprint=first_plan.environment_snapshot_fingerprint,
        reports=(first_report, second_report),
        steps=(first_step, second_step),
    )


class _SingleModelBroker(BaseAgent):
    name = "ModelBrokerAgent"

    def __init__(self, request) -> None:
        self.plan, self.adapter, self.prepared = _plan_and_prepared(request)
        self.wrapper = _ScalarWrapper()
        self.wrapper._capability_artifact_snapshot = ArtifactSnapshot.empty()
        self.receipt = AdapterInputReceipt.from_prepared(self.prepared)
        self.pack_view_receipt = PackViewReceiptV1(
            schema_version="vc.prepared-pack-view-receipt.v1",
            pack_id=_PACK_ID,
            pack_version=_PACK_VERSION,
            pack_fingerprint=_PACK_FINGERPRINT,
            taxonomy_id="NCBITaxon:999999",
            assembly_accession="test-assembly-v1",
            assets=(
                PackViewAssetV1(
                    asset_id="test-only",
                    media_type="application/test",
                    sha256=_ARTIFACT_FINGERPRINT,
                    size_bytes=1,
                ),
            ),
        )

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        assert message.message_type == "execution_plan_v2_request"
        bus.send(
            AgentMessage(
                message_id=f"{message.message_id}:plan",
                sender=self.name,
                receiver="AgentRuntime",
                message_type="execution_plan_ready",
                payload={
                    "execution_plan": self.plan.to_dict(),
                    "adapter_input_receipts": {
                        _MODEL_NAME: self.receipt.to_dict(),
                    },
                    "pack_view_receipt": self.pack_view_receipt.to_dict(),
                },
                timestamp=message.timestamp,
                parent_message_id=message.message_id,
            )
        )

    def take_prepared_v2(self, plan_id: str) -> dict:
        assert plan_id == self.plan.plan_id
        return {
            _MODEL_NAME: {
                "wrapper": self.wrapper,
                "adapter": self.adapter,
                "adapter_input": self.prepared,
                "artifact_snapshot": self.wrapper.capability_artifact_snapshot,
                "pack_verifier": lambda: True,
            }
        }


class _ReplyOnceBroker(_SingleModelBroker):
    """A hostile/custom Broker used to prove stale responses cannot be reused."""

    def __init__(self, request) -> None:
        super().__init__(request)
        self.calls = 0

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        self.calls += 1
        if self.calls == 1:
            super().handle(message, bus)


class _MissingPackViewReceiptBroker(_SingleModelBroker):
    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        super().handle(message, bus)
        response = bus.latest("execution_plan_ready")
        assert response is not None
        response.payload.pop("pack_view_receipt")


def _runtime() -> AgentRuntime:
    runtime = AgentRuntime(
        RuntimeConfig(),
        bus=MessageBus(),
        clock=Clock(),
        idgen=IdGen(),
    )
    runtime.register_agent(ModelBrokerAgent())
    return runtime


def test_direct_v2_without_pack_hard_abstains_before_adapter_or_legacy_flow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime()
    broker = runtime._agents["ModelBrokerAgent"]

    def forbidden(*_args, **_kwargs):
        raise AssertionError("a missing Pack must not prepare or execute a wrapper")

    monkeypatch.setattr(broker._capabilities, "instantiate", forbidden)
    import praxis_virtualcell.core.runtime as runtime_module

    monkeypatch.setattr(runtime_module, "legacy_request_to_v2", forbidden)

    report = runtime.run_workflow_v2(require_v2_request(_request()))

    plan = report["provenance"]["execution_plan"]
    assert plan["schema_version"] == "vc.execution-plan.v2"
    assert plan["executable"] is False
    assert plan["steps"] == []
    assert report["abstain"] is True
    assert report["prediction"] is None
    assert report["models_used"] == []
    assert "execution_plan_not_executable" in report["abstain_reasons"]
    assert "pack_required" in report["abstain_reasons"]
    assert report["provenance"]["adapter_input_receipts"] == {}
    assert report["provenance"]["per_call_hashes"] == {}
    assert [message.message_type for message in runtime.bus.trace] == [
        "execution_plan_v2_request",
        "execution_plan_ready",
        "execution_result_ready",
    ]


def test_direct_v2_executes_one_generic_research_authorized_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = require_v2_request(_request())
    broker = _SingleModelBroker(request)
    runtime = AgentRuntime(
        RuntimeConfig(),
        bus=MessageBus(),
        clock=Clock(),
        idgen=IdGen(),
    )
    runtime.register_agent(broker)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("direct-v2 must not project through the legacy runtime")

    import praxis_virtualcell.core.runtime as runtime_module

    monkeypatch.setattr(runtime_module, "legacy_request_to_v2", forbidden)

    report = runtime.run_workflow_v2(
        request,
        pack_id=_PACK_ID,
        pack_version=_PACK_VERSION,
    )

    assert broker.wrapper.calls == 1
    assert report["abstain"] is False
    assert report["prediction"]["task"] == "test_scalar_task"
    assert report["prediction"]["output"] == "test_output"
    assert report["prediction"]["values"] == [0.25]
    assert report["models_used"] == [_MODEL_NAME]
    assert report["scientifically_validated"] is False
    assert report["execution_scope"] == "research_only"
    assert report["provenance"]["adapter_input_receipts"] == {
        _MODEL_NAME: broker.receipt.to_dict(),
    }
    assert set(report["provenance"]["per_call_hashes"]) == {_MODEL_NAME}


def test_direct_v2_multi_step_plan_abstains_before_wrapper_or_adapter_preparation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = require_v2_request(_request())
    plan = _two_step_plan(request)
    broker = ModelBrokerAgent()
    calls: list[tuple] = []

    monkeypatch.setattr(broker, "plan", lambda *_args, **_kwargs: plan)

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("U2-disabled multi-step plans must not instantiate")

    monkeypatch.setattr(broker._capabilities, "instantiate", forbidden)
    runtime = AgentRuntime(
        RuntimeConfig(),
        bus=MessageBus(),
        clock=Clock(),
        idgen=IdGen(),
    )
    runtime.register_agent(broker)

    report = runtime.run_workflow_v2(
        request,
        pack_id=_PACK_ID,
        pack_version=_PACK_VERSION,
    )

    public_plan = report["provenance"]["execution_plan"]
    assert calls == []
    assert public_plan["executable"] is False
    assert public_plan["steps"] == []
    assert all(entry["executable"] is False for entry in public_plan["reports"])
    assert all("output_reducer_required" in entry["reasons"] for entry in public_plan["reports"])
    assert report["provenance"]["adapter_input_receipts"] == {}
    assert "output_reducer_required" in report["abstain_reasons"]
    assert broker._prepared_v2 == {}


def test_v2_public_plan_projection_keeps_absent_policy_extension_fields_omitted() -> None:
    """A legacy V2 report never gains synthetic null policy-extension fields."""

    from praxis_virtualcell.pack_product import _public_plan

    request = require_v2_request(_request())
    plan, _adapter, _prepared = _plan_and_prepared(request)

    raw = plan.to_dict()
    for report in raw["reports"]:
        report.pop("research_execution_authorized")
        report.pop("research_execution_scope")
    public = _public_plan(raw)

    assert public["schema_version"] == "vc.execution-plan.v2"
    assert all(
        "research_execution_authorized" not in report and "research_execution_scope" not in report
        for report in public["reports"]
    )


def test_direct_v2_refuses_a_stale_broker_response_when_runtime_is_reused() -> None:
    request = require_v2_request(_request())
    runtime = AgentRuntime(
        RuntimeConfig(),
        bus=MessageBus(),
        clock=Clock(),
        idgen=IdGen(),
    )
    runtime.register_agent(_ReplyOnceBroker(request))

    first = runtime.run_workflow_v2(
        request,
        pack_id=_PACK_ID,
        pack_version=_PACK_VERSION,
    )
    assert first["abstain"] is False

    with pytest.raises(RuntimeError):
        runtime.run_workflow_v2(
            request,
            pack_id=_PACK_ID,
            pack_version=_PACK_VERSION,
        )


def test_direct_v2_refuses_an_executable_plan_without_a_pack_view_receipt() -> None:
    request = require_v2_request(_request())
    runtime = AgentRuntime(
        RuntimeConfig(),
        bus=MessageBus(),
        clock=Clock(),
        idgen=IdGen(),
    )
    runtime.register_agent(_MissingPackViewReceiptBroker(request))

    report = runtime.run_workflow_v2(
        request,
        pack_id=_PACK_ID,
        pack_version=_PACK_VERSION,
    )

    assert report["abstain"] is True
    assert "pack_view_receipt_invalid" in report["abstain_reasons"]


def test_direct_v2_broker_revalidates_pack_before_preparing_model_input(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from praxis_virtualcell.data_packs.registry import PackRegistry

    root = tmp_path / "pack"
    shutil.copytree(_PACK_ROOT, root)
    packs = PackRegistry()
    packs.register(root)
    registered = packs.record("tiny-human-scrna", "0.1.0")
    asset = registered.manifest.assets[0]
    asset_path = root / asset.path
    asset_path.write_bytes(b"x" * asset_path.stat().st_size)

    request = require_v2_request(_request())
    plan, _adapter, _prepared = _plan_and_prepared(request)
    broker = ModelBrokerAgent(pack_registry=packs)
    calls: list[tuple] = []
    monkeypatch.setattr(broker, "plan", lambda *_args, **_kwargs: plan)

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("drifted Pack must not reach model preparation")

    monkeypatch.setattr(broker._capabilities, "instantiate", forbidden)
    bus = MessageBus()
    broker.handle(
        AgentMessage(
            "pack-drift-direct-v2",
            "client",
            "ModelBrokerAgent",
            "execution_plan_v2_request",
            {
                "request": request.to_dict(),
                "request_fingerprint": _fingerprint(request.to_dict()),
                "pack_id": registered.manifest.pack_id,
                "pack_version": registered.manifest.pack_version,
            },
            "t0001",
        ),
        bus,
    )

    output = bus.latest("execution_plan_ready")
    assert output is not None
    assert calls == []
    assert output.payload["execution_plan"]["steps"] == []
    assert all("pack.integrity_drift" in report["reasons"] for report in output.payload["execution_plan"]["reports"])
    assert broker._prepared_v2 == {}


def test_execution_pack_view_is_path_free_and_seals_declared_asset_bytes(tmp_path) -> None:
    root = tmp_path / "pack"
    shutil.copytree(_PACK_ROOT, root)
    packs = PackRegistry()
    packs.register(root)
    registered = packs.record("tiny-human-scrna", "0.1.0")
    asset = registered.manifest.assets[0]
    expected = (root / asset.path).read_bytes()

    view = packs.issue_execution_view(registered)

    assert type(view) is PreparedPackViewV1
    assert not hasattr(view, "root")
    assert view.fingerprint == registered.fingerprint
    assert view.receipt.pack_fingerprint == registered.fingerprint
    assert view.asset_ids == (asset.id,)
    assert view.asset(asset.id).sha256 == asset.sha256
    assert view.asset(asset.id).size_bytes == len(expected)
    assert "path" not in view.asset(asset.id).to_dict()
    with pytest.raises(KeyError):
        view.asset("not-declared")

    (root / asset.path).write_bytes(b"x" * len(expected))
    assert view.asset(asset.id).sha256 == asset.sha256


def test_direct_v2_broker_publishes_only_receipts_and_keeps_execution_private(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = require_v2_request(_request())
    plan, adapter, prepared = _plan_and_prepared(request)
    wrapper = _ScalarWrapper()
    wrapper._runtime_adapter = adapter
    wrapper._prepared_adapter_input = prepared
    wrapper._capability_artifact_snapshot = ArtifactSnapshot.empty()
    wrappers = WrapperRegistry()
    wrappers.register(plan.steps[0].wrapper, _ScalarWrapper)
    broker = ModelBrokerAgent(wrapper_registry=wrappers)
    # This unit test supplies an intentionally synthetic private plan rather
    # than a release-bound registry.  Isolate receipt projection from the
    # separate artifact-budget gate exercised through real registries below.
    monkeypatch.setattr(broker, "_artifact_snapshot_budget_reason", lambda _plan: None)
    monkeypatch.setattr(
        broker,
        "plan",
        lambda *_args, **_kwargs: plan,
    )
    monkeypatch.setattr(
        broker._capabilities,
        "instantiate",
        lambda *_args, **_kwargs: wrapper,
    )
    bus = MessageBus()

    broker.handle(
        AgentMessage(
            "direct-v2-broker",
            "client",
            "ModelBrokerAgent",
            "execution_plan_v2_request",
            {
                "request": request.to_dict(),
                "request_fingerprint": _fingerprint(request.to_dict()),
                "pack_id": _PACK_ID,
                "pack_version": _PACK_VERSION,
            },
            "2026-08-11T00:00:00Z",
        ),
        bus,
    )

    result = bus.latest("execution_plan_ready")
    assert result is not None
    assert result.receiver == "AgentRuntime"
    assert result.payload["adapter_input_receipts"] == {
        _MODEL_NAME: AdapterInputReceipt.from_prepared(prepared).to_dict(),
    }
    assert "model_input" not in str(result.payload)
    execution = broker.take_prepared_v2(plan.plan_id)[_MODEL_NAME]
    assert execution["wrapper"] is wrapper
    assert execution["adapter"] is adapter
    assert execution["adapter_input"].fingerprint() == prepared.fingerprint()
    assert execution["artifact_snapshot"] is wrapper.capability_artifact_snapshot
    assert callable(execution["pack_verifier"])
    assert "artifact_snapshot" not in str(result.payload)
    assert "pack_verifier" not in str(result.payload)


def _pack_bound_request():
    value = _request()
    value["species"] = {
        "schema_version": "vc.species-ref.v1",
        "taxonomy_id": "NCBITaxon:9606",
        "scientific_name": "Homo sapiens",
        "common_name": "human",
    }
    value["cell_context"] = {
        "schema_version": "vc.cell-context.v1",
        "cell_type_name": "K562",
        "cell_type_id": None,
        "tissue_name": None,
        "tissue_id": None,
        "attributes": {},
    }
    value["input_modality"] = {
        "schema_version": "vc.modality.v1",
        "name": "scRNA",
        "ontology_id": "EFO:0008913",
        "unit": None,
        "feature_namespace": "EnsemblGene",
    }
    value["output_modality"] = {
        "schema_version": "vc.modality.v1",
        "name": "test_output",
        "ontology_id": None,
        "unit": "dimensionless",
        "feature_namespace": "EnsemblGene",
    }
    value["perturbation"] = {
        "schema_version": "vc.perturbation.v1",
        "kind": "gene",
        "targets": ["AHR"],
        "dose_value": None,
        "dose_unit": None,
        "timepoint": None,
    }
    return require_v2_request(value)


def test_direct_v2_real_broker_executes_a_generic_research_authorized_step(
    tmp_path,
) -> None:
    request = _pack_bound_request()
    card = _card()
    card.update(
        {
            "name": _MODEL_NAME,
            "wrapper": f"{_ScalarWrapper.__module__}.{_ScalarWrapper.__qualname__}",
            "task": "test_scalar_task",
            "output": ["test_output"],
        }
    )
    packs = _pack_registry()
    pack = packs.record("tiny-human-scrna", "0.1.0")
    adapter = _PathlessPackAdapter()
    registry_v2, environment = _v2_registry_and_environment(
        card,
        pack.fingerprint,
        promoted=False,
        runtime_adapter=adapter,
        research_execution_authorized=True,
        runtime_tasks=("test_scalar_task",),
        runtime_outputs=("test_output",),
        snapshot_budget=_TEST_ARTIFACT_SNAPSHOT_BUDGET,
    )
    zoo = _write_registry(tmp_path, card, registry_v2=registry_v2)
    cache = ModelCache(root=str(tmp_path / "cache"))
    asset_path = cache.asset_path(_MODEL_NAME, "model.bin")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(_MODEL_BYTES)
    wrappers = WrapperRegistry()
    wrappers.register(card["wrapper"], _ScalarWrapper)
    runtime = AgentRuntime(
        RuntimeConfig(),
        bus=MessageBus(),
        clock=Clock(),
        idgen=IdGen(),
    )
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

    report = runtime.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert report["abstain"] is False
    assert report["prediction"]["output"] == "test_output"
    assert report["scientifically_validated"] is False
    assert report["execution_scope"] == "research_only"
    assert report["provenance"]["execution_plan"]["steps"][0]["model_name"] == _MODEL_NAME
    assert type(adapter.seen_pack) is PreparedPackViewV1
    assert "root" not in json.dumps(report["provenance"]["pack_view_receipt"])
    assert "path" not in json.dumps(report["provenance"]["pack_view_receipt"])


def test_direct_v2_adapter_and_wrapper_receive_pathless_compatibility_reports(tmp_path) -> None:
    request = _pack_bound_request()
    card = _card()
    card.update(
        {
            "name": _MODEL_NAME,
            "wrapper": f"{_PathlessCompatibilityWrapper.__module__}.{_PathlessCompatibilityWrapper.__qualname__}",
            "task": "test_scalar_task",
            "output": ["test_output"],
        }
    )
    packs = _pack_registry()
    pack = packs.record("tiny-human-scrna", "0.1.0")
    adapter = _PathlessCompatibilityAdapter()
    registry_v2, environment = _v2_registry_and_environment(
        card,
        pack.fingerprint,
        promoted=False,
        runtime_adapter=adapter,
        research_execution_authorized=True,
        runtime_tasks=("test_scalar_task",),
        runtime_outputs=("test_output",),
        snapshot_budget=_TEST_ARTIFACT_SNAPSHOT_BUDGET,
    )
    zoo = _write_registry(tmp_path, card, registry_v2=registry_v2)
    cache = ModelCache(root=str(tmp_path / "cache"))
    asset_path = cache.asset_path(_MODEL_NAME, "model.bin")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(_MODEL_BYTES)
    wrappers = WrapperRegistry()
    wrappers.register(card["wrapper"], _PathlessCompatibilityWrapper)
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
    _PathlessCompatibilityWrapper.seen_compatibility_asset_paths = []

    report = runtime.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    raw_plan = runtime.bus.latest("execution_plan_ready").payload["execution_plan"]
    assert raw_plan["reports"][0]["asset_paths"] == {"model.bin": str(asset_path)}
    assert report["abstain"] is False
    assert adapter.seen_compatibility_asset_paths == {}
    assert _PathlessCompatibilityWrapper.seen_compatibility_asset_paths == [{}]


def test_direct_v2_raw_broker_rejects_legacy_v2_environment_before_snapshot_or_wrapper(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _pack_bound_request()
    card = _card()
    card.update(
        {
            "name": _MODEL_NAME,
            "wrapper": f"{_ScalarWrapper.__module__}.{_ScalarWrapper.__qualname__}",
            "task": "test_scalar_task",
            "output": ["test_output"],
        }
    )
    packs = _pack_registry()
    pack = packs.record("tiny-human-scrna", "0.1.0")
    adapter = _PathlessPackAdapter()
    registry_v2, legacy_environment = _v2_registry_and_environment(
        card,
        pack.fingerprint,
        promoted=False,
        runtime_adapter=adapter,
        research_execution_authorized=True,
        runtime_tasks=("test_scalar_task",),
        runtime_outputs=("test_output",),
    )
    zoo = _write_registry(tmp_path, card, registry_v2=registry_v2)
    cache = ModelCache(root=str(tmp_path / "cache"))
    asset_path = cache.asset_path(_MODEL_NAME, "model.bin")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(_MODEL_BYTES)
    wrappers = WrapperRegistry()
    wrappers.register(card["wrapper"], _ScalarWrapper)
    broker = ModelBrokerAgent(
        registry=zoo,
        cache=cache,
        pack_registry=packs,
        environment=legacy_environment,
        adapter_registry=AdapterRegistry([adapter]),
        wrapper_registry=wrappers,
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("legacy direct-v2 environment must stop before private execution work")

    monkeypatch.setattr(broker._capabilities, "instantiate", forbidden)
    monkeypatch.setattr(cache, "snapshot", forbidden)
    runtime = AgentRuntime(RuntimeConfig(), bus=MessageBus(), clock=Clock(), idgen=IdGen())
    runtime.register_agent(broker)

    report = runtime.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert report["abstain"] is True
    assert report["prediction"] is None
    plan = report["provenance"]["execution_plan"]
    assert plan["steps"] == []
    assert "environment.identity" in plan["reports"][0]["reasons"]
    assert report["abstain_reasons"] == [
        "execution_plan_not_executable",
        "artifact.snapshot_budget_unavailable",
    ]


@pytest.mark.parametrize("wrapper_class", (_UnsupportedSnapshotWrapper, _UnadaptedSnapshotWrapper))
def test_direct_v2_rejects_a_wrapper_without_the_declared_base_snapshot_factory_before_snapshot(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    wrapper_class,
) -> None:
    """A registered wrapper needs support and the base snapshot factory before bytes are read."""

    request = _pack_bound_request()
    card = _card()
    card.update(
        {
            "name": _MODEL_NAME,
            "wrapper": f"{wrapper_class.__module__}.{wrapper_class.__qualname__}",
            "task": "test_scalar_task",
            "output": ["test_output"],
        }
    )
    packs = _pack_registry()
    pack = packs.record("tiny-human-scrna", "0.1.0")
    adapter = _PathlessPackAdapter()
    registry_v2, environment = _v2_registry_and_environment(
        card,
        pack.fingerprint,
        promoted=False,
        runtime_adapter=adapter,
        research_execution_authorized=True,
        runtime_tasks=("test_scalar_task",),
        runtime_outputs=("test_output",),
        snapshot_budget=_TEST_ARTIFACT_SNAPSHOT_BUDGET,
    )
    zoo = _write_registry(tmp_path, card, registry_v2=registry_v2)
    cache = ModelCache(root=str(tmp_path / "cache"))
    asset_path = cache.asset_path(_MODEL_NAME, "model.bin")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(_MODEL_BYTES)
    wrappers = WrapperRegistry()
    wrappers.register(card["wrapper"], wrapper_class)
    runtime = AgentRuntime(
        RuntimeConfig(),
        bus=MessageBus(),
        clock=Clock(),
        idgen=IdGen(),
    )
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
    snapshot_calls = 0
    original_snapshot = cache.snapshot

    def observe_snapshot(*args, **kwargs):
        nonlocal snapshot_calls
        snapshot_calls += 1
        return original_snapshot(*args, **kwargs)

    monkeypatch.setattr(cache, "snapshot", observe_snapshot)

    report = runtime.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert report["abstain"] is True
    assert report["prediction"] is None
    assert report["provenance"]["execution_plan"]["steps"] == []
    assert "model.wrapper_initialization" in report["abstain_reasons"]
    assert snapshot_calls == 0


def test_direct_v2_uses_a_sealed_artifact_snapshot_after_cache_path_replacement(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post-handoff path replacement cannot alter the bytes seen by a wrapper."""

    request = _pack_bound_request()
    card = _card()
    card.update(
        {
            "name": _MODEL_NAME,
            "wrapper": f"{_SnapshotScalarWrapper.__module__}.{_SnapshotScalarWrapper.__qualname__}",
            "task": "test_scalar_task",
            "output": ["test_output"],
        }
    )
    packs = _pack_registry()
    pack = packs.record("tiny-human-scrna", "0.1.0")
    adapter = _PathlessPackAdapter()
    registry_v2, environment = _v2_registry_and_environment(
        card,
        pack.fingerprint,
        promoted=False,
        runtime_adapter=adapter,
        research_execution_authorized=True,
        runtime_tasks=("test_scalar_task",),
        runtime_outputs=("test_output",),
        snapshot_budget=_TEST_ARTIFACT_SNAPSHOT_BUDGET,
    )
    zoo = _write_registry(tmp_path, card, registry_v2=registry_v2)
    cache = ModelCache(root=str(tmp_path / "cache"))
    asset_path = cache.asset_path(_MODEL_NAME, "model.bin")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(_MODEL_BYTES)
    wrappers = WrapperRegistry()
    wrappers.register(card["wrapper"], _SnapshotScalarWrapper)
    broker = ModelBrokerAgent(
        registry=zoo,
        cache=cache,
        pack_registry=packs,
        environment=environment,
        adapter_registry=AdapterRegistry([adapter]),
        wrapper_registry=wrappers,
    )
    runtime = AgentRuntime(
        RuntimeConfig(),
        bus=MessageBus(),
        clock=Clock(),
        idgen=IdGen(),
    )
    runtime.register_agent(broker)

    original_take = broker.take_prepared_v2
    prepared_wrappers: list[_SnapshotScalarWrapper] = []

    def tamper_after_preparation(plan_id: str) -> dict:
        prepared = original_take(plan_id)
        wrapper = prepared[_MODEL_NAME]["wrapper"]
        assert isinstance(wrapper, _SnapshotScalarWrapper)
        prepared_wrappers.append(wrapper)
        asset_path.write_bytes(b"x" * len(_MODEL_BYTES))
        return prepared

    monkeypatch.setattr(broker, "take_prepared_v2", tamper_after_preparation)

    report = runtime.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert report["abstain"] is False
    assert report["prediction"]["values"] == [0.25]
    assert len(prepared_wrappers) == 1
    assert prepared_wrappers[0].calls == 1
    assert prepared_wrappers[0].seen_asset_bytes == {"model.bin": _MODEL_BYTES}


def test_artifact_snapshot_rejects_declared_size_mismatch_before_reading_bytes(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A larger-than-declared artifact must not be read into the snapshot."""

    cache = ModelCache(root=str(tmp_path / "cache"))
    asset_path = cache.asset_path(_MODEL_NAME, "model.bin")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(_MODEL_BYTES)
    read_calls = 0

    def unexpected_read(_descriptor: int, _size: int) -> bytes:
        nonlocal read_calls
        read_calls += 1
        raise AssertionError("declared-size mismatch must stop before os.read")

    monkeypatch.setattr(cache_module.os, "read", unexpected_read)

    with pytest.raises(ValueError, match="cannot seal an exact artifact snapshot"):
        cache.snapshot(
            (
                (
                    _MODEL_NAME,
                    "model.bin",
                    hashlib.sha256(_MODEL_BYTES).hexdigest(),
                    len(_MODEL_BYTES) - 1,
                    str(asset_path),
                ),
            )
        )

    assert read_calls == 0


def test_artifact_snapshot_rejects_append_without_reading_past_declared_size(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An append during a snapshot must be bounded then fail closed."""

    cache = ModelCache(root=str(tmp_path / "cache"))
    asset_path = cache.asset_path(_MODEL_NAME, "model.bin")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(_MODEL_BYTES)
    appended = b"concurrent-append"
    original_read = cache_module.os.read
    original_fstat = cache_module.os.fstat
    read_payloads: list[bytes] = []
    observed_sizes: list[int] = []
    appended_once = False

    def append_before_read(descriptor: int, size: int) -> bytes:
        nonlocal appended_once
        if not appended_once:
            appended_once = True
            with asset_path.open("ab") as handle:
                handle.write(appended)
        payload = original_read(descriptor, size)
        if payload:
            read_payloads.append(payload)
        return payload

    def observe_fstat(descriptor: int):
        result = original_fstat(descriptor)
        observed_sizes.append(result.st_size)
        return result

    monkeypatch.setattr(cache_module.os, "read", append_before_read)
    monkeypatch.setattr(cache_module.os, "fstat", observe_fstat)

    with pytest.raises(ValueError, match="cannot seal an exact artifact snapshot"):
        cache.snapshot(
            (
                (
                    _MODEL_NAME,
                    "model.bin",
                    hashlib.sha256(_MODEL_BYTES).hexdigest(),
                    len(_MODEL_BYTES),
                    str(asset_path),
                ),
            )
        )

    assert b"".join(read_payloads) == _MODEL_BYTES
    assert observed_sizes == [len(_MODEL_BYTES), len(_MODEL_BYTES) + len(appended)]


def test_artifact_snapshot_rejects_fd_identity_change_after_exact_read(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The post-read descriptor identity must still match the pre-read identity."""

    cache = ModelCache(root=str(tmp_path / "cache"))
    asset_path = cache.asset_path(_MODEL_NAME, "model.bin")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(_MODEL_BYTES)
    original_fstat = cache_module.os.fstat
    fstat_calls = 0

    def changed_identity(descriptor: int):
        nonlocal fstat_calls
        result = original_fstat(descriptor)
        fstat_calls += 1
        if fstat_calls == 2:
            fields = list(result)
            fields[1] += 1
            return type(result)(fields)
        return result

    monkeypatch.setattr(cache_module.os, "fstat", changed_identity)

    with pytest.raises(ValueError, match="cannot seal an exact artifact snapshot"):
        cache.snapshot(
            (
                (
                    _MODEL_NAME,
                    "model.bin",
                    hashlib.sha256(_MODEL_BYTES).hexdigest(),
                    len(_MODEL_BYTES),
                    str(asset_path),
                ),
            )
        )

    assert fstat_calls == 2


@pytest.mark.parametrize(
    ("bindings", "max_live_snapshot_payload_bytes", "max_snapshot_entries_per_execution"),
    (
        (
            (
                (
                    _MODEL_NAME,
                    "model.bin",
                    hashlib.sha256(_MODEL_BYTES).hexdigest(),
                    len(_MODEL_BYTES),
                    "unused",
                ),
            ),
            len(_MODEL_BYTES) - 1,
            1,
        ),
        (
            (
                (_MODEL_NAME, "one.bin", "1" * 64, 1, "unused-one"),
                (_MODEL_NAME, "two.bin", "2" * 64, 1, "unused-two"),
            ),
            2,
            1,
        ),
    ),
)
def test_artifact_snapshot_budget_rejects_before_reading_bytes(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    bindings,
    max_live_snapshot_payload_bytes: int,
    max_snapshot_entries_per_execution: int,
) -> None:
    """Budget rejection is a pre-read gate, never a best-effort memory check."""

    cache = ModelCache(root=str(tmp_path / "cache"))
    read_calls = 0

    def unexpected_read(_descriptor: int, _size: int) -> bytes:
        nonlocal read_calls
        read_calls += 1
        raise AssertionError("snapshot budget must stop before os.read")

    monkeypatch.setattr(cache_module.os, "read", unexpected_read)

    with pytest.raises(ValueError, match="snapshot budget"):
        cache.snapshot(
            bindings,
            max_live_snapshot_payload_bytes=max_live_snapshot_payload_bytes,
            max_snapshot_entries_per_execution=max_snapshot_entries_per_execution,
        )

    assert read_calls == 0


def test_direct_v2_rejects_a_replaced_private_artifact_snapshot_before_wrapper_execution(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A same-byte but different snapshot object cannot be spliced into a handoff."""

    request = _pack_bound_request()
    card = _card()
    card.update(
        {
            "name": _MODEL_NAME,
            "wrapper": f"{_SnapshotScalarWrapper.__module__}.{_SnapshotScalarWrapper.__qualname__}",
            "task": "test_scalar_task",
            "output": ["test_output"],
        }
    )
    packs = _pack_registry()
    pack = packs.record("tiny-human-scrna", "0.1.0")
    adapter = _PathlessPackAdapter()
    registry_v2, environment = _v2_registry_and_environment(
        card,
        pack.fingerprint,
        promoted=False,
        runtime_adapter=adapter,
        research_execution_authorized=True,
        runtime_tasks=("test_scalar_task",),
        runtime_outputs=("test_output",),
        snapshot_budget=_TEST_ARTIFACT_SNAPSHOT_BUDGET,
    )
    zoo = _write_registry(tmp_path, card, registry_v2=registry_v2)
    cache = ModelCache(root=str(tmp_path / "cache"))
    asset_path = cache.asset_path(_MODEL_NAME, "model.bin")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(_MODEL_BYTES)
    wrappers = WrapperRegistry()
    wrappers.register(card["wrapper"], _SnapshotScalarWrapper)
    broker = ModelBrokerAgent(
        registry=zoo,
        cache=cache,
        pack_registry=packs,
        environment=environment,
        adapter_registry=AdapterRegistry([adapter]),
        wrapper_registry=wrappers,
    )
    runtime = AgentRuntime(
        RuntimeConfig(),
        bus=MessageBus(),
        clock=Clock(),
        idgen=IdGen(),
    )
    runtime.register_agent(broker)

    original_take = broker.take_prepared_v2
    wrappers_seen: list[_SnapshotScalarWrapper] = []

    def splice_different_snapshot(plan_id: str) -> dict:
        prepared = original_take(plan_id)
        execution = prepared[_MODEL_NAME]
        wrapper = execution["wrapper"]
        assert isinstance(wrapper, _SnapshotScalarWrapper)
        wrappers_seen.append(wrapper)
        plan = broker._capabilities.plan(
            request,
            pack,
            require_registered_wrapper=True,
        )
        replacement = broker._capabilities.direct_v2_artifact_snapshot(
            plan.steps[0],
            plan.reports[0],
        )
        assert replacement is not execution["artifact_snapshot"]
        execution["artifact_snapshot"] = replacement
        return prepared

    monkeypatch.setattr(broker, "take_prepared_v2", splice_different_snapshot)

    report = runtime.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert report["abstain"] is True
    assert report["prediction"] is None
    assert report["abstain_reasons"] == ["prepared_execution_invalid"]
    assert len(wrappers_seen) == 1
    assert wrappers_seen[0].calls == 0


def test_direct_v2_rechecks_pack_before_data_free_wrapper_execution(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A drifted Pack must stop even when the adapter consumes no Pack values."""

    root = tmp_path / "pack"
    shutil.copytree(_PACK_ROOT, root)
    packs = PackRegistry()
    packs.register(root)
    pack = packs.record("tiny-human-scrna", "0.1.0")
    request = _pack_bound_request()
    card = _card()
    card.update(
        {
            "name": _MODEL_NAME,
            "wrapper": f"{_ScalarWrapper.__module__}.{_ScalarWrapper.__qualname__}",
            "task": "test_scalar_task",
            "output": ["test_output"],
        }
    )
    adapter = _PathlessPackAdapter()
    registry_v2, environment = _v2_registry_and_environment(
        card,
        pack.fingerprint,
        promoted=False,
        runtime_adapter=adapter,
        research_execution_authorized=True,
        runtime_tasks=("test_scalar_task",),
        runtime_outputs=("test_output",),
        snapshot_budget=_TEST_ARTIFACT_SNAPSHOT_BUDGET,
    )
    zoo = _write_registry(tmp_path, card, registry_v2=registry_v2)
    cache = ModelCache(root=str(tmp_path / "cache"))
    asset_path = cache.asset_path(_MODEL_NAME, "model.bin")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(_MODEL_BYTES)
    wrappers = WrapperRegistry()
    wrappers.register(card["wrapper"], _ScalarWrapper)
    broker = ModelBrokerAgent(
        registry=zoo,
        cache=cache,
        pack_registry=packs,
        environment=environment,
        adapter_registry=AdapterRegistry([adapter]),
        wrapper_registry=wrappers,
    )
    runtime = AgentRuntime(
        RuntimeConfig(),
        bus=MessageBus(),
        clock=Clock(),
        idgen=IdGen(),
    )
    runtime.register_agent(broker)

    original_take = broker.take_prepared_v2
    calls: list[object] = []

    def tamper_after_preparation(plan_id: str) -> dict:
        prepared = original_take(plan_id)
        wrapper = prepared[_MODEL_NAME]["wrapper"]
        original_run = wrapper.run_prediction

        def record_call(model_input: dict) -> dict:
            calls.append(model_input)
            return original_run(model_input)

        monkeypatch.setattr(wrapper, "run_prediction", record_call)
        asset = pack.manifest.assets[0]
        pack_path = root / asset.path
        pack_path.write_bytes(b"x" * pack_path.stat().st_size)
        return prepared

    monkeypatch.setattr(broker, "take_prepared_v2", tamper_after_preparation)

    report = runtime.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert report["abstain"] is True
    assert report["prediction"] is None
    assert report["abstain_reasons"] == ["pack.integrity_drift"]
    assert calls == []


def test_direct_v2_rejects_unsafe_output_metadata_before_it_can_be_public(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = require_v2_request(_request())
    runtime = AgentRuntime(
        RuntimeConfig(),
        bus=MessageBus(),
        clock=Clock(),
        idgen=IdGen(),
    )
    broker = _SingleModelBroker(request)
    runtime.register_agent(broker)
    original_adapt = broker.adapter.adapt_output
    secret = "/private/test-pack-root/model.bin"

    def unsafe_metadata(prepared: PreparedAdapterInput, raw_output: dict):
        return original_adapt(prepared, raw_output).model_copy(update={"projection_metadata": {"local_path": secret}})

    monkeypatch.setattr(broker.adapter, "adapt_output", unsafe_metadata)

    report = runtime.run_workflow_v2(
        request,
        pack_id=_PACK_ID,
        pack_version=_PACK_VERSION,
    )

    assert report["abstain"] is True
    assert report["prediction"] is None
    assert report["abstain_reasons"] == ["adapter_execution_failed"]
    assert secret not in json.dumps(report, sort_keys=True)


def test_direct_v2_rejects_unsafe_uncertainty_reason_before_it_can_be_public(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = require_v2_request(_request())
    runtime = AgentRuntime(
        RuntimeConfig(),
        bus=MessageBus(),
        clock=Clock(),
        idgen=IdGen(),
    )
    broker = _SingleModelBroker(request)
    runtime.register_agent(broker)
    original_adapt = broker.adapter.adapt_output
    secret = "/private/test-pack-root/model.bin"

    def unsafe_uncertainty(prepared: PreparedAdapterInput, raw_output: dict):
        envelope = original_adapt(prepared, raw_output)
        return envelope.model_copy(
            update={
                "uncertainty": AdapterUncertainty(
                    available=False,
                    method="point_estimate",
                    calibrated=False,
                    reason=secret,
                )
            }
        )

    monkeypatch.setattr(broker.adapter, "adapt_output", unsafe_uncertainty)

    report = runtime.run_workflow_v2(
        request,
        pack_id=_PACK_ID,
        pack_version=_PACK_VERSION,
    )

    assert report["abstain"] is True
    assert report["prediction"] is None
    assert report["abstain_reasons"] == ["adapter_execution_failed"]
    assert secret not in json.dumps(report, sort_keys=True)


def test_direct_v2_serializes_shared_runtime_execution_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One shared runtime must not interleave two direct-v2 message spines."""

    request = require_v2_request(_request())
    runtime = AgentRuntime(
        RuntimeConfig(),
        bus=MessageBus(),
        clock=Clock(),
        idgen=IdGen(),
    )
    broker = _SingleModelBroker(request)
    runtime.register_agent(broker)
    first_prediction_entered = threading.Event()
    release_first_prediction = threading.Event()
    second_broker_entered = threading.Event()
    counter_lock = threading.Lock()
    prediction_calls = 0
    broker_calls = 0
    original_run = broker.wrapper.run_prediction
    original_handle = broker.handle

    def block_first_prediction(model_input: dict) -> dict:
        nonlocal prediction_calls
        with counter_lock:
            prediction_calls += 1
            call_number = prediction_calls
        if call_number == 1:
            first_prediction_entered.set()
            assert release_first_prediction.wait(timeout=2)
        return original_run(model_input)

    def observe_broker(message: AgentMessage, bus: MessageBus) -> None:
        nonlocal broker_calls
        if message.message_type == "execution_plan_v2_request":
            with counter_lock:
                broker_calls += 1
                if broker_calls == 2:
                    second_broker_entered.set()
        original_handle(message, bus)

    monkeypatch.setattr(broker.wrapper, "run_prediction", block_first_prediction)
    monkeypatch.setattr(broker, "handle", observe_broker)
    reports: dict[str, dict] = {}
    errors: list[BaseException] = []

    def execute(trace_id: str, task_id: str) -> None:
        try:
            reports[trace_id] = runtime.run_workflow_v2(
                request,
                trace_id=trace_id,
                task_id=task_id,
                pack_id=_PACK_ID,
                pack_version=_PACK_VERSION,
            )
        except BaseException as exc:  # noqa: BLE001 - worker outcome is asserted below
            errors.append(exc)

    first = threading.Thread(target=execute, args=("trace-A", "task-A"))
    second = threading.Thread(target=execute, args=("trace-B", "task-B"))
    first.start()
    assert first_prediction_entered.wait(timeout=2)
    second.start()

    assert not second_broker_entered.wait(timeout=0.2)
    release_first_prediction.set()
    first.join(timeout=2)
    second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    assert reports["trace-A"]["abstain"] is False
    assert reports["trace-B"]["abstain"] is False
    trace_ids = [message.trace_id for message in runtime.bus.trace]
    assert trace_ids == ["trace-A"] * 3 + ["trace-B"] * 3


def test_direct_v2_data_required_adapter_abstains_without_a_core_content_materializer(
    tmp_path,
) -> None:
    request = _pack_bound_request()
    card = _card()
    card.update(
        {
            "name": _MODEL_NAME,
            "wrapper": f"{_ScalarWrapper.__module__}.{_ScalarWrapper.__qualname__}",
            "task": "test_scalar_task",
            "output": ["test_output"],
        }
    )
    packs = _pack_registry()
    pack = packs.record("tiny-human-scrna", "0.1.0")
    adapter = _DataRequiredPackAdapter()
    registry_v2, environment = _v2_registry_and_environment(
        card,
        pack.fingerprint,
        promoted=False,
        runtime_adapter=adapter,
        research_execution_authorized=True,
        runtime_tasks=("test_scalar_task",),
        runtime_outputs=("test_output",),
        snapshot_budget=_TEST_ARTIFACT_SNAPSHOT_BUDGET,
    )
    zoo = _write_registry(tmp_path, card, registry_v2=registry_v2)
    cache = ModelCache(root=str(tmp_path / "cache"))
    asset_path = cache.asset_path(_MODEL_NAME, "model.bin")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(_MODEL_BYTES)
    wrappers = WrapperRegistry()
    wrappers.register(card["wrapper"], _ScalarWrapper)
    runtime = AgentRuntime(
        RuntimeConfig(),
        bus=MessageBus(),
        clock=Clock(),
        idgen=IdGen(),
    )
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

    report = runtime.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert report["abstain"] is True
    assert adapter.prepare_calls == 0
    assert report["provenance"]["execution_plan"]["steps"] == []
    assert (
        "pack.selected_content_materializer_unavailable"
        in report["provenance"]["execution_plan"]["reports"][0]["reasons"]
    )
    assert "pack.selected_content_materializer_unavailable" in report["abstain_reasons"]


def test_v1_policy_cannot_be_forged_into_research_execution(tmp_path) -> None:
    request = _pack_bound_request()
    card = _card()
    card.update(
        {
            "name": _MODEL_NAME,
            "wrapper": f"{_ScalarWrapper.__module__}.{_ScalarWrapper.__qualname__}",
            "task": "test_scalar_task",
            "output": ["test_output"],
        }
    )
    packs = _pack_registry()
    pack = packs.record("tiny-human-scrna", "0.1.0")
    adapter = _ScalarAdapter()
    registry_v2, environment = _v2_registry_and_environment(
        card,
        pack.fingerprint,
        promoted=False,
        runtime_adapter=adapter,
        runtime_tasks=("test_scalar_task",),
        runtime_outputs=("test_output",),
        snapshot_budget=_TEST_ARTIFACT_SNAPSHOT_BUDGET,
    )
    zoo = _write_registry(tmp_path, card, registry_v2=registry_v2)
    cache = ModelCache(root=str(tmp_path / "cache"))
    asset_path = cache.asset_path(_MODEL_NAME, "model.bin")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(_MODEL_BYTES)
    wrappers = WrapperRegistry()
    wrappers.register(card["wrapper"], _ScalarWrapper)
    broker = ModelBrokerAgent(
        registry=zoo,
        cache=cache,
        pack_registry=packs,
        environment=environment,
        adapter_registry=AdapterRegistry([adapter]),
        wrapper_registry=wrappers,
    )
    original = broker._capabilities.evaluate(
        request,
        pack,
        _MODEL_NAME,
        environment,
        require_registered_wrapper=True,
    )
    forged_raw = original.to_dict()
    forged_raw.update(
        {
            "research_execution_authorized": True,
            "research_execution_scope": "research_only",
            "executable": True,
        }
    )
    forged = CompatibilityReportV2.from_dict(forged_raw)
    step = ExecutionStepV2(
        schema_version="vc.execution-step.v2",
        model_name=forged.model_name,
        model_version=forged.model_version,
        model_fingerprint=forged.model_fingerprint,
        release_fingerprint=forged.release_fingerprint,
        capability_fingerprint=forged.capability_fingerprint,
        artifact_fingerprints=forged.artifact_fingerprints,
        environment_fingerprint=forged.environment_fingerprint,
        adapter_fingerprints=forged.adapter_fingerprints,
        evidence_fingerprints=forged.evidence_fingerprints,
        policy_fingerprint=forged.policy_fingerprint,
        compatibility_fingerprint=forged.fingerprint(),
        wrapper=card["wrapper"],
        agent_name=_MODEL_NAME,
        asset_paths=forged.asset_paths,
    )

    with pytest.raises(ValueError, match="policy"):
        broker._capabilities.instantiate(
            step,
            forged,
            request=request,
            pack=pack,
            require_registered_wrapper=True,
        )
