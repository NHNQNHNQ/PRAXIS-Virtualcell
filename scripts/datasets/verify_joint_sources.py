#!/usr/bin/env python3
"""Verify prepared joint supervision against byte-identical relocated sources."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from praxis_virtualcell.datasets.verify_joint_sources import main


if __name__ == "__main__":
    main()
