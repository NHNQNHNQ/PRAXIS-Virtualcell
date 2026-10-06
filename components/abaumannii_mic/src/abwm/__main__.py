"""Narrow CLI for direct MIC prediction, curation, and supervised training."""
import argparse
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
DEFAULT_DATA = REPO / "data/antibacterial/abaumannii"
DEFAULT_MODELS = REPO / "models/abaumannii/direct_mic"
DEFAULT_REPORTS = REPO / "reports/antibacterial/direct_mic"


def main():
    parser = argparse.ArgumentParser(prog="praxis-ab-mic")
    commands = parser.add_subparsers(dest="command", required=True)
    predict = commands.add_parser("predict")
    predict.add_argument("--input", type=Path, required=True)
    predict.add_argument("--output", type=Path)
    predict.add_argument("--model-root", type=Path, default=DEFAULT_MODELS)
    predict.add_argument("--seed", type=int, default=42)
    predict.add_argument("--scheme", choices=["compound", "scaffold", "study", "isolate"], default="compound")
    predict.add_argument("--device", default="cpu")
    curate = commands.add_parser("curate")
    curate.add_argument("--data-root", type=Path, default=DEFAULT_DATA)
    acquire = commands.add_parser("acquire")
    acquire.add_argument("--data-root", type=Path, default=DEFAULT_DATA)
    train = commands.add_parser("train")
    train.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[2] / "configs/direct_mic.json")
    train.add_argument("--data-root", type=Path, default=DEFAULT_DATA)
    train.add_argument("--model-root", type=Path, required=True)
    train.add_argument("--output-root", type=Path, required=True)
    train.add_argument("--scheme", choices=["compound", "scaffold", "study", "isolate"], default="compound")
    train.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.command == "predict":
        from .inference import Predictor
        result = Predictor(args.model_root, args.seed, args.scheme, args.device).predict(json.loads(args.input.read_text()))
        text = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text)
        else:
            print(text, end="")
    elif args.command == "curate":
        from .data import curate_mic
        curate_mic(args.data_root)
    elif args.command == "acquire":
        from .acquire import chembl
        chembl(args.data_root)
    else:
        # A fresh output directory preserves the imported historical checkpoints.
        args.model_root.mkdir(parents=True, exist_ok=False)
        args.output_root.mkdir(parents=True, exist_ok=False)
        from .training import mic
        mic(json.loads(args.config.read_text()), args.seed, args.scheme,
            args.data_root, args.model_root, args.output_root, resume=False)


if __name__ == "__main__":
    main()
