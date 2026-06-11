---
name: pdb-fetcher
description: 从 RCSB PDB 拉取结构 (mmCIF + JSON 元数据), 缺失 PDB 的 UniProt 自动从 AlphaFold DB 回退到预测结构。支持单 PDB ID、批量 (--from-jsonl 消费 cazy-crawler 输出)、本地 90 天缓存。
---

# PDB Fetcher Skill

## 一句话原则
mmCIF 优于 legacy PDB 格式 (字段更全);RCSB 实验结构优先,无则用 UniProt accession 从 AlphaFold DB 拉预测;90 天缓存。

## 适用场景
- 把 cazy-crawler 输出的所有 PDB ID 拉到本地
- 给案例的 `parent_enzyme.pdb` 字段提供本地结构
- 缺实验结构的 UniProt 自动从 AlphaFold DB 补预测,确保每个家族成员至少有一个结构

## 标准跑法

### 单 PDB ID
```bash
python skills/workflows/pdb-fetcher/fetch.py --pdb 1CEL
```

### 从 cazy-crawler 输出批量
```bash
python skills/workflows/pdb-fetcher/fetch.py --from-jsonl data/cazy/members/GH7.jsonl
```

### 同时把无 PDB 条目的 AlphaFold 预测拉下来
```bash
python skills/workflows/pdb-fetcher/fetch.py --from-jsonl data/cazy/members/GH7.jsonl --alphafold-fallback
```

### 仅元数据探测 (不下大文件)
```bash
python skills/workflows/pdb-fetcher/fetch.py --from-jsonl data/cazy/members/GH7.jsonl --metadata-only
```

## 参数

| 参数 | 默认 | 说明 |
|------|------|------|
| `--pdb` | - | 单一 PDB ID (可重复) |
| `--from-jsonl` | - | JSONL 路径,提取 `pdb` (列表) 与 `uniprot` (用于 AF fallback) |
| `--out-pdb-dir` | `data/pdb` | PDB 缓存目录 |
| `--out-af-dir` | `data/alphafold` | AlphaFold 缓存目录 |
| `--alphafold-fallback` | off | 无 PDB 时从 AlphaFold DB 拉预测 |
| `--metadata-only` | off | 只拉 JSON 元数据,不下结构文件 |
| `--format` | `cif` | `cif` / `pdb` |
| `--delay` | 0.3 | 请求间隔秒 |
| `--force` | off | 忽略缓存 |
| `--cache-days` | 90 | 缓存有效期 |

## 输出
- `data/pdb/{id_lower}.cif` (或 `.pdb`) — 结构
- `data/pdb/{id_lower}.json` — 元数据 (resolution / method / organism / 链信息 ...)
- `data/alphafold/AF-{uniprot}-F1-model_v4.pdb` — AF 预测 (when fallback)

## 关键元数据字段提取建议
```python
import json
m = json.load(open('data/pdb/1cel.json'))
resolution = m.get('rcsb_entry_info', {}).get('resolution_combined', [None])[0]
method = m.get('exptl', [{}])[0].get('method')        # X-RAY DIFFRACTION / NMR / EM
organisms = [o.get('scientific_name') for o in m.get('rcsb_entity_source_organism', [])]
title = m.get('struct', {}).get('title')
```

AlphaFold PDB 文件中每个 ATOM 的 B-factor 列实际是 pLDDT (0-100 信心分):
```python
# 平均 pLDDT
import re
total = n = 0
for line in open('data/alphafold/AF-P62694-F1-model_v4.pdb'):
    if line.startswith('ATOM'):
        total += float(line[60:66])
        n += 1
avg_plddt = total / n
```

## 数据校验检查清单
- [ ] mmCIF 文件以 `data_` 开头
- [ ] PDB 文件以 `HEADER` 或 `ATOM` 开头
- [ ] 元数据 JSON 含 `rcsb_entry_info`
- [ ] AlphaFold 结构平均 pLDDT > 70 (否则结构置信度低,慎用)
- [ ] 文件大小 > 1KB (排除空响应)

## 常见问题
| 现象 | 原因 | 修复 |
| --- | --- | --- |
| `404` for PDB ID | obsolete / 错误 ID | 检查 RCSB 是否替换为新 ID;cazy-crawler 输出可能含旧 ID |
| 大文件 (>50MB) | EM 大复合物 | 正常,留意磁盘空间 |
| AlphaFold 404 | UniProt 不在 AF DB (古老 / 非 model organism) | 跳过, 记 warning |
| `cif` 解析失败 | 老条目格式不规范 | 切换 `--format pdb` |

## 速率
RCSB 与 EBI AlphaFold 都允许较高速率, 默认 0.3s 即可。
若并发批量 (>500 IDs) 建议调到 0.5s 避免被限。
**不需要 API key**。

## 给酶学研究者的最小可用流程
```bash
pip install requests
python fetch.py --pdb 1CEL --out-pdb-dir ./out
ls ./out/                  # 1cel.cif + 1cel.json
```

## 输出契约

```json
{
  "skill_id": "pdb-fetcher",
  "fetched": [],
  "diagnostics": {
    "brain": "enzyme",
    "archetype": "fetcher"
  }
}
```
