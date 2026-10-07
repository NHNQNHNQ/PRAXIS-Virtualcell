"""Reproducible local omics readiness inventory, without models or downloads."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from praxis_virtualcell.omics import ProfileError, load_profile
from praxis_virtualcell.omics.prepare_baseline_samples import _sample_metadata
from praxis_virtualcell.omics.prepare_genome import current19_sources, inspect_genome


def _csv(path: Path) -> tuple[list[str], list[tuple[int, dict]]]:
    if not path.is_file():
        return [], []
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames or [], list(enumerate(reader, 2))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _matrix(path: Path) -> dict:
    if not path.is_file():
        return {"path": str(path), "available": False}
    fields, rows = _csv(path)
    if not fields:
        return {"path": str(path), "available": True, "usable": False, "reason": "missing_header"}
    feature_ids = [row[fields[0]] for _, row in rows]
    identity_kind = ("numeric_row_index" if feature_ids and all(item.isdigit() for item in feature_ids)
                     else "ABUW_native_locus_tag" if feature_ids and all(item.startswith("ABUW_") for item in feature_ids)
                     else "requires_native_feature_identity_review")
    return {"path": str(path.resolve()), "available": True, "size_bytes": path.stat().st_size,
            "sha256": _sha256(path), "feature_count": len(rows), "sample_column_count": len(fields) - 1,
            "first_column": fields[0], "first_feature_ids": feature_ids[:3],
            "feature_identity_kind": identity_kind, "unique_feature_ids": len(set(feature_ids)),
            "sample_columns": fields[1:]}


def _author_baselines(source_root: Path) -> dict:
    raw = source_root / "raw_data/metadata.csv"
    qc = source_root / "interim/metadata_qc.csv"
    _, raw_rows = _csv(raw)
    _, qc_rows = _csv(qc)
    matrix = _matrix(source_root / "interim/log_tpm_qc.csv")
    gene_info = source_root / "external/gene_info.csv"
    identities, errors = [], []
    for sample in ("Abaum_0017", "Abaum_0023"):
        try:
            identity = _sample_metadata(raw_rows, qc_rows, sample)
            identity["expression_column_available"] = sample in matrix.get("sample_columns", [])
            identities.append(identity)
        except ProfileError as exc:
            errors.append(str(exc))
    recoverable = (sum(identity["expression_column_available"] for identity in identities)
                   if matrix.get("feature_identity_kind") == "ABUW_native_locus_tag" and gene_info.is_file() else 0)
    return {"source_root": str(source_root), "raw_metadata_path": str(raw), "raw_metadata_rows": len(raw_rows),
            "qc_metadata_path": str(qc), "qc_metadata_rows": len(qc_rows), "individual_expression_matrix": matrix,
            "native_gene_info_path": str(gene_info), "native_gene_info_available": gene_info.is_file(),
            "verified_untreated_author_columns": identities, "recoverable_verified_column_count": recoverable,
            "distinct_verified_runs": len({identity["run_accession"] for identity in identities}),
            "distinct_verified_biosamples": len({identity["biosample_accession"] for identity in identities}),
            "independent_biological_replicates": None,
            "independence_note": "Distinct columns/runs are not automatically distinct biological samples.",
            "metadata_errors": errors}


def build_omics_inventory(repo_root: str | Path, archive_root: str | Path | None = None,
                          author_data_root: str | Path | None = None) -> dict:
    """Read actual local assets; a remote host must run this against its own paths."""
    repo = Path(repo_root).resolve()
    organisms = repo / "data/organisms"
    sources = organisms / "_sources"
    archive = (Path(archive_root).resolve() if archive_root else
               repo.parent / "PRAXIS-virtualcell-old/Ab-虚拟细胞世界模型")
    canonical = []
    records_path = sources / "source_records.json"
    if records_path.is_file():
        for record in json.loads(records_path.read_text())["records"]:
            path = organisms / record["canonical_path"]
            exists = path.is_file()
            matches = exists and path.stat().st_size == record["size_bytes"] and _sha256(path) == record["sha256"]
            canonical.append({"path": str(path.resolve()), "exists": exists, "source_record_matches": matches,
                              "sha256": record["sha256"], "size_bytes": record["size_bytes"]})
    profiles, errors = [], []
    for path in sorted(organisms.glob("*/manifest.json")):
        try:
            profile = load_profile(path.parent.name, organisms)
            overview = profile.overview()
            row = {key: overview[key] for key in ("profile_id", "species", "strain", "condition", "feature_count",
                                                  "available_modalities", "source_samples")}
            row["source_manifest"] = str(path)
            if "observation_unit" in overview:
                row["observation_unit"] = overview["observation_unit"]
            else:
                row["observation_unit"] = {name: item["observation_unit"] for name, item in overview["modalities"].items()}
            profiles.append(row)
        except (ProfileError, OSError, ValueError) as exc:
            errors.append({"path": str(path), "error": str(exc)})
    _, pair_rows = _csv(sources / "abwm/delta_response_v1/ab5075/pairs.csv")
    groups = sorted({row["control_ids"] for _, row in pair_rows})
    members = sorted({sample for group in groups for sample in json.loads(group)})
    frozen_path = sources / "abwm/delta_response_v1/ab5075/arrays.npz"
    frozen = {"path": str(frozen_path), "available": frozen_path.is_file(), "pair_rows": len(pair_rows),
              "distinct_declared_control_groups": len(groups), "source_member_ids": members,
              "source_member_count": len(members), "individual_vectors_recoverable_from_means": False}
    if frozen_path.is_file():
        with np.load(frozen_path, allow_pickle=False) as archive_npz:
            control = archive_npz["control"]
            frozen.update(control_shape=list(control.shape), distinct_control_mean_vectors=int(len(np.unique(control, axis=0))))
    # Canonical migration kept metadata, not the original individual QC matrix.
    local_ab = _author_baselines(sources / "abaumprecise")
    author_ab = _author_baselines(Path(author_data_root).resolve()) if author_data_root else None
    pa_raw = archive / "pan_bacterial_20260915_review/raw"
    pa_matrix = _matrix(pa_raw / "paeru_log_tpm_qc.csv")
    pa_matrix["automatic_profile_import_ready"] = False
    pa_matrix["blockers"] = ["Native locus-tag bridge must be verified; numeric matrix row IDs are not biological gene IDs.",
                             "Metadata column semantics and archive/sample/medium crosswalk need source-specific review.",
                             "Different profiles sharing one run must not be counted as independent samples."]
    genome_refs, genome_errors = [], []
    try:
        for source in current19_sources(repo):
            observation = inspect_genome(Path(source["assets"]["fasta"]["path"]),
                                         Path(source["assets"]["gff3"]["path"]), source["assembly_accession"])
            observation.pop("features")
            genome_refs.append({**source, **observation, "input_kind": "sequenced_reference_annotation",
                                "phenotype_pairing_admitted": False})
    except (ProfileError, OSError, ValueError, KeyError) as exc:
        genome_errors.append(str(exc))
    gate = repo / ("research/mdr_gnb/mic_discovery/2026-08-14-m1b1-current-gate-ledger-ecoli-meropenem/"
                   "derived/ecoli-meropenem-current-m1-gate-ledger-v1.jsonl")
    historic_gate_codes = set()
    if gate.is_file():
        for text in gate.read_text().splitlines():
            historic_gate_codes.update(json.loads(text).get("unresolved_gate_codes", []))
    protein_candidates = []
    if archive.is_dir():
        for path in archive.rglob("*"):
            name = path.name.casefold()
            if path.is_file() and not name.startswith("._") and (
                "proteom" in name or "protein" in name or path.suffix.lower() in {".mzml", ".mzxml", ".mgf"}
            ) and path.suffix.lower() in {".csv", ".tsv", ".json", ".mzml", ".mzxml", ".mgf"}:
                protein_candidates.append({"path": str(path.resolve()), "classification": "requires_measurement_review"})
    for candidate in protein_candidates:
        if any(word in Path(candidate["path"]).name for word in ("orthogroup", "reference_protein")):
            candidate["classification"] = "reference_sequence_or_translation_not_measured_proteome"
    modality_counts = Counter(name for profile in profiles for name in profile["available_modalities"])
    return {
        "schema_version": "praxis.omics-readiness-inventory.v1", "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": {"repo_root": str(repo), "organisms_root": str(organisms), "archive_root": str(archive),
                  "author_data_root": str(Path(author_data_root).resolve()) if author_data_root else None,
                  "network_requests": 0, "source_assets_copied": False},
        "canonical_source_records": canonical, "verified_profiles": profiles, "profile_errors": errors,
        "profile_modality_counts": dict(modality_counts), "ab_frozen_control_means": frozen,
        "ab_canonical_metadata_only": local_ab, "ab_original_author_data": author_ab,
        "pa_author_expression_candidate": pa_matrix,
        "genome_references": {"verified_assembly_count": len(genome_refs),
                              "distinct_biosample_count": len({item["biosample_accession"] for item in genome_refs}),
                              "annotation_feature_count": sum(item["gene_pseudogene_count"] for item in genome_refs),
                              "origin_spanning_feature_count": sum(item["origin_spanning_gene_count"] for item in genome_refs),
                              "references": genome_refs, "errors": genome_errors,
                              "historic_mic_admission_marker": "not_admitted", "historic_gate_codes": sorted(historic_gate_codes),
                              "interpretation": "Verified sequence annotation can provide genome-only context; this does not validate associated MIC measurements or imply a measured proteome."},
        "proteome": {"verified_measured_profile_count": modality_counts.get("proteome", 0),
                     "candidate_assets": protein_candidates,
                     "note": "No measured protein abundance matrix has been verified in these scanned local roots."},
        "readiness_blockers": [
            "T7 canonical AB sources lack the original individual expression matrix; frozen means cannot recover it.",
            "AB untreated expression columns share BioSample in the original author records; independence needs verification.",
            "PA expression requires validated native feature mapping and corrected source metadata before profile import.",
            "No verified pre-treatment measured proteome or genuine genome/RNA/protein pairing is available in the scanned local roots.",
            "Genome-only context does not resolve historic MIC assay/identity/rights/negative-call qualification gaps.",
        ],
    }


def render_inventory_markdown(inventory: dict) -> str:
    counts = inventory["profile_modality_counts"]
    frozen = inventory["ab_frozen_control_means"]
    genome = inventory["genome_references"]
    lines = ["# 组学数据盘点", "", f"生成时间：{inventory['created_at']}", "",
             "本报告读取本地资产，未下载、调用模型、复制原始数据或把历史均值拆成单样本。", "",
             "| 项目 | 已核验数量与含义 |", "| --- | --- |",
             f"| 已加载 profile | {len(inventory['verified_profiles'])} |",
             f"| genome profile | {counts.get('genome', 0)}；独立的 sequenced_reference 背景 |",
             f"| transcriptome profile | {counts.get('transcriptome', 0)}；观测单位详见 JSON |",
             f"| proteome profile | {counts.get('proteome', 0)} |",
             f"| 冻结 AB control 数组 | {frozen.get('pair_rows', 0)} 行，{frozen.get('distinct_control_mean_vectors', 0)} 个不同均值 |",
             f"| 均值源样本 ID | {frozen.get('source_member_count', 0)}；不能据此恢复这些单样本向量 |",
             f"| 官方 E. coli FASTA/GFF | {genome['verified_assembly_count']} assembly / {genome['distinct_biosample_count']} BioSample |",
             f"| gene/pseudogene 注释 | {genome['annotation_feature_count']}；{genome['origin_spanning_feature_count']} 条跨环状原点注释 |", "",
             "## AB 单样本原件", ""]
    for label, record in [("T7 canonical", inventory["ab_canonical_metadata_only"]),
                          ("显式作者数据根", inventory["ab_original_author_data"])]:
        if record is None:
            continue
        matrix = record["individual_expression_matrix"]
        lines.extend([f"- {label}：`{record['source_root']}`。raw metadata {record['raw_metadata_rows']} 行，QC metadata {record['qc_metadata_rows']} 行。",
                      f"- 原始 QC 表达矩阵存在：{matrix['available']}；可恢复的已核验 AZI_000 作者列：{record['recoverable_verified_column_count']}。",
                      f"- 已核验 source runs {record['distinct_verified_runs']}，BioSample {record['distinct_verified_biosamples']}；独立生物重复未证实。", ""])
    lines.extend(["## PA 与蛋白组", "",
                  f"PA 作者矩阵：`{inventory['pa_author_expression_candidate']['path']}`。"
                  f"feature ID 类型：{inventory['pa_author_expression_candidate'].get('feature_identity_kind', 'unavailable')}。",
                  "数字行索引不能直接替代原生基因 ID；作者 metadata 字段、重复 run 和培养基 crosswalk 仍需审核。",
                  "reference_proteins、protein_orthogroups 和参考翻译注释不属于实测蛋白丰度。", "",
                  "## 基因组背景与 MIC 准入", "",
                  "参考 genome profile 只提供 GFF 中真实观察到的基因/伪基因注释。presence=true 表示注释存在，"
                  "不表示功能、表达、蛋白丰度或目标药物活性；未命中的 feature 不作为基因阴性调用。",
                  "19 个参考 profile 不与 AB RNA 融合，也不宣称原始培养/暴露条件；condition.role 为 sequenced_reference。",
                  "历史 MIC pairing 的 not_admitted 标记不会由于基因组导出而改变。仍需解决：",
                  *[f"- `{code}`" for code in genome["historic_gate_codes"]], "", "## 当前阻塞项", "",
                  *[f"- {item}" for item in inventory["readiness_blockers"]], ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--archive-root")
    parser.add_argument("--author-data-root", help="Optional original AbaumPRECISE repository/data root on this host")
    parser.add_argument("--output-dir", required=True, help="Write inventory JSON and Markdown here")
    args = parser.parse_args()
    inventory = build_omics_inventory(args.repo_root, args.archive_root, args.author_data_root)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "omics_inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n")
    (output / "omics_inventory.md").write_text(render_inventory_markdown(inventory))
    print(json.dumps({"output_dir": str(output.resolve()), "verified_profile_count": len(inventory["verified_profiles"]),
                      "modality_counts": inventory["profile_modality_counts"]}))


if __name__ == "__main__":
    main()
