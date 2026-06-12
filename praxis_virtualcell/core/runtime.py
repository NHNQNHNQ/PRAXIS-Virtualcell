"""注册 + 派发 + 驱动 workflow。predictor fan-out 也走 bus(no fake multi-agent)。"""
from __future__ import annotations

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
        m = self.mk_message("client", "InputInterpreter", "parse_request",
                            {"request_dict": asdict(request)})
        out = self._dispatch_collect(m, "request_parsed")
        m = self.mk_message(out.sender, "BioObjectNormalizer", "normalize",
                            out.payload, out.message_id)
        out = self._dispatch_collect(m, "object_normalized")
        m = self.mk_message(out.sender, "SpeciesBrain", "retrieve", out.payload, out.message_id)
        out = self._dispatch_collect(m, "brain_retrieved")
        m = self.mk_message(out.sender, "ModelApplicability", "decide", out.payload, out.message_id)
        app = self._dispatch_collect(m, "applicability_decided")
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
        return rep.payload["report"]

    def export_outputs(self, out_dir: str, report: dict) -> None:
        d = Path(out_dir)
        d.mkdir(parents=True, exist_ok=True)
        self.bus.export_trace(str(d / "trace.json"))
        (d / "prediction_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        (d / "provenance.json").write_text(
            json.dumps(report.get("provenance", {}), ensure_ascii=False, indent=2), encoding="utf-8")
