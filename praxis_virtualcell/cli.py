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
    from praxis_virtualcell.llm_prediction import analyze_with_agents
    settings = LLMSettings.load(args.env_file)
    settings.require_key()
    model = args.model or settings.model
    output_override = getattr(args, "max_output_tokens", None)
    limits = {"max_output_tokens": settings.max_output_tokens if output_override is None else output_override,
              "reasoning_effort": getattr(args, "reasoning_effort", None) or settings.reasoning_effort}
    if getattr(args, "modalities", None) is not None:
        limits["modalities"] = args.modalities
    if getattr(args, "knowledge_catalog", None) is not None:
        limits["knowledge_catalog_path"] = args.knowledge_catalog
    client = LLMClient(settings.api_key, settings.base_url, timeout_s=180)
    def progress(candidate_id):
        def emit(event):
            print(json.dumps({"candidate_id": candidate_id, "progress": event}, ensure_ascii=False), flush=True)
        return emit
    try:
        if args.command == "analyze":
            result = await analyze_with_agents(args.smiles, args.profile, client=client, model=model,
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
                result = await analyze_with_agents(candidate["smiles"], args.profile, client=client, model=model,
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
    parser = argparse.ArgumentParser(description="PRAXIS: strain or species-reference omics with LLM-only antibacterial inference")
    parser.add_argument("--data-root", help="Organism profile directory (default: data/organisms)")
    parser.add_argument("--env-file", help="Local credential file (default: .env)")
    parser.add_argument("--knowledge-catalog", help="Curated mechanism catalog; never experimental MIC labels")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("profiles", help="List locally available organism profiles")
    inspect = sub.add_parser("inspect", help="Inspect real profile identity and omics coverage")
    inspect.add_argument("--profile", default="AB5075-AZI000")
    inspect.add_argument("--modalities", nargs="+", choices=["genome", "transcriptome", "proteome"])
    for command in ("analyze", "batch"):
        item = sub.add_parser(command)
        item.add_argument("--profile", default="AB5075-AZI000")
        item.add_argument("--modalities", nargs="+", choices=["genome", "transcriptome", "proteome"],
                          help="One or more available profile modalities used by the agents")
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
    export = sub.add_parser("export-sft", help="Export public agent/tool trajectories from a saved report")
    export.add_argument("--input", required=True, help="Saved report JSON")
    export.add_argument("--output", required=True, help="Output training trajectory JSONL")
    export.add_argument("--supervision", help="Optional explicit reviewed supervision JSON")
    curate = sub.add_parser("curate-labels", help="Prepare independent measured labels, quarantining ambiguous contexts")
    curate.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    curate.add_argument("--output", required=True)
    freeze = sub.add_parser("freeze-evaluation", help="Freeze grouped inputs and a separate private answer index")
    freeze.add_argument("--labels", required=True)
    freeze.add_argument("--output", required=True)
    freeze.add_argument("--grouping", choices=["compound", "scaffold", "strain", "study", "joint"], default="compound")
    freeze.add_argument("--seed", type=int, default=20261007)
    freeze.add_argument("--paired-only", action="store_true")
    score = sub.add_parser("score-evaluation", help="Score saved predictions after inference, with coverage and censoring")
    score.add_argument("--manifest", required=True)
    score.add_argument("--predictions", required=True)
    score.add_argument("--split", choices=["train", "validation", "test"], default="test")
    score.add_argument("--output", required=True)
    seeds = sub.add_parser("prepare-seeds", help="Prepare source-grounded tool supervision candidates for review")
    seeds.add_argument("--output", required=True)
    seeds.add_argument("--limit", type=int, default=80)
    species_db = sub.add_parser("build-species-db", help="Link canonical measured labels to one reference per species and modality")
    species_db.add_argument("--references", required=True, help="Selected native reference profiles JSON")
    species_db.add_argument("--labels", nargs="+", required=True, help="Existing canonical ExperimentRecord JSONL files")
    species_db.add_argument("--output", required=True, help="New version directory for the derived SQLite database")
    coverage = sub.add_parser("species-db", help="Inspect species/MIC/reference coverage without reading MIC answers")
    coverage.add_argument("--database", required=True)
    species_inputs = sub.add_parser("export-species-inputs", help="Export species-reference inputs without endpoints or assay labels")
    species_inputs.add_argument("--database", required=True)
    species_inputs.add_argument("--output", required=True)
    species_freeze = sub.add_parser("freeze-species-evaluation", help="Freeze species-reference inputs by global compound, scaffold or study groups")
    species_freeze.add_argument("--database", required=True)
    species_freeze.add_argument("--output", required=True)
    species_freeze.add_argument("--grouping", choices=["compound", "scaffold", "study", "scaffold_study"], default="scaffold")
    species_freeze.add_argument("--seed", type=int, default=20261007)
    species_score = sub.add_parser("score-species-evaluation", help="Score frozen species-reference predictions with per-species coverage")
    species_score.add_argument("--manifest", required=True)
    species_score.add_argument("--predictions", required=True)
    species_score.add_argument("--split", choices=["train", "validation", "test"], default="test")
    species_score.add_argument("--output", required=True)
    supervision = sub.add_parser("prepare-species-supervision", help="Prepare reviewed-later tool observations and train-only experimental answer pointers")
    supervision.add_argument("--manifest", required=True, help="Frozen species evaluation manifest")
    supervision.add_argument("--output", required=True)
    supervision.add_argument("--limit-per-species", type=int, default=8)
    acquire = sub.add_parser("acquire-species-mic", help="Reuse native metadata and acquire bounded official MIC pages for curation")
    acquire.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    acquire.add_argument("--archive-root", help="Existing archived AB project, for native molecule metadata reuse")
    acquire.add_argument("--taxon-ids", nargs="+", type=int, choices=[470, 562, 573, 287], default=[562, 573, 287])
    acquire.add_argument("--per-species-limit", type=int, default=300, help="Cumulative maximum native activities to inspect per species")
    acquire.add_argument("--page-size", type=int, default=1000, help="Maximum activities in each continuation page")
    acquire.add_argument("--reuse-cache", nargs="*", default=[], help="Existing native cache roots reused without copying responses")
    acquire.add_argument("--reuse-labels", nargs="*", default=[], help="Canonical experimental JSONL files referenced without copying")
    acquire.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "acquire-species-mic":
            from praxis_virtualcell.datasets.chembl_import import acquire_species_mic
            result = acquire_species_mic(args.repo_root, args.output, taxon_ids=tuple(args.taxon_ids),
                                         per_species_limit=args.per_species_limit, archive_root=args.archive_root,
                                         reused_label_paths=tuple(args.reuse_labels),
                                         reuse_cache_roots=tuple(args.reuse_cache), page_size=args.page_size)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "freeze-species-evaluation":
            from praxis_virtualcell.datasets.species_evaluation import freeze_species_evaluation
            result = freeze_species_evaluation(args.database, args.output, grouping=args.grouping, seed=args.seed)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["status"] == "ready" else 2
        if args.command == "score-species-evaluation":
            from praxis_virtualcell.datasets.species_evaluation import score_species_evaluation
            result = score_species_evaluation(args.manifest, args.predictions, split=args.split)
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({key: value for key, value in result.items() if key != "details"}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "prepare-species-supervision":
            from praxis_virtualcell.datasets.species_supervision import prepare_species_supervision
            result = prepare_species_supervision(args.manifest, args.output, limit_per_species=args.limit_per_species)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "build-species-db":
            from praxis_virtualcell.datasets.species_registry import build_species_database
            from praxis_virtualcell.omics.profiles import _data_root
            result = build_species_database(args.references, args.labels, args.output, profile_root=_data_root(args.data_root))
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "species-db":
            from praxis_virtualcell.datasets.species_registry import database_coverage
            print(json.dumps(database_coverage(args.database), ensure_ascii=False, indent=2))
            return 0
        if args.command == "export-species-inputs":
            from praxis_virtualcell.datasets.species_registry import export_species_inputs
            count = export_species_inputs(args.database, args.output)
            print(json.dumps({"records": count, "output": str(Path(args.output).resolve()),
                              "prediction_scope": "species_reference", "labels_included": False}, ensure_ascii=False))
            return 0
        if args.command == "curate-labels":
            from praxis_virtualcell.datasets.curation import curate_existing_labels
            print(json.dumps(curate_existing_labels(args.repo_root, args.output), ensure_ascii=False, indent=2))
            return 0
        if args.command == "freeze-evaluation":
            from praxis_virtualcell.datasets.evaluation import freeze_evaluation
            result = freeze_evaluation(args.labels, args.output, grouping=args.grouping, seed=args.seed,
                                       paired_only=args.paired_only)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["status"] == "ready" else 2
        if args.command == "score-evaluation":
            from praxis_virtualcell.datasets.evaluation import score_evaluation
            result = score_evaluation(args.manifest, args.predictions, split=args.split)
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({key: value for key, value in result.items() if key != "details"}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "prepare-seeds":
            from praxis_virtualcell.datasets.seeds import prepare_seed_queue
            from praxis_virtualcell.omics.profiles import _data_root
            print(json.dumps(prepare_seed_queue(_data_root(args.data_root), args.output, limit=args.limit), ensure_ascii=False, indent=2))
            return 0
        if args.command in {"profiles", "inspect"}:
            from praxis_virtualcell.omics import list_profiles, load_profile
            if args.command == "profiles":
                result = list_profiles(args.data_root)
            else:
                profile = load_profile(args.profile, args.data_root)
                if args.modalities is not None:
                    profile = profile.select_modalities(args.modalities)
                result = profile.overview()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "export-sft":
            from praxis_virtualcell.llm_prediction.trajectories import export_trajectories, write_trajectories_jsonl
            report = json.loads(Path(args.input).read_text(encoding="utf-8"))
            supervision = json.loads(Path(args.supervision).read_text(encoding="utf-8")) if args.supervision else None
            exported = export_trajectories(report, supervision)
            count = write_trajectories_jsonl(args.output, exported)
            print(json.dumps({"records": count, "skipped": len(exported["skipped"]),
                              "output": str(Path(args.output).resolve())}, ensure_ascii=False))
            return 0 if count else 2
        if args.command == "serve":
            import uvicorn
            from praxis_virtualcell.web.app import create_app
            uvicorn.run(create_app(data_root=args.data_root, env_file=args.env_file,
                                   knowledge_catalog_path=args.knowledge_catalog), host=args.host, port=args.port)
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
