"""Persistence contract for the generic direct-v2 execution slice."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import threading
from pathlib import Path

import pytest

from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Clock, IdGen, Mode, RuntimeConfig
from praxis_virtualcell.core.exceptions import InputValidationError, UnknownAgentError
from praxis_virtualcell.core.request_v2 import require_v2_request
from praxis_virtualcell.core.runtime import AgentRuntime
from praxis_virtualcell.io import job_store as job_store_module
from praxis_virtualcell.io.job_store import JobStore
from praxis_virtualcell.model_zoo.adapter_sdk import (
    AdapterExecutionProvenance,
    AdapterInputReceipt,
    AdapterOutputEnvelope,
    AdapterRegistry,
    PreparedAdapterInput,
)
from praxis_virtualcell.model_zoo.cache import ModelCache
from praxis_virtualcell.model_zoo.capability_registry import ExecutionPlanV3
from praxis_virtualcell.model_zoo.post_result_policy import (
    OutputReducerBindingV1,
    OutputReducerReceiptV1,
    OutputReducerStepReceiptV1,
)
from praxis_virtualcell.model_zoo.wrapper_registry import WrapperRegistry
from praxis_virtualcell.tests.test_capability_runtime import (
    _MODEL_BYTES,
    _TEST_ARTIFACT_SNAPSHOT_BUDGET,
    _card,
    _pack_registry,
    _v2_registry_and_environment,
    _write_registry,
)
from praxis_virtualcell.tests.test_direct_v2_public_contracts import _request
from praxis_virtualcell.tests.test_direct_v2_single_model import (
    _MODEL_NAME,
    _PACK_ID,
    _PACK_VERSION,
    _pack_bound_request,
    _plan_and_prepared,
    _ScalarAdapter,
    _ScalarWrapper,
    _SingleModelBroker,
    _two_step_plan,
)
from praxis_virtualcell.tests.test_direct_v2_single_model import (
    _fingerprint as _fixture_fingerprint,
)
from praxis_virtualcell.workflows.runtime_builder import DirectV2RuntimeFactory
from praxis_virtualcell.workflows.submit_job import submit_direct_v2_job


def _mark_failed_reservation_in_child(
    runs_dir: str,
    job_id: str,
    attempting_lock,
    outcome,
) -> None:
    """Exercise a reservation transition from a separate process."""

    original_flock = job_store_module._fcntl.flock

    def signal_then_lock(*args, **kwargs):
        attempting_lock.set()
        return original_flock(*args, **kwargs)

    job_store_module._fcntl.flock = signal_then_lock
    try:
        JobStore(runs_dir).mark_failed_reservation(job_id)
    except Exception as exc:  # noqa: BLE001 - parent asserts the public outcome
        outcome.put(type(exc).__name__)
    else:
        outcome.put("ok")
    finally:
        job_store_module._fcntl.flock = original_flock


def _runtime(request) -> AgentRuntime:
    runtime = AgentRuntime(
        RuntimeConfig(),
        bus=MessageBus(),
        clock=Clock(),
        idgen=IdGen(),
    )
    runtime.register_agent(_SingleModelBroker(request))
    return runtime


def _direct_v2_trace() -> list[dict]:
    """A payload-free direct-v2 trace spine for persistence-only conformance."""

    route = (
        ("client", "ModelBrokerAgent", "execution_plan_v2_request"),
        ("ModelBrokerAgent", "AgentRuntime", "execution_plan_ready"),
        ("AgentRuntime", "client", "execution_result_ready"),
    )
    message_ids = ("u2-trace-1", "u2-trace-2", "u2-trace-3")
    return [
        {
            "schema_version": "vc.msg.v1",
            "message_id": message_ids[index],
            "sender": sender,
            "receiver": receiver,
            "message_type": message_type,
            "timestamp": "2026-08-12T00:00:00Z",
            "parent_message_id": None if index == 0 else message_ids[index - 1],
            "trace_id": "u2-trace",
            "task_id": "u2-task",
            "payload_fingerprint": hashlib.sha256(f"u2-payload-{index}".encode()).hexdigest(),
        }
        for index, (sender, receiver, message_type) in enumerate(route)
    ]


def _v3_reduced_result(request) -> tuple[ExecutionPlanV3, dict]:
    """Build a generic, already-reduced V3 result without a product runtime."""

    v2_plan = _two_step_plan(request)
    output_reducer = OutputReducerBindingV1(
        schema_version="vc.output-reducer-binding.v1",
        policy_id="test-only-mean",
        policy_version="1.0.0",
        policy_fingerprint=hashlib.sha256(b"test-only-mean-policy").hexdigest(),
    )
    plan = ExecutionPlanV3.build(
        request_id=v2_plan.request_id,
        request_fingerprint=v2_plan.request_fingerprint,
        pack_id=v2_plan.pack_id,
        pack_version=v2_plan.pack_version,
        pack_fingerprint=v2_plan.pack_fingerprint,
        environment_snapshot_fingerprint=v2_plan.environment_snapshot_fingerprint,
        output_reducer=output_reducer,
        reports=v2_plan.reports,
        steps=v2_plan.steps,
    )
    _unused_plan, adapter, first_prepared = _plan_and_prepared(request)
    second_prepared = PreparedAdapterInput.model_validate(
        {
            **first_prepared.to_dict(),
            "compatibility_fingerprint": plan.steps[1].compatibility_fingerprint,
        }
    )
    prepared_by_name = {
        plan.steps[0].model_name: first_prepared,
        plan.steps[1].model_name: second_prepared,
    }
    receipts = {name: AdapterInputReceipt.from_prepared(prepared) for name, prepared in prepared_by_name.items()}
    envelopes = {name: adapter.adapt_output(prepared, {"value": 0.25}) for name, prepared in prepared_by_name.items()}
    reduced = AdapterOutputEnvelope(
        schema_version="vc.adapter-output-envelope.v1",
        task=adapter.output_contract.task,
        output=adapter.output_contract.output,
        shape=(1,),
        unit=adapter.output_contract.unit,
        values=(0.25,),
        uncertainty=None,
        ood=None,
        abstain=False,
        abstain_reasons=(),
        projection_metadata={"fixture": "u2-job-store"},
        provenance=AdapterExecutionProvenance(
            schema_version="vc.adapter-execution-provenance.v1",
            adapter_fingerprint=adapter.fingerprint(),
            input_fingerprints=tuple(receipts[step.model_name].prepared_input_fingerprint for step in plan.steps),
            input_contract_fingerprint=adapter.input_contract.fingerprint(),
            output_contract_fingerprint=adapter.output_contract.fingerprint(),
            request_fingerprints=(plan.request_fingerprint,),
            pack_fingerprints=(plan.pack_fingerprint,),
            compatibility_fingerprints=tuple(
                receipts[step.model_name].compatibility_fingerprint for step in plan.steps
            ),
        ),
    )
    per_call_hashes = {
        step.model_name: {
            "model_name": step.model_name,
            "model_version": step.model_version,
            "input_hash": receipts[step.model_name].prepared_input_fingerprint,
            "output_hash": _fixture_fingerprint(envelopes[step.model_name].to_dict()),
        }
        for step in plan.steps
    }
    reducer_receipt = OutputReducerReceiptV1(
        schema_version="vc.output-reducer-receipt.v1",
        output_reducer=output_reducer,
        step_receipts=tuple(
            OutputReducerStepReceiptV1(
                schema_version="vc.output-reducer-step-receipt.v1",
                model_name=step.model_name,
                execution_step_fingerprint=step.fingerprint(),
                input_hash=receipts[step.model_name].prepared_input_fingerprint,
                output_hash=per_call_hashes[step.model_name]["output_hash"],
            )
            for step in plan.steps
        ),
        reduced_output_hash=_fixture_fingerprint(reduced.to_dict()),
    )
    pack_view_receipt = _SingleModelBroker(request).pack_view_receipt
    provenance = {
        "execution_contract": "vc.direct-v2-execution.v1",
        "execution_plan": plan.to_dict(),
        "compatibility_reports": [report.to_dict() for report in plan.reports],
        "adapter_input_receipts": {name: receipt.to_dict() for name, receipt in receipts.items()},
        "per_call_hashes": per_call_hashes,
        "pack_view_receipt": pack_view_receipt.to_dict(),
        "output_reducer_receipt": reducer_receipt.to_dict(),
    }
    structured_report = {
        "request_id": plan.request_id,
        "request_fingerprint": plan.request_fingerprint,
        "execution_status": "completed",
        "execution_scope": "research_only",
        "scientifically_validated": False,
        "prediction": reduced.to_dict(),
        "models_used": [step.model_name for step in plan.steps],
        "models_rejected": [],
        "models_failed": [],
        "abstain": False,
        "abstain_reasons": [],
        "reliability": "medium",
        "runtime_confidence": "medium",
        "provenance": provenance,
    }
    return plan, {
        "structured_report": structured_report,
        "provenance": provenance,
        "trace": _direct_v2_trace(),
        "narrative": None,
    }


def test_direct_v2_research_job_persists_v4_identity_and_redacted_hash_spine(
    tmp_path,
) -> None:
    request = require_v2_request(_request())
    store = JobStore(str(tmp_path / "runs"))

    submitted = submit_direct_v2_job(
        request,
        runtime=_runtime(request),
        pack_id=_PACK_ID,
        pack_version=_PACK_VERSION,
        job_store=store,
        job_id="generic-direct-v2-research",
    )
    loaded = store.load(submitted["job_id"])

    identity = loaded["execution_identity"]
    assert submitted == {
        "job_id": "generic-direct-v2-research",
        "status": "done",
    }
    assert identity["schema_version"] == "vc.job-execution-identity.v4"
    assert identity["models"][0]["research_execution_authorized"] is True
    assert identity["models"][0]["research_execution_scope"] == "research_only"
    assert identity["models"][0]["production_promoted"] is False
    assert loaded["report"]["scientifically_validated"] is False
    assert loaded["report"]["execution_scope"] == "research_only"
    assert loaded["provenance"]["execution_contract"] == "vc.direct-v2-execution.v1"
    assert loaded["provenance"]["pack_view_receipt"]["pack_fingerprint"] == (identity["pack"]["fingerprint"])
    assert "root" not in json.dumps(loaded["provenance"]["pack_view_receipt"])
    assert "path" not in json.dumps(loaded["provenance"]["pack_view_receipt"])

    trace = loaded["trace"]
    assert [item["message_type"] for item in trace] == [
        "execution_plan_v2_request",
        "execution_plan_ready",
        "execution_result_ready",
    ]
    assert trace[0]["parent_message_id"] is None
    assert trace[1]["parent_message_id"] == trace[0]["message_id"]
    assert trace[2]["parent_message_id"] == trace[1]["message_id"]
    assert all("payload" not in item for item in trace)
    assert all(len(item["payload_fingerprint"]) == 64 for item in trace)
    assert identity["public_trace_fingerprint"]

    rendered = json.dumps(loaded, sort_keys=True)
    assert "model_input" not in rendered
    assert "sealed" not in rendered


def test_direct_v2_missing_pack_persists_a_v4_hard_abstention(tmp_path) -> None:
    request = require_v2_request(_request())
    store = JobStore(str(tmp_path / "runs"))
    runtime = AgentRuntime(
        RuntimeConfig(),
        bus=MessageBus(),
        clock=Clock(),
        idgen=IdGen(),
    )
    runtime.register_agent(ModelBrokerAgent())

    submitted = submit_direct_v2_job(
        request,
        runtime=runtime,
        pack_id=None,
        pack_version=None,
        job_store=store,
        job_id="generic-direct-v2-no-pack",
    )
    loaded = store.load(submitted["job_id"])

    assert loaded["execution_identity"]["schema_version"] == ("vc.job-execution-identity.v4")
    assert loaded["execution_identity"]["pack"] is None
    assert loaded["execution_identity"]["outcome"] == {
        "abstain": True,
        "models_used": [],
        "prediction_present": False,
    }
    assert loaded["report"]["prediction"] is None
    assert "pack_required" in loaded["report"]["abstain_reasons"]


def test_direct_v2_artifact_backed_job_redacts_private_cache_bindings(tmp_path) -> None:
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
        research_execution_authorized=True,
        runtime_tasks=("test_scalar_task",),
        runtime_outputs=("test_output",),
        snapshot_budget=_TEST_ARTIFACT_SNAPSHOT_BUDGET,
    )
    zoo = _write_registry(tmp_path, card, registry_v2=registry_v2)
    cache = ModelCache(root=str(tmp_path / "private-cache"))
    asset_path = cache.asset_path(_MODEL_NAME, "model.bin")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(_MODEL_BYTES)
    wrappers = WrapperRegistry()
    wrappers.register(card["wrapper"], _ScalarWrapper)
    factory = DirectV2RuntimeFactory(
        registry=zoo,
        cache=cache,
        pack_registry=packs,
        environment=environment,
        adapter_registry=AdapterRegistry([adapter]),
        wrapper_registry=wrappers,
    )
    store = JobStore(str(tmp_path / "runs"))

    submitted = submit_direct_v2_job(
        request,
        runtime=factory.build(),
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
        job_store=store,
        job_id="generic-direct-v2-artifact-redaction",
    )
    loaded = store.load(submitted["job_id"])
    rendered = json.dumps(loaded, sort_keys=True)

    assert loaded["report"]["abstain"] is False
    assert str(cache.root) not in rendered
    assert str(asset_path) not in rendered
    assert "asset_paths" not in rendered
    assert "asset_verifier" not in rendered


def test_direct_v2_rejects_llm_runtime_before_trace_or_job_write(tmp_path) -> None:
    request = require_v2_request(_request())
    runtime = AgentRuntime(
        RuntimeConfig(mode=Mode.LLM_ASSISTED, llm_enabled=True),
        bus=MessageBus(),
        clock=Clock(),
        idgen=IdGen(),
    )
    runtime.register_agent(_SingleModelBroker(request))
    store = JobStore(str(tmp_path / "runs"))

    with pytest.raises(InputValidationError, match="offline"):
        submit_direct_v2_job(
            request,
            runtime=runtime,
            pack_id=_PACK_ID,
            pack_version=_PACK_VERSION,
            job_store=store,
            job_id="direct-v2-llm-forbidden",
        )

    assert runtime.bus.trace == []
    assert not store.root.exists()


def test_direct_v2_duplicate_job_id_is_rejected_before_second_execution(tmp_path) -> None:
    request = require_v2_request(_request())
    store = JobStore(str(tmp_path / "runs"))
    first_runtime = _runtime(request)
    submit_direct_v2_job(
        request,
        runtime=first_runtime,
        pack_id=_PACK_ID,
        pack_version=_PACK_VERSION,
        job_store=store,
        job_id="generic-direct-v2-duplicate",
    )
    second_runtime = _runtime(request)
    second_broker = second_runtime._agents["ModelBrokerAgent"]

    with pytest.raises(FileExistsError, match="already exists"):
        submit_direct_v2_job(
            request,
            runtime=second_runtime,
            pack_id=_PACK_ID,
            pack_version=_PACK_VERSION,
            job_store=store,
            job_id="generic-direct-v2-duplicate",
        )

    assert second_broker.wrapper.calls == 0
    assert second_runtime.bus.trace == []
    assert store.list_jobs() == ["generic-direct-v2-duplicate"]


def test_direct_v2_submit_serializes_trace_capture_for_a_shared_runtime(
    tmp_path,
    monkeypatch,
) -> None:
    """Trace slicing belongs to the same critical section as execution."""

    request = require_v2_request(_request())
    store = JobStore(str(tmp_path / "runs"))
    runtime = _runtime(request)
    first_result_ready = threading.Event()
    release_first = threading.Event()
    second_started = threading.Event()
    original_run = runtime.run_workflow_v2
    calls = 0
    calls_lock = threading.Lock()

    def delay_first_result(*args, **kwargs):
        nonlocal calls
        result = original_run(*args, **kwargs)
        with calls_lock:
            calls += 1
            call_number = calls
        if call_number == 1:
            first_result_ready.set()
            assert release_first.wait(timeout=2)
        return result

    monkeypatch.setattr(runtime, "run_workflow_v2", delay_first_result)
    errors: list[BaseException] = []

    def submit(job_id: str, started: threading.Event | None = None) -> None:
        try:
            if started is not None:
                started.set()
            submit_direct_v2_job(
                request,
                runtime=runtime,
                pack_id=_PACK_ID,
                pack_version=_PACK_VERSION,
                job_store=store,
                job_id=job_id,
            )
        except BaseException as exc:  # noqa: BLE001 - asserted after worker joins
            errors.append(exc)

    first = threading.Thread(target=submit, args=("shared-runtime-first",))
    second = threading.Thread(
        target=submit,
        args=("shared-runtime-second", second_started),
    )
    first.start()
    assert first_result_ready.wait(timeout=2)
    second.start()
    assert second_started.wait(timeout=2)
    with calls_lock:
        assert calls == 1

    release_first.set()
    first.join(timeout=2)
    second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    for job_id in ("shared-runtime-first", "shared-runtime-second"):
        loaded = store.load(job_id)
        assert [item["message_type"] for item in loaded["trace"]] == [
            "execution_plan_v2_request",
            "execution_plan_ready",
            "execution_result_ready",
        ]


def test_direct_v2_runtime_failure_retains_failed_reservation(tmp_path) -> None:
    request = require_v2_request(_request())
    store = JobStore(str(tmp_path / "runs"))
    runtime = AgentRuntime(
        RuntimeConfig(),
        bus=MessageBus(),
        clock=Clock(),
        idgen=IdGen(),
    )

    with pytest.raises(UnknownAgentError):
        submit_direct_v2_job(
            request,
            runtime=runtime,
            pack_id=_PACK_ID,
            pack_version=_PACK_VERSION,
            job_store=store,
            job_id="generic-direct-v2-failed-reservation",
        )

    failed = store.load("generic-direct-v2-failed-reservation")
    assert failed == {
        "job_id": "generic-direct-v2-failed-reservation",
        "status": "failed",
    }


def test_direct_v2_persistence_failure_retains_failed_reservation(tmp_path, monkeypatch) -> None:
    request = require_v2_request(_request())
    store = JobStore(str(tmp_path / "runs"))

    def fail_write(*_args, **_kwargs) -> None:
        raise RuntimeError("persist boom")

    monkeypatch.setattr(store, "_w", fail_write)

    with pytest.raises(RuntimeError, match="persist boom"):
        submit_direct_v2_job(
            request,
            runtime=_runtime(request),
            pack_id=_PACK_ID,
            pack_version=_PACK_VERSION,
            job_store=store,
            job_id="generic-direct-v2-persistence-failed-reservation",
        )

    assert store.load("generic-direct-v2-persistence-failed-reservation") == {
        "job_id": "generic-direct-v2-persistence-failed-reservation",
        "status": "failed",
    }


def test_reserve_status_write_failure_leaves_an_unknown_non_reusable_orphan(tmp_path, monkeypatch) -> None:
    """A failed initial reservation write keeps its ID fail-closed and inspectable."""

    store = JobStore(str(tmp_path / "runs"))
    job_id = "generic-reserve-initial-status-failure"
    original_write_new_at = store._write_new_at

    def fail_initial_status_write(directory_fd: int, name: str, text: str) -> None:
        if name == "status" and text == "reserved":
            raise OSError("initial reservation status write failed")
        original_write_new_at(directory_fd, name, text)

    monkeypatch.setattr(store, "_write_new_at", fail_initial_status_write)

    with pytest.raises(OSError, match="initial reservation status write failed"):
        store.reserve(job_id)

    root = tmp_path / "runs" / job_id
    assert (root / "status").read_text(encoding="utf-8") == "unknown"
    assert store.load(job_id) == {"job_id": job_id, "status": "unknown"}
    with pytest.raises(FileExistsError, match="already exists"):
        store.reserve(job_id)


def test_partial_reservation_status_is_unknown_and_non_reusable(tmp_path) -> None:
    """A failed marker's partial bytes can never become a recoverable state."""

    store = JobStore(str(tmp_path / "runs"))
    job_id = "generic-partial-reservation-status"
    root = tmp_path / "runs" / job_id
    root.mkdir(parents=True)
    (root / "status").write_text("res", encoding="utf-8")

    assert store.load(job_id) == {"job_id": job_id, "status": "unknown"}
    with pytest.raises(FileExistsError, match="already exists"):
        store.reserve(job_id)


