from praxis2.core.rmcp import Phase, get_phase
from praxis2.core.state import State
from praxis2.hooks.builtin import advance_phase_on_real_retrieval


class _BrainQueryReal:
    name = "BrainQuery"
    last_retrieval_real_hit = True


class _BrainQueryFixture:
    name = "BrainQuery"
    last_retrieval_real_hit = False


def _ok(tid="t"):
    return {"type": "tool_result", "tool_use_id": tid, "is_error": False, "content": "x"}


def test_real_hit_advances_init_to_retrieve():
    st = State()  # INIT
    out = advance_phase_on_real_retrieval(_BrainQueryReal(), {"id": "t"}, _ok(), st)
    assert out is None
    assert get_phase(st) is Phase.RETRIEVE


def test_fixture_hit_does_not_advance():
    st = State()
    advance_phase_on_real_retrieval(_BrainQueryFixture(), {"id": "t"}, _ok(), st)
    assert get_phase(st) is Phase.INIT


def test_idempotent_no_double_advance_no_phaseerror():
    st = State()
    advance_phase_on_real_retrieval(_BrainQueryReal(), {"id": "t"}, _ok(), st)
    advance_phase_on_real_retrieval(_BrainQueryReal(), {"id": "t"}, _ok(), st)
    assert get_phase(st) is Phase.RETRIEVE


def test_error_result_does_not_advance():
    st = State()
    err = {"type": "tool_result", "tool_use_id": "t", "is_error": True, "content": "boom"}
    advance_phase_on_real_retrieval(_BrainQueryReal(), {"id": "t"}, err, st)
    assert get_phase(st) is Phase.INIT
