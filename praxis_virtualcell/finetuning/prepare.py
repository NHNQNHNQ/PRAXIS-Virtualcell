"""CLI for Qwen chat preparation without model downloads or training."""
from __future__ import annotations

import argparse
import json

from praxis_virtualcell.datasets.qwen_sft import prepare_qwen_sft, validate_qwen_sft


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supervision-dir")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--joint-dir")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.validate_only:
        result = validate_qwen_sft(args.output_dir)
    else:
        if not args.supervision_dir:
            parser.error("--supervision-dir is required when preparing")
        result = prepare_qwen_sft(args.supervision_dir, args.output_dir, joint_dir=args.joint_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