def test_reservation_requires_posix_lock_before_creating_a_job_directory(tmp_path, monkeypatch) -> None:
    """Unsupported platforms fail before creating an ambiguous reservation orphan."""

    monkeypatch.setattr(job_store_module, "_fcntl", None)
    store = JobStore(str(tmp_path / "runs"))
    job_id = "generic-posix-lock-required"

    with pytest.raises(OSError, match="POSIX flock"):
        store.reserve(job_id)

    assert not (tmp_path / "runs" / job_id).exists()


def test_write_new_failure_is_terminal_and_requires_a_new_job_id(tmp_path, monkeypatch) -> None:
    """Ordinary write-new failures retain a terminal audit anchor, never a retry slot."""

    store = JobStore(str(tmp_path / "runs"))
    job_id = "generic-write-new-terminal-failure"

    def fail_write(*_args, **_kwargs) -> None:
        raise RuntimeError("ordinary write failed")

    monkeypatch.setattr(store, "_w", fail_write)

    with pytest.raises(RuntimeError, match="ordinary write failed"):
        store.save(job_id, candidate={"source": "inside"})

    assert store.load(job_id) == {"job_id": job_id, "status": "failed"}
    with pytest.raises(FileExistsError, match="already exists"):
        store.save(job_id, candidate={"source": "retry"})




