"""The pure LLM platform CLI. Historical predictors remain at praxis-mdr."""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from pathlib import Path

from praxis_virtualcell.settings import LLMSettings


def read_candidates(path: str | Path, limit: int | None = None) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if not rows or not any(name.lower() == "smiles" for name in rows[0]):
        raise ValueError("Candidate CSV must contain a SMILES column")
    candidates = []
    for index, row in enumerate(rows):
        row = {key.lower(): value for key, value in row.items()}
        smiles = row.get("smiles", "").strip()
        if not smiles:
            raise ValueError(f"Empty SMILES in CSV row {index + 2}")
        candidates.append({"id": row.get("id") or row.get("candidate_id") or f"candidate-{index + 1:03d}", "smiles": smiles})
    return candidates if limit is None else candidates[:limit]


def write_result(result: dict, output: str | Path) -> None:
    from praxis_virtualcell.llm_prediction import render_report
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output.with_suffix(".md").write_text(render_report(result), encoding="utf-8")


async def run_analysis(args):
    from praxis2.llm.client import LLMClient
    from praxis_virtualcell.llm_prediction import analyze_candidate
    settings = LLMSettings.load(args.env_file)
    settings.require_key()
    model = args.model or settings.model
    output_override = getattr(args, "max_output_tokens", None)
    limits = {"max_output_tokens": settings.max_output_tokens if output_override is None else output_override,
              "reasoning_effort": getattr(args, "reasoning_effort", None) or settings.reasoning_effort}
    client = LLMClient(settings.api_key, settings.base_url, timeout_s=180)
    def progress(candidate_id):
        def emit(event):
            print(json.dumps({"candidate_id": candidate_id, "progress": event}, ensure_ascii=False), flush=True)
        return emit
    try:
        if args.command == "analyze":
            result = await analyze_candidate(args.smiles, args.profile, client=client, model=model,
                                             data_root=args.data_root, max_turns=args.max_turns,
                                             candidate_id=args.candidate_id, on_progress=progress(args.candidate_id), **limits)
            write_result(result, args.output)
            print(json.dumps({"status": result["status"], "report": str(Path(args.output).resolve())}, ensure_ascii=False))
            return 0 if result["status"] == "completed" else 2
        candidates = read_candidates(args.input, args.limit)
        destination = Path(args.output)
        destination.mkdir(parents=True, exist_ok=True)
        gate = asyncio.Semaphore(args.concurrency)
        async def analyze_one(index, candidate):
            async with gate:
                result = await analyze_candidate(candidate["smiles"], args.profile, client=client, model=model,
                                                 data_root=args.data_root, max_turns=args.max_turns,
                                                 candidate_id=candidate["id"], on_progress=progress(candidate["id"]), **limits)
            report = destination / f"{index + 1:03d}.json"
            write_result(result, report)
            assessment = result.get("assessment", {})
            entry = {"candidate_id": candidate["id"], "status": result["status"],
                     "activity": assessment.get("activity"), "mic_estimate": assessment.get("mic_estimate"),
                     "report": report.name}
            print(json.dumps({"index": index + 1, "total": len(candidates), **entry}, ensure_ascii=False), flush=True)
            return entry
        summary = await asyncio.gather(*(analyze_one(index, candidate) for index, candidate in enumerate(candidates)))
        (destination / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if all(item["status"] == "completed" for item in summary) else 2
    finally:
        await client.aclose()


def main(argv=None):
    parser = argparse.ArgumentParser(description="PRAXIS: real strain omics with LLM-only antibacterial inference")
    parser.add_argument("--data-root", help="Organism profile directory (default: data/organisms)")
    parser.add_argument("--env-file", help="Local credential file (default: .env)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("profiles", help="List locally available organism profiles")
    inspect = sub.add_parser("inspect", help="Inspect real profile identity and omics coverage")
    inspect.add_argument("--profile", default="AB5075-AZI000")
    for command in ("analyze", "batch"):
        item = sub.add_parser(command)
        item.add_argument("--profile", default="AB5075-AZI000")
        item.add_argument("--model")
        item.add_argument("--max-turns", type=int, default=8)
        item.add_argument("--max-output-tokens", type=int, help="Per-call reasoning and answer budget (1024–131072)")
        item.add_argument("--reasoning-effort", choices=["low", "high", "max"])
        if command == "analyze":
            item.add_argument("--smiles", required=True)
            item.add_argument("--candidate-id", default="candidate-001")
            item.add_argument("--output", default="reports/llm_live/assessment.json")
        else:
            item.add_argument("--input", required=True, help="CSV containing SMILES")
            item.add_argument("--limit", type=int, help="Positive maximum number of candidates")
            item.add_argument("--concurrency", type=int, default=1, choices=range(1, 5), help="Simultaneous LLM analyses (1–4)")
            item.add_argument("--output", default="reports/llm_live/batch")
    serve = sub.add_parser("serve", help="Open the strain/candidate analysis platform")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8787)
    args = parser.parse_args(argv)
    try:
        if args.command in {"profiles", "inspect"}:
            from praxis_virtualcell.omics import list_profiles, load_profile
            result = list_profiles(args.data_root) if args.command == "profiles" else load_profile(args.profile, args.data_root).overview()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "serve":
            import uvicorn
            from praxis_virtualcell.web.app import create_app
            uvicorn.run(create_app(data_root=args.data_root, env_file=args.env_file), host=args.host, port=args.port)
            return 0
        if not 1 <= args.max_turns <= 20:
            raise ValueError("max-turns must be between 1 and 20")
        if args.max_output_tokens is not None and not 1024 <= args.max_output_tokens <= 131072:
            raise ValueError("max-output-tokens must be between 1024 and 131072")
        if args.command == "batch" and args.limit is not None and args.limit < 1:
            raise ValueError("limit must be positive")
        return asyncio.run(run_analysis(args))
    except Exception as exc:
        # Upstream exceptions can include request bodies. Do not print them with credentials or omics.
        print(f"Operation failed ({type(exc).__name__}); check local configuration and profile inputs.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
