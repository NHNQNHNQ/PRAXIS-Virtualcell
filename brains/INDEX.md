# PRAXIS Suite — Agent Brains 完整大脑索引

> 每个 PRAXIS 模块完整的「**案例学习大脑**」：cases / rules / indices / skills / schemas / prompts / agents / scripts / lims / memory + INIT/BUILD report。
> **不是**单纯的 system prompt——是从零起即可手工构建并继续学习的 agent 全状态。
> 上传：2026-05-08 from Mac `/Volumes/T7/newagent/` + `/Volumes/T7/EnzymeAgent/` + `/Volumes/T7/MDAgent/Naruto-main/`
> 目标：`zkyd@10.102.106.53:/home/zkyd/data1/mzy/PRAXIS-DEMO/_brains/` (≈ 1.1 GB)

---

## 总览：14 个学科大脑（v0.21.0 真实统计 2026-06-10）

> 数字由 `scripts/brain_audit.py` 自动统计（已清除 609 个 macOS `._` AppleDouble 垃圾文件）。
> 文件格式规范见 [`docs/项目说明与路线图.md`](../docs/项目说明与路线图.md) §四。

| 学科 | cases | rules | skills | 说明 |
|---|---|---|---|---|
| cell | 32 | 7 | 11 | 单细胞 |
| crispr | 29 | 12 | 11 | 基因编辑 |
| cryo | 23 | 14 | 11 | 冷冻电镜 |
| dock | 41 | 3 | 13 | 分子对接 |
| drug | 11 | 14 | 12 | 药物设计（4-stage orchestrator） |
| enzyme | 72 | 13 | 11 | 酶工程 |
| immuno | 25 | 8 | 11 | 免疫 |
| md | 17 | 11 | 8 | 分子动力学（v0.21 本地 A100 真执行链） |
| microbiome | 29 | 16 | 24 | 微生物组 |
| omics | 30 | 20 | 13 | 组学 |
| pharma | 21 | 15 | 11 | 药代/PKPD |
| protein | 48 | 13 | 17 | 蛋白设计（4-stage orchestrator） |
| synth | 11 | 22 | 13 | 合成生物学 |
| _common | — | 1 | 1 | 跨学科共享规则 |
| **总计** | **389** | **169** | **167** | 14 学科 |

> 历史校准：旧版本表格写「12 模块 411 cases」，系 ① macOS `._` 垃圾文件被翻倍计数 ② Synth 未计入 ③ 文件总数含 prompts/data/ 等非 case 文件。已用 `brain_audit.py` 按真实 `memory/cases/*.md`（排除 README/`._`）重算。
>
> 已知待整理：md 学科 17 个 case 无标准 frontmatter（Naruto-main 导入格式）；md 目录结构 `Naruto-main/` 嵌套待归一（见路线图 Phase 1.4）。

---

## 每个模块包含什么

```
_brains/<module>/                 ← 全部从 Mac canonical 拷过来
├── README.md / CLAUDE.md / BUILD_REPORT.md     ← 元文档
├── prompts/<MODULE>-AGENT-PROMPT.md            ← runtime brain (paste-ready)
├── agents/                                     ← 4-stage orchestrator + retrieval
│   ├── orchestrator.py / runtime.py / retrieval.py
│   └── prompts/{scoping,design,execution,reporting,reviewer}.md
├── memory/                                     ← 案例学习核心
│   ├── cases/<positive>.md                     ← 真实文献案例 (10-72 each)
│   ├── cases/_neg/NEG-*.md                     ← 反例 (12 ~ each)
│   ├── rules/<rule>.md                         ← 案例提炼出的硬/软规则
│   ├── layers/                                 ← case_cards (RAG-friendly) + compiled
│   ├── archive/                                ← 历史快照
│   └── index.json                              ← 全索引 v2.0
├── indices/                                    ← BM25 + 向量 + anti-retrieval
│   ├── bm25/   vector/  anti/  knowledge/
│   └── index_manifest.json
├── skills/                                     ← 真实计算能力
│   ├── workflows/<skill>/SKILL.md + run.py
│   └── _common.py / _<helper>.py
├── schemas/                                    ← 输入输出 JSON Schema
├── config/                                     ← agent.yaml / retrieval.yaml / tools.yaml
├── scripts/                                    ← distill / fetch / retrieval 脚本
├── lims/                                       ← 跨 agent envelope_router + filedrop_watcher
├── tools/                                      ← rdkit_props / sgrna_scoring / 等领域工具
├── tests/                                      ← pytest 套件
├── data/                                       ← 数据缓存 (Greengenes / hg38 / DepMap / 等)
└── runs/                                       ← 历史 run 输出
```