def test_reserved_save_and_failure_marker_use_a_cross_process_terminal_transition(
    tmp_path,
    monkeypatch,
) -> None:
    """A separate process cannot mark a reserved job failed after save starts."""

    if os.name == "nt":
        # The implementation must reject direct reservations on this platform;
        # there is no POSIX flock contract to exercise here.
        with pytest.raises(OSError, match="POSIX flock"):
            JobStore(str(tmp_path / "runs")).reserve("generic-posix-only-reservation")
        return

    store = JobStore(str(tmp_path / "runs"))
    job_id = "generic-cross-process-terminal-transition"
    store.reserve(job_id)
    entered_write = threading.Event()
    release_write = threading.Event()
    original_write = store._w

    def pause_first_write(*args, **kwargs) -> None:
        entered_write.set()
        assert release_write.wait(timeout=5)
        original_write(*args, **kwargs)

    monkeypatch.setattr(store, "_w", pause_first_write)
    save_errors: list[BaseException] = []

    def save_reserved_job() -> None:
        try:
            store.save(job_id, candidate={"source": "inside"}, reserved=True)
        except BaseException as exc:  # noqa: BLE001 - asserted after the worker joins
            save_errors.append(exc)

    writer = threading.Thread(target=save_reserved_job)
    writer.start()
    assert entered_write.wait(timeout=5)

    context = multiprocessing.get_context("spawn")
    child_attempting_lock = context.Event()
    child_outcome = context.Queue()
    marker = context.Process(
        target=_mark_failed_reservation_in_child,
        args=(str(tmp_path / "runs"), job_id, child_attempting_lock, child_outcome),
    )
    marker.start()
    assert child_attempting_lock.wait(timeout=5)

    release_write.set()
    writer.join(timeout=5)
    marker.join(timeout=5)
    if marker.is_alive():
        marker.terminate()
        marker.join(timeout=5)
        pytest.fail("cross-process failure marker did not finish")

    assert not writer.is_alive()
    assert marker.exitcode == 0
    assert save_errors == []
    assert child_outcome.get(timeout=1) == "ValueError"
    assert store.load(job_id)["status"] == "done"


