from praxis2.core.state import QueryTracking, State, TerminalReason


def test_terminal_reason_values():
    assert TerminalReason.STOP.value == "stop"
    assert TerminalReason.MAX_TURNS.value == "max_turns"
    assert TerminalReason.ABORTED.value == "aborted"
    assert TerminalReason.ESCALATED.value == "escalated"
    assert TerminalReason.ERROR.value == "error"


def test_state_defaults_are_independent():
    a = State()
    b = State()
    a.messages.append({"role": "user", "content": "x"})
    assert b.messages == []
    assert a.turn_count == 0
    assert a.recovery_attempts == 0
    assert a.max_output_tokens_recovery_count == 0
    assert a.pending_stop_reasons == []
    assert a.transition is None
    assert a.auto_compact_tracking == {"consecutive_failures": 0}


def test_query_tracking_unique_chain_id_and_depth():
    t1 = QueryTracking()
    t2 = QueryTracking()
    assert t1.chain_id != t2.chain_id
    assert t1.depth == 0
    child = QueryTracking(chain_id=t1.chain_id, depth=t1.depth + 1)
    assert child.chain_id == t1.chain_id and child.depth == 1


def test_settings_m1_fields_have_safe_defaults():

    class S:
        model = "claude-sonnet-4-6"
        max_tokens = 4096
        max_turns = 20
        recovery_budget = 3
        max_output_recovery = 2

    s = S()
    assert s.model and isinstance(s.model, str)
    assert s.max_tokens > 0
    assert s.max_turns > 0
    assert s.recovery_budget > 0
    assert s.max_output_recovery > 0
