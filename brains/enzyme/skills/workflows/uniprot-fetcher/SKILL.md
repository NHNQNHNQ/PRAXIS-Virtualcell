---
name: uniprot-fetcher
description: 用 UniProt REST API 批量拉取 accession 的完整 JSON 注释 (organism / function / EC / active sites / glycosylation / PDB cross-refs) 与 FASTA 序列到 data/uniprot/。批量端点 200/请求,显著快于逐条;支持单个 accession、JSONL 批量 (--from-jsonl 直接消费 cazy-crawler 输出)、本地 90 天缓存。
---

# UniProt Fetcher Skill

## 一句话原则
UniProt 有干净的 REST API,优先用批量端点 (200/批);单次批量响应里既含注释也含序列,无需为 FASTA 再发请求;90 天缓存。

## 适用场景
- 把 cazy-crawler 输出的 JSONL 中所有 UniProt accession 全量拉到本地
- 单独补充某个 accession 的完整注释
- 给案例/检索索引提供序列与字段 (organism / EC / active_site / glycosylation / PDB cross-refs)

## 先检查环境
```bash
python3 -c "import requests; print('OK')"
ls /Volumes/T7/EnzymeAgent/data/uniprot/
```

## 标准跑法

### 单 accession
```bash
python skills/workflows/uniprot-fetcher/fetch.py --accession P62694
```

### 从 cazy-crawler 输出批量拉取 (推荐)
```bash
python skills/workflows/uniprot-fetcher/fetch.py --from-jsonl data/cazy/members/GH7.jsonl
```

### 强制刷新已缓存的条目
```bash
python skills/workflows/uniprot-fetcher/fetch.py --from-jsonl data/cazy/members/GH7.jsonl --force
```

### 只要 FASTA (省磁盘空间, 跳过 JSON 写文件)
```bash
python skills/workflows/uniprot-fetcher/fetch.py --from-jsonl data/cazy/members/GH7.jsonl --fasta-only
```

## 参数

| 参数 | 默认 | 说明 |
|------|------|------|
| `--accession` | - | 单一 UniProt accession (可重复) |
| `--from-jsonl` | - | JSONL 路径,提取 `uniprot` 字段,与 --accession 互斥 |
| `--out-dir` | `data/uniprot` | 输出目录 |
| `--batch-size` | 100 | 每批 accession 数,API 上限 200 |
| `--delay` | 0.5 | 批次之间间隔秒 |
| `--force` | off | 忽略缓存强制重拉 |
| `--fasta-only` | off | 跳过 JSON 文件写盘 (网络仍是 JSON 批量) |
| `--cache-days` | 90 | 缓存有效期 |
| `-v / --verbose` | off | DEBUG 日志 |

## 输出
- `data/uniprot/{accession}.json` — 完整注释 (UniProt JSON schema)
- `data/uniprot/{accession}.fasta` — 序列 (从 JSON 派生,header 兼容 SwissProt 风格)

## 关键 JSON 字段提取建议
```python
import json
e = json.load(open('data/uniprot/P62694.json'))
seq = e['sequence']['value']
ec_numbers = [x['value'] for x in e.get('proteinDescription', {})
              .get('recommendedName', {}).get('ecNumbers', [])]
organism = e['organism']['scientificName']
active_sites = [(f['location']['start']['value'], f.get('description'))
                for f in e.get('features', []) if f['type'] == 'Active site']
glyco_sites = [f['location']['start']['value']
               for f in e.get('features', []) if f['type'] == 'Glycosylation']
pdbs = [x['id'] for x in e.get('uniProtKBCrossReferences', [])
        if x['database'] == 'PDB']
```

## 数据校验检查清单
- [ ] FASTA 文件以 `>` 开头, 序列行宽 60
- [ ] JSON 含 `sequence.value` 字段
- [ ] JSON 文件大小 > 1KB (空响应通常是 obsolete accession)
- [ ] 批次失败率 < 5%

## 常见问题

| 现象 | 原因 | 修复 |
| --- | --- | --- |
| `404 Not Found` (单批漏几个) | accession 已 obsolete | 用 secondary accession; 检查 https://www.uniprot.org/uniprotkb/{acc} 是否 redirect |
| 大量 None 序列 | 批响应中无该 accession | 检查 accession 拼写; isoform 后缀 (-1/-2) 可能不被 batch 接受 |
| `429 Too Many Requests` | 速率过快 | 调慢 `--delay` 到 1s |
| 中断后重跑慢 | 已缓存条目仍在 | 默认会跳过, 看 `[cache]` 日志确认 |

## 速率上限
UniProt REST 允许约 25 req/s (批量端点);默认配置远低于此。**不需要 API key**。

## 给酶学研究者的最小可用流程
```bash
pip install requests
python fetch.py --accession P62694 --out-dir ./out
cat ./out/P62694.fasta
python -c "import json; e=json.load(open('./out/P62694.json')); print(e['organism']['scientificName'])"
```

## 输出契约

```json
{
  "skill_id": "uniprot-fetcher",
  "fetched": [],
  "diagnostics": {
    "brain": "enzyme",
    "archetype": "fetcher"
  }
}
```