---

## 用法

### 1. 想直接用某模块的 agent（最常见）
```bash
# 远端
cd /home/zkyd/data1/mzy/PRAXIS-DEMO/_brains/<module>/

# 把 brain 提示词作为 system prompt paste 给 LLM
cat prompts/PRAXIS-<MODULE>-AGENT-PROMPT.md   # for Cell/CRISPR/Cryo/Immuno/Pharma
cat <MODULE>-system-prompt.md                  # for Dock
cat SYSTEM-PROMPT-PRAXIS-<MODULE>.md           # for Microbiome
cat AGENT_PROMPT.md                            # for Omics
cat .claude/agents/praxis-enzyme.md            # for Enzyme

# 启动 4-stage orchestrator (Drug / Protein / Enzyme)
python -m agents.orchestrator --task-id mytask ...
# 或 single-agent 一次性脑（Omics 已封装）
cat agents/prompts/single_agent.md
```

### 2. 检索同模块的相关案例（预热 / 调试）
```bash
cd /home/zkyd/data1/mzy/PRAXIS-DEMO/_brains/<module>/
python scripts/retrieval/build_index.py     # 重建本地索引
python scripts/retrieval/test_anti_retrieval.py   # 验证 NEG 反例命中率
ls memory/cases/ | head                     # 查看实际案例
ls memory/cases/_neg/                       # 查看反例
ls memory/rules/                            # 查看规则
```

### 3. 接着学习（写新案例 → 蒸馏 → 升 promotion）
```bash
cd /home/zkyd/data1/mzy/PRAXIS-DEMO/_brains/<module>/
# 在 memory/cases/ 写一份新 case .md（按 schemas/ 里的 case 模板）
python scripts/distill/run.py             # Extractor → Normalizer → Merger → Promoter
```

### 4. 想造一个还不存在的 agent（如 PRAXIS-Synth、PRAXIS-Glycoscience）
```bash
cat /home/zkyd/data1/mzy/PRAXIS-DEMO/_brains/_meta/PROMPT-PRAXIS-Synth.md
# 把这份 META 提示词喂给 Claude，等它把整套目录树 + 案例 + 规则 + skills 都构建出来
```

---

## 关键约定

每个 PRAXIS-* 模块的 brain 都遵循同一份模板（来自 PRAXIS-Enzyme 参考实现）：

| 元素 | 文件 / 路径 | 说明 |
|---|---|---|
| 8 条**硬规则** | runtime brain 顶部 | 每个 PRAXIS 都有，内容因领域而异 |
| 12 条**反规则禁忌** | runtime brain + memory/rules/06-anti-rules-from-NEG-cases.md | NEG- 反例系统化 |
| **RMCP 5-Phase 写回** | runtime brain 中段 | Retrieval → Memory → Case → Promotion |
| **2-of-3 工具一致性** | skills/workflows/<skill>/SKILL.md | 任何关键决策必须 2 个独立工具同向 |
| **真实文献门槛** | scripts/distill/qa.py | CrossRef DOI / UniProt / PDB / GEO 等 6 层 QA |
| **跨 agent envelope** | lims/filedrop_watcher.py + envelope_router.py | 多 agent 协作的统一 schema |

---

## 同步与更新

**Mac 是 canonical 源**——所有写回（新案例、新规则）发生在 Mac，再 rsync 到 remote。

```bash
# Mac → remote 更新（增量；不删旧文件）
sync_one() {
    rsync -az --partial \
        --exclude=__pycache__ --exclude='._*' --exclude='*.pyc' --exclude='.DS_Store' \
        "$1/" "zkyd@10.102.106.53:$2/"
}
sync_one /Volumes/T7/newagent/PRAXIS-Cell /home/zkyd/data1/mzy/PRAXIS-DEMO/_brains/cell
# ... (每个模块同样)
```

如要 remote → Mac 反向同步（实验状态重新落盘）：在 rsync 命令里把 src / dst 互换即可。