def test_failed_reservation_never_surfaces_partial_job_contents(tmp_path) -> None:
    store = JobStore(str(tmp_path / "runs"))
    store.reserve("generic-direct-v2-partial-failed")
    root = tmp_path / "runs" / "generic-direct-v2-partial-failed"
    (root / "request.json").write_text("{not-json", encoding="utf-8")
    store.mark_failed_reservation("generic-direct-v2-partial-failed")

    assert store.load("generic-direct-v2-partial-failed") == {
        "job_id": "generic-direct-v2-partial-failed",
        "status": "failed",
    }


def test_direct_v2_preserves_runtime_error_when_failure_marker_cannot_be_written(
    tmp_path,
    monkeypatch,
) -> None:
    request = require_v2_request(_request())
    store = JobStore(str(tmp_path / "runs"))
    runtime = AgentRuntime(
        RuntimeConfig(),
        bus=MessageBus(),
        clock=Clock(),
        idgen=IdGen(),
    )

    def fail_marker(_job_id: str) -> None:
        raise OSError("marker unavailable")

    monkeypatch.setattr(store, "mark_failed_reservation", fail_marker)

    with pytest.raises(UnknownAgentError):
        submit_direct_v2_job(
            request,
            runtime=runtime,
            pack_id=_PACK_ID,
            pack_version=_PACK_VERSION,
            job_store=store,
            job_id="generic-direct-v2-marker-failed",
        )

    assert store.load("generic-direct-v2-marker-failed")["status"] == "reserved"


def test_only_reserved_job_may_transition_to_failed(tmp_path) -> None:
    request = require_v2_request(_request())
    store = JobStore(str(tmp_path / "runs"))
    submitted = submit_direct_v2_job(
        request,
        runtime=_runtime(request),
        pack_id=_PACK_ID,
        pack_version=_PACK_VERSION,
        job_store=store,
        job_id="generic-direct-v2-done-state",
    )

    with pytest.raises(ValueError, match="not reserved"):
        store.mark_failed_reservation(submitted["job_id"])

    assert store.load(submitted["job_id"])["status"] == "done"


