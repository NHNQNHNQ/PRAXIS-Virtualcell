#!/usr/bin/env python3
"""Print the frozen Phase 9 external-validation artifact as JSON."""

from __future__ import annotations

import argparse
import json

from praxis_virtualcell.benchmarks.p9_external import build_external_validation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--source-counts", required=True)
    parser.add_argument("--source-soft", required=True)
    parser.add_argument("--external-raw", required=True)
    parser.add_argument("--external-soft", required=True)
    args = parser.parse_args()
    result = build_external_validation(
        manifest_path=args.manifest,
        source_counts=args.source_counts,
        source_soft=args.source_soft,
        external_raw=args.external_raw,
        external_soft=args.external_soft,
    )
    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
