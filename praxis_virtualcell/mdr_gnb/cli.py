"""Dedicated local CLI for the MDR-GNB production contract.

This command intentionally does not reuse ``praxis-vc``: that command belongs
to the generic VirtualCell product and speaks a different request/API protocol.
``praxis-mdr run`` normalizes exactly as FastAPI does, then delegates to the
same service adapter.  It therefore does not create a second scientific or
governance decision path.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load_normalized_request(args: argparse.Namespace) -> dict[str, Any] | None:
    """Read one JSON object and apply the same schema projection as ``/predict``.

    A malformed/non-object payload returns a stable non-zero CLI result instead
    of letting a separate CLI-only schema reach the scientific core.
    """
    try:
        if args.stdin:
            payload = json.load(sys.stdin)
        else:
            with Path(args.request).open(encoding="utf-8") as handle:
                payload = json.load(handle)
    except json.JSONDecodeError as exc:
        print(f"invalid JSON: {exc.msg}", file=sys.stderr)
        return None
    except OSError as exc:
        print(f"cannot read request: {exc}", file=sys.stderr)
        return None

    if not isinstance(payload, dict):
        print("invalid request JSON: expected an object", file=sys.stderr)
        return None

    from pydantic import ValidationError

    from praxis_virtualcell.mdr_gnb.api.schemas import PredictRequest

    try:
        return PredictRequest.model_validate(payload).to_raw()
    except ValidationError as exc:
        print(f"invalid request schema: {exc}", file=sys.stderr)
        return None


def _cmd_run(args: argparse.Namespace) -> int:
    raw = _load_normalized_request(args)
    if raw is None:
        return 2

    # ``service.predict`` is also what FastAPI calls after ``PredictRequest``
    # normalization.  It binds the governance context, model lifecycle, runtime
    # evidence and active-learning advisory; a direct core call here would skip
    # those API-facing, auditable contract fields.
    from praxis_virtualcell.mdr_gnb.api import service

    # Mirror the HTTP adapter's model-integrity boundary.  A CLI has no response
    # cache, but it must not turn an unreadable catalog into a traceback or a
    # later core-level hard-abstain that HTTP would have reported as unavailable.
    preflight = service.runtime_model_execution_context(raw)
    if preflight.context is None:
        print("runtime_model_preflight_unavailable", file=sys.stderr)
        return 1
    try:
        preflight.context.assert_current()
    except Exception:  # noqa: BLE001 - do not expose runtime/filesystem details
        print("request_artifact_integrity_drift", file=sys.stderr)
        return 1

    response = service.predict(raw, runtime_model_preflight=preflight)["response"]
    print(json.dumps(
        response,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ))
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    # Lazy import keeps ``praxis-mdr run`` usable without initializing a web
    # server.  The target is deliberately the MDR ASGI app, not the generic
    # ``praxis_vc_api`` service used by the legacy ``praxis-vc`` command.
    import uvicorn

    uvicorn.run(
        "praxis_virtualcell.mdr_gnb.api.asgi:app",
        host=args.host,
        port=args.port,
        reload=False,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="praxis-mdr",
        description="PRAXIS-MDR-GNB 的确定性本地 CLI（与 /predict 共用合同）",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="以与 FastAPI 相同的 schema 运行一次 MDR 请求")
    source = run.add_mutually_exclusive_group(required=True)
    source.add_argument("--request", metavar="FILE", help="请求 JSON 文件")
    source.add_argument("--stdin", action="store_true", help="从标准输入读取请求 JSON")
    run.set_defaults(handler=_cmd_run)

    serve = subparsers.add_parser("serve", help="启动 MDR FastAPI/ASGI 服务")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8099)
    serve.set_defaults(handler=_cmd_serve)

    args = parser.parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
