import pytest

from praxis2.core.rmcp import (
    ALLOWED_OPS,
    TRANSITIONS,
    Phase,
    PhaseError,
    PhaseMachine,
    advance_phase,
    get_phase,
    set_phase,
)
from praxis2.core.state import State


def test_phase_set_is_v1_seven_phases():

    assert [p.value for p in Phase] == ["init", "retrieve", "anti_filter", "plan", "execute", "seal", "done"]


def test_transition_table_matches_v1_with_three_retrieve_fallbacks():

    assert TRANSITIONS[Phase.INIT] == frozenset({Phase.RETRIEVE})
    assert TRANSITIONS[Phase.RETRIEVE] == frozenset({Phase.ANTI_FILTER})
    assert TRANSITIONS[Phase.ANTI_FILTER] == frozenset({Phase.PLAN, Phase.RETRIEVE})
    assert TRANSITIONS[Phase.PLAN] == frozenset({Phase.EXECUTE, Phase.RETRIEVE})
    assert TRANSITIONS[Phase.EXECUTE] == frozenset({Phase.SEAL, Phase.PLAN, Phase.RETRIEVE})
    assert TRANSITIONS[Phase.SEAL] == frozenset({Phase.DONE})
    assert TRANSITIONS[Phase.DONE] == frozenset()


def test_allowed_ops_match_v1_whitelist():

    assert ALLOWED_OPS[Phase.RETRIEVE] == frozenset(
        {"retrieve_cases", "retrieve_rules", "retrieve_skills", "retrieve_neg_cases"}
    )
    assert ALLOWED_OPS[Phase.ANTI_FILTER] == frozenset({"anti_retrieval"})
    assert ALLOWED_OPS[Phase.PLAN] == frozenset({"plan_pipeline", "list_excluded_methods", "state_evidence"})
    assert ALLOWED_OPS[Phase.EXECUTE] == frozenset({"call_skill"})
    assert ALLOWED_OPS[Phase.SEAL] == frozenset({"write_case", "write_neg_case", "promote_rule", "demote_rule"})
    assert ALLOWED_OPS[Phase.INIT] == frozenset()
    assert ALLOWED_OPS[Phase.DONE] == frozenset()


def test_phase_machine_advance_legal_and_illegal():
    m = PhaseMachine()
    assert m.phase is Phase.INIT
    m.advance(Phase.RETRIEVE)
    assert m.phase is Phase.RETRIEVE
    m.advance(Phase.ANTI_FILTER)
    m.advance(Phase.RETRIEVE)
    assert m.phase is Phase.RETRIEVE
    with pytest.raises(PhaseError):
        m.advance(Phase.EXECUTE)

    with pytest.raises(PhaseError):
        PhaseMachine(phase=Phase.DONE).advance(Phase.INIT)


def test_phase_machine_check_op_in_and_out_of_phase():
    m = PhaseMachine()
    m.advance(Phase.RETRIEVE)
    m.check_op("retrieve_cases")
    with pytest.raises(PhaseError):
        m.check_op("call_skill")

    with pytest.raises(PhaseError):
        PhaseMachine().check_op("retrieve_cases")


def test_phase_defaults_to_init_when_absent():
    st = State()
    assert get_phase(st) is Phase.INIT


def test_set_and_get_phase_roundtrips_via_tool_use_context():
    st = State()
    set_phase(st, Phase.RETRIEVE)
    assert get_phase(st) is Phase.RETRIEVE

    assert st.tool_use_context["rmcp_phase"] == Phase.RETRIEVE.value


def test_advance_phase_enforces_transition_table_on_state():
    st = State()
    advance_phase(st, Phase.RETRIEVE)
    advance_phase(st, Phase.ANTI_FILTER)
    assert get_phase(st) is Phase.ANTI_FILTER
    with pytest.raises(PhaseError):
        advance_phase(st, Phase.SEAL)
