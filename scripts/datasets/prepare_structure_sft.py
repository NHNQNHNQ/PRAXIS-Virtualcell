#!/usr/bin/env python3
"""Derive traceable structure-augmented public SFT without loading a model."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from praxis_virtualcell.datasets.structure_supervision import main


if __name__ == "__main__":
    main()
