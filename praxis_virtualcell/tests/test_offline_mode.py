from praxis_virtualcell.core.config import Mode, Clock, IdGen, RuntimeConfig


def test_default_mode_is_offline():
    cfg = RuntimeConfig()
    assert cfg.mode is Mode.OFFLINE
    assert cfg.llm_enabled is False


def test_clock_is_deterministic_and_monotonic():
    c = Clock()
    assert c.now() == "t0001"
    assert c.now() == "t0002"


def test_idgen_is_deterministic():
    g = IdGen("msg")
    assert g.next() == "msg_0001"
    assert g.next() == "msg_0002"
