#!/usr/bin/env python3
"""User-facing CLI for PRAXIS-Synth.

Examples:
  python scripts/engineer_synth.py --synth-task pathway_design --host "E. coli" \
                                    --target-compound lycopene --scale fermenter
  python scripts/engineer_synth.py --synth-task fba --host "E. coli K-12 MG1655"
  python scripts/engineer_synth.py --task-file runs/inputs/my_task.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.orchestrator import run_pipeline, RUNS_DIR  # noqa: E402
from agents.retrieval import retrieve  # noqa: E402

SYNTH_TASKS = ["fba", "pathway_design", "plasmid_assembly", "codon_opt", "circuit",
               "cell_free", "biosensor", "strain_engineering", "bgc_mining"]
SCALES = ["test_tube", "shake_flask", "fermenter", "industrial"]
ASSEMBLY = ["golden_gate", "gibson", "yeast_assembly", "moclo", "klenow"]
PATHWAY_CLASS = ["terpenoid", "polyketide", "amino_acid", "alkaloid", "ripp", "none"]


def build_task_from_args(args: argparse.Namespace) -> dict:
    target = None
    if args.target_compound:
        target = {"name": args.target_compound}
        if args.target_kegg:
            target["kegg_id"] = args.target_kegg
    return {
        "task_id": args.task_id or _slug(args),
        "problem": {
            "synth_task": args.synth_task,
            "host_organism": args.host,
            "target_compound": target,
            "target_protein": args.target_protein,
            "target_analyte": args.target_analyte,
            "scale": args.scale,
            "assembly_strategy": args.assembly_strategy,
            "pathway_class": args.pathway_class,
            "constraints": args.constraint or [],
        },
    }


def _slug(args: argparse.Namespace) -> str:
    parts = [args.synth_task]
    if args.host:
        parts.append(args.host.lower().split()[0].replace(".", "").rstrip(","))
    if args.target_compound:
        parts.append(args.target_compound.lower().replace(" ", "-")[:20])
    if args.scale:
        parts.append(args.scale)
    return "-".join(p for p in parts if p)


def main() -> int:
    ap = argparse.ArgumentParser(description="PRAXIS-Synth user-facing CLI", formatter_class=argparse.RawTextHelpFormatter)

    src = ap.add_mutually_exclusive_group()
    src.add_argument("--task-file", type=Path, help="JSON task spec to load instead of inline args")

    # Inline task args
    ap.add_argument("--task-id", help="Override task id (auto-derived otherwise)")
    ap.add_argument("--synth-task", choices=SYNTH_TASKS,
                    help="One of: " + " | ".join(SYNTH_TASKS))
    ap.add_argument("--host", help="Host organism (e.g., 'E. coli', 'Saccharomyces cerevisiae')")
    ap.add_argument("--target-compound", help="Target compound (free-text or KEGG name)")
    ap.add_argument("--target-kegg", help="KEGG compound ID (e.g., C05433 lycopene)")
    ap.add_argument("--target-protein", help="Target protein (for codon_opt/cell_free)")
    ap.add_argument("--target-analyte", help="Target analyte (for biosensor)")
    ap.add_argument("--scale", choices=SCALES)
    ap.add_argument("--assembly-strategy", choices=ASSEMBLY)
    ap.add_argument("--pathway-class", choices=PATHWAY_CLASS)
    ap.add_argument("--constraint", action="append", help="Add a constraint string (repeatable)")

    # Behavior
    ap.add_argument("--retrieval-only", action="store_true",
                    help="Just print the retrieval bundle, don't run the orchestrator")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--mode", choices=["stub", "llm"], default="stub")
    ap.add_argument("--skip-reviewer", action="store_true")
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--json", action="store_true", help="Emit result as JSON instead of summary")
    ap.add_argument("--verbose", "-v", action="store_true")

    args = ap.parse_args()

    # Load task
    if args.task_file:
        task = json.loads(args.task_file.read_text(encoding="utf-8"))
    else:
        if not args.synth_task:
            ap.error("either --task-file or --synth-task is required")
        task = build_task_from_args(args)

    # Retrieval-only mode
    if args.retrieval_only:
        problem = task["problem"]
        bundle = retrieve(
            {
                "synth_task": problem.get("synth_task"),
                "host_organism": problem.get("host_organism"),
                "target_compound": (problem.get("target_compound", {}) or {}).get("name") if isinstance(problem.get("target_compound"), dict) else problem.get("target_compound"),
                "pathway_class": problem.get("pathway_class"),
                "assembly_strategy": problem.get("assembly_strategy"),
                "scale": problem.get("scale"),
            },
            stage="scoping",
            top_k=args.top_k,
        )
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
        return 0

    # Run full pipeline
    run_dir = args.out_dir or (RUNS_DIR / task["task_id"])
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "intermediates").mkdir(exist_ok=True)
    (run_dir / "outputs").mkdir(exist_ok=True)

    history = run_pipeline(task, mode=args.mode, skip_reviewer=args.skip_reviewer, run_dir=run_dir)

    for stage_key, stage_out in history.items():
        (run_dir / "intermediates" / f"{stage_key}.json").write_text(
            json.dumps(stage_out, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    (run_dir / "outputs" / "report.json").write_text(
        json.dumps(history.get("report", {}), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if args.json:
        print(json.dumps(history, ensure_ascii=False, indent=2))
        return 0

    # Pretty summary
    report = history.get("report", {})
    summary = report.get("summary", {})
    headline = summary.get("headline_metric", {})
    interp = report.get("interpretation", {})
    print(f"\n=== PRAXIS-Synth report — {task['task_id']} ===")
    print(f"  Title:          {summary.get('title', '?')}")
    print(f"  Headline:       {headline.get('name')} = {headline.get('value')} {headline.get('unit', '')}")
    print(f"  TL;DR:          {summary.get('tldr', '')}")
    print(f"  Confidence:     {report.get('confidence', '?')}")
    print(f"  Rules invoked:  {interp.get('rules_invoked', [])}")
    print(f"  Why succeeded:  {interp.get('why_succeeded', [])}")
    print(f"  Why failed:     {interp.get('why_failed', [])}")
    refs = report.get("references", [])
    if refs:
        print(f"  References:")
        for r in refs:
            print(f"    - {r.get('citation', '')}  doi:{r.get('doi', '?')}  case:{r.get('case_id', '-')}")
    print(f"\n  Outputs at:     {run_dir}/outputs/report.json")
    print(f"  Intermediates:  {run_dir}/intermediates/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
