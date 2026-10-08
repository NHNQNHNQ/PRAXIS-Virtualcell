#!/usr/bin/env python3
"""Prepare the fixed public validation pilot and paired evidence ablations."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from praxis_virtualcell.datasets.validation_pilot import main


if __name__ == "__main__":
    main()