def test_done_job_with_corrupt_json_is_not_exposed_as_replayable(tmp_path) -> None:
    request = require_v2_request(_request())
    store = JobStore(str(tmp_path / "runs"))
    submitted = submit_direct_v2_job(
        request,
        runtime=_runtime(request),
        pack_id=_PACK_ID,
        pack_version=_PACK_VERSION,
        job_store=store,
        job_id="generic-direct-v2-corrupt-done",
    )
    root = tmp_path / "runs" / submitted["job_id"]
    (root / "report.json").write_text("{not-json", encoding="utf-8")

    assert store.load(submitted["job_id"]) == {
        "job_id": submitted["job_id"],
        "status": "corrupt",
    }


def test_done_job_with_unreadable_markdown_is_not_exposed_as_replayable(tmp_path) -> None:
    request = require_v2_request(_request())
    store = JobStore(str(tmp_path / "runs"))
    submitted = submit_direct_v2_job(
        request,
        runtime=_runtime(request),
        pack_id=_PACK_ID,
        pack_version=_PACK_VERSION,
        job_store=store,
        job_id="generic-direct-v2-corrupt-markdown",
    )
    root = tmp_path / "runs" / submitted["job_id"]
    (root / "report.md").write_bytes(b"\xff")

    assert store.load(submitted["job_id"]) == {
        "job_id": submitted["job_id"],
        "status": "corrupt",
    }


def test_done_job_with_deep_json_companion_is_projected_as_corrupt(tmp_path) -> None:
    """Untrusted archive JSON must not leak a decoder RecursionError."""

    store = JobStore(str(tmp_path / "runs"))
    job_id = "generic-deep-json"
    root = tmp_path / "runs" / job_id
    root.mkdir(parents=True)
    (root / "status").write_text("done", encoding="utf-8")
    (root / "request.json").write_text("[" * 20_000 + "]" * 20_000, encoding="utf-8")

    assert store.load(job_id) == {"job_id": job_id, "status": "corrupt"}


@pytest.mark.parametrize(
    "companion",
    (
        "request.json",
        "candidate_request.json",
        "report.json",
        "trace.json",
        "provenance.json",
        "execution_identity.json",
        "llm_meta.json",
        "report.md",
        "narrative_report.md",
    ),
)
def test_done_job_rejects_symlink_companions_without_reading_outside_root(tmp_path, companion: str) -> None:
    """Completed archives never follow JSON or Markdown companion symlinks."""

    store = JobStore(str(tmp_path / "runs"))
    job_id = "generic-symlink-companion"
    root = tmp_path / "runs" / job_id
    root.mkdir(parents=True)
    (root / "status").write_text("done", encoding="utf-8")
    outside = tmp_path / f"outside-{companion.replace('.', '-')}"
    outside_content = (
        "[]" if companion == "trace.json" else '{"outside": true}' if companion.endswith(".json") else "outside"
    )
    outside.write_text(outside_content, encoding="utf-8")
    (root / companion).symlink_to(outside)

    assert store.load(job_id) == {"job_id": job_id, "status": "corrupt"}


def test_done_job_rejects_a_symlinked_status_marker(tmp_path) -> None:
    """The initial status read also stays inside the job directory."""

    store = JobStore(str(tmp_path / "runs"))
    job_id = "generic-symlink-status"
    root = tmp_path / "runs" / job_id
    root.mkdir(parents=True)
    outside = tmp_path / "outside-status"
    outside.write_text("done", encoding="utf-8")
    (root / "status").symlink_to(outside)

    assert store.load(job_id) == {"job_id": job_id, "status": "corrupt"}


def test_job_directory_symlink_is_corrupt_and_not_listed(tmp_path) -> None:
    """The runs index must not turn a linked job directory into an archive root."""

    store = JobStore(str(tmp_path / "runs"))
    job_id = "generic-symlink-job"
    outside = tmp_path / "outside-job"
    outside.mkdir()
    (outside / "status").write_text("done", encoding="utf-8")
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs" / job_id).symlink_to(outside, target_is_directory=True)

    assert store.load(job_id) == {"job_id": job_id, "status": "corrupt"}
    assert store.list_jobs() == []


@pytest.mark.parametrize("link_kind", ("root", "intermediate"))
def test_job_store_never_follows_a_symlinked_runs_root(tmp_path, link_kind: str) -> None:
    """Host configuration cannot redirect JobStore writes through a root link."""

    outside = tmp_path / f"outside-{link_kind}"
    outside.mkdir()
    alias = tmp_path / f"alias-{link_kind}"
    alias.symlink_to(outside, target_is_directory=True)
    runs_root = alias if link_kind == "root" else alias / "runs"
    store = JobStore(str(runs_root))

    with pytest.raises(OSError):
        store.reserve(f"generic-{link_kind}-root-link")

    assert list(outside.iterdir()) == []
    assert store.list_jobs() == []


def test_reserve_rejects_job_id_traversal_before_creating_a_directory(tmp_path) -> None:
    store = JobStore(str(tmp_path / "runs"))

    with pytest.raises(ValueError, match="safe local identifier"):
        store.reserve("../escaped")

    assert not (tmp_path / "escaped").exists()


def test_mark_failed_rejects_job_id_traversal_before_opening_a_directory(tmp_path) -> None:
    store = JobStore(str(tmp_path / "runs"))
    outside = tmp_path / "outside"
    outside.mkdir()
    status = outside / "status"
    status.write_text("reserved", encoding="utf-8")

    with pytest.raises(ValueError, match="safe local identifier"):
        store.mark_failed_reservation("../outside")

    assert status.read_text(encoding="utf-8") == "reserved"


def test_reserve_does_not_write_through_a_job_directory_symlink(tmp_path, monkeypatch) -> None:
    """A directory swap during reservation must not create status outside runs."""

    store = JobStore(str(tmp_path / "runs"))
    outside = tmp_path / "outside-reservation"
    outside.mkdir()
    original_new_dir = store._new_job_directory

    def replace_new_directory(job_id: str):
        directory, directory_fd = original_new_dir(job_id)
        os.close(directory_fd)
        directory.rmdir()
        directory.symlink_to(outside, target_is_directory=True)
        return directory, store._open_job_directory(job_id)

    monkeypatch.setattr(store, "_new_job_directory", replace_new_directory)

    with pytest.raises(OSError):
        store.reserve("generic-reservation-directory-swap")

    assert not (outside / "status").exists()


def test_write_new_save_does_not_write_through_a_job_directory_symlink(tmp_path, monkeypatch) -> None:
    """A swap after write-new directory creation cannot redirect archive writes."""

    store = JobStore(str(tmp_path / "runs"))
    outside = tmp_path / "outside-write-new"
    outside.mkdir()
    original_new_dir = store._new_job_directory

    def replace_new_directory(job_id: str):
        directory, directory_fd = original_new_dir(job_id)
        os.close(directory_fd)
        directory.rmdir()
        directory.symlink_to(outside, target_is_directory=True)
        return directory, store._open_job_directory(job_id)

    monkeypatch.setattr(store, "_new_job_directory", replace_new_directory)

    with pytest.raises(OSError):
        store.save("generic-write-new-directory-swap", candidate={"source": "inside"})

    assert not (outside / "candidate_request.json").exists()
    assert not (outside / "status").exists()


