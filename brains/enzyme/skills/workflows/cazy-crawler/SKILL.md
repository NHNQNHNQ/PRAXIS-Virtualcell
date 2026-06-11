---
name: cazy-crawler
description: 从 CAZy (http://www.cazy.org) 增量爬取指定家族的酶成员列表,输出标准 JSONL 到 data/cazy/members/。支持本地 HTML 缓存、断点续爬、礼貌速率限制。下游索引构建 (MMseqs2 / Foldseek) 与案例库扩充的入口。
status: green
host_env: praxis-protein
deps: [requests]
---

# CAZy Crawler Skill

## 一句话原则
礼貌爬取 (≥2s 间隔) + 本地 raw HTML 缓存 + 增量续爬。CAZy 不提供 API,只能爬 HTML;CAZy 月更新一次,无需高频抓取。

## 适用场景
- 为某个 CAZy 家族 (如 GH7) 取全部成员的 UniProt / PDB / EC,用于:
  - 序列检索索引构建 (MMseqs2)
  - 结构检索索引构建 (Foldseek)
  - 案例库的候选 parent 池扩充
- 不适用: 跨所有家族的批量爬取,优先考虑 [`cazy_webscraper`](https://github.com/HobnobMancer/cazy_webscraper) (PyPI, MIT)

## 先检查环境
```bash
python3 -c "import requests, bs4; print('OK')"
ls /Volumes/T7/EnzymeAgent/data/cazy/   # 应能看到 raw/ 和 members/
```

## 标准跑法

### 单家族
```bash
cd /Volumes/T7/EnzymeAgent
python skills/workflows/cazy-crawler/crawl.py --family GH7
```

### 批量 GH 全家族 (~3 小时)
```bash
for n in $(seq 1 173); do
  python skills/workflows/cazy-crawler/crawl.py --family GH$n --resume --delay 2
done
```

### 仅重解析本地缓存 (改 parser 后)
```bash
python skills/workflows/cazy-crawler/crawl.py --family GH7 --from-cache
```

### 验证输出
```bash
wc -l data/cazy/members/GH7.jsonl
head -3 data/cazy/members/GH7.jsonl | python -m json.tool
```

## 参数

| 参数 | 默认 | 说明 |
|------|------|------|
| `--family` | (必填) | CAZy 家族名,大小写敏感 (GH7 / GT1 / PL2 / CE5 / AA9) |
| `--tabs` | `characterized,structure` | 逗号分隔。可选: `all` `bacteria` `eukaryota` `archaea` `viruses` |
| `--cache-dir` | `data/cazy/raw` | 原始 HTML 缓存目录 |
| `--out-dir` | `data/cazy/members` | JSONL 输出目录 |
| `--delay` | `2.0` | 两次请求间隔秒,**不允许 < 1.0** |
| `--resume` | off | 跳过已有 `{family}.jsonl` 的家族 (用于批量) |
| `--from-cache` | off | 只解析本地缓存,不发网络请求 |
| `-v / --verbose` | off | DEBUG 日志 |

## 输出 JSONL 字段
```json
{
  "family": "GH7",
  "subfamily": null,
  "tab": "characterized",
  "protein_name": "Cellobiohydrolase I (Cel7A)",
  "ec": "3.2.1.176",
  "organism": "Trichoderma reesei",
  "genbank": "AAA34210.1",
  "uniprot": "P62694",
  "pdb": ["1CEL"],
  "characterized": true,
  "crawled_at": "2026-04-27T14:30:00Z"
}
```

跨 tab 时按 `(uniprot, genbank)` 去重。

## 礼貌爬取规则 (硬性)
- 默认 2s 间隔,**绝不调到 < 1s** (脚本会拒绝)
- User-Agent 标明研究目的: `EnzymeAgent-research/0.0.1`
- HTTP 503 / 403 / 429 → 退避 (10s, 30s, 60s),三次失败放弃该家族
- 已有缓存 HTML 且 mtime < 30 天 → 不重复请求

## 数据校验检查清单 (跑完必看)
- [ ] JSONL 行数 ≥ 该家族 CAZy 网页显示成员数的 80%
- [ ] `uniprot` 字段非空率 ≥ 60% (古老条目可能无 UniProt)
- [ ] 至少 1 条记录有 `pdb`
- [ ] `organism` 不为空
- [ ] 没有 HTML 标签泄漏 (如 `<a href=...`)

## 常见问题

| 现象 | 原因 | 修复 |
|------|------|------|
| `403 Forbidden` | UA 被标 / 速率太快 | 调慢 `--delay` 到 5,换 UA |
| `0 records written` | CAZy 改版 | 检查 `data/cazy/raw/` 的 HTML 是否含成员表;若结构变更需更新 `parse_member_table()` |
| 所有 `uniprot` 都为 None | 列顺序变更 | 检查 `--verbose` 输出的 headers 是否被识别 |
| 编码错误 | 部分页面 latin-1 | 脚本默认 utf-8;失败时降级 latin-1 |
| 家族名错误 (404) | 子家族写法不同 | 检查 cazy.org 实际 URL,例如 `GH5_4` 不是 `GH5.4` |

## 法律 / 伦理
- CAZy 是公开学术数据库,礼貌爬取自用合规
- **不要 redistribute** 抓取数据集 (违反 CAZy 服务条款)
- 用于研究、记忆库填充、索引构建均可
- 生产场景建议直接用 `cazy_webscraper` (功能更全,有 API 缓存数据库)

## 与 EnzymeAgent 其他模块的衔接
- 输出 JSONL → `scripts/retrieval/seq.py` (待写, MMseqs2 序列库构建)
- 输出 UniProt → `skills/workflows/uniprot-fetcher/` (拉取 FASTA + 完整 JSON 注释)
- 输出 PDB ID → `skills/workflows/pdb-fetcher/` (拉取结构 + 元数据,缺则 AlphaFold 回退)
- 输出 family + ec → 用于 retrieval 通道的强先验 (见 `config/retrieval.yaml`)

## 给酶学研究者的最小可用流程

如果你只想快速拿到一个 CAZy 家族的成员清单 (不依赖 EnzymeAgent 其余模块):

```bash
# 1. 安装最小依赖
pip install requests beautifulsoup4

# 2. 跑
python crawl.py --family GH7 --out-dir ./out

# 3. 看结果
head -1 ./out/GH7.jsonl | python -m json.tool
```

输出 JSONL 可直接 import 到 pandas / Excel / 自家数据库。

## 输出契约

```json
{
  "skill_id": "cazy-crawler",
  "fetched": [],
  "diagnostics": {
    "brain": "enzyme",
    "archetype": "fetcher"
  }
}
```
