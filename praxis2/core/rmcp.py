"""Track retrieval, reverse filtering, planning, execution, and evidence phases."""

from enum import StrEnum  # ruff UP042 + py311

from praxis2.core.state import State


class Phase(StrEnum):
    INIT = "init"
    RETRIEVE = "retrieve"
    ANTI_FILTER = "anti_filter"
    PLAN = "plan"
    EXECUTE = "execute"
    SEAL = "seal"
    DONE = "done"


TRANSITIONS: dict[Phase, frozenset[Phase]] = {
    Phase.INIT: frozenset({Phase.RETRIEVE}),
    Phase.RETRIEVE: frozenset({Phase.ANTI_FILTER}),
    Phase.ANTI_FILTER: frozenset({Phase.PLAN, Phase.RETRIEVE}),
    Phase.PLAN: frozenset({Phase.EXECUTE, Phase.RETRIEVE}),
    Phase.EXECUTE: frozenset({Phase.SEAL, Phase.PLAN, Phase.RETRIEVE}),
    Phase.SEAL: frozenset({Phase.DONE}),
    Phase.DONE: frozenset(),
}


ALLOWED_OPS: dict[Phase, frozenset[str]] = {
    Phase.INIT: frozenset(),
    Phase.RETRIEVE: frozenset({"retrieve_cases", "retrieve_rules", "retrieve_skills", "retrieve_neg_cases"}),
    Phase.ANTI_FILTER: frozenset({"anti_retrieval"}),
    Phase.PLAN: frozenset({"plan_pipeline", "list_excluded_methods", "state_evidence"}),
    Phase.EXECUTE: frozenset({"call_skill"}),
    Phase.SEAL: frozenset({"write_case", "write_neg_case", "promote_rule", "demote_rule"}),
    Phase.DONE: frozenset(),
}


class PhaseError(Exception):
    pass


class PhaseMachine:
    def __init__(self, phase: Phase = Phase.INIT) -> None:
        self.phase = phase

    def advance(self, to: Phase) -> None:
        if to not in TRANSITIONS[self.phase]:
            raise PhaseError(f"Invalid phase transition:{self.phase.value} → {to.value}")
        self.phase = to

    def check_op(self, op: str) -> None:
        if op not in ALLOWED_OPS[self.phase]:
            raise PhaseError(
                "Operation "
                f"{op!r}"
                "is not allowed in phase "
                f"{self.phase.value}"
                "; first transition to a phase that allows it"
            )


PHASE_KEY = "rmcp_phase"


def get_phase(state: State) -> Phase:

    return Phase(state.tool_use_context.get(PHASE_KEY, Phase.INIT.value))


def set_phase(state: State, phase: Phase) -> None:

    state.tool_use_context[PHASE_KEY] = phase.value


def advance_phase(state: State, to: Phase) -> None:

    m = PhaseMachine(get_phase(state))
    m.advance(to)
    set_phase(state, m.phase)
