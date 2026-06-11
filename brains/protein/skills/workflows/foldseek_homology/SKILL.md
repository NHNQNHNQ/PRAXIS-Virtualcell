---
name: foldseek_homology
description: Foldseek 3Di structural homology search + MMseqs2 sequence parallel
host_env: praxis-protein
---

## 一句话原则
**Foldseek + MMseqs2 并跑 union** (rule 04); TM ≥ 0.5 + E ≤ 1e-5 才认 same-fold; 同 fold ≠ 同功能 (synthesis §一)。

## 适用场景
- design_task == structure_search_homology
- 已有 query structure (PDB or AF predicted)
- 远源同源（seq id < 25%）

## 不适用
- ❌ Membrane proteins — 50+ false positive (TM helix bundle 都看着一样)
- ❌ Coiled coil/IDR — 3Di encoding 不稳
- ❌ < 50 aa — 3Di too few unique letters

## 环境检查
```bash
echo $FOLDSEEK_BIN
foldseek --version
which mmseqs
```

## 输入契约
```json
{
  "query_pdb": "path/to/query.pdb",
  "database": "PDB100",  // or "AFDB" or local
  "tm_threshold": 0.5,
  "evalue_threshold": 1e-5,
  "alignment_type": 1,    // 3Di + aa
  "mmseqs_parallel": true,
  "out_dir": "..."
}
```

## 输出契约
```json
{
  "skill_id": "foldseek_homology",
  "msa_path": "",
  "n_sequences": 0,
  "conservation_csv": "",
  "diagnostics": {
    "brain": "protein",
    "archetype": "msa_conservation"
  }
}
```

## QC gate
- TM_score ≥ 0.5 + E ≤ 1e-5 → reliable
- TM 0.4-0.5 → review
- TM < 0.4 → discard
- query 是 membrane / coiled coil / < 50 aa → emit warning

## 实现状态
- ✅ SKILL.md
- ✅ runner.py — **real Foldseek + MMseqs2 wrapper** (CPU works); falls back to --simulate if binary missing
- ✅ All CPU work complete