def test_write_new_save_failure_never_cleans_a_replaced_job_directory(tmp_path, monkeypatch) -> None:
    """A post-pin failure retains its own audit anchor, never removes a path replacement."""

    store = JobStore(str(tmp_path / "runs"))
    job_id = "generic-write-new-cleanup-swap"
    job = tmp_path / "runs" / job_id
    displaced = tmp_path / "displaced-job"

    def replace_then_fail(*_args, **_kwargs) -> None:
        job.rename(displaced)
        job.mkdir()
        (job / "protected").write_text("outside", encoding="utf-8")
        raise RuntimeError("write failed")

    monkeypatch.setattr(store, "_w", replace_then_fail)

    with pytest.raises(RuntimeError, match="write failed"):
        store.save(job_id, candidate={"source": "inside"})

    assert (job / "protected").read_text(encoding="utf-8") == "outside"
    assert (displaced / "status").read_text(encoding="utf-8") == "failed"


@pytest.mark.parametrize(
    ("operation", "expected_error"),
    (("save", FileExistsError), ("mark_failed", FileNotFoundError)),
)
@pytest.mark.parametrize("replacement", ("directory", "status"))
def test_reserved_write_paths_do_not_follow_replaced_symlinks(
    tmp_path,
    operation: str,
    expected_error: type[Exception],
    replacement: str,
) -> None:
    """A reserved job can never turn save/failure marking into an outside write."""

    store = JobStore(str(tmp_path / "runs"))
    job_id = f"generic-reserved-{operation}-{replacement}-swap"
    store.reserve(job_id)
    job = tmp_path / "runs" / job_id
    outside = tmp_path / f"outside-{operation}-{replacement}"
    outside.mkdir()
    (outside / "status").write_text("reserved", encoding="utf-8")

    if replacement == "directory":
        (job / "status").unlink()
        job.rmdir()
        job.symlink_to(outside, target_is_directory=True)
    else:
        (job / "status").unlink()
        (job / "status").symlink_to(outside / "status")

    with pytest.raises(expected_error):
        if operation == "save":
            store.save(job_id, candidate={"source": "inside"}, reserved=True)
        else:
            store.mark_failed_reservation(job_id)

    assert (outside / "status").read_text(encoding="utf-8") == "reserved"
    assert not (outside / "candidate_request.json").exists()


@pytest.mark.parametrize(
    ("operation", "expected_error"),
    (("save", FileExistsError), ("mark_failed", FileNotFoundError)),
)
def test_reserved_status_hardlink_is_rejected_without_mutating_its_peer(
    tmp_path,
    operation: str,
    expected_error: type[Exception],
) -> None:
    """Reservation status is private to its job, never a writable hardlink peer."""

    store = JobStore(str(tmp_path / "runs"))
    job_id = f"generic-reserved-hardlink-{operation}"
    store.reserve(job_id)
    job = tmp_path / "runs" / job_id
    outside_status = tmp_path / f"outside-hardlink-{operation}-status"
    outside_status.write_text("reserved", encoding="utf-8")
    (job / "status").unlink()
    os.link(outside_status, job / "status")

    with pytest.raises(expected_error):
        if operation == "save":
            store.save(job_id, candidate={"source": "inside"}, reserved=True)
        else:
            store.mark_failed_reservation(job_id)

    assert outside_status.read_text(encoding="utf-8") == "reserved"
    assert not (job / "candidate_request.json").exists()


def test_load_does_not_follow_a_status_symlink_swapped_after_path_check(tmp_path, monkeypatch) -> None:
    """Reading a completed status must use one nofollow file descriptor."""

    store = JobStore(str(tmp_path / "runs"))
    job_id = "generic-read-status-swap"
    job = tmp_path / "runs" / job_id
    job.mkdir(parents=True)
    status = job / "status"
    status.write_text("done", encoding="utf-8")
    outside = tmp_path / "outside-read-status"
    outside.write_text("outside-secret", encoding="utf-8")
    original_read_text = Path.read_text

    def replace_before_path_read(path: Path, *args, **kwargs):
        if path == status:
            status.unlink()
            status.symlink_to(outside)
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", replace_before_path_read)

    assert store.load(job_id) == {"job_id": job_id, "status": "done"}


def test_load_does_not_follow_a_companion_symlink_swapped_after_path_check(tmp_path, monkeypatch) -> None:
    """Companion reads must use the same nofollow descriptor boundary."""

    store = JobStore(str(tmp_path / "runs"))
    job_id = "generic-read-companion-swap"
    job = tmp_path / "runs" / job_id
    job.mkdir(parents=True)
    (job / "status").write_text("done", encoding="utf-8")
    request = job / "request.json"
    request.write_text('{"source": "inside"}', encoding="utf-8")
    outside = tmp_path / "outside-read-companion"
    outside.write_text('{"source": "outside-secret"}', encoding="utf-8")
    original_read_text = Path.read_text

    def replace_before_path_read(path: Path, *args, **kwargs):
        if path == request:
            request.unlink()
            request.symlink_to(outside)
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", replace_before_path_read)

    assert store.load(job_id) == {
        "job_id": job_id,
        "status": "done",
        "request": {"source": "inside"},
    }


def test_direct_v2_job_rejects_scope_and_trace_tampering_on_load(tmp_path) -> None:
    request = require_v2_request(_request())
    store = JobStore(str(tmp_path / "runs"))
    submitted = submit_direct_v2_job(
        request,
        runtime=_runtime(request),
        pack_id=_PACK_ID,
        pack_version=_PACK_VERSION,
        job_store=store,
        job_id="generic-direct-v2-tamper",
    )
    root = tmp_path / "runs" / submitted["job_id"]

    report_path = root / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["execution_scope"] = "production"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    assert store.load(submitted["job_id"])["execution_identity"]["available"] is False

    report["execution_scope"] = "research_only"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    report["provenance"]["pack_view_receipt"]["assets"][0]["path"] = "forbidden"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    assert store.load(submitted["job_id"])["execution_identity"]["available"] is False

    report["provenance"]["pack_view_receipt"]["assets"][0].pop("path")
    report_path.write_text(json.dumps(report), encoding="utf-8")
    trace_path = root / "trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    secret = "/private/raw-message-payload"
    trace[1]["payload"] = {"private_path": secret}
    trace_path.write_text(json.dumps(trace), encoding="utf-8")
    loaded = store.load(submitted["job_id"])
    assert loaded["execution_identity"]["available"] is False
    assert loaded["trace"] == []
    assert secret not in json.dumps(loaded, sort_keys=True)


