"""Metadata for the local MDR regression profiles."""

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "local_artifacts: requires the local MDR data/model catalog and optional scientific runtime",
    )
