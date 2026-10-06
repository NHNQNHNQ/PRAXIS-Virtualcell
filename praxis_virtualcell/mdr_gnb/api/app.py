"""FastAPI app 工厂:把 mdr_gnb 服务层暴露成只读 API。

端点:/health /species /models /predict /trace/{task_id} /executions/{task_id}
/execution/{record_id} /jobs。
科学决策全在 run_mdr_query;本层只做 HTTP 适配 + trace 存取,不重算。
仅非空 db_url 才让 /predict 落库（本地 SQLite 有回归；PG/部署尚未验证）；
/trace 内存未命中时才回落该显式配置的 DB（跨重启可回放）。
公开 trace/replay 一律是脱敏投影；完整输入和 trace 留在服务端存储，访问控制/保留
策略仍是独立的未闭合治理项。
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from praxis_virtualcell.mdr_gnb.api import service
from praxis_virtualcell.mdr_gnb.api.schemas import PredictRequest
from praxis_virtualcell.mdr_gnb.api.store import JobStore


def _assert_runtime_model_context_current(context: object) -> None:
    """Translate a post-cache-read model receipt drift into a safe API failure."""
    try:
        context.assert_current()  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001 - do not expose filesystem/runtime details
        raise HTTPException(
            status_code=503,
            detail="request_artifact_integrity_drift",
            headers={"X-MDR-Cache": "bypass"},
        ) from exc


def _trace_metadata_from_events(trace: list[dict]) -> dict:
    """Recover the version/hash spine from persisted trace events without a DB migration.

    ``Prediction`` rows predate the explicit ``trace_metadata`` field.  The
    append-only event payloads are therefore the authoritative fallback for a
    restart replay: no current scientific decision is reconstructed or changed.
    """
    parsed: dict = {}
    governance: dict = {}
    critic: dict = {}
    report: dict = {}
    response_advisory: dict = {}
    for event in trace:
        payload = event.get("payload") or {}
        message_type = event.get("message_type")
        if message_type == "task_parsed":
            parsed = payload
        elif message_type == "governance_snapshot_bound":
            governance = payload
        elif message_type == "critic_checked":
            critic = payload
        elif message_type == "report_built":
            report = payload
        elif message_type == "response_advisory_built":
            response_advisory = {
                "schema_version": payload.get("schema_version"),
                "advisory_policy_version": payload.get("advisory_policy_version"),
                "message_id": event.get("message_id"),
                "parent_message_id": event.get("parent_message_id"),
                "payload_sha256": payload.get("payload_sha256"),
            }
    metadata = {
        "schema_version": parsed.get("schema_version"),
        "input_sha256": parsed.get("input_sha256"),
        "report_sha256": report.get("report_sha256"),
        "critic_policy_version": critic.get("policy_version"),
        "governance_snapshot_digest": governance.get("governance_digest"),
    }
    if response_advisory:
        metadata["response_advisory"] = response_advisory
    return metadata


def _redact_public_trace(trace: list[dict]) -> list[dict]:
    """Return a public trace projection without request-level biological inputs.

    Trace events intentionally retain the original parent/message spine.  The
    persisted full trace remains in server-side storage; this projection does
    not itself establish an authorization or retention policy.  The returned
    hash therefore identifies that full stored trace, not this redacted view.
    """
    # ``request`` is deliberately redacted as a whole: it can grow with new
    # request-schema fields, so allowlisting individual biological inputs would
    # silently leak new fields.  The direct keys protect future trace events
    # that may carry a request field outside that wrapper.
    sensitive_keys = {
        "amr_profile",
        "assay_context",
        "compound",
        "features",
        "input_manifest",
        "raw",
        "request",
        "sequence",
        "smiles",
    }

    def redact(value):
        if isinstance(value, dict):
            return {
                key: ({"redacted": True} if key in sensitive_keys else redact(child))
                for key, child in value.items()
            }
        if isinstance(value, list):
            return [redact(item) for item in value]
        return value

    return redact(trace)


def _public_trace_record(record: dict) -> dict:
    """Project an in-memory trace record for unauthenticated HTTP replay.

    The original object is never mutated: the memory store and repository retain
    their full record, while every public replay shares one conservative
    projection.  This redaction is not a substitute for storage access control.
    """
    public = {key: value for key, value in record.items() if key != "input_manifest"}
    public["trace"] = _redact_public_trace(record["trace"])
    public["trace_redacted"] = True
    public["trace_hash_scope"] = "stored_full_trace"
    return public


def _persisted_trace_record(row: dict, *, redact_execution_trace: bool = False) -> dict:
    """Project a persisted latest/execution row into the public replay shape.

    The database retains the raw input manifest for internal reproducibility, but
    public replay deliberately exposes hashes and redacted events, not the
    original AMR profile.  The same projection is used by ``/trace`` and
    ``/execution``.
    """
    stored_trace = row["trace"]
    trace = _redact_public_trace(stored_trace) if redact_execution_trace else stored_trace
    record = {
        "task_id": row["task_id"],
        "trace": trace,
        "trace_metadata": dict(
            row.get("trace_metadata") or _trace_metadata_from_events(trace)
        ),
        "route": (row["report"].get("provenance", {}) or {}).get("route"),
        "capability": (row["report"].get("provenance", {}) or {}).get("capability"),
        "trace_hash": row["trace_hash"],
        "registry_version": row["registry_version"],
    }
    for key in ("execution_record_id", "execution_id", "db_version", "created_at"):
        if key in row:
            record[key] = row[key]
    if redact_execution_trace:
        record["trace_redacted"] = True
        record["trace_hash_scope"] = "stored_full_trace"
    return record


def create_app(db_url: str | None = None, cache=None, static_root: str | None = None) -> FastAPI:
    """A nonblank db_url opts into persistence; otherwise use memory only.

    ``MDR_DB_URL`` is environment sourced, so an empty or whitespace-only value
    must mean the same thing as absent.  Treating it as a database request would
    otherwise invoke the lower-level SQLite helper default and unexpectedly retain
    raw trace inputs.  ``cache`` is optional response caching; ``static_root``
    optionally serves a same-origin frontend build.
    """
    if db_url is not None:
        db_url = db_url.strip() or None
    app = FastAPI(title="PRAXIS-MDR-GNB API", version="0.9")
    store = JobStore()

    # 放行 Vite dev(5173)跨源:前端只读展示,不影响后端科学决策。
    # 生产同源(FastAPI 托管 dist)无需 CORS。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # 可选持久化：只有显式、非空 URL 才建 repo。标准 ASGI 默认纯内存；
    # SQLite 仅有本地合同，PostgreSQL/.53 不在此处分配运行时保证。
    repo = None
    if db_url is not None:
        from praxis_virtualcell.mdr_gnb.api.db import (
            PredictionRepo, init_db, make_engine, registry_version,
        )
        engine = make_engine(db_url)
        init_db(engine)
        repo = PredictionRepo(engine)

    @app.get("/health")
    def health() -> dict:
        supported = service.supported_species()
        return {
            "status": "ok",
            "service": "praxis-mdr-gnb",
            "n_species_supported": len(supported),
            "n_species_total": len(service.SPECIES_FRAMEWORK),
            "persistence": "on" if repo is not None else "memory",
            "cache": "on" if cache is not None else "off",
        }

    @app.get("/species")
    def species() -> dict:
        return {"species": service.species_status()}

    @app.get("/models")
    def models() -> dict:
        return service.models_summary()

    @app.post("/predict")
    def predict(body: PredictRequest, response: Response) -> dict:
        raw = body.to_raw()
        # Bind one content-addressed execution identity before cache lookup and
        # pass the same facts through the core trace and persistence record. A
        # rules/evidence file changing mid-request must never leave a report
        # stored under the preceding governance cache namespace.
        runtime_model_preflight = service.runtime_model_execution_context(raw)
        if runtime_model_preflight.context is None:
            # A response cache must never act as an availability fallback for an
            # unreadable model catalog.  Returning an explicit service failure is
            # more honest than replaying an older prediction under unknown state.
            raise HTTPException(
                status_code=503,
                detail="runtime_model_preflight_unavailable",
                headers={"X-MDR-Cache": "bypass"},
            )
        lifecycle_identity = dict(runtime_model_preflight.lifecycle_identity)
        requested_model_integrity = dict(
            runtime_model_preflight.requested_model_integrity
        )
        # Capture source bytes once before cache lookup.  The same private
        # context supplies the cache identity, core decision inputs, response
        # evidence, and persisted public snapshot; no later stage re-opens a
        # mutable governance file under this execution namespace.
        governance_context = service.governance_execution_context()
        governance_snapshot = dict(governance_context.snapshot)
        cache_key = service.execution_cache_key(
            raw,
            lifecycle_identity=lifecycle_identity,
            governance_snapshot=governance_snapshot,
            requested_model_integrity=requested_model_integrity,
        )
        # Cache admission follows the request-scoped model preflight.  If the
        # catalog cannot be observed, never replay or write a stale response.
        hit = None
        if cache is not None and runtime_model_preflight.cacheable:
            hit = cache.get(cache_key)
        # This check happens after cache I/O but before either a cache return or
        # core execution.  A catalog/source/artifact change in that interval must
        # never replay or write a response under the preceding receipt.
        _assert_runtime_model_context_current(runtime_model_preflight.context)
        if hit is not None:
            if service.cache_response_matches_execution(
                hit,
                execution_id=cache_key,
                lifecycle_identity=lifecycle_identity,
                governance_snapshot=governance_snapshot,
                requested_model_integrity=requested_model_integrity,
            ):
                response.headers["X-MDR-Cache"] = "hit"
                return hit
        result = service.predict(
            raw,
            lifecycle_identity=lifecycle_identity,
            governance_snapshot=governance_snapshot,
            governance_context=governance_context,
            runtime_model_preflight=runtime_model_preflight,
        )
        rec = result["trace_record"]
        store.put(rec["task_id"], rec)              # 内存(快)
        if repo is not None:                         # 落库(可回放,provenance 入库)
            repo.save_prediction(
                result["response"],
                rec,
                registry_version=registry_version(
                    lifecycle_identity=lifecycle_identity,
                    governance_snapshot=governance_snapshot,
                ),
            )
        if cache is not None and runtime_model_preflight.cacheable:
            cache.set(cache_key, result["response"])
            response.headers["X-MDR-Cache"] = "miss"
        elif cache is not None:
            response.headers["X-MDR-Cache"] = "bypass"
        return result["response"]

    @app.get("/trace/{task_id}")
    def trace(task_id: str) -> dict:
        rec = store.get(task_id)
        if rec is None and repo is not None:         # 内存未命中回落 DB(跨重启)
            row = repo.get(task_id)
            if row is not None:
                rec = _persisted_trace_record(row, redact_execution_trace=True)
        if rec is None:
            raise HTTPException(status_code=404, detail="task_id not found")
        # Repository fallback is already projected.  In-memory records must
        # receive exactly the same public redaction before HTTP serialization.
        return rec if rec.get("trace_redacted") is True else _public_trace_record(rec)

    @app.get("/executions/{task_id}")
    def executions(task_id: str) -> dict:
        """List immutable persisted execution metadata for one raw task ID."""
        if repo is None:
            raise HTTPException(status_code=404, detail="persistence disabled")
        rows = repo.list_execution_summaries(task_id)
        if not rows:
            raise HTTPException(status_code=404, detail="task_id not found")
        return {"task_id": task_id, "executions": rows}

    @app.get("/execution/{execution_record_id}")
    def execution(execution_record_id: int) -> dict:
        """Replay one immutable persisted execution without exposing raw input."""
        if repo is None:
            raise HTTPException(status_code=404, detail="persistence disabled")
        row = repo.get_execution(execution_record_id)
        if row is None:
            raise HTTPException(status_code=404, detail="execution not found")
        return _persisted_trace_record(row, redact_execution_trace=True)

    @app.get("/jobs")
    def jobs() -> dict:
        """已落库 job 列表(仅持久化模式)。"""
        if repo is not None:
            return {"jobs": repo.list_ids(), "source": "db"}
        return {"jobs": store.all_ids(), "source": "memory"}

    # 同源托管前端构建产物(生产 .53:API 与 SPA 同源,免 CORS)。
    # html=True → 目录访问回退 index.html;API 路由已先注册,优先级更高。
    if static_root is not None:
        from pathlib import Path

        from fastapi.staticfiles import StaticFiles
        root = Path(static_root)
        if root.is_dir():
            app.mount("/", StaticFiles(directory=str(root), html=True), name="spa")

    return app
