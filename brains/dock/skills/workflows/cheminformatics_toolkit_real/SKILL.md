---
name: cheminformatics_toolkit
description: RDKit 通用化学信息学工具 — SMILES↔InChI↔规范化、分子式、Morgan 指纹 Tanimoto 相似性、SMARTS 子结构匹配、Murcko 骨架、Lipinski 类描述符。通用计算工具(非对接分析链)，跨 dock/synth/pharma/enzyme 高频复用。
host_env: praxis-dock
schema_version: 1
domains: [dock]
inputs_schema:
  smiles: {type: string, required: true, desc: "分子 SMILES"}
  operations: {type: array, required: false, desc: "操作列表;不传则给默认分析"}
  smiles2: {type: string, required: false, desc: "第二分子 SMILES(tanimoto 相似性用)"}
  smarts: {type: string, required: false, desc: "SMARTS 模式(substructure_match 用)"}
status: real
references: []
---

# cheminformatics_toolkit — RDKit 通用化学信息学工具

## When to use

需要对小分子做**通用、原子级**化学信息学操作时（不是某学科的完整分析链）：

- **格式转换**：SMILES → 规范化 SMILES / InChI / InChIKey
- **分子识别**：分子式、Lipinski 类描述符(MW/logP/HBD/HBA/TPSA/环数/可旋转键)
- **相似性**：两分子 Morgan(ECFP4) 指纹 Tanimoto 系数
- **子结构**：SMARTS 模式匹配 + 命中数
- **骨架**：Murcko 骨架

对接分析链（vina_gnina_dock / pose_buster 等）仍走各专用 skill；
本 skill 只补"裸 RDKit 计算"的通用工具缺口，跨化学多学科复用。

## Operations

| operation | 需要 | 输出 |
| --- | --- | --- |
| `canonical_smiles` | — | RDKit 规范化 SMILES |
| `inchi` | — | InChI 字符串 |
| `inchikey` | — | InChIKey(27 字符) |
| `formula` | — | 分子式(Hill 记法) |
| `scaffold` | — | Murcko 骨架 SMILES |
| `descriptors` | — | `{mol_weight,logp,h_donors,h_acceptors,tpsa,num_rings,rotatable_bonds}` |
| `tanimoto` | smiles2 | Morgan(r=2,2048bit) Tanimoto 系数 |
| `substructure_match` | smarts | `{match:bool, count:int}` |

不传 `operations` 时默认 `[canonical_smiles, formula, inchikey, descriptors]`。

## I/O

- 输入：`--inputs '{"smiles":"CC(=O)Oc1ccccc1C(=O)O","operations":["formula"]}'`(JSON 文件路径或 inline)
- 输出：stdout JSON `{"ok":true,"input_smiles":"...","results":{...}}`
- 失败(非法 SMILES/空)：`{"ok":false,"error":"..."}`

## 示例

```bash
python run.py --inputs '{"smiles":"CC(=O)Oc1ccccc1C(=O)O","operations":["formula","inchikey"]}'
# → results.formula == "C9H8O4", results.inchikey 以 BSYNRYMUTXBXSQ 开头(阿司匹林,PubChem CID 2244)

python run.py --inputs '{"smiles":"CC(=O)Oc1ccccc1C(=O)O","smiles2":"c1ccccc1","operations":["tanimoto"]}'
# → 0 < results.tanimoto < 1
```

## host_env

`praxis-dock`(rdkit 2025.03.6 已装)。纯计算，无外部网络/GPU 依赖。

## 测试

同目录 `test_run.py`(不依赖 pytest)覆盖 12 个用例，praxis-dock env 真跑 rdkit 全 PASS。
Oracle 出处标注于测试注释(阿司匹林值经 PubChem CID 2244 + NIH CACTUS 双源核对)。
