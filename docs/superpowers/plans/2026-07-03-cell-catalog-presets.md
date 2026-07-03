# Cell catalog 预设 + 结构化下拉增强 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans。Steps 用 checkbox 跟踪。

**Goal:** 加只读 cell/model 预设 catalog + 经 /api/options 暴露 + 前端 ConfirmView 结构化下拉/预设增强。薄 catalog,不碰权威/治理。

**Architecture:** 后端 `catalogs/cell_catalog.yaml`(≥10 预设)+ `load_cell_presets()`(校验 species∈白名单防漂移)+ `options()` 加 `cell_presets`。前端 `getOptions()` + ConfirmView 用枚举下拉 + 预设选择器填充。词汇/治理权威不变。

**Tech Stack:** Python/pytest/PyYAML · React+TS+Vite。

**铁律:** catalog 只读展示,不引入新词汇/治理权威;cell_type 仍自由文本;不碰 species_schema/route/governance 逻辑。后端每 task 全量 `pytest praxis_virtualcell/tests` 0 failed 后 commit+push;前端 `npm run build` 通过。commit 前删 `._*`,末尾 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`。

---

## Task 1: 后端 cell catalog + loader + options 扩展(TDD)

**Files:**
- Create: `praxis_virtualcell/catalogs/__init__.py`
- Create: `praxis_virtualcell/catalogs/cell_catalog.yaml`
- Create: `praxis_virtualcell/tests/test_cell_catalog.py`
- Modify: `praxis_vc_api/services/runtime_service.py`(options 加 cell_presets)
- Modify: `praxis_virtualcell/tests/test_api.py`(test_options 加断言)

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_cell_catalog.py`:

```python
"""cell catalog 预设测试:只读展示层,species 不得越白名单(防与单一真相源漂移)。"""
from praxis_virtualcell.catalogs import load_cell_presets
from praxis_virtualcell.workflows.run_virtualcell_query import SUPPORTED_SPECIES


def test_presets_loaded_min_count():
    presets = load_cell_presets()
    assert len(presets) >= 10, f"预设过少:{len(presets)}"


def test_preset_fields_and_species_in_whitelist():
    for p in load_cell_presets():
        assert p.get("id") and p.get("cell_type") and p.get("label"), f"字段缺失:{p}"
        assert p["species"] in SUPPORTED_SPECIES, f"预设 species 越白名单:{p['species']}"


def test_all_four_species_covered():
    species = {p["species"] for p in load_cell_presets()}
    assert species == SUPPORTED_SPECIES, f"物种覆盖不全:{species} != {SUPPORTED_SPECIES}"


def test_preset_ids_unique():
    ids = [p["id"] for p in load_cell_presets()]
    assert len(ids) == len(set(ids)), f"预设 id 重复:{ids}"
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_cell_catalog.py -q`
Expected: FAIL(ModuleNotFoundError: praxis_virtualcell.catalogs)

- [ ] **Step 3: 写 catalog yaml**

写 `praxis_virtualcell/catalogs/cell_catalog.yaml`:

```yaml
# 只读 UI 辅助:curated cell/model 预设(展示层)。非权威词汇/治理决策。
# species 必须 ∈ SUPPORTED_SPECIES(loader 校验);cell_type 自由文本;仅供前端便捷选择。
presets:
  - {id: human_k562, species: human, cell_type: K562, label: "K562 — human CML (Norman perturb-seq)", example_perturbation_type: gene, example_targets: [AHR, GATA1]}
  - {id: human_pbmc, species: human, cell_type: PBMC, label: "PBMC — human immune (Kang IFN-β)", example_perturbation_type: gene, example_targets: [STAT1]}
  - {id: human_a549, species: human, cell_type: A549, label: "A549 — human lung adenocarcinoma", example_perturbation_type: drug, example_targets: [vorinostat]}
  - {id: human_hek293t, species: human, cell_type: HEK293T, label: "HEK293T — human embryonic kidney", example_perturbation_type: gene, example_targets: [TP53]}
  - {id: human_ipsc, species: human, cell_type: iPSC, label: "iPSC — human induced pluripotent", example_perturbation_type: gene, example_targets: [SNAI1]}
  - {id: mouse_tcell, species: mouse, cell_type: T cell, label: "T cell — mouse (ortholog 迁移)", example_perturbation_type: gene, example_targets: [Gata1]}
  - {id: mouse_hematopoietic, species: mouse, cell_type: hematopoietic, label: "Hematopoietic — mouse (Paul15 分化)", example_perturbation_type: gene, example_targets: [Gata1]}
  - {id: mouse_fibroblast, species: mouse, cell_type: fibroblast, label: "Fibroblast — mouse", example_perturbation_type: gene, example_targets: [Myc]}
  - {id: yeast_scerevisiae, species: yeast, cell_type: S. cerevisiae, label: "S. cerevisiae — yeast GEM (Yeast8)", example_perturbation_type: gene, example_targets: [YBR166C]}
  - {id: yeast_carbon, species: yeast, cell_type: S. cerevisiae, label: "S. cerevisiae — 碳源切换 (medium)", example_perturbation_type: medium, example_targets: []}
  - {id: ecoli_iml1515, species: bacteria, cell_type: E. coli, label: "E. coli — iML1515 GEM (KO 生长)", example_perturbation_type: gene, example_targets: [b0720]}
  - {id: ecoli_antibiotic, species: bacteria, cell_type: E. coli, label: "E. coli — 抗生素 (靶代谢 FBA)", example_perturbation_type: drug, example_targets: [trimethoprim]}
```

