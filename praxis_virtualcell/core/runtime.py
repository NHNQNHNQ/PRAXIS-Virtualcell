"""注册 + 派发 + 驱动 workflow。predictor fan-out 也走 bus(no fake multi-agent)。"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Clock, IdGen, RuntimeConfig
from praxis_virtualcell.core.exceptions import UnknownAgentError
from praxis_virtualcell.core.message import AgentMessage


class AgentRuntime:
    def __init__(self, config: RuntimeConfig, *, bus: MessageBus,
                 clock: Clock, idgen: IdGen) -> None:
        self.config = config
        self.bus = bus
        self.clock = clock
        self.idgen = idgen
        self._agents: dict[str, BaseAgent] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        self._agents[agent.name] = agent

    def mk_message(self, sender: str, receiver: str, message_type: str,
                   payload: dict, parent_message_id: str | None = None) -> AgentMessage:
        return AgentMessage(self.idgen.next(), sender, receiver, message_type,
                            payload, self.clock.now(), parent_message_id)

    def dispatch_message(self, message: AgentMessage) -> None:
        agent = self._agents.get(message.receiver)
        if agent is None:
            raise UnknownAgentError(f"未注册 agent: {message.receiver}")
        self.bus.send(message)
        agent.handle(message, self.bus)

    def _dispatch_collect(self, message: AgentMessage, expected_type: str) -> AgentMessage:
        self.dispatch_message(message)
        out = self.bus.latest(expected_type)
        if out is None:
            raise RuntimeError(f"{message.receiver} 未产出 {expected_type}")
        return out

    def run_workflow(self, request) -> dict:
        """request: VirtualCellRequest。返回最终 report dict。全程经 bus。"""
        _req_dict = asdict(request)
        _h = hashlib.sha256(
            json.dumps(_req_dict, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:8]
        self.bus.set_context(trace_id=f"trace_{_h}", task_id=f"task_{_h}")
        m = self.mk_message("client", "InputInterpreter", "parse_request",
                            {"request_dict": _req_dict})
        out = self._dispatch_collect(m, "request_parsed")
        m = self.mk_message(out.sender, "BioObjectNormalizer", "normalize",
                            out.payload, out.message_id)
        out = self._dispatch_collect(m, "object_normalized")
        m = self.mk_message(out.sender, "SpeciesBrain", "retrieve", out.payload, out.message_id)
        out = self._dispatch_collect(m, "brain_retrieved")
        m = self.mk_message(out.sender, "ModelApplicability", "decide", out.payload, out.message_id)
        app = self._dispatch_collect(m, "applicability_decided")
        # Phase 4:module-aware 路由旁路挂载(SpeciesContext →[LLMModulePlanner?]→ ModuleRouter),
        # 产 module_plan 挂进 report.provenance.module_plan;不改下游 predictor fan-out 契约。
        # 旁路 gating:module_plan 只对"可路由"请求有意义(如同 predictor 只对 applicable 请求跑)。
        # unsupported 物种(applicable 空)/ 空 perturbation_targets 走 abstain 路径,本无有意义的
        # module_plan —— 不旁路(不调 normalize_request、不崩),与现有 abstain 语义一致。
        module_plan = None
        llm_cross_module = None
        if "ModuleRouterAgent" in self._agents and self._is_routable(app):
            module_plan = self._build_module_plan(app)
            if "LLMCrossModuleReasoner" in self._agents and module_plan is not None:
                xm = self.mk_message("ModuleRouterAgent", "LLMCrossModuleReasoner",
                                     "cross_module_review", {"module_plan": module_plan},
                                     app.message_id)
                llm_cross_module = self._dispatch_collect(xm, "llm_cross_module_notes").payload
        llm_route = None
        if "LLMRouter" in self._agents:
            rmsg = self.mk_message("ModelApplicability", "LLMRouter", "route_suggest",
                {"request": app.payload["request"], "brain_context": app.payload["brain_context"],
                 "applicable": app.payload["applicable"],
                 "rejected_candidates": app.payload["rejected_candidates"]}, app.message_id)
            llm_route = self._dispatch_collect(rmsg, "llm_route_suggestion").payload
        results = []
        for pname in list(app.payload["applicable"]) + list(app.payload["rejected_candidates"]):
            pm = self.mk_message("ModelApplicability", pname, "predict",
                                {"request": app.payload["request"],
                                 "brain_context": app.payload["brain_context"]}, app.message_id)
            r = self._dispatch_collect(pm, "predictor_result")
            results.append(r.payload)
        m = self.mk_message("ModelApplicability", "EnsembleCoordinator", "ensemble",
                            {"request": app.payload["request"],
                             "brain_context": app.payload["brain_context"], "results": results},
                            app.message_id)
        ens = self._dispatch_collect(m, "ensemble_done")
        m = self.mk_message(ens.sender, "Reliability", "assess", ens.payload, ens.message_id)
        rel = self._dispatch_collect(m, "reliability_decided")
        m = self.mk_message(rel.sender, "Critic", "review", rel.payload, rel.message_id)
        crit = self._dispatch_collect(m, "critic_done")
        m = self.mk_message(crit.sender, "ProvenanceAgent", "assemble", crit.payload, crit.message_id)
        prov = self._dispatch_collect(m, "provenance_done")
        m = self.mk_message(prov.sender, "Report", "render", prov.payload, prov.message_id)
        rep = self._dispatch_collect(m, "report_done")
        report = rep.payload["report"]
        if llm_route is not None:
            report.setdefault("provenance", {})["llm_route_suggestion"] = llm_route
        if module_plan is not None:
            report.setdefault("provenance", {})["module_plan"] = module_plan
        if llm_cross_module is not None:
            report.setdefault("provenance", {})["llm_cross_module_notes"] = llm_cross_module
        # Phase 5:证据等级(插点 C)+ 主动学习(插点 D)旁路挂载。确定性零 LLM,advisory 不碰裁决。
        # 读已组装完成的 report(reliability/abstain/disagreement/downgrade/caution/learned/module_plan
        # 信号全齐的最早时机)→ 只往 report.provenance 追加 evidence_level/learning_queue 两新键,
        # 不动任何现有键、不改 prediction/裁决。gated:agent 不在册则分支不进(OFFLINE 字节等价)。
        evidence_level = None
        if "EvidenceLevelAgent" in self._agents:
            em = self.mk_message("Report", "EvidenceLevelAgent",
                                 "evidence_level_request", {"report": report}, rep.message_id)
            evidence_level = self._dispatch_collect(em, "evidence_level_ready").payload["evidence_level"]
            report.setdefault("provenance", {})["evidence_level"] = evidence_level
        if "ActiveLearningAgent" in self._agents:
            am = self.mk_message("EvidenceLevelAgent", "ActiveLearningAgent",
                                 "learning_queue_request",
                                 {"report": report, "evidence_level": evidence_level}, rep.message_id)
            report.setdefault("provenance", {})["learning_queue"] = \
                self._dispatch_collect(am, "learning_queue_ready").payload["learning_queue"]
        if "LLMCritic" in self._agents:
            cm = self.mk_message("Report", "LLMCritic", "llm_review", {"report": report},
                                 rep.message_id)
            report.setdefault("provenance", {})["llm_critic_notes"] = \
                self._dispatch_collect(cm, "llm_critic_notes").payload
        if "LLMReport" in self._agents:
            nm = self.mk_message("Report", "LLMReport", "llm_render", {"report": report},
                                 rep.message_id)
            report["narrative"] = self._dispatch_collect(nm, "llm_narrative").payload["narrative"]
        return report

    @staticmethod
    def _is_routable(app: AgentMessage) -> bool:
        """module_plan 旁路的"可路由"判据(显式条件,非捕获异常)。

        与现有管线 abstain 语义同源,排除两类本就无有意义 module_plan 的请求:
          1) unsupported 物种(martian/bacteria/yeast)→ ModelApplicability 产 applicable==[]
             (如同现有管线不对它们跑 predictor);
          2) 空 perturbation_targets → reliability 判 no_perturbation_specified 硬 abstain
             (与 reliability.py 第 43 行 `[t for t in targets if str(t).strip()]` 判据同源)。
        两者恰是 module 路由 normalize_request 会抛 SchemaError 的情况;不满足则不旁路。
        """
        req = app.payload.get("request", {})
        applicable = app.payload.get("applicable") or []
        targets = [t for t in (req.get("perturbation_targets") or []) if str(t).strip()]
        return bool(applicable) and bool(targets)

    def _build_module_plan(self, app: AgentMessage) -> dict | None:
        """Phase 4 旁路:SpeciesContext →[LLMModulePlanner?]→ ModuleRouter,产 module_plan(dict)。
        OFFLINE(无 LLMModulePlanner)→ ModuleRouter 走确定性 secondary,零 LLM。"""
        module_req = self._request_to_module_input(app.payload["request"])
        sm = self.mk_message("ModelApplicability", "SpeciesContextAgent",
                             "species_context", {"request": module_req}, app.message_id)
        ctx = self._dispatch_collect(sm, "species_context_ready").payload
        base_payload = {"request": module_req, "module_support": ctx["module_support"],
                        "mismatch_queries": ctx["mismatch_queries"]}
        if "LLMModulePlanner" in self._agents:
            pm = self.mk_message("SpeciesContextAgent", "LLMModulePlanner",
                                 "module_plan_request", base_payload, app.message_id)
            mc = self._dispatch_collect(pm, "module_candidates_llm").payload
            route_payload = mc                            # 已含 request/module_support/mismatch/module_candidates
        else:
            route_payload = base_payload                  # OFFLINE:无候选 → ModuleRouter 走确定性
        rm = self.mk_message("SpeciesContextAgent", "ModuleRouterAgent",
                             "module_route", route_payload, app.message_id)
        return self._dispatch_collect(rm, "module_plan_ready").payload

    @staticmethod
    def _request_to_module_input(req: dict) -> dict:
        """把管线 request(键 perturbation_type/output_modality/metadata.requested_outputs)确定性映射到
        module 路由期望的 raw(键 perturbation_object/target_output/perturbation_targets)。零 LLM。

        实读 model_applicability 产出的 req 键:species/perturbation_type/perturbation_targets/
        input_modality/output_modality/task_type/cell_type/metadata。module 路由的 normalize_request
        期望:species/perturbation_object/target_output/perturbation_targets(+可选 cell_type/medium/dose)。
        """
        # output_modality → target_output(TARGET_OUTPUTS = expression/growth/flux/state/communication)
        _OUT_MAP = {"delta_expression": "expression", "pathway_response": "flux",
                    "reliability_report": "expression", "growth": "growth", "flux": "flux",
                    "state": "state", "communication": "communication", "expression": "expression"}
        requested = ((req.get("metadata") or {}).get("requested_outputs") or [])
        # 优先 requested_outputs 里第一个合法输出;否则由 output_modality 映射;再否则默认 expression
        target_output = next((o for o in requested if o in _OUT_MAP.values()), None)
        if target_output is None:
            target_output = _OUT_MAP.get(str(req.get("output_modality", "")).lower(), "expression")
        raw = {"species": req.get("species"),
               "perturbation_object": req.get("perturbation_type"),
               "target_output": target_output,
               "perturbation_targets": list(req.get("perturbation_targets") or [])}
        for k in ("cell_type", "medium", "dose"):
            if req.get(k) is not None:
                raw[k] = req[k]
        return raw

    def export_outputs(self, out_dir: str, report: dict) -> None:
        d = Path(out_dir)
        d.mkdir(parents=True, exist_ok=True)
        self.bus.export_trace(str(d / "trace.json"))
        (d / "prediction_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        (d / "provenance.json").write_text(
            json.dumps(report.get("provenance", {}), ensure_ascii=False, indent=2), encoding="utf-8")

    def run_workflow_from_text(self, text: str) -> dict:
        """free-text(仅 llm_assisted+key):LLMInputInterpreter 解析 → run_workflow。"""
        from praxis_virtualcell.core.exceptions import InputValidationError
        from praxis_virtualcell.core.request import VirtualCellRequest
        if "LLMInputInterpreter" not in self._agents:
            raise InputValidationError("free-text 需 llm_assisted + DEEPSEEK_API_KEY")
        m = self.mk_message("client", "LLMInputInterpreter", "parse_text", {"text": text})
        self.dispatch_message(m)
        parsed = self.bus.latest("request_parsed")
        if parsed is None:
            fail = self.bus.latest("llm_input_failed")
            return {"request_id": None, "abstain": True, "reliability": "low",
                    "prediction": None, "models_used": [], "models_rejected": [],
                    "abstain_reasons": ["input_missing"], "critic_violations": [],
                    "narrative": "", "provenance": {"llm_input_failed": fail.payload if fail else None}}
        return self.run_workflow(VirtualCellRequest.from_dict(parsed.payload["request"]))
