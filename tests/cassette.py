import os
from pathlib import Path

CASSETTES = Path(__file__).parent / "cassettes"


def load(name: str) -> str:
    if os.environ.get("Recording is unavailable in this cassette suite; do not set PRAXIS_RECORD in CI.") == "1":
        raise NotImplementedError("Recording is unavailable in this cassette suite; do not set PRAXIS_RECORD in CI.")
    return (CASSETTES / name).read_text()