- [ ] **Step 4: 写 loader**

写 `praxis_virtualcell/catalogs/__init__.py`:

```python
"""只读 cell/model 预设 catalog(展示层)。非权威词汇/治理——权威仍在
species_schema/run_virtualcell_query 白名单 + model_applicability/reliability。"""
from __future__ import annotations

from pathlib import Path

import yaml

from praxis_virtualcell.workflows.run_virtualcell_query import SUPPORTED_SPECIES

_CATALOG = Path(__file__).parent / "cell_catalog.yaml"


def load_cell_presets() -> list[dict]:
    """读 cell_catalog.yaml 的 presets。校验 species ∈ SUPPORTED_SPECIES(防与单一真相源漂移)。"""
    doc = yaml.safe_load(_CATALOG.read_text(encoding="utf-8")) or {}
    presets = doc.get("presets", [])
    bad = [p["id"] for p in presets if p.get("species") not in SUPPORTED_SPECIES]
    if bad:
        raise ValueError(f"cell_catalog 预设 species 越白名单:{bad}")
    return presets
```

- [ ] **Step 5: 扩 options() 加 cell_presets**

`praxis_vc_api/services/runtime_service.py`:改 `options()`。在 return dict 加一行(`cell_type_free_text` 之后):

```python
def options() -> dict:
    """暴露后端权威枚举供前端下拉(只读)。cell_type 后端不限制,仅给示例可自由填。"""
    from praxis_virtualcell.catalogs import load_cell_presets
    return {
        "species": sorted(SUPPORTED_SPECIES),
        "perturbation_type": sorted(SUPPORTED_PERTURBATION),
        "task_type": sorted(SUPPORTED_TASKS),
        "cell_type_examples": list(_CELL_TYPE_EXAMPLES),
        "cell_type_free_text": True,
        "cell_presets": load_cell_presets(),
    }
```

- [ ] **Step 6: 扩 test_api.py::test_options**

`praxis_virtualcell/tests/test_api.py`:在 `test_options` 末尾追加断言:

```python
    presets = d["cell_presets"]
    assert len(presets) >= 10
    p0 = presets[0]
    assert p0["species"] in d["species"] and p0["cell_type"] and p0["label"]
```

- [ ] **Step 7: 跑测试 + ruff + 全量**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_cell_catalog.py praxis_virtualcell/tests/test_api.py -q`
Expected: PASS(4 catalog + 8 api = 12 passed)

Run: `.venv/bin/ruff check praxis_virtualcell/catalogs/ praxis_vc_api/services/runtime_service.py`
Expected: All checks passed!

Run(后台): `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider -o console_output_style=classic 2>&1 | tail -1`
Expected: `275 passed, 25 skipped`(271 + 4),**0 failed**(看完整行)

- [ ] **Step 8: commit + push**

```bash
find docs praxis_virtualcell praxis_vc_api praxis_vc_react -name '._*' -delete
git add praxis_virtualcell/catalogs/ praxis_vc_api/services/runtime_service.py praxis_virtualcell/tests/test_cell_catalog.py praxis_virtualcell/tests/test_api.py
git commit -m "feat(v0.6): cell catalog 预设(12 条 4 物种)+ /api/options 暴露 cell_presets

薄 catalog 只读展示;species 校验不越白名单(防漂移);词汇/治理权威不变。

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push origin main
```

---

## Task 2: 前端 ConfirmView 结构化下拉 + 预设选择器

**Files:**
- Modify: `praxis_vc_react/src/api.ts`(Options 类型 + getOptions)
- Modify: `praxis_vc_react/src/views/ConfirmView.tsx`(下拉 + 预设)

- [ ] **Step 1: api.ts 加 Options 类型 + getOptions**

`praxis_vc_react/src/api.ts`:在 `ProvenanceResult` 接口后加类型,并在末尾加方法:

```typescript
export interface CellPreset {
  id: string;
  species: string;
  cell_type: string;
  label: string;
  example_perturbation_type?: string;
  example_targets?: string[];
}

