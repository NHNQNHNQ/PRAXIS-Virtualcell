from praxis_virtualcell.core.exceptions import PraxisVCError, SchemaError


def test_schema_error_is_praxisvc_error():
    assert issubclass(SchemaError, PraxisVCError)
