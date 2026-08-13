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
    from praxis_virtualcell.workflows.run_virtualcell_query import run_formal_query

    cfg = _config(a.mode)
    req = json.loads(open(a.request, encoding="utf-8").read())
    out = run_formal_query(req, config=cfg, enable_llm_report=a.llm_report)
    if a.out:
        JobStore(os.path.dirname(a.out) or "runs").save(os.path.basename(a.out), request=req, result=out)
    print(
        json.dumps(
            {
                "reliability_decision": out["reliability_decision"],
                "llm_used_for_prediction": out["llm_used_for_prediction"],
                "mode": out["mode"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _cmd_ask(a) -> int:
    from praxis_virtualcell.io.job_store import JobStore
    from praxis_virtualcell.workflows.run_virtualcell_query import (
        parse_query,
        run_formal_query,
    )

    cfg = _config(a.mode)
    parsed = parse_query(a.text, config=cfg)
    print("== parsed ==")
    print(
        json.dumps(
            {
                "candidate_request": parsed["candidate_request"],
                "parser": parsed["parser"],
                "schema_valid": parsed["schema_valid"],
                "missing_fields": parsed["missing_fields"],
                "llm_used": parsed["llm_used"],
                "fallback_used": parsed["fallback_used"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not parsed["schema_valid"]:
        print("== clarification_required ==", parsed["missing_fields"] or parsed["errors"])
        return 2
    if not a.yes:
        print("(加 --yes 确认执行;或用 web/API 的确认页)")
        return 0
    out = run_formal_query(
        parsed["candidate_request"],
        config=cfg,
        enable_llm_report=a.llm_report,
    )
    if a.out:
        JobStore(os.path.dirname(a.out) or "runs").save(
            os.path.basename(a.out), candidate=parsed["candidate_request"], result={**out, "parsed": parsed}
        )
    print("== reliability_decision ==")
    print(json.dumps(out["reliability_decision"], ensure_ascii=False, indent=2))
    return 0


def _cmd_serve(a) -> int:
    import uvicorn

    from praxis_vc_api.main import app, configure_direct_v2_factory

    try:
        factory = _direct_v2_factory(a)
    except (OSError, TypeError, ValueError):
        _print_json({"status": "rejected", "reason": "golden_research_configuration_invalid"})
        return 2
    configure_direct_v2_factory(
        factory,
        research_tasks=_golden_research_tasks() if a.golden_registration_root is not None else (),
    )
    try:
        uvicorn.run(app, host=a.host, port=a.port, reload=False)
    finally:
        configure_direct_v2_factory(None)
    return 0


def _golden_research_tasks() -> tuple[dict, ...]:
    from praxis_virtualcell.model_zoo.golden_additive_research import (
        MODEL_NAME,
        MODEL_VERSION,
        PACK_ID,
        PACK_VERSION,
        golden_ahr_klf1_request,
    )

    return (
        {
            "schema_version": "vc.research-task.v1",
            "task_id": "norman-2019-ahr-klf1-research",
            "request": golden_ahr_klf1_request().to_dict(),
            "pack_id": PACK_ID,
            "pack_version": PACK_VERSION,
            "model_name": MODEL_NAME,
            "model_version": MODEL_VERSION,
            "execution_scope": "research_only",
            "scientifically_validated": False,
        },
    )


def _cmd_web(a) -> int:
    os.environ["PRAXIS_VC_API"] = a.api
    import subprocess

    app_path = files("praxis_vc_web").joinpath("app.py")
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path),
            "--server.address",
            a.host,
            "--server.port",
            str(a.port),
        ]
    )


def _json_file(path: str) -> dict:
    with open(path, encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError("JSON input must be an object")
    return value


def _print_json(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _direct_v2_factory(a):
    supplied = (
        a.golden_registration_root,
        a.golden_pack_root,
        a.golden_model_cache_root,
    )
    if any(value is not None for value in supplied):
        if not all(value is not None for value in supplied) or a.direct_v2_factory is not None:
            raise ValueError("Golden runtime roots must be supplied together without an injected factory")
        from praxis_virtualcell.model_zoo.golden_additive_research import (
            load_golden_additive_research,
        )

        return load_golden_additive_research(
            registration_root=a.golden_registration_root,
            pack_root=a.golden_pack_root,
            model_cache_root=a.golden_model_cache_root,
        ).factory()
    return a.direct_v2_factory


def _golden_runtime_arguments(parser) -> None:
    parser.add_argument("--golden-registration-root")
    parser.add_argument("--golden-pack-root")
    parser.add_argument("--golden-model-cache-root")


def _cmd_pack_inspect(a) -> int:
    from praxis_virtualcell.pack_product import inspect_pack

    _print_json(inspect_pack(a.pack_root))
    return 0


def _cmd_pack_validate(a) -> int:
    from praxis_virtualcell.pack_product import validate_pack_summary

    result = validate_pack_summary(a.pack_root)
    _print_json(result)
    return 0 if result["pack_valid"] else 2


def _load_factory_upload(data_root_value: str, upload_id_value: str):
    import uuid
    from pathlib import Path

    from praxis_virtualcell.pack_factory import (
        PackFactoryError,
        load_quarantined_upload,
    )

    requested_data_root = Path(data_root_value)
    try:
        data_root = requested_data_root.resolve(strict=True)
    except OSError as exc:
        raise PackFactoryError("data root is unavailable") from exc
    if (
        not requested_data_root.is_absolute()
        or requested_data_root.is_symlink()
        or requested_data_root != data_root
        or not data_root.is_dir()
    ):
        raise PackFactoryError("data root must be an explicit canonical real directory")

    uploads = data_root / "uploads"
    quarantine = uploads / "quarantine"
    for directory, label in ((uploads, "uploads"), (quarantine, "quarantine")):
        try:
            valid = not directory.is_symlink() and directory.is_dir() and directory.resolve(strict=True) == directory
        except OSError as exc:
            raise PackFactoryError(f"{label} directory is unavailable") from exc
        if not valid:
            raise PackFactoryError(f"{label} must be a canonical real non-symlink directory")

    try:
        parsed_upload_id = uuid.UUID(upload_id_value)
    except ValueError as exc:
        raise PackFactoryError("upload id must be a canonical UUIDv4") from exc
    if parsed_upload_id.version != 4 or str(parsed_upload_id) != upload_id_value:
        raise PackFactoryError("upload id must be a canonical UUIDv4")
    return data_root, uploads, load_quarantined_upload(quarantine / upload_id_value)


def _cmd_pack_factory_init(a) -> int:
    from pathlib import Path

    from praxis_virtualcell.pack_factory import PackFactoryError, PackFactoryStore

    _, uploads, upload = _load_factory_upload(a.data_root, a.upload_id)

    store_path = Path(a.store)
    if not store_path.is_absolute():
        raise PackFactoryError("factory store root must be an explicit absolute path")
    try:
        resolved_store_path = store_path.resolve(strict=False)
    except OSError as exc:
        raise PackFactoryError("factory store path is unavailable") from exc
    if resolved_store_path == uploads or uploads in resolved_store_path.parents:
        raise PackFactoryError("factory store must be outside the data-root uploads subtree")

    store = PackFactoryStore.create(store_path)
    receipt_fingerprint = store.record_upload(upload)
    _print_json(
        {
            "schema_version": "vc.pack-factory-init.v1",
            "status": "receipt_recorded",
            "upload_id": upload.receipt.upload_id,
            "receipt_fingerprint": receipt_fingerprint,
            "store_root": str(store.root),
            "candidate_created": False,
            "factory_registered": False,
            "scientifically_validated": False,
            "executable": False,
        }
    )
    return 0


def _cmd_pack_candidate_prepare(a) -> int:
    from pathlib import Path

    from praxis_virtualcell.pack_factory import (
        PackFactoryError,
        PackFactoryStore,
        UploadReceiptV1,
        load_pack_candidate_authoring,
        prepare_pack_candidate,
    )

    _, uploads, upload = _load_factory_upload(a.data_root, a.upload_id)
    store = PackFactoryStore.open(a.store)
    if store.get(UploadReceiptV1, upload.receipt.fingerprint()) != upload.receipt:
        raise PackFactoryError("factory store does not bind the exact upload receipt")

    raw_pack = Path(a.pack_root)
    raw_authoring = Path(a.authoring)
    if not raw_pack.is_absolute() or not raw_authoring.is_absolute():
        raise PackFactoryError("candidate Pack and authoring paths must be absolute")
    try:
        pack_root = raw_pack.resolve(strict=True)
        authoring_path = raw_authoring.resolve(strict=True)
    except OSError as exc:
        raise PackFactoryError("candidate Pack or authoring path is unavailable") from exc
    if raw_pack.is_symlink() or not pack_root.is_dir() or pack_root != raw_pack:
        raise PackFactoryError("candidate Pack root must be canonical and non-symlink")
    if raw_authoring.is_symlink() or raw_authoring != authoring_path:
        raise PackFactoryError("candidate authoring file must be canonical and non-symlink")
    if (
        pack_root == uploads
        or uploads in pack_root.parents
        or pack_root == store.root
        or store.root in pack_root.parents
        or pack_root in store.root.parents
        or authoring_path == pack_root
        or pack_root in authoring_path.parents
        or authoring_path == uploads
        or uploads in authoring_path.parents
        or authoring_path == store.root
        or store.root in authoring_path.parents
    ):
        raise PackFactoryError("candidate Pack and authoring file must stay outside uploads, store, and each other")

    authoring = load_pack_candidate_authoring(authoring_path)
    prepared = prepare_pack_candidate(
        upload,
        pack_root,
        source_asset_id=authoring["source_asset_id"],
        mapping_asset_ids=authoring["mapping_asset_ids"],
        value_semantics=authoring["value_semantics"],
        units=authoring["units"],
        claim_origins=authoring["claim_origins"],
    )
    candidate_fingerprint = store.record_candidate(prepared)
    candidate_path = store.root / "candidates" / f"{candidate_fingerprint}.json"
    _print_json(
        {
            "schema_version": "vc.pack-candidate-prepare-result.v1",
            "status": "candidate_unvalidated",
            "upload_id": upload.receipt.upload_id,
            "receipt_fingerprint": upload.receipt.fingerprint(),
            "candidate_fingerprint": candidate_fingerprint,
            "candidate_path": str(candidate_path),
            "pack_valid": None,
            "review_created": False,
            "validation_performed": False,
            "factory_registered": False,
            "model_compatible": None,
            "scientifically_validated": False,
            "executable": False,
        }
    )
    return 0


def _cmd_pack_candidate_validate(a) -> int:
    from praxis_virtualcell.pack_factory import (
        PackCandidateV1,
        PackFactoryError,
        PackFactoryStore,
        PackMetadataReviewV1,
        bind_pack_candidate,
        load_factory_contract,
        validate_metadata_review,
        validate_pack_candidate,
    )

    _, _, upload = _load_factory_upload(a.data_root, a.upload_id)
    store = PackFactoryStore.open(a.store)
    candidate = load_factory_contract(a.candidate, PackCandidateV1)
    if store.get(PackCandidateV1, candidate.fingerprint()) != candidate:
        raise PackFactoryError("factory store does not bind the exact candidate")
    review = load_factory_contract(a.review, PackMetadataReviewV1)
    prepared = bind_pack_candidate(upload, a.pack_root, candidate)
    review = validate_metadata_review(prepared, review)
    review_fingerprint = store.record(review)
    report = validate_pack_candidate(prepared, review)
    validation_fingerprint = store.record_validation(prepared, review, report)
    _print_json(
        {
            "schema_version": "vc.pack-candidate-validate-result.v1",
            "status": "validated" if report.passed else "validation_failed",
            "candidate_fingerprint": candidate.fingerprint(),
            "review_fingerprint": review_fingerprint,
            "review_path": str(store.root / "reviews" / f"{review_fingerprint}.json"),
            "validation_report_fingerprint": validation_fingerprint,
            "validation_path": str(store.root / "validations" / f"{validation_fingerprint}.json"),
            "pack_valid": report.pack_valid,
            "registration_allowed": report.registration_allowed,
            "factory_registered": False,
            "model_compatible": None,
            "scientifically_validated": False,
            "executable": False,
        }
    )
    return 0 if report.passed and report.registration_allowed else 2


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


def _cmd_direct_v2_run(a) -> int:
    """Submit an explicit direct-v2 job through the injected generic factory."""

    from praxis_virtualcell.core.request_v2 import require_v2_request
    from praxis_virtualcell.io.job_store import JobStore
    from praxis_virtualcell.workflows.submit_job import (
        DirectV2FactoryUnconfigured,
        submit_direct_v2_job_from_factory,
    )

    try:
        factory = _direct_v2_factory(a)
    except (OSError, TypeError, ValueError):
        _print_json(
            {
                "status": "rejected",
                "reason": "golden_research_configuration_invalid",
            }
        )
        return 2
    request = require_v2_request(_json_file(a.request))
    try:
        result = submit_direct_v2_job_from_factory(
            request,
            factory=factory,
            pack_id=a.pack_id,
            pack_version=a.pack_version,
            job_store=JobStore(os.path.dirname(a.out) or "runs"),
            job_id=os.path.basename(a.out),
        )
    except DirectV2FactoryUnconfigured:
        _print_json(
            {
                "status": "rejected",
                "reason": "direct_v2_factory_unconfigured",
            }
        )
        return 2
    except FileExistsError:
        _print_json(
            {
                "status": "rejected",
                "reason": "job_already_exists",
            }
        )
        return 2
    _print_json(result)
    return 0


def _cmd_training_dry_run(a) -> int:
    from praxis_virtualcell.model_zoo.training.pipeline import (
        TrainingPipelineError,
        load_training_job,
        run_training_job,
    )
    from praxis_virtualcell.pack_product import PackIndex

    try:
        job = load_training_job(a.job)
        outcome = run_training_job(
            job,
            index=PackIndex(index_path=a.index, include_builtins=False),
            output_root=a.output_root,
        )
    except TrainingPipelineError:
        _print_json({"status": "rejected"})
        return 2
    _print_json(
        {
            "status": "candidate_cataloged_contract_only",
            "training_job_fingerprint": outcome.job.fingerprint(),
            "checkpoint_fingerprint": outcome.checkpoint.fingerprint(),
            "training_result_fingerprint": outcome.result.fingerprint(),
            "candidate_model_fingerprint": outcome.candidate_model.fingerprint(),
        }
    )
    return 0


def _pack_identity_arguments(parser) -> None:
    parser.add_argument("--pack-id", required=True)
    parser.add_argument("--pack-version", required=True)


def main(argv=None, *, direct_v2_factory=None) -> int:
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
    _golden_runtime_arguments(s)
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
    factory_init_cmd = pack_sub.add_parser(
        "factory-init",
        help="重验一个 quarantine receipt 并初始化 write-new Factory store",
    )
    factory_init_cmd.add_argument(
        "--data-root",
        required=True,
        help="P7 data root 的 canonical 绝对路径",
    )
    factory_init_cmd.add_argument(
        "--upload-id",
        required=True,
        help="已完成 quarantine receipt 的 canonical UUIDv4",
    )
    factory_init_cmd.add_argument(
        "--store",
        required=True,
        help="位于 uploads 子树外的绝对 write-new 路径",
    )
    factory_init_cmd.set_defaults(fn=_cmd_pack_factory_init)
    candidate_prepare_cmd = pack_sub.add_parser(
        "candidate-prepare",
        help="冻结 operator-authored Pack 为未审核 candidate；不推断 metadata",
    )
    candidate_prepare_cmd.add_argument("--data-root", required=True)
    candidate_prepare_cmd.add_argument("--upload-id", required=True)
    candidate_prepare_cmd.add_argument("--store", required=True)
    candidate_prepare_cmd.add_argument("--pack-root", required=True)
    candidate_prepare_cmd.add_argument("--authoring", required=True)
    candidate_prepare_cmd.set_defaults(fn=_cmd_pack_candidate_prepare)
    candidate_validate_cmd = pack_sub.add_parser(
        "candidate-validate",
        help="绑定人工 metadata review 并生成 strict validation report",
    )
    candidate_validate_cmd.add_argument("--data-root", required=True)
    candidate_validate_cmd.add_argument("--upload-id", required=True)
    candidate_validate_cmd.add_argument("--store", required=True)
    candidate_validate_cmd.add_argument("--pack-root", required=True)
    candidate_validate_cmd.add_argument("--candidate", required=True)
    candidate_validate_cmd.add_argument("--review", required=True)
    candidate_validate_cmd.set_defaults(fn=_cmd_pack_candidate_validate)
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
    direct_v2 = sub.add_parser(
        "direct-v2",
        help="经显式注入的 generic direct-v2 factory 提交一个 job",
    )
    direct_v2_sub = direct_v2.add_subparsers(dest="direct_v2_cmd", required=True)
    direct_v2_run = direct_v2_sub.add_parser(
        "run",
        help="只接受 vc.request.v2；不自动发现 Pack、模型或领域插件",
    )
    direct_v2_run.add_argument("--request", required=True)
    _pack_identity_arguments(direct_v2_run)
    direct_v2_run.add_argument(
        "--out",
        required=True,
        help="JobStore 路径，例如 runs/my-direct-v2-job",
    )
    _golden_runtime_arguments(direct_v2_run)
    direct_v2_run.set_defaults(fn=_cmd_direct_v2_run)
    training = sub.add_parser(
        "training",
        help="运行 contract-only 确定性训练 dry-run",
    )
    training_sub = training.add_subparsers(dest="training_cmd", required=True)
    dry_run_cmd = training_sub.add_parser(
        "dry-run",
        help="从冻结 job 同步生成 candidate artifacts",
    )
    dry_run_cmd.add_argument("--job", required=True)
    dry_run_cmd.add_argument("--index", required=True)
    dry_run_cmd.add_argument("--output-root", required=True)
    dry_run_cmd.set_defaults(fn=_cmd_training_dry_run)
    a = p.parse_args(argv)
    a.direct_v2_factory = direct_v2_factory
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
