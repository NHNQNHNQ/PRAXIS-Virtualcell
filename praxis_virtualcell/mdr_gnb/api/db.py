"""9.2 持久化层:同步 SQLAlchemy。

``make_engine(None)`` 作为低层 helper 仍默认 SQLite，便于显式本地调用；标准
MDR ASGI 不会在 URL 未设或空白时调用它，因此默认服务是内存模式。PostgreSQL
驱动、迁移与 .53 运行时均未在此模块中得到验证。

只存轻量元数据 + 可回放产物:job metadata、input manifest、prediction output、
trace hash、model/registry/db 版本。不存大模型/大文件(joblib 在文件系统)。
provenance 可追溯红线:trace_hash + registry_version + db_version 入库。
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON, Boolean, DateTime, Integer, String, Text, create_engine, select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

# schema 版本:表结构或审计写入语义变更时 +1(入库随每条 prediction,供审计)。v2 添加
# ``prediction_executions`` append-only 表；v3 为本地 SQLite 添加 DML guard，不改写或伪造
# v1/v2 ``predictions`` 历史。
DB_VERSION = "3"

DEFAULT_SQLITE_URL = "sqlite:///./data/mdr_gnb/mdr_api.db"


class Base(DeclarativeBase):
    pass


class Prediction(Base):
    __tablename__ = "predictions"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    species: Mapped[str] = mapped_column(String(64), index=True)
    drug: Mapped[str] = mapped_column(String(64), index=True)
    sir: Mapped[str | None] = mapped_column(String(4), nullable=True)
    abstained: Mapped[bool] = mapped_column(Boolean)
    output_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    trace_hash: Mapped[str] = mapped_column(String(64))
    registry_version: Mapped[str] = mapped_column(String(32))
    db_version: Mapped[str] = mapped_column(String(8))
    input_manifest: Mapped[dict] = mapped_column(JSON)
    report: Mapped[dict] = mapped_column(JSON)
    trace: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class PredictionExecution(Base):
    """One immutable persisted execution, including repeated identical requests.

    ``Prediction`` remains the backwards-compatible latest-by-task snapshot used
    by /trace/{task_id}.  This table is deliberately separate and has no foreign
    key to it, so a pre-v2 database can acquire the new table without rewriting
    or deleting its legacy latest records.
    """

    __tablename__ = "prediction_executions"

    execution_record_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    task_id: Mapped[str] = mapped_column(String(64), index=True)
    execution_id: Mapped[str] = mapped_column(String(64), index=True)
    species: Mapped[str] = mapped_column(String(64), index=True)
    drug: Mapped[str] = mapped_column(String(64), index=True)
    sir: Mapped[str | None] = mapped_column(String(4), nullable=True)
    abstained: Mapped[bool] = mapped_column(Boolean)
    output_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    trace_hash: Mapped[str] = mapped_column(String(64))
    registry_version: Mapped[str] = mapped_column(String(32))
    db_version: Mapped[str] = mapped_column(String(8))
    input_manifest: Mapped[dict] = mapped_column(JSON)
    report: Mapped[dict] = mapped_column(JSON)
    trace: Mapped[list] = mapped_column(JSON)
    trace_metadata: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime)


def trace_hash(trace: list[dict[str, Any]]) -> str:
    """确定性 trace 指纹(canonical JSON → sha256)。供跨系统校验 replay 一致。"""
    blob = json.dumps(trace, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def registry_version(
    *,
    lifecycle_identity: dict[str, Any] | None = None,
    governance_snapshot: dict[str, Any] | None = None,
) -> str:
    """Registry + catalog + governance sources + safety policy 的可审计版本号。"""
    from praxis_virtualcell.mdr_gnb.api.service import (
        RUNTIME_POLICY_VERSION,
        governance_snapshot_identity,
        model_lifecycle_identity,
    )
    from praxis_virtualcell.mdr_gnb.predictors.default_registry import build_default_registry
    sig = sorted(f"{s.name}@{s.version}" for s in build_default_registry().all_specs())
    identity = dict(lifecycle_identity or model_lifecycle_identity())
    governance = dict(governance_snapshot or governance_snapshot_identity())
    sig.extend([
        f"catalog_sha256={identity['catalog_digest']}",
        f"governance_sha256={governance['governance_digest']}",
        f"runtime_policy={RUNTIME_POLICY_VERSION}",
    ])
    return hashlib.sha256("\n".join(sig).encode("utf-8")).hexdigest()[:16]


def resolve_db_url(url: str | None = None) -> str:
    """Helper URL 解析:非空显式值 > 非空 env 值 > SQLite 默认。

    This helper-level fallback is intentionally distinct from the ASGI factory,
    which requires a nonblank URL before constructing an engine at all.
    """
    explicit = url.strip() if url is not None else ""
    configured = os.environ.get("MDR_DB_URL", "").strip()
    return explicit or configured or DEFAULT_SQLITE_URL


def make_engine(url: str | None = None) -> Engine:
    resolved = resolve_db_url(url)
    if resolved.startswith("sqlite:///") and ":memory:" not in resolved:
        # 确保 sqlite 目录存在
        path = resolved.replace("sqlite:///", "", 1)
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
    return create_engine(resolved, future=True)


def _install_sqlite_execution_history_guards(engine: Engine) -> None:
    """Make the SQLite execution audit table append-only at the database layer.

    This deliberately protects only ``prediction_executions``.  The legacy
    ``predictions`` table is a latest-by-task compatibility snapshot and must
    remain replaceable by :class:`PredictionRepo`.  PostgreSQL and operational
    database governance need a separately reviewed migration; SQLite-specific
    DDL must never be sent to another dialect.
    """
    if engine.dialect.name != "sqlite":
        return

    statements = (
        """
        CREATE TRIGGER IF NOT EXISTS prediction_executions_no_update
        BEFORE UPDATE ON prediction_executions
        BEGIN
            SELECT RAISE(ABORT, 'prediction_executions is append-only');
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS prediction_executions_no_delete
        BEFORE DELETE ON prediction_executions
        BEGIN
            SELECT RAISE(ABORT, 'prediction_executions is append-only');
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS prediction_executions_no_replace
        BEFORE INSERT ON prediction_executions
        WHEN NEW.execution_record_id IS NOT NULL
          AND EXISTS (
              SELECT 1 FROM prediction_executions
              WHERE execution_record_id = NEW.execution_record_id
          )
        BEGIN
            SELECT RAISE(ABORT, 'prediction_executions is append-only');
        END
        """,
    )
    with engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    _install_sqlite_execution_history_guards(engine)


class PredictionRepo:
    """Latest task snapshot plus additive, per-execution audit history."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save_prediction(self, response: dict[str, Any], trace_record: dict[str, Any],
                        *, registry_version: str, now: datetime | None = None) -> int:
        """Persist one new audit execution and refresh the legacy latest snapshot.

        The returned primary key is intentionally storage-local rather than part
        of the deterministic HTTP response.  Repeated requests with the same
        content-addressed ``execution_id`` still receive distinct records; a
        cache hit does not invoke this method and therefore is not mislabeled as
        a fresh scientific execution.
        """
        report = response["report"]
        task_id = response["task_id"]
        recorded_at = now or datetime.now(timezone.utc)
        trace = trace_record["trace"]
        fields = {
            "task_id": task_id,
            "species": response.get("species", "") or "",
            "drug": response.get("drug", "") or report.get("drug", "") or "",
            "sir": report.get("sir"),
            "abstained": bool(report.get("abstained")),
            "output_kind": report.get("output_kind"),
            "trace_hash": trace_hash(trace),
            "registry_version": registry_version,
            "db_version": DB_VERSION,
            "input_manifest": trace_record.get("input_manifest", {}),
            "report": report,
            "trace": trace,
            "created_at": recorded_at,
        }
        # ``execution_id`` is a stricter content identity than ``task_id``: it
        # includes catalog/governance/policy facts.  It is separately indexed so
        # audit tooling can group repeat runs without collapsing them.
        execution_id = str(
            trace_record.get("execution_id")
            or response.get("execution_id")
            or f"legacy-{fields['trace_hash']}"
        )
        with Session(self._engine) as s:
            execution = PredictionExecution(
                execution_id=execution_id,
                trace_metadata=dict(trace_record.get("trace_metadata") or {}),
                **fields,
            )
            s.add(execution)
            s.flush()
            existing = s.get(Prediction, task_id)
            if existing is not None:
                s.delete(existing)
                s.flush()
            s.add(Prediction(**fields))
            s.commit()
            return int(execution.execution_record_id)

    def get(self, task_id: str) -> dict[str, Any] | None:
        with Session(self._engine) as s:
            row = s.get(Prediction, task_id)
            if row is None:
                return None
            return _to_dict(row)

    def list_ids(self) -> list[str]:
        with Session(self._engine) as s:
            return list(s.scalars(select(Prediction.task_id)))

    def list_execution_summaries(self, task_id: str) -> list[dict[str, Any]]:
        """Return chronological metadata without exposing stored raw requests."""
        with Session(self._engine) as s:
            rows = list(s.scalars(
                select(PredictionExecution)
                .where(PredictionExecution.task_id == task_id)
                .order_by(PredictionExecution.execution_record_id)
            ))
        return [_execution_summary(row) for row in rows]

    def get_execution(self, execution_record_id: int) -> dict[str, Any] | None:
        with Session(self._engine) as s:
            row = s.get(PredictionExecution, execution_record_id)
            if row is None:
                return None
            return _execution_to_dict(row)


def _to_dict(row: Prediction) -> dict[str, Any]:
    return {
        "task_id": row.task_id,
        "species": row.species,
        "drug": row.drug,
        "sir": row.sir,
        "abstained": row.abstained,
        "output_kind": row.output_kind,
        "trace_hash": row.trace_hash,
        "registry_version": row.registry_version,
        "db_version": row.db_version,
        "input_manifest": row.input_manifest,
        "report": row.report,
        "trace": row.trace,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _execution_summary(row: PredictionExecution) -> dict[str, Any]:
    return {
        "execution_record_id": row.execution_record_id,
        "task_id": row.task_id,
        "execution_id": row.execution_id,
        "trace_hash": row.trace_hash,
        "registry_version": row.registry_version,
        "db_version": row.db_version,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _execution_to_dict(row: PredictionExecution) -> dict[str, Any]:
    return {
        **_execution_summary(row),
        "species": row.species,
        "drug": row.drug,
        "sir": row.sir,
        "abstained": row.abstained,
        "output_kind": row.output_kind,
        "input_manifest": row.input_manifest,
        "report": row.report,
        "trace": row.trace,
        "trace_metadata": row.trace_metadata,
    }