def test_direct_v3_rejects_unknown_provenance_fields_before_public_persistence(tmp_path) -> None:
    """Direct V3 has a closed public provenance schema, not a copy-through bag."""

    request = require_v2_request(_request())
    _plan, result = _v3_reduced_result(request)
    result["provenance"]["private_path"] = "/private/reducer-source.py"
    result["structured_report"]["provenance"] = result["provenance"]
    store = JobStore(str(tmp_path / "runs"))
    job_id = "generic-direct-v3-unknown-provenance"
    store.reserve(job_id)

    with pytest.raises(ValueError, match="unsupported fields"):
        store.save(job_id, request=request.to_dict(), result=result, reserved=True)

    assert not (tmp_path / "runs" / job_id / "provenance.json").exists()


def test_direct_v2_runtime_provenance_is_a_closed_public_contract(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A tampered runtime result cannot turn provenance into a public payload bag."""

    request = require_v2_request(_request())
    runtime = _runtime(request)
    original = runtime.run_workflow_v2

    def with_private_provenance(*args, **kwargs):
        report = original(*args, **kwargs)
        report["provenance"]["private_path"] = "/private/runtime-provenance"
        return report

    monkeypatch.setattr(runtime, "run_workflow_v2", with_private_provenance)
    store = JobStore(str(tmp_path / "runs"))

    with pytest.raises(ValueError, match="unsupported fields"):
        submit_direct_v2_job(
            request,
            runtime=runtime,
            pack_id=_PACK_ID,
            pack_version=_PACK_VERSION,
            job_store=store,
            job_id="generic-direct-v2-runtime-private-provenance",
        )

    assert store.load("generic-direct-v2-runtime-private-provenance") == {
        "job_id": "generic-direct-v2-runtime-private-provenance",
        "status": "failed",
    }


def test_direct_v2_identity_requires_all_replay_companions(tmp_path) -> None:
    request = require_v2_request(_request())
    store = JobStore(str(tmp_path / "runs"))
    submitted = submit_direct_v2_job(
        request,
        runtime=_runtime(request),
        pack_id=_PACK_ID,
        pack_version=_PACK_VERSION,
        job_store=store,
        job_id="generic-direct-v2-complete",
    )
    source = tmp_path / "runs" / submitted["job_id"] / "execution_identity.json"
    incomplete = tmp_path / "runs" / "generic-direct-v2-identity-only"
    incomplete.mkdir()
    (incomplete / "status").write_text("done", encoding="utf-8")
    (incomplete / "execution_identity.json").write_text(
        source.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    identity = store.load(incomplete.name)["execution_identity"]
    assert identity["available"] is False


def test_direct_v3_reduced_job_persists_v5_identity_and_receipt(tmp_path) -> None:
    """A reducer-bound V3 completion must write a distinct, replayable v5 ID."""

    request = require_v2_request(_request())
    plan, result = _v3_reduced_result(request)
    store = JobStore(str(tmp_path / "runs"))
    store.reserve("generic-direct-v3-reduced")
    store.save(
        "generic-direct-v3-reduced",
        request=request.to_dict(),
        result=result,
        reserved=True,
    )

    loaded = store.load("generic-direct-v3-reduced")
    identity = loaded["execution_identity"]
    assert identity["schema_version"] == "vc.job-execution-identity.v5"
    assert identity["execution_contract"] == "vc.direct-v2-execution.v1"
    assert identity["plan_schema_version"] == "vc.execution-plan.v3"
    assert identity["outcome"] == {
        "abstain": False,
        "models_used": [step.model_name for step in plan.steps],
        "prediction_present": True,
    }
    assert identity["output_reducer"] == plan.output_reducer.to_dict()
    assert len(identity["output_reducer_receipt_fingerprint"]) == 64


def test_direct_v3_real_generic_runtime_submission_persists_v5(tmp_path) -> None:
    """The real Broker/runtime path, not a fabricated report, writes V5."""

    from praxis_virtualcell.tests.test_direct_v2_multi_model_reducer import (
        _runtime_with_mean_policy,
    )

    request, runtime, _adapter, zoo, policy = _runtime_with_mean_policy(tmp_path / "runtime")
    store = JobStore(str(tmp_path / "runs"))

    submitted = submit_direct_v2_job(
        request,
        runtime=runtime,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
        job_store=store,
        job_id="generic-direct-v3-real-runtime",
    )

    loaded = store.load("generic-direct-v3-real-runtime")
    identity = loaded["execution_identity"]
    assert submitted == {"job_id": "generic-direct-v3-real-runtime", "status": "done"}
    assert loaded["report"]["prediction"]["values"] == [0.5]
    assert identity["schema_version"] == "vc.job-execution-identity.v5"
    assert identity["outcome"]["models_used"] == zoo.capability_names()
    assert identity["output_reducer"] == policy.binding().to_dict()
    public = json.dumps(loaded, sort_keys=True)
    assert "entrypoint" not in public
    assert "model_input" not in public


def test_execution_plan_v3_rejects_a_tampered_executable_flag() -> None:
    request = require_v2_request(_request())
    plan, _result = _v3_reduced_result(request)
    raw = plan.to_dict()
    raw["executable"] = False

    with pytest.raises(ValueError, match="executable must match"):
        ExecutionPlanV3.from_dict(raw)


def test_direct_v3_partial_execution_hard_abstention_persists_v5_without_reducer_receipt(
    tmp_path,
) -> None:
    """A failed later step never leaves a reduced prediction or receipt behind."""

    request = require_v2_request(_request())
    plan, result = _v3_reduced_result(request)
    result = json.loads(json.dumps(result))
    provenance = result["provenance"]
    first_name, second_name = (step.model_name for step in plan.steps)
    provenance["per_call_hashes"] = {first_name: provenance["per_call_hashes"][first_name]}
    provenance.pop("output_reducer_receipt")
    result["structured_report"].update(
        {
            "execution_status": "abstained",
            "execution_scope": None,
            "scientifically_validated": False,
            "prediction": None,
            "models_used": [],
            "models_rejected": [],
            "models_failed": [second_name],
            "abstain": True,
            "abstain_reasons": ["adapter_execution_failed"],
            "reliability": "low",
            "runtime_confidence": "low",
            "provenance": provenance,
        }
    )
    store = JobStore(str(tmp_path / "runs"))
    store.reserve("generic-direct-v3-partial-hard-abstain")
    store.save(
        "generic-direct-v3-partial-hard-abstain",
        request=request.to_dict(),
        result=result,
        reserved=True,
    )

    identity = store.load("generic-direct-v3-partial-hard-abstain")["execution_identity"]
    assert identity["schema_version"] == "vc.job-execution-identity.v5"
    assert identity["outcome"] == {
        "abstain": True,
        "models_used": [],
        "prediction_present": False,
    }
    assert identity["output_reducer_receipt_fingerprint"] is None


def test_direct_v3_reducer_receipt_tampering_is_not_replayable(tmp_path) -> None:
    request = require_v2_request(_request())
    _plan, result = _v3_reduced_result(request)
    store = JobStore(str(tmp_path / "runs"))
    job_id = "generic-direct-v3-reducer-tamper"
    store.reserve(job_id)
    store.save(job_id, request=request.to_dict(), result=result, reserved=True)

    provenance_path = tmp_path / "runs" / job_id / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["output_reducer_receipt"]["step_receipts"].reverse()
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    report_path = tmp_path / "runs" / job_id / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["provenance"] = provenance
    report_path.write_text(json.dumps(report), encoding="utf-8")

    assert store.load(job_id)["execution_identity"] == {
        "schema_version": None,
        "available": False,
        "reason": "unsupported_or_invalid_execution_identity",
    }


def test_direct_v3_requires_the_direct_execution_contract_marker(tmp_path) -> None:
    """V3 never falls back to the older generic V2 identity branch."""

    request = require_v2_request(_request())
    _plan, result = _v3_reduced_result(request)
    result = json.loads(json.dumps(result))
    result["provenance"].pop("execution_contract")
    result["structured_report"]["provenance"] = result["provenance"]
    store = JobStore(str(tmp_path / "runs"))
    job_id = "generic-direct-v3-marker-required"
    store.reserve(job_id)

    with pytest.raises(ValueError, match="direct-v3 execution contract marker is missing"):
        store.save(job_id, request=request.to_dict(), result=result, reserved=True)

    assert not (tmp_path / "runs" / job_id / "execution_identity.json").exists()


def test_direct_v3_corrupt_reducer_metadata_never_enters_public_loaded_job(tmp_path) -> None:
    """A malformed archived reducer object cannot reflect a local path publicly."""

    request = require_v2_request(_request())
    _plan, result = _v3_reduced_result(request)
    store = JobStore(str(tmp_path / "runs"))
    job_id = "generic-direct-v3-public-reducer-redaction"
    store.reserve(job_id)
    store.save(job_id, request=request.to_dict(), result=result, reserved=True)

    provenance_path = tmp_path / "runs" / job_id / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    secret = "/private/reducer-source.py"
    provenance["execution_plan"]["output_reducer"]["entrypoint"] = secret
    provenance["output_reducer_receipt"]["entrypoint"] = secret
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    report_path = tmp_path / "runs" / job_id / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["provenance"] = provenance
    report_path.write_text(json.dumps(report), encoding="utf-8")

    loaded = store.load(job_id)

    assert secret not in json.dumps(loaded, sort_keys=True)
    assert loaded["execution_identity"]["available"] is False


def test_direct_v3_pathlike_reducer_identifiers_never_enter_public_loaded_job(tmp_path) -> None:
    """Even schema-shaped archive tampering must not echo rooted identifiers."""

    request = require_v2_request(_request())
    _plan, result = _v3_reduced_result(request)
    store = JobStore(str(tmp_path / "runs"))
    job_id = "generic-direct-v3-public-reducer-identifiers"
    store.reserve(job_id)
    store.save(job_id, request=request.to_dict(), result=result, reserved=True)

    secret = "/private/reducer-source.py"
    provenance_path = tmp_path / "runs" / job_id / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["execution_plan"]["output_reducer"]["policy_version"] = secret
    provenance["output_reducer_receipt"]["step_receipts"][0]["model_name"] = secret
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    report_path = tmp_path / "runs" / job_id / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["provenance"] = provenance
    report_path.write_text(json.dumps(report), encoding="utf-8")

    loaded = store.load(job_id)

    assert secret not in json.dumps(loaded, sort_keys=True)
    assert loaded["execution_identity"]["available"] is False


def test_direct_v3_empty_plan_without_pack_persists_v5_hard_abstention(tmp_path) -> None:
    """V3 remains auditably fail-closed even before any Pack is bound."""

    request = require_v2_request(_request())
    reducer_plan, _result = _v3_reduced_result(request)
    report_value = reducer_plan.reports[0].to_dict()
    report_value.update(
        {
            "pack_id": None,
            "pack_version": None,
            "pack_fingerprint": None,
            "pack_valid": False,
            "executable": False,
            "reasons": ["pack.unregistered"],
        }
    )
    report = type(reducer_plan.reports[0]).from_dict(report_value)
    plan = ExecutionPlanV3.build(
        request_id=reducer_plan.request_id,
        request_fingerprint=reducer_plan.request_fingerprint,
        pack_id=None,
        pack_version=None,
        pack_fingerprint=None,
        environment_snapshot_fingerprint=reducer_plan.environment_snapshot_fingerprint,
        output_reducer=reducer_plan.output_reducer,
        reports=(report,),
        steps=(),
    )
    provenance = {
        "execution_contract": "vc.direct-v2-execution.v1",
        "execution_plan": plan.to_dict(),
        "compatibility_reports": [report.to_dict()],
        "adapter_input_receipts": {},
        "per_call_hashes": {},
    }
    result = {
        "structured_report": {
            "request_id": plan.request_id,
            "request_fingerprint": plan.request_fingerprint,
            "execution_status": "abstained",
            "execution_scope": None,
            "scientifically_validated": False,
            "prediction": None,
            "models_used": [],
            "models_rejected": [report.model_name],
            "models_failed": [],
            "abstain": True,
            "abstain_reasons": ["execution_plan_not_executable", "pack_required"],
            "reliability": "low",
            "runtime_confidence": "low",
            "provenance": provenance,
        },
        "provenance": provenance,
        "trace": _direct_v2_trace(),
        "narrative": None,
    }
    store = JobStore(str(tmp_path / "runs"))
    job_id = "generic-direct-v3-empty-no-pack"
    store.reserve(job_id)
    store.save(job_id, request=request.to_dict(), result=result, reserved=True)

    identity = store.load(job_id)["execution_identity"]
    assert identity["schema_version"] == "vc.job-execution-identity.v5"
    assert identity["pack"] is None
    assert identity["execution_step_model_names"] == []
    assert identity["outcome"]["abstain"] is True
