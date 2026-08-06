"""v0.6:本地 job store —— 把一次 query 的 request/candidate/report/trace/provenance/narrative/llm 落盘。

runs/<job_id>/{request,candidate_request,report,trace,provenance,narrative_report,llm_meta}。
无数据库依赖(纯文件);API/CLI/web 共用。LLM 只存 hash 元数据,不存 key/原始 prompt 敏感内容。
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

_JOB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _canonical_fingerprint(value: dict) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _valid_execution_identity(value: dict) -> bool:
    """Validate stored identity bytes before projecting them to public fields."""

    def text(item) -> bool:
        return isinstance(item, str) and bool(item) and item.strip() == item

    def fingerprint(item) -> bool:
        return isinstance(item, str) and _SHA256.fullmatch(item) is not None

    def optional_fingerprint(item) -> bool:
        return item is None or fingerprint(item)

    def fingerprints(items) -> bool:
        return (
            isinstance(items, list)
            and all(fingerprint(item) for item in items)
            and len(items) == len(set(items))
        )

    def pack(item) -> bool:
        return item is None or (
            isinstance(item, dict)
            and set(item) == {"pack_id", "pack_version", "fingerprint"}
            and text(item["pack_id"])
            and text(item["pack_version"])
            and fingerprint(item["fingerprint"])
        )

    schema = value.get("schema_version")
    if schema not in {
        "vc.job-execution-identity.v1",
        "vc.job-execution-identity.v2",
        "vc.job-execution-identity.v3",
    }:
        return False
    common_keys = {
        "schema_version",
        "legacy_adapter",
        "pack",
        "models",
        "fingerprint",
    }
    expected_keys = common_keys
    if schema in {
        "vc.job-execution-identity.v2",
        "vc.job-execution-identity.v3",
    }:
        expected_keys = common_keys | {
            "plan_id",
            "submitted_request_fingerprint",
            "request_fingerprint",
            "environment_snapshot_fingerprint",
            "execution_step_fingerprints",
            "structured_report_fingerprint",
            "outcome",
        }
        if schema == "vc.job-execution-identity.v3":
            expected_keys |= {"brain_fingerprint", "dag_fingerprint"}
    if set(value) != expected_keys:
        return False

    stored_fingerprint = value["fingerprint"]
    unsigned = dict(value)
    unsigned.pop("fingerprint")
    try:
        signature_valid = fingerprint(stored_fingerprint) and (
            _canonical_fingerprint(unsigned) == stored_fingerprint
        )
    except (TypeError, ValueError, OverflowError):
        return False
    if not signature_valid or not isinstance(value["legacy_adapter"], bool):
        return False
    if not pack(value["pack"]) or not isinstance(value["models"], list):
        return False

    v1_model_keys = {
        "name",
        "version",
        "fingerprint",
        "compatibility_fingerprint",
        "executable",
    }
    v2_model_keys = v1_model_keys | {
        "release_fingerprint",
        "capability_fingerprint",
        "artifact_fingerprints",
        "environment_fingerprint",
        "adapter_fingerprints",
        "evidence_fingerprints",
        "policy_fingerprint",
        "cataloged",
        "artifact_ready",
        "revoked",
        "superseded_by",
        "benchmark_passed",
        "scientifically_validated",
        "promotion_eligible",
        "policy_present",
        "production_promoted",
    }
    for model in value["models"]:
        if not isinstance(model, dict) or set(model) != (
            v1_model_keys if schema == "vc.job-execution-identity.v1" else v2_model_keys
        ):
            return False
        if not (
            text(model["name"])
            and (text(model["version"]) if schema.endswith(".v1") else (
                model["version"] is None or text(model["version"])
            ))
            and fingerprint(model["fingerprint"])
            and fingerprint(model["compatibility_fingerprint"])
            and isinstance(model["executable"], bool)
        ):
            return False
        if schema.endswith(".v1"):
            continue
        if not (
            optional_fingerprint(model["release_fingerprint"])
            and optional_fingerprint(model["capability_fingerprint"])
            and fingerprints(model["artifact_fingerprints"])
            and optional_fingerprint(model["environment_fingerprint"])
            and fingerprints(model["adapter_fingerprints"])
            and fingerprints(model["evidence_fingerprints"])
            and optional_fingerprint(model["policy_fingerprint"])
            and optional_fingerprint(model["superseded_by"])
            and all(
                isinstance(model[name], bool)
                for name in (
                    "cataloged",
                    "artifact_ready",
                    "revoked",
                    "policy_present",
                    "production_promoted",
                )
            )
            and all(
                model[name] is None or isinstance(model[name], bool)
                for name in (
                    "benchmark_passed",
                    "scientifically_validated",
                    "promotion_eligible",
                )
            )
        ):
            return False
        release_fields = (
            model["release_fingerprint"],
            model["capability_fingerprint"],
        )
        release_present = all(item is not None for item in release_fields)
        if any(item is not None for item in release_fields) != release_present:
            return False
        if not release_present and (
            model["environment_fingerprint"] is not None
            or model["artifact_fingerprints"]
            or model["adapter_fingerprints"]
            or model["evidence_fingerprints"]
            or model["policy_fingerprint"] is not None
            or model["cataloged"]
            or model["artifact_ready"]
            or model["revoked"]
            or model["superseded_by"] is not None
        ):
            return False
        evidence = (
            model["benchmark_passed"],
            model["scientifically_validated"],
            model["promotion_eligible"],
        )
        if any(item is None for item in evidence) != all(
            item is None for item in evidence
        ):
            return False
        if model["scientifically_validated"] and not model["benchmark_passed"]:
            return False
        if model["promotion_eligible"] and not (
            model["benchmark_passed"] and model["scientifically_validated"]
        ):
            return False
        if model["policy_present"] != (model["policy_fingerprint"] is not None):
            return False
        if model["production_promoted"] and not model["policy_present"]:
            return False
        if model["production_promoted"] and not (
            model["evidence_fingerprints"]
            and model["benchmark_passed"] is True
            and model["scientifically_validated"] is True
            and model["promotion_eligible"] is True
        ):
            return False
        if model["executable"] and not (
            release_present
            and model["version"] is not None
            and model["artifact_fingerprints"]
            and model["environment_fingerprint"] is not None
            and model["adapter_fingerprints"]
            and model["evidence_fingerprints"]
            and model["cataloged"]
            and model["artifact_ready"]
            and not model["revoked"]
            and model["superseded_by"] is None
            and all(evidence)
            and model["policy_present"]
            and model["production_promoted"]
        ):
            return False

    if schema == "vc.job-execution-identity.v1":
        return not value["legacy_adapter"] or (
            value["pack"] is None and value["models"] == []
        )

    if value["legacy_adapter"] or not re.fullmatch(r"plan_[0-9a-f]{24}", value["plan_id"]):
        return False
    if not (
        fingerprint(value["submitted_request_fingerprint"])
        and fingerprint(value["request_fingerprint"])
        and fingerprint(value["environment_snapshot_fingerprint"])
        and fingerprints(value["execution_step_fingerprints"])
        and fingerprint(value["structured_report_fingerprint"])
    ):
        return False
    if schema == "vc.job-execution-identity.v3" and not (
        fingerprint(value["brain_fingerprint"])
        and fingerprint(value["dag_fingerprint"])
    ):
        return False
    outcome = value["outcome"]
    if not (
        isinstance(outcome, dict)
        and set(outcome) == {"abstain", "models_used", "prediction_present"}
        and isinstance(outcome["abstain"], bool)
        and isinstance(outcome["prediction_present"], bool)
        and isinstance(outcome["models_used"], list)
        and all(text(name) for name in outcome["models_used"])
        and len(outcome["models_used"]) == len(set(outcome["models_used"]))
    ):
        return False
    executable_models = {
        model["name"] for model in value["models"] if model["executable"]
    }
    model_names = [model["name"] for model in value["models"]]
    return (
        len(model_names) == len(set(model_names))
        and len(value["execution_step_fingerprints"]) == len(executable_models)
        and set(outcome["models_used"]).issubset(executable_models)
        and outcome["prediction_present"] == (not outcome["abstain"])
        and (not outcome["prediction_present"] or bool(outcome["models_used"]))
        and (not executable_models or value["pack"] is not None)
    )


def _public_execution_identity(value: object) -> dict:
    from praxis_virtualcell.model_zoo.registry_v2 import public_model_version

    if not isinstance(value, dict) or value.get("schema_version") not in {
        "vc.job-execution-identity.v1",
        "vc.job-execution-identity.v2",
        "vc.job-execution-identity.v3",
    } or not _valid_execution_identity(value):
        return {
            "schema_version": None,
            "available": False,
            "reason": "unsupported_or_invalid_execution_identity",
        }

    def fingerprint(item):
        return item if isinstance(item, str) and _SHA256.fullmatch(item) else None

    def fingerprints(items):
        if not isinstance(items, list):
            return []
        return [item for item in items if fingerprint(item) is not None]

    raw_pack = value.get("pack")
    pack = None
    if isinstance(raw_pack, dict):
        pack = {
            "pack_id": public_model_version(raw_pack.get("pack_id")),
            "pack_version": public_model_version(raw_pack.get("pack_version")),
            "fingerprint": fingerprint(raw_pack.get("fingerprint")),
        }

    models = []
    for raw in value.get("models", []):
        if not isinstance(raw, dict):
            continue
        model = {
            "name": public_model_version(raw.get("name")),
            "version": public_model_version(raw.get("version")),
            "fingerprint": fingerprint(raw.get("fingerprint")),
            "compatibility_fingerprint": fingerprint(
                raw.get("compatibility_fingerprint")
            ),
            "executable": raw.get("executable")
            if isinstance(raw.get("executable"), bool)
            else False,
        }
        if value["schema_version"] in {
            "vc.job-execution-identity.v2",
            "vc.job-execution-identity.v3",
        }:
            model.update(
                {
                    "release_fingerprint": fingerprint(
                        raw.get("release_fingerprint")
                    ),
                    "capability_fingerprint": fingerprint(
                        raw.get("capability_fingerprint")
                    ),
                    "artifact_fingerprints": fingerprints(
                        raw.get("artifact_fingerprints")
                    ),
                    "environment_fingerprint": fingerprint(
                        raw.get("environment_fingerprint")
                    ),
                    "adapter_fingerprints": fingerprints(
                        raw.get("adapter_fingerprints")
                    ),
                    "evidence_fingerprints": fingerprints(
                        raw.get("evidence_fingerprints")
                    ),
                    "policy_fingerprint": fingerprint(
                        raw.get("policy_fingerprint")
                    ),
                    "cataloged": raw.get("cataloged")
                    if isinstance(raw.get("cataloged"), bool)
                    else False,
                    "artifact_ready": raw.get("artifact_ready")
                    if isinstance(raw.get("artifact_ready"), bool)
                    else False,
                    "revoked": raw.get("revoked")
                    if isinstance(raw.get("revoked"), bool)
                    else False,
                    "superseded_by": fingerprint(raw.get("superseded_by")),
                    "benchmark_passed": raw.get("benchmark_passed")
                    if isinstance(raw.get("benchmark_passed"), bool)
                    else None,
                    "scientifically_validated": raw.get(
                        "scientifically_validated"
                    )
                    if isinstance(raw.get("scientifically_validated"), bool)
                    else None,
                    "promotion_eligible": raw.get("promotion_eligible")
                    if isinstance(raw.get("promotion_eligible"), bool)
                    else None,
                    "policy_present": raw.get("policy_present")
                    if isinstance(raw.get("policy_present"), bool)
                    else False,
                    "production_promoted": raw.get("production_promoted")
                    if isinstance(raw.get("production_promoted"), bool)
                    else False,
                }
            )
        models.append(model)

    public = {
        "schema_version": value["schema_version"],
        "legacy_adapter": value.get("legacy_adapter")
        if isinstance(value.get("legacy_adapter"), bool)
        else True,
        "pack": pack,
        "models": models,
        "fingerprint": fingerprint(value.get("fingerprint")),
    }
    if value["schema_version"] in {
        "vc.job-execution-identity.v2",
        "vc.job-execution-identity.v3",
    }:
        raw_outcome = value.get("outcome")
        outcome = None
        if isinstance(raw_outcome, dict):
            outcome = {
                "abstain": raw_outcome.get("abstain")
                if isinstance(raw_outcome.get("abstain"), bool)
                else None,
                "models_used": [
                    name
                    for name in raw_outcome.get("models_used", [])
                    if public_model_version(name) is not None
                ]
                if isinstance(raw_outcome.get("models_used"), list)
                else [],
                "prediction_present": raw_outcome.get("prediction_present")
                if isinstance(raw_outcome.get("prediction_present"), bool)
                else None,
            }
        public.update(
            {
                "plan_id": public_model_version(value.get("plan_id")),
                "submitted_request_fingerprint": fingerprint(
                    value.get("submitted_request_fingerprint")
                ),
                "request_fingerprint": fingerprint(value.get("request_fingerprint")),
                "environment_snapshot_fingerprint": fingerprint(
                    value.get("environment_snapshot_fingerprint")
                ),
                "execution_step_fingerprints": fingerprints(
                    value.get("execution_step_fingerprints")
                ),
                "structured_report_fingerprint": fingerprint(
                    value.get("structured_report_fingerprint")
                ),
                "outcome": outcome,
            }
        )
        if value["schema_version"] == "vc.job-execution-identity.v3":
            public.update(
                {
                    "brain_fingerprint": fingerprint(
                        value.get("brain_fingerprint")
                    ),
                    "dag_fingerprint": fingerprint(value.get("dag_fingerprint")),
                }
            )
    return public


class JobStore:
    def __init__(self, runs_dir: str = "runs") -> None:
        self.root = Path(runs_dir)

    def _path(self, job_id: str) -> Path:
        if not isinstance(job_id, str) or not _JOB_ID.fullmatch(job_id):
            raise ValueError("job_id must be a safe local identifier")
        return self.root / job_id

    def _new_dir(self, job_id: str) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        directory = self._path(job_id)
        try:
            directory.mkdir()
        except FileExistsError as exc:
            raise FileExistsError(f"job already exists: {job_id}") from exc
        return directory

    def _w(self, d: Path, name: str, obj) -> None:
        if isinstance(obj, str):
            (d / name).write_text(obj, encoding="utf-8")
        else:
            (d / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _execution_identity(result: dict, *, request: dict | None = None) -> dict:
        from praxis_virtualcell.model_zoo.capability_registry import (
            ExecutionPlan,
            ExecutionPlanV2,
        )

        provenance = result.get("provenance") or {}
        raw_plan = provenance.get("execution_plan")
        if raw_plan is None:
            value = {
                "schema_version": "vc.job-execution-identity.v1",
                "legacy_adapter": True,
                "pack": None,
                "models": [],
            }
        else:
            schema = raw_plan.get("schema_version") if isinstance(raw_plan, dict) else None
            if schema == "vc.execution-plan.v1":
                plan = ExecutionPlan.from_dict(raw_plan)
            elif schema == "vc.execution-plan.v2":
                plan = ExecutionPlanV2.from_dict(raw_plan)
            else:
                raise ValueError("unsupported execution plan schema in job provenance")
            pack = (
                {
                    "pack_id": plan.pack_id,
                    "pack_version": plan.pack_version,
                    "fingerprint": plan.pack_fingerprint,
                }
                if plan.pack_id is not None
                else None
            )
            if isinstance(plan, ExecutionPlan):
                value = {
                    "schema_version": "vc.job-execution-identity.v1",
                    "legacy_adapter": False,
                    "pack": pack,
                    "models": [
                        {
                            "name": report.model_name,
                            "version": report.model_version,
                            "fingerprint": report.model_fingerprint,
                            "compatibility_fingerprint": report.fingerprint(),
                            "executable": report.executable,
                        }
                        for report in plan.reports
                    ],
                }
            else:
                if request is None:
                    raise ValueError("v2 execution identity requires the submitted request")
                from praxis_virtualcell.model_zoo.registry_v2 import (
                    public_model_version,
                )
                from praxis_virtualcell.pack_product import (
                    _public_provenance,
                    _runtime_request_v2,
                )

                submitted_request_fingerprint = _canonical_fingerprint(request)
                normalized_request = _runtime_request_v2(request)
                normalized_request_fingerprint = _canonical_fingerprint(
                    normalized_request.to_dict()
                )
                if normalized_request_fingerprint != plan.request_fingerprint:
                    raise ValueError("submitted request does not match execution plan")
                raw_compilation = provenance.get("virtual_experiment")
                experiment_contract = provenance.get("execution_contract")
                compilation = None
                if raw_compilation is not None:
                    from praxis_virtualcell.virtual_experiment import (
                        VirtualExperimentCompilationV1,
                    )

                    compilation = VirtualExperimentCompilationV1.from_dict(
                        raw_compilation
                    )
                structured_report = result.get("structured_report")
                if not isinstance(structured_report, dict):
                    raise ValueError("v2 execution identity requires a structured report")
                experiment_report_keys = {
                    "request_id",
                    "prediction",
                    "models_used",
                    "models_rejected",
                    "models_failed",
                    "abstain",
                    "abstain_reasons",
                    "reliability",
                    "provenance",
                }
                direct_contract_shape = (
                    request.get("schema_version") == "vc.request.v2"
                    and structured_report.get("abstain") is True
                    and structured_report.get("prediction") is None
                    and structured_report.get("models_used") == []
                )
                if compilation is None and (
                    experiment_contract
                    == "vc.virtual-experiment-compilation.v1"
                    or direct_contract_shape
                ):
                    raise ValueError(
                        "direct contract-only jobs require a virtual experiment"
                    )
                if compilation is not None and (
                    experiment_contract
                    != "vc.virtual-experiment-compilation.v1"
                ):
                    raise ValueError(
                        "virtual experiment provenance contract marker is missing"
                    )
                report_provenance = structured_report.get("provenance") or {}
                if compilation is not None and report_provenance != provenance:
                    raise ValueError(
                        "structured report and top-level provenances differ"
                    )
                report_plan = (
                    report_provenance.get("execution_plan")
                    if isinstance(report_provenance, dict)
                    else None
                )
                if report_plan != raw_plan:
                    raise ValueError("structured report and provenance execution plans differ")
                report_compilation = (
                    report_provenance.get("virtual_experiment")
                    if isinstance(report_provenance, dict)
                    else None
                )
                if report_compilation != raw_compilation:
                    raise ValueError(
                        "structured report and provenance virtual experiments differ"
                    )
                if compilation is not None:
                    from praxis_virtualcell.virtual_experiment import (
                        execution_plan_fingerprint,
                    )

                    dag = compilation.dag
                    brain = compilation.brain_context
                    reports = plan.reports
                    steps_by_fingerprint = {
                        step.fingerprint(): step for step in plan.steps
                    }
                    expected_step_fingerprints = tuple(
                        sorted(steps_by_fingerprint)
                    )
                    expected_capability_fingerprints = tuple(
                        sorted({step.capability_fingerprint for step in plan.steps})
                    )
                    if not (
                        dag.request_id == plan.request_id
                        and dag.request_fingerprint == plan.request_fingerprint
                        and dag.cell_context_fingerprint
                        == _canonical_fingerprint(
                            normalized_request.cell_context.to_dict()
                        )
                        and dag.pack_id == plan.pack_id
                        and dag.pack_version == plan.pack_version
                        and dag.pack_fingerprint == plan.pack_fingerprint
                        and dag.environment_snapshot_fingerprint
                        == plan.environment_snapshot_fingerprint
                        and dag.plan_id == plan.plan_id
                        and dag.plan_fingerprint == execution_plan_fingerprint(plan)
                        and brain.request_id == plan.request_id
                        and brain.request_fingerprint == plan.request_fingerprint
                        and brain.pack_id == plan.pack_id
                        and brain.pack_version == plan.pack_version
                        and brain.pack_fingerprint == plan.pack_fingerprint
                        and brain.environment_snapshot_fingerprint
                        == plan.environment_snapshot_fingerprint
                        and brain.plan_id == plan.plan_id
                        and brain.plan_fingerprint == dag.plan_fingerprint
                        and brain.dag_fingerprint == dag.fingerprint()
                        and dag.validated_step_fingerprints
                        == expected_step_fingerprints
                        and dag.participating_capability_fingerprints
                        == expected_capability_fingerprints
                        and brain.execution_step_fingerprints
                        == expected_step_fingerprints
                        and brain.participating_capability_fingerprints
                        == expected_capability_fingerprints
                        and compilation.decision.participating_capability_fingerprints
                        == expected_capability_fingerprints
                    ):
                        raise ValueError(
                            "virtual experiment does not match execution plan"
                        )
                    for node in dag.nodes:
                        step = steps_by_fingerprint.get(
                            node.execution_step_fingerprint
                        )
                        if step is None or not (
                            node.model_fingerprint == step.model_fingerprint
                            and node.release_fingerprint
                            == step.release_fingerprint
                            and node.capability_fingerprint
                            == step.capability_fingerprint
                            and node.environment_fingerprint
                            == step.environment_fingerprint
                            and node.adapter_fingerprints
                            == step.adapter_fingerprints
                        ):
                            raise ValueError(
                                "DAG node does not match an execution plan step"
                            )
                    expected_brain_bindings = {
                        "compatibility_fingerprints": tuple(
                            sorted({report.fingerprint() for report in reports})
                        ),
                        "model_fingerprints": tuple(
                            sorted({report.model_fingerprint for report in reports})
                        ),
                        "release_fingerprints": tuple(
                            sorted(
                                {
                                    report.release_fingerprint
                                    for report in reports
                                    if report.release_fingerprint is not None
                                }
                            )
                        ),
                        "capability_fingerprints": tuple(
                            sorted(
                                {
                                    report.capability_fingerprint
                                    for report in reports
                                    if report.capability_fingerprint is not None
                                }
                            )
                        ),
                        "environment_fingerprints": tuple(
                            sorted(
                                {
                                    report.environment_fingerprint
                                    for report in reports
                                    if report.environment_fingerprint is not None
                                }
                            )
                        ),
                        "adapter_fingerprints": tuple(
                            sorted(
                                {
                                    item
                                    for report in reports
                                    for item in report.adapter_fingerprints
                                }
                            )
                        ),
                        "evidence_fingerprints": tuple(
                            sorted(
                                {
                                    item
                                    for report in reports
                                    for item in report.evidence_fingerprints
                                }
                            )
                        ),
                        "policy_fingerprints": tuple(
                            sorted(
                                {
                                    report.policy_fingerprint
                                    for report in reports
                                    if report.policy_fingerprint is not None
                                }
                            )
                        ),
                    }
                    if any(
                        getattr(brain, field) != expected
                        for field, expected in expected_brain_bindings.items()
                    ):
                        raise ValueError(
                            "Brain context does not match compatibility reports"
                        )
                model_names = {step.model_name for step in plan.steps}
                models_used = structured_report.get("models_used")
                if not isinstance(models_used, list) or any(
                    not isinstance(name, str) for name in models_used
                ):
                    raise ValueError("structured report models_used must be an array of names")
                if len(set(models_used)) != len(models_used):
                    raise ValueError("structured report models_used must be unique")
                if not set(models_used).issubset(model_names):
                    raise ValueError("structured report used a model outside the execution plan")
                abstain = structured_report.get("abstain")
                prediction = structured_report.get("prediction")
                if not isinstance(abstain, bool):
                    raise ValueError("structured report abstain must be boolean")
                if prediction is not None and (abstain or not models_used):
                    raise ValueError(
                        "structured report prediction requires a non-abstained used model"
                    )
                if not abstain and prediction is None:
                    raise ValueError("non-abstained structured report requires a prediction")
                if compilation is not None and (
                    not abstain
                    or prediction is not None
                    or models_used
                    or not compilation.decision.abstain
                    or compilation.decision.execution_performed
                ):
                    raise ValueError(
                        "virtual experiment jobs must remain contract-only abstentions"
                    )
                if compilation is not None:
                    rejected_models = [
                        report.model_name
                        for report in plan.reports
                        if not report.executable
                    ]
                    if not (
                        set(structured_report) == experiment_report_keys
                        and structured_report["request_id"] == plan.request_id
                        and structured_report["models_rejected"]
                        == rejected_models
                        and structured_report["models_failed"] == []
                        and structured_report["abstain_reasons"]
                        == [compilation.decision.reason]
                        and structured_report["reliability"] == "low"
                    ):
                        raise ValueError(
                            "virtual experiment structured report is inconsistent"
                        )
                    if result.get("trace") != [] or result.get("narrative") is not None:
                        raise ValueError(
                            "virtual experiment trace and narrative must be empty"
                        )
                public_report = json.loads(json.dumps(structured_report))
                public_report["provenance"] = _public_provenance(
                    structured_report.get("provenance") or {}
                )
                if compilation is not None:
                    public_report["provenance"]["virtual_experiment"] = (
                        compilation.authoritative_dict()
                    )
                value = {
                    "schema_version": (
                        "vc.job-execution-identity.v3"
                        if compilation is not None
                        else "vc.job-execution-identity.v2"
                    ),
                    "legacy_adapter": False,
                    "plan_id": plan.plan_id,
                    "submitted_request_fingerprint": (
                        submitted_request_fingerprint
                    ),
                    "request_fingerprint": plan.request_fingerprint,
                    "pack": pack,
                    "environment_snapshot_fingerprint": (
                        plan.environment_snapshot_fingerprint
                    ),
                    "execution_step_fingerprints": [
                        step.fingerprint() for step in plan.steps
                    ],
                    "structured_report_fingerprint": _canonical_fingerprint(
                        public_report
                    ),
                    "outcome": {
                        "abstain": abstain,
                        "models_used": models_used,
                        "prediction_present": prediction is not None,
                    },
                    "models": [
                        {
                            "name": report.model_name,
                            "version": public_model_version(report.model_version),
                            "fingerprint": report.model_fingerprint,
                            "release_fingerprint": report.release_fingerprint,
                            "capability_fingerprint": report.capability_fingerprint,
                            "artifact_fingerprints": list(
                                report.artifact_fingerprints
                            ),
                            "environment_fingerprint": (
                                report.environment_fingerprint
                            ),
                            "adapter_fingerprints": list(
                                report.adapter_fingerprints
                            ),
                            "evidence_fingerprints": list(
                                report.evidence_fingerprints
                            ),
                            "policy_fingerprint": report.policy_fingerprint,
                            "compatibility_fingerprint": report.fingerprint(),
                            "cataloged": report.cataloged,
                            "artifact_ready": report.artifact_ready,
                            "revoked": report.revoked,
                            "superseded_by": report.superseded_by,
                            "benchmark_passed": report.benchmark_passed,
                            "scientifically_validated": (
                                report.scientifically_validated
                            ),
                            "promotion_eligible": report.promotion_eligible,
                            "policy_present": report.policy_present,
                            "production_promoted": report.production_promoted,
                            "executable": report.executable,
                        }
                        for report in plan.reports
                    ],
                }
                if compilation is not None:
                    value.update(
                        {
                            "brain_fingerprint": (
                                compilation.brain_context.fingerprint()
                            ),
                            "dag_fingerprint": compilation.dag.fingerprint(),
                        }
                    )
        value["fingerprint"] = _canonical_fingerprint(value)
        return value

    def save(self, job_id: str, *, candidate=None, request=None, result=None) -> str:
        """落盘一次 job;result 为 run_query 的返回。返回 job 目录。"""
        if self._path(job_id).exists():
            raise FileExistsError(f"job already exists: {job_id}")
        execution_identity = (
            self._execution_identity(result, request=request)
            if result is not None
            else None
        )
        public_provenance = None
        public_report = None
        if result is not None:
            from praxis_virtualcell.pack_product import _public_provenance

            public_provenance = _public_provenance(result.get("provenance") or {})
            public_report = json.loads(
                json.dumps(result.get("structured_report", {}))
            )
            if isinstance(public_report, dict):
                public_report["provenance"] = public_provenance
        d = self._new_dir(job_id)
        try:
            if candidate is not None:
                self._w(d, "candidate_request", candidate)
            if request is not None:
                self._w(d, "request", request)
            if result is not None:
                self._w(d, "report", public_report)
                self._w(d, "trace", result.get("trace", []))
                self._w(d, "provenance", public_provenance)
                self._w(
                    d,
                    "execution_identity",
                    execution_identity,
                )
                if result.get("narrative"):
                    self._w(d, "narrative_report.md", result["narrative"])
                # 确定性 Markdown 报告:每次都写(含 offline),与 LLM narrative 正交
                from praxis_virtualcell.io.report_markdown import render_report_md
                job_like = {
                    "report": public_report,
                    "request": request, "candidate_request": candidate,
                    "trace": result.get("trace", []),
                    "provenance": public_provenance,
                    "mode": result.get("mode"), "llm_enabled": result.get("llm_enabled"),
                }
                self._w(d, "report.md", render_report_md(job_like))
                # LLM 元数据只存 hash(不存 key/原文)
                llm = (result.get("parsed") or {}).get("llm_metadata") or {}
                self._w(d, "llm_meta", {k: v for k, v in llm.items() if k != "api_key"})
            (d / "status").write_text("done", encoding="utf-8")
        except Exception:
            shutil.rmtree(d)
            raise
        return str(d)

    def load(self, job_id: str) -> dict:
        d = self._path(job_id)
        if not d.is_dir():
            raise FileNotFoundError(job_id)
        out: dict = {"job_id": job_id, "status": (d / "status").read_text().strip()
                     if (d / "status").is_file() else "unknown"}
        for name in (
            "report",
            "trace",
            "provenance",
            "execution_identity",
            "candidate_request",
            "request",
            "llm_meta",
        ):
            f = d / f"{name}.json"
            if f.is_file():
                out[name] = json.loads(f.read_text(encoding="utf-8"))
        nf = d / "narrative_report.md"
        if nf.is_file():
            out["narrative"] = nf.read_text(encoding="utf-8")
        rf = d / "report.md"
        if rf.is_file():
            out["report_md"] = rf.read_text(encoding="utf-8")
        from praxis_virtualcell.pack_product import _public_provenance

        if isinstance(out.get("provenance"), dict):
            out["provenance"] = _public_provenance(out["provenance"])
        if isinstance(out.get("report"), dict):
            report = json.loads(json.dumps(out["report"]))
            if isinstance(report.get("provenance"), dict):
                report["provenance"] = _public_provenance(report["provenance"])
            out["report"] = report
        if "execution_identity" in out:
            execution_identity = out["execution_identity"]
            schema = (
                execution_identity.get("schema_version")
                if isinstance(execution_identity, dict)
                else None
            )
            if schema in {
                "vc.job-execution-identity.v1",
                "vc.job-execution-identity.v2",
                "vc.job-execution-identity.v3",
            }:
                companion_keys = ("request", "report", "provenance", "trace")
                companions_present = tuple(key in out for key in companion_keys)
                if any(companions_present) and not all(companions_present):
                    execution_identity = {}
                elif all(companions_present):
                    try:
                        expected = self._execution_identity(
                            {
                                "structured_report": out["report"],
                                "provenance": out["provenance"],
                                "trace": out["trace"],
                                "narrative": out.get("narrative"),
                            },
                            request=out["request"],
                        )
                    except (KeyError, TypeError, ValueError):
                        execution_identity = {}
                    else:
                        if execution_identity != expected:
                            execution_identity = {}
            out["execution_identity"] = _public_execution_identity(
                execution_identity
            )
        return out

    def list_jobs(self) -> list[str]:
        if not self.root.is_dir():
            return []
        return sorted(p.name for p in self.root.iterdir() if p.is_dir())
