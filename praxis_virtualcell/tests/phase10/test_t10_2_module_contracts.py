from praxis_virtualcell.core.exceptions import PraxisVCError, UnsupportedEngine


def test_unsupported_engine_is_praxisvc_error():
    assert issubclass(UnsupportedEngine, PraxisVCError)