export interface Options {
  species: string[];
  perturbation_type: string[];
  task_type: string[];
  cell_type_examples: string[];
  cell_type_free_text: boolean;
  cell_presets: CellPreset[];
}
```

末尾追加:

```typescript
export function getOptions(): Promise<Options> {
  return req<Options>("/api/options");
}
```

- [ ] **Step 2: ConfirmView 加 options 拉取 + 下拉 + 预设**

`praxis_vc_react/src/views/ConfirmView.tsx`:改 import 首行加 `getOptions, type CellPreset, type Options`:

```tsx
import { useEffect, useState } from "react";
import { createJob, getOptions, type CellPreset, type Mode, type Options, type ParseResult } from "../api";
```

在 `const [err, setErr] = useState<string | null>(null);` 之后加 options state + 拉取:

```tsx
  const [opts, setOpts] = useState<Options | null>(null);
  useEffect(() => {
    getOptions().then(setOpts).catch(() => setOpts(null)); // 失败静默降级为纯文本
  }, []);

  // 选中预设 → 填充 species/cell_type/perturbation_type/targets(便捷,仍可手改)
  function applyPreset(p: CellPreset) {
    setSpecies(p.species);
    setCellType(p.cell_type);
    if (p.example_perturbation_type) setPertType(p.example_perturbation_type);
    if (p.example_targets) setTargets(p.example_targets.join(", "));
  }

  // 下拉选项:枚举 + 保留当前值(避免锁死非枚举内的历史值)
  function withCurrent(list: string[] | undefined, cur: string): string[] {
    const xs = list ?? [];
    return cur && !xs.includes(cur) ? [cur, ...xs] : xs;
  }
```

把 `<div className="grid2">` 之前插入预设选择器:

```tsx
      {opts && opts.cell_presets.length > 0 && (
        <label>
          载入 cell 预设(便捷,可再手改)
          <select
            defaultValue=""
            onChange={(e) => {
              const p = opts.cell_presets.find((x) => x.id === e.target.value);
              if (p) applyPreset(p);
            }}
          >
            <option value="">— 选择物种/细胞预设 —</option>
            {opts.cell_presets.map((p) => (
              <option key={p.id} value={p.id}>{p.label}</option>
            ))}
          </select>
        </label>
      )}
```

把 species 的 `<input>` 改为下拉(options 加载时用 select,否则退回 input):

```tsx
        <label>
          species
          {opts ? (
            <select value={species} onChange={(e) => setSpecies(e.target.value)}>
              {withCurrent(opts.species, species).map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          ) : (
            <input value={species} onChange={(e) => setSpecies(e.target.value)} />
          )}
        </label>
```

把 perturbation_type 的 `<input>` 同样改为下拉:

```tsx
        <label>
          perturbation_type
          {opts ? (
            <select value={pertType} onChange={(e) => setPertType(e.target.value)}>
              {withCurrent(opts.perturbation_type, pertType).map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          ) : (
            <input value={pertType} onChange={(e) => setPertType(e.target.value)} />
          )}
        </label>
```

cell_type 与 targets 的 input 保持不变(自由文本)。

- [ ] **Step 3: 构建验证**

Run: `cd praxis_vc_react && npm run build`
Expected: tsc + vite build 无 error,产出 dist/

- [ ] **Step 4: commit + push**

```bash
cd /Volumes/T7/PRAXIS-virtualcell
find docs praxis_virtualcell praxis_vc_api praxis_vc_react -name '._*' -delete
git add praxis_vc_react/src/api.ts praxis_vc_react/src/views/ConfirmView.tsx
git commit -m "feat(v0.6): ConfirmView species/perturbation_type 下拉 + cell 预设选择器(消费 /api/options)

前端只展示:下拉/预设仅填充输入,失败静默降级纯文本;终局仍后端确定性 runtime。

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push origin main
```

---

## 验收(全部完成后)
- `/api/options` 返回 `cell_presets`(≥10,4 物种,species 不越白名单)。
- ConfirmView 有 species/perturbation_type 下拉 + cell 预设选择器;选预设自动填充,仍可手改;options 拉取失败退回纯文本。
- 全量 `praxis_virtualcell/tests` 0 failed;`npm run build` 通过;每 task 已 push。

## 停止条件(硬门)
1. 预设 species 越白名单(测试红)→ 修预设(不改白名单);2. pytest 回归/npm build 失败无法自解;3. git push 失败/CI 红;4. Task 1–2 完成→切片 3 收尾,简短汇报后继续切片 4(Linux 发行版)。
