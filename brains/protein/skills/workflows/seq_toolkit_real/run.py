"""seq_toolkit — BioPython 通用序列工具(host_env: protein)。

通用、原子级序列计算(非领域分析链):DNA 翻译/反向互补/GC/ORF,
蛋白分子量/等电点/组成,两序列 pairwise 比对。

I/O:
  --inputs '{"sequence":"ATG...","operations":["translate"]}'(JSON 文件路径或 inline)
  --out 输出 JSON 路径(默认 stdout)
  stdout: {"ok":true,"seq_type_detected":"dna","length":N,"results":{...}}
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

_STOPS = {"TAA", "TAG", "TGA"}


def detect_type(seq: str) -> str:
    s = seq.strip().upper().replace("U", "T")
    if not s:
        return "unknown"
    nuc = sum(1 for c in s if c in "ACGTN")
    return "dna" if nuc / len(s) >= 0.9 else "protein"


def find_orfs(seq: str, min_aa: int = 1) -> list:
    from Bio.Seq import Seq  # noqa: PLC0415
    s = seq.upper().replace("U", "T")
    orfs = []
    for frame in range(3):
        i = frame
        while i < len(s) - 2:
            if s[i:i + 3] == "ATG":
                j = i
                while j < len(s) - 2:
                    if s[j:j + 3] in _STOPS:
                        prot = str(Seq(s[i:j + 3]).translate(to_stop=True))
                        if len(prot) >= min_aa:
                            orfs.append({"start": i, "end": j + 3,
                                         "length": j + 3 - i, "protein": prot})
                        i = j
                        break
                    j += 3
            i += 3
    return orfs


def _pairwise(seq1: str, seq2: str) -> dict:
    from Bio.Align import PairwiseAligner  # noqa: PLC0415
    aligner = PairwiseAligner()
    aligner.mode = "global"
    aligner.match_score = 2
    aligner.mismatch_score = -1
    aligner.open_gap_score = -10
    aligner.extend_gap_score = -0.5
    aln = aligner.align(seq1.upper(), seq2.upper())[0]
    a, b = str(aln[0]), str(aln[1])
    matches = sum(1 for x, y in zip(a, b) if x == y and x != "-")
    aln_len = len(a)
    return {
        "identity": round(matches / aln_len * 100, 4) if aln_len else 0.0,
        "score": float(aln.score),
        "alignment_length": aln_len,
        "matches": matches,
    }


def compute(spec: dict) -> dict:
    seq = (spec.get("sequence") or "").strip()
    if not seq:
        return {"ok": False, "error": "sequence 为空"}

    seq_type = spec.get("seq_type", "auto")
    if seq_type in (None, "", "auto"):
        seq_type = detect_type(seq)
    seq2 = (spec.get("sequence2") or "").strip()
    ops = spec.get("operations")
    if not ops:
        ops = (["translate", "reverse_complement", "gc_content"] if seq_type == "dna"
               else ["molecular_weight", "isoelectric_point", "composition"])

    from Bio.Seq import Seq  # noqa: PLC0415
    results: dict = {}
    for op in ops:
        if op == "translate":
            results["translate"] = str(Seq(seq.upper().replace("U", "T")).translate())
        elif op == "reverse_complement":
            results["reverse_complement"] = str(Seq(seq.upper()).reverse_complement())
        elif op == "gc_content":
            from Bio.SeqUtils import gc_fraction  # noqa: PLC0415
            results["gc_content"] = round(gc_fraction(seq.upper().replace("U", "T")) * 100, 4)
        elif op == "orf":
            results["orf"] = find_orfs(seq)
        elif op == "composition":
            results["composition"] = dict(Counter(seq.upper()))
        elif op == "molecular_weight":
            from Bio.SeqUtils.ProtParam import ProteinAnalysis  # noqa: PLC0415
            results["molecular_weight"] = round(ProteinAnalysis(seq.upper()).molecular_weight(), 2)
        elif op == "isoelectric_point":
            from Bio.SeqUtils.ProtParam import ProteinAnalysis  # noqa: PLC0415
            results["isoelectric_point"] = round(ProteinAnalysis(seq.upper()).isoelectric_point(), 2)
        elif op == "pairwise_align":
            results["pairwise_align"] = (_pairwise(seq, seq2) if seq2
                                         else {"error": "需要 sequence2"})
        else:
            results[op] = {"error": f"未知 operation: {op}"}

    return {"ok": True, "seq_type_detected": seq_type, "length": len(seq), "results": results}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True, help="JSON 文件路径或 inline JSON 字符串")
    ap.add_argument("--out", help="输出 JSON 路径(默认 stdout)")
    args, _unknown = ap.parse_known_args()

    raw = args.inputs
    try:
        p = Path(raw)
        spec = json.loads(p.read_text()) if (len(raw) < 512 and p.exists()) else json.loads(raw)
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": f"无法解析 inputs: {e}"}, ensure_ascii=False))
        return 0

    try:
        out = compute(spec)
    except Exception as e:  # noqa: BLE001
        out = {"ok": False, "error": f"{type(e).__name__}: {e}"}

    payload = json.dumps(out, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
