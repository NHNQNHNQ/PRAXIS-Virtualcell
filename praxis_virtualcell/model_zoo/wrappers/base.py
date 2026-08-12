"""ModelWrapper:model zoo 的统一模型契约。extends PredictorAgent(保留 fail-closed +
retrieve-before-predict 门),补两个显式治理方法:

- declare_scope() -> dict:声明该模型适用的 species/module/task/perturbation 边界,供治理读。
- estimate_uncertainty(model_input, prediction) -> dict:显式不确定性。默认从 run_prediction 的
  uncertainty 提取;若无(run_prediction 未产 uncertainty)→ available=False(诚实,不假造)。

超出 scope 的输入由继承的 assess_applicability/handle 走 rejected,不硬预测。
"""
from __future__ import annotations

import math
from abc import abstractmethod
from copy import deepcopy

from praxis_virtualcell.core.request_v2 import _json_value
from praxis_virtualcell.model_zoo.adapter_sdk import (
    PreparedAdapterInput,
    VirtualCellModelAdapter,
)
from praxis_virtualcell.model_zoo.cache import ArtifactSnapshot
from praxis_virtualcell.predictors.base import PredictorAgent


def _finite_runtime_number(value) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


class ModelWrapper(PredictorAgent):
    name = "ModelWrapper"
    artifact_snapshot_supported = False

    @classmethod
    def from_capability(
        cls,
        *,
        card,
        compatibility_report,
        asset_paths=None,
        runtime_adapter=None,
        prepared_input=None,
        artifact_snapshot=None,
    ):
        """Construct and bind a zero-argument plugin after broker validation."""
        if (runtime_adapter is None) != (prepared_input is None):
            raise ValueError("runtime_adapter and prepared_input must be bound together")
        if artifact_snapshot is not None:
            if not isinstance(artifact_snapshot, ArtifactSnapshot) or not artifact_snapshot.is_intact():
                raise ValueError("artifact_snapshot must be an intact ArtifactSnapshot")
            if cls.artifact_snapshot_supported is not True:
                raise ValueError("direct-v2 wrapper has not declared artifact snapshot support")
            if asset_paths is not None:
                raise ValueError("snapshot-bound wrappers must not receive asset paths")
        if runtime_adapter is not None:
            if not isinstance(runtime_adapter, VirtualCellModelAdapter):
                raise TypeError("runtime_adapter must implement VirtualCellModelAdapter")
            if not isinstance(prepared_input, PreparedAdapterInput):
                raise TypeError("prepared_input must be PreparedAdapterInput")
            prepared_input = runtime_adapter.validate_prepared_input(prepared_input)
        instance = cls()
        instance.name = card.name
        instance.model_version = card.version
        instance._capability_card = card
        instance._compatibility_report = compatibility_report
        instance._capability_assets = {} if artifact_snapshot is not None else dict(asset_paths or {})
        instance._capability_artifact_snapshot = artifact_snapshot
        if runtime_adapter is not None:
            instance._runtime_adapter = runtime_adapter
            instance._prepared_adapter_input = prepared_input
        return instance

    @property
    def capability_assets(self) -> dict[str, str]:
        return dict(getattr(self, "_capability_assets", {}))

    @property
    def capability_asset_bytes(self) -> dict[str, bytes]:
        snapshot = getattr(self, "_capability_artifact_snapshot", None)
        return {} if snapshot is None else snapshot.asset_bytes

    @property
    def capability_artifact_snapshot(self) -> ArtifactSnapshot | None:
        snapshot = getattr(self, "_capability_artifact_snapshot", None)
        return snapshot if isinstance(snapshot, ArtifactSnapshot) else None

    def bound_adapter_execution(
        self,
    ) -> tuple[VirtualCellModelAdapter, PreparedAdapterInput]:
        """Return the Broker-bound adapter/input pair without exposing it publicly."""
        adapter = getattr(self, "_runtime_adapter", None)
        prepared = getattr(self, "_prepared_adapter_input", None)
        if not isinstance(adapter, VirtualCellModelAdapter) or not isinstance(
            prepared, PreparedAdapterInput
        ):
            raise ValueError("wrapper has no Broker-bound adapter execution")
        return adapter, adapter.validate_prepared_input(prepared)

    def assess_applicability(self, request: dict, brain_context: dict) -> tuple[float, str | None]:
        report = getattr(self, "_compatibility_report", None)
        if report is not None:
            if report.executable:
                return 1.0, None
            return 0.0, "broker_compatibility_rejected"
        return super().assess_applicability(request, brain_context)

    def prepare_input(self, request: dict, brain_context: dict) -> dict:
        prepared = getattr(self, "_prepared_adapter_input", None)
        if prepared is None:
            return super().prepare_input(request, brain_context)
        if request.get("request_id") != prepared.model_input.get("request_id"):
            raise ValueError("runtime request_id differs from broker-prepared input")
        return deepcopy(prepared.model_input)

    def _result_status(self, out: dict) -> tuple[str, str | None]:
        adapter = getattr(self, "_runtime_adapter", None)
        prepared = getattr(self, "_prepared_adapter_input", None)
        if adapter is not None:
            try:
                _json_value(out, "$.plugin_output")
                envelope = adapter.adapt_output(prepared, out)
                envelope = adapter.validate_prepared_envelope(prepared, envelope)
            except Exception:  # noqa: BLE001 — third-party adapter boundary is fail-closed
                return "rejected", "runtime_output_adapter_contract"
            if out.get("provenance") is None:
                out["provenance"] = {}
            out["provenance"]["adapter_output"] = envelope.to_dict()
            uncertainty_contract = getattr(
                getattr(self, "_capability_card", None), "uncertainty", None
            )
            if uncertainty_contract is not None:
                if (
                    getattr(uncertainty_contract, "required", False)
                    and envelope.uncertainty is None
                ):
                    return "rejected", "uncertainty_contract_missing"
                allowed_methods = getattr(uncertainty_contract, "methods", ())
                if (
                    envelope.uncertainty is not None
                    and allowed_methods
                    and envelope.uncertainty.method not in allowed_methods
                ):
                    return "rejected", "uncertainty_contract_method"
                calibrated = getattr(uncertainty_contract, "calibrated", None)
                if (
                    envelope.uncertainty is not None
                    and isinstance(calibrated, bool)
                    and envelope.uncertainty.calibrated != calibrated
                ):
                    return "rejected", "uncertainty_contract_calibration"
            if envelope.abstain:
                return "rejected", "runtime_adapter_abstained"
            return super()._result_status(out)
        card = getattr(self, "_capability_card", None)
        if card is None:
            return super()._result_status(out)
        _json_value(out, "$.plugin_output")
        if (
            card.task != "predict_delta_expression"
            or "delta_expression" not in card.output
        ):
            return "rejected", "runtime_output_adapter_missing"
        delta = out.get("prediction", {}).get("delta")
        if (
            not isinstance(delta, list)
            or not delta
            or any(not _finite_runtime_number(value) for value in delta)
        ):
            return "rejected", "prediction_contract_delta"
        ood = out.get("ood") or {}
        if ood.get("detected"):
            dimensions = ood.get("dimensions") or []
            return "rejected", f"ood:{dimensions}"
        uncertainty = out.get("uncertainty")
        if card.uncertainty.required and not isinstance(uncertainty, dict):
            return "rejected", "uncertainty_contract_missing"
        if isinstance(uncertainty, dict) and uncertainty.get("method") not in card.uncertainty.methods:
            return "rejected", "uncertainty_contract_method"
        return super()._result_status(out)

    @abstractmethod
    def declare_scope(self) -> dict:
        """返回 {species: list, module: str, task: list, perturbation?: list}。治理据此判 in/out of scope。"""

    def estimate_uncertainty(self, model_input: dict, prediction: dict | None) -> dict:
        """默认:调 run_prediction 取 uncertainty(可能为 None → available=False,不假造)。
        子类可覆写为更显式的估计(如 bootstrap CI / ensemble disagreement)。"""
        try:
            out = self.run_prediction(model_input)
        except Exception as e:  # noqa: BLE001 — 不确定性估计失败视为不可用,fail-closed
            return {"available": False, "reason": f"uncertainty_estimation_failed: {e}"}
        unc = out.get("uncertainty")
        if unc is None:
            return {"available": False, "reason": "model_reports_no_uncertainty"}
        return {"available": True, "uncertainty": unc}

    def declare_provenance(self) -> dict:
        """返回模型级 provenance(静态模型卡:训练数据/指标锚点/远端坐标/可分发性)。
        默认空(机制模型如 GEM 无训练锚点);ML wrapper(GEARS/scGPT)覆写返回真锚点。
        与运行时 PredictorResultMessage.provenance 正交(那是逐次预测的证据链)。"""
        return {}
