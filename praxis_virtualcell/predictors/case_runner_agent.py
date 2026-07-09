"""真实 case runner → offline 主链的 adapter。PredictorAgent 子类,内部按 route engine
分发到具体 run_*_case,把 CaseReport 映射成 {prediction:{delta},uncertainty,evidence,provenance}。
诚实透传 CaseReport 的 disposition/boundary,不伪造。"""
from __future__ import annotations

from praxis_virtualcell.agents.request_adapter import request_to_module_input
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.core.exceptions import UnsupportedEngine
from praxis_virtualcell.predictors.base import PredictorAgent
from praxis_virtualcell.predictors.case_dispatch import dispatch_runner, map_case_delta


class CaseRunnerPredictorAgent(PredictorAgent):
    name = "CaseRunner"

    def prepare_input(self, request: dict, brain_context: dict) -> dict:
        return {"request": request}          # adapter 需完整 request(route+dispatch 用)

    def assess_applicability(self, request: dict, brain_context: dict) -> tuple[float, str | None]:
        raw = request_to_module_input(request)
        engine = route(normalize_request(raw)).engine
        try:
            dispatch_runner(engine, raw)
        except UnsupportedEngine as e:
            return 0.0, str(e)
        return 1.0, None

    def run_prediction(self, model_input: dict) -> dict:
        request = model_input["request"]
        raw = request_to_module_input(request)
        engine = route(normalize_request(raw)).engine
        runner = dispatch_runner(engine, raw)
        report, _ = runner(raw)              # runner 内部自 normalize+route+真跑
        return {
            "prediction": {"delta": map_case_delta(engine, report)},
            "uncertainty": {"disposition": report.reliability_decision["disposition"],
                            "caution_flags": report.reliability_decision["caution_flags"]},
            "evidence": list(report.provenance_boundary.get("rules_hit", [])),
            "provenance": {**report.provenance_boundary, "case_id": report.case_id, "engine": engine},
        }
