"""v0.6:praxis-vc 命令行入口。

  praxis-vc run  --request examples/ahr_k562.json --mode offline --out runs/ahr
  praxis-vc ask  --text "在 human 细胞里敲掉 AHR 会怎么样" --mode llm-assisted --out runs/ahr_llm
  praxis-vc serve --host 127.0.0.1 --port 8000        # FastAPI(需 [api] extra)
  praxis-vc web  --api http://127.0.0.1:8000          # Streamlit(需 [web] extra)

React 正式网站(praxis_vc_react/,只读展示,不参与预测/治理决策):
  开发:另起 `cd praxis_vc_react && npm run dev`(5173),serve 作后端。
  生产:`cd praxis_vc_react && npm run build` 后,serve 会自动把 dist 挂到 "/"
        (同源),浏览器开 http://127.0.0.1:8000 即前端+后端。

默认 offline;llm-assisted 需 .env 有 DEEPSEEK_API_KEY,否则自动 fallback。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from importlib.resources import files

from praxis_virtualcell import __version__


def _config(mode: str):
    from praxis_virtualcell.core.config import Mode, RuntimeConfig
    if mode in ("llm-assisted", "llm_assisted"):
        os.environ["PRAXIS_VIRTUALCELL_MODE"] = "llm_assisted"
        return RuntimeConfig.from_env()
    return RuntimeConfig(mode=Mode.OFFLINE, llm_enabled=False)


def _cmd_run(a) -> int:
    from praxis_virtualcell.io.job_store import JobStore
    from praxis_virtualcell.workflows.run_virtualcell_query import run_query
    cfg = _config(a.mode)
    req = json.loads(open(a.request, encoding="utf-8").read())
    out = run_query(req, config=cfg, enable_llm_report=a.llm_report)
    if a.out:
        JobStore(os.path.dirname(a.out) or "runs").save(os.path.basename(a.out), request=req, result=out)
    print(json.dumps({"reliability_decision": out["reliability_decision"],
                      "llm_used_for_prediction": out["llm_used_for_prediction"],
                      "mode": out["mode"]}, ensure_ascii=False, indent=2))
    return 0


def _cmd_ask(a) -> int:
    from praxis_virtualcell.io.job_store import JobStore
    from praxis_virtualcell.workflows.run_virtualcell_query import parse_query, run_query
    cfg = _config(a.mode)
    parsed = parse_query(a.text, config=cfg)
    print("== parsed ==")
    print(json.dumps({"candidate_request": parsed["candidate_request"], "parser": parsed["parser"],
                      "schema_valid": parsed["schema_valid"], "missing_fields": parsed["missing_fields"],
                      "llm_used": parsed["llm_used"], "fallback_used": parsed["fallback_used"]},
                     ensure_ascii=False, indent=2))
    if not parsed["schema_valid"]:
        print("== clarification_required ==", parsed["missing_fields"] or parsed["errors"])
        return 2
    if not a.yes:
        print("(加 --yes 确认执行;或用 web/API 的确认页)")
        return 0
    out = run_query(parsed["candidate_request"], config=cfg, enable_llm_report=a.llm_report)
    if a.out:
        JobStore(os.path.dirname(a.out) or "runs").save(os.path.basename(a.out),
                 candidate=parsed["candidate_request"], result={**out, "parsed": parsed})
    print("== reliability_decision ==")
    print(json.dumps(out["reliability_decision"], ensure_ascii=False, indent=2))
    return 0


def _cmd_serve(a) -> int:
    import uvicorn
    uvicorn.run("praxis_vc_api.main:app", host=a.host, port=a.port, reload=False)
    return 0


def _cmd_web(a) -> int:
    os.environ["PRAXIS_VC_API"] = a.api
    import subprocess
    app_path = files("praxis_vc_web").joinpath("app.py")
    return subprocess.call([sys.executable, "-m", "streamlit", "run",
                            str(app_path), "--server.address", a.host, "--server.port", str(a.port)])


def _json_file(path: str) -> dict:
    with open(path, encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError("JSON input must be an object")
    return value


def _print_json(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _cmd_pack_inspect(a) -> int:
    from praxis_virtualcell.pack_product import inspect_pack

    _print_json(inspect_pack(a.pack_root))
    return 0


def _cmd_pack_validate(a) -> int:
    from praxis_virtualcell.pack_product import validate_pack_summary

    result = validate_pack_summary(a.pack_root)
    _print_json(result)
    return 0 if result["pack_valid"] else 2


def _cmd_pack_register(a) -> int:
    from praxis_virtualcell.pack_factory import (
        PackCandidateV1,
        PackFactoryStore,
        PackMetadataReviewV1,
        PackOperatorDecisionV1,
        PackValidationReportV1,
        bind_pack_candidate,
        load_factory_contract,
        load_quarantined_upload,
        register_pack_candidate,
    )
    from praxis_virtualcell.pack_product import PackIndex

    upload = load_quarantined_upload(a.upload_directory)
    candidate = load_factory_contract(a.candidate, PackCandidateV1)
    review = load_factory_contract(a.review, PackMetadataReviewV1)
    validation = load_factory_contract(a.validation, PackValidationReportV1)
    decision = load_factory_contract(a.decision, PackOperatorDecisionV1)
    prepared = bind_pack_candidate(upload, a.pack_root, candidate)
    index = PackIndex(index_path=a.index)
    store = PackFactoryStore.open(a.store)
    registration = register_pack_candidate(
        prepared,
        review,
        validation,
        decision,
        index=index,
        store=store,
    )
    _print_json(
        {
            **registration.to_dict(),
            "registration_fingerprint": registration.fingerprint(),
        }
    )
    return 0


def _cmd_pack_list(a) -> int:
    from praxis_virtualcell.pack_product import pack_catalog_payload

    _print_json(pack_catalog_payload())
    return 0


def _cmd_pack_compatibility(a) -> int:
    from praxis_virtualcell.pack_product import compatibility_payload

    _print_json(
        compatibility_payload(
            _json_file(a.request),
            pack_id=a.pack_id,
            pack_version=a.pack_version,
        )
    )
    return 0


def _cmd_pack_run(a) -> int:
    from praxis_virtualcell.io.job_store import JobStore
    from praxis_virtualcell.pack_product import run_pack_query

    request = _json_file(a.request)
    result = run_pack_query(
        request,
        pack_id=a.pack_id,
        pack_version=a.pack_version,
        config=_config(a.mode),
        enable_llm_report=a.llm_report,
    )
    if a.out:
        JobStore(os.path.dirname(a.out) or "runs").save(
            os.path.basename(a.out),
            request=request,
            result=result,
        )
    _print_json(
        {
            "reliability_decision": result["reliability_decision"],
            "llm_used_for_prediction": result["llm_used_for_prediction"],
            "mode": result["mode"],
            "pack_id": a.pack_id,
            "pack_version": a.pack_version,
        }
    )
    return 0


def _pack_identity_arguments(parser) -> None:
    parser.add_argument("--pack-id", required=True)
    parser.add_argument("--pack-version", required=True)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="praxis-vc", description="PRAXIS-VirtualCell 本地科学家界面")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="从 request JSON 跑一次(离线确定性)")
    r.add_argument("--request", required=True)
    r.add_argument("--mode", default="offline")
    r.add_argument("--out", default=None)
    r.add_argument("--llm-report", action="store_true", dest="llm_report")
    r.set_defaults(fn=_cmd_run)
    k = sub.add_parser("ask", help="自然语言提问 → 解析 → (--yes)执行")
    k.add_argument("--text", required=True)
    k.add_argument("--mode", default="offline")
    k.add_argument("--out", default=None)
    k.add_argument("--yes", action="store_true")
    k.add_argument("--llm-report", action="store_true", dest="llm_report")
    k.set_defaults(fn=_cmd_ask)
    s = sub.add_parser("serve", help="启动 FastAPI 本地服务")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.set_defaults(fn=_cmd_serve)
    w = sub.add_parser("web", help="启动 Streamlit 本地网页")
    w.add_argument("--api", default="http://127.0.0.1:8000")
    w.add_argument("--host", default="127.0.0.1")
    w.add_argument("--port", type=int, default=8501)
    w.set_defaults(fn=_cmd_web)
    pack = sub.add_parser("pack", help="检查、注册和运行 VirtualCellPack")
    pack_sub = pack.add_subparsers(dest="pack_cmd", required=True)
    inspect_cmd = pack_sub.add_parser(
        "inspect",
        help="解析 manifest；不读取资产，不声明 Pack 有效",
    )
    inspect_cmd.add_argument("pack_root")
    inspect_cmd.set_defaults(fn=_cmd_pack_inspect)
    validate_cmd = pack_sub.add_parser(
        "validate",
        help="重验 manifest、资产和数据语义",
    )
    validate_cmd.add_argument("pack_root")
    validate_cmd.set_defaults(fn=_cmd_pack_validate)
    register_cmd = pack_sub.add_parser(
        "register",
        help="以完整 P19 receipt/review/validation/operator chain 写入本地索引",
    )
    register_cmd.add_argument("--upload-directory", required=True)
    register_cmd.add_argument("--pack-root", required=True)
    register_cmd.add_argument("--candidate", required=True)
    register_cmd.add_argument("--review", required=True)
    register_cmd.add_argument("--validation", required=True)
    register_cmd.add_argument("--decision", required=True)
    register_cmd.add_argument("--index", required=True)
    register_cmd.add_argument("--store", required=True)
    register_cmd.set_defaults(fn=_cmd_pack_register)
    list_cmd = pack_sub.add_parser(
        "list",
        help="列出内置和已注册 Pack，并逐项重验",
    )
    list_cmd.set_defaults(fn=_cmd_pack_list)
    compatibility_cmd = pack_sub.add_parser(
        "compatibility",
        help="计算请求、Pack、模型和环境兼容性；不执行模型",
    )
    compatibility_cmd.add_argument("--request", required=True)
    _pack_identity_arguments(compatibility_cmd)
    compatibility_cmd.set_defaults(fn=_cmd_pack_compatibility)
    pack_run_cmd = pack_sub.add_parser(
        "run",
        help="按 Pack identity 执行；无可执行模型时诚实弃权",
    )
    pack_run_cmd.add_argument("--request", required=True)
    _pack_identity_arguments(pack_run_cmd)
    pack_run_cmd.add_argument("--mode", default="offline")
    pack_run_cmd.add_argument("--out", default=None)
    pack_run_cmd.add_argument(
        "--llm-report",
        action="store_true",
        dest="llm_report",
    )
    pack_run_cmd.set_defaults(fn=_cmd_pack_run)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
