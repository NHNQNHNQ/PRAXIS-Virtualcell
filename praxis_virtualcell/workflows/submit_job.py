"""Single, explicit submission seam for generic direct-v2 jobs."""

from __future__ import annotations

import hashlib
import json

from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2
from praxis_virtualcell.core.runtime import AgentRuntime
from praxis_virtualcell.io.job_store import JobStore
from praxis_virtualcell.workflows.runtime_builder import DirectV2RuntimeFactory

DIRECT_V2_EXECUTION_CONTRACT = "vc.direct-v2-execution.v1"


class DirectV2FactoryUnconfigured(RuntimeError):
    """Raised when a direct-v2 host did not explicitly supply a runtime factory."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _public_trace(messages: list[object]) -> list[dict]:
    """Project the direct execution spine without retaining any message payload."""

    trace: list[dict] = []
    for message in messages:
        payload = getattr(message, "payload", None)
        if not isinstance(payload, dict):
            raise ValueError("direct-v2 message payload must be structured")
        trace.append(
            {
                "schema_version": getattr(message, "schema_version", None),
                "message_id": getattr(message, "message_id", None),
                "sender": getattr(message, "sender", None),
                "receiver": getattr(message, "receiver", None),
                "message_type": getattr(message, "message_type", None),
                "timestamp": getattr(message, "timestamp", None),
                "parent_message_id": getattr(message, "parent_message_id", None),
                "trace_id": getattr(message, "trace_id", None),
                "task_id": getattr(message, "task_id", None),
                "payload_fingerprint": _fingerprint(payload),
            }
        )
    return trace


def submit_direct_v2_job(
    request: VirtualCellRequestV2,
    *,
    runtime: AgentRuntime,
    pack_id: str | None,
    pack_version: str | None,
    job_store: JobStore,
    job_id: str,
) -> dict[str, str]:
    """Run and persist one direct-v2 job through the shared upstream seam.

    This intentionally accepts only an already-validated ``VirtualCellRequestV2``.
    It neither constructs a legacy request nor selects a task-specific runtime.
    """

    if not isinstance(request, VirtualCellRequestV2):
        raise TypeError("submit_direct_v2_job requires VirtualCellRequestV2")
    if not isinstance(runtime, AgentRuntime):
        raise TypeError("submit_direct_v2_job requires AgentRuntime")
    if not isinstance(job_store, JobStore):
        raise TypeError("submit_direct_v2_job requires JobStore")
    # Keep the public Python seam as strict as the factory/HTTP paths.  The
    # runtime repeats this check so direct callers cannot bypass it either.
    from praxis_virtualcell.core.config import Mode, RuntimeConfig, assert_llm_boundaries
    from praxis_virtualcell.core.exceptions import InputValidationError

    if not isinstance(runtime.config, RuntimeConfig):
        raise TypeError("direct-v2 runtime must have RuntimeConfig")
    if runtime.config.mode != Mode.OFFLINE or runtime.config.llm_enabled:
        raise InputValidationError("direct-v2 runtime requires offline mode with LLM disabled")
    assert_llm_boundaries(runtime.config)

    job_store.reserve(job_id)
    try:
        with runtime.execution_context():
            trace_start = len(runtime.bus.trace)
            report = runtime.run_workflow_v2(
                request,
                pack_id=pack_id,
                pack_version=pack_version,
            )
            provenance = report.get("provenance")
            if not isinstance(provenance, dict) or (
                provenance.get("execution_contract") != DIRECT_V2_EXECUTION_CONTRACT
            ):
                raise RuntimeError("direct-v2 runtime did not produce its execution contract")
            result = {
                "structured_report": report,
                "provenance": provenance,
                "trace": _public_trace(runtime.bus.trace[trace_start:]),
                "narrative": None,
                "mode": "direct_v2",
                "llm_enabled": False,
                "llm_used_for_prediction": False,
            }
        job_store.save(
            job_id,
            request=request.to_dict(),
            result=result,
            reserved=True,
        )
    except Exception as exc:
        try:
            job_store.mark_failed_reservation(job_id)
        except Exception as marker_exc:  # noqa: BLE001 - original execution error remains authoritative
            exc.add_note(f"direct-v2 failed-reservation marker unavailable: {marker_exc!r}")
        raise
    return {"job_id": job_id, "status": "done"}


def submit_direct_v2_job_from_factory(
    request: VirtualCellRequestV2,
    *,
    factory: DirectV2RuntimeFactory | None,
    pack_id: str,
    pack_version: str,
    job_store: JobStore,
    job_id: str,
) -> dict[str, str]:
    """Build one explicit offline runtime, then enter the sole direct-v2 seam.

    Hosts must inject a fully constructed ``DirectV2RuntimeFactory``.  This
    helper deliberately does not infer a Pack, model registry, adapter,
    wrapper, domain extension, or plugin from request data or environment.
    """

    if factory is None:
        raise DirectV2FactoryUnconfigured("direct-v2 factory is not configured")
    if not isinstance(factory, DirectV2RuntimeFactory):
        raise TypeError("direct-v2 factory must be DirectV2RuntimeFactory")
    if not isinstance(pack_id, str) or not pack_id or pack_id.strip() != pack_id:
        raise ValueError("direct-v2 requires an exact pack_id")
    if not isinstance(pack_version, str) or not pack_version or pack_version.strip() != pack_version:
        raise ValueError("direct-v2 requires an exact pack_version")

    return submit_direct_v2_job(
        request,
        runtime=factory.build(),
        pack_id=pack_id,
        pack_version=pack_version,
        job_store=job_store,
        job_id=job_id,
    )
