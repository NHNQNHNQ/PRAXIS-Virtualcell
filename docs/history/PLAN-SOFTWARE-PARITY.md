# PLAN — 大脑分析方案 ↔ .53 软件可用性对账

> 起草日期:2026-05-22
> 目标:确保智能体提出的每个分析方案,都能在 staging `.53`(10.102.106.53)上找到对应可执行的软件、conda env、数据集。
> 形式:**先写计划,等用户确认再执行**。

---

## 0. 任务定义

智能体(任意 mode)被一个用户问题触发后,会从大脑里检索/引用一个或多个 **分析方案**(SKILL.md 描述的 workflow,例如 `cellpose-segment` / `alphafold-plddt-analyzer` / `vina-docking`)。
要让方案可执行,必须满足:

| 维度 | 怎么判 |
|---|---|
| **软件** | `.53` 上能找到二进制(`which xxx`)或 python 包(`import xxx`)|
| **conda env** | SKILL.md 的 `env:` 字段对应的 conda env 在 `.53` 存在,且装齐了 deps |
| **数据 / 模型** | 如 hg38 / Brunello / AFDB / DepMap 这些大文件在 `.53` 上找到入口 |
| **license / weights** | 闭源(FoldX / Schrödinger / Rosetta)有授权;模型权重(AF3 / RoseTTAFold)已下载 |
| **GPU / HPC** | 重算力 skill 能跑(局部 GPU 或 HPC `bio000070` 投递) |

只要**任一**维度缺失 → 方案在 `.53` 无法落地,属于「**幻觉式建议**」(智能体提了用户没法执行)。

---

## 1. 当前已掌握的事实(本地勘察)

- 大脑总量:**139** 个 SKILL.md(`find brains -name SKILL.md`)
- 大脑里出现的 conda env 命名(粗扫,出现 ≥2 次):
  - `praxis-pharma`(10)、`praxis-cryo-base`(8)、`praxis-microbiome-kraken`(6)、`praxis-microbiome`(3)、`praxis-drug-base`(3)、`qiime2`(2)、`praxis-drug-vina`(2)、`openclaw-md`(2)、`praxis-drug-rosetta` / `praxis-drug-reinvent` / `praxis-drug-p2m` / `praxis-drug-openfe` / `praxis-drug-aizynth` / `praxis-drug-admet`(各 1)
  - **现状**:staging `.53` 现在**只有一个** `praxis2` env(python 3.13.13 + `.[prod]` + litellm + argon2-cffi + psycopg2)。**大脑预设的 20+ 个学科 env 中,绝大多数不存在**。
- 大脑里出现的工具命名频次(粗扫,top):dali 371†、star 308†、esm 128、chimera 69、cellpose 59、vina 57、foldx 55、salmon 38、bowtie 25、qiime 23、alphafold 22、rdkit 21、gromacs 20、foldseek 20、deseq2 18、relion 17、aizynth 16、pymol 14、cryosparc 10
  - † `dali` / `star` 等是常用英文词,粗扫有 false positive;需要精确正则 + 上下文验证(详见 §3.2)
- SKILL.md frontmatter 大多**没填 `deps:` / `env:`** 字段(上次盘点;仅 `cryo/skills/workflows/environment_setup/SKILL.md` 等极少数)→ 必须从 body 文本启发式提取
- 我**没有 ssh 进 .53 的凭证**,本计划需用户授权或代跑

---

## 2. 阶段总览

```
阶段 0 — 取 .53 环境快照     (需用户决策:ssh 自跑 vs 用户代跑)
阶段 1 — 解析大脑 SKILL.md → 「方案 → 软件/env/数据」清单
阶段 2 — 对账,产「缺口表」
阶段 3 — 写 SOFTWARE-GAP-REPORT.md(给用户看的总报告)
阶段 4 — (可选)回写 SKILL.md frontmatter 的 `deps:` / `env:`,
         让 probe_dependencies() 真能工作
```

每个阶段单独可中断;阶段 4 是可选的「修复回写」,不在「先看清楚」的最小集里。

---

## 3. 阶段细节

### 阶段 0:取 `.53` 环境快照

**目标产物**:`/Volumes/T7/clade-learn/PRAXIS-2/_audit/host_inventory.json`(单文件结构化清单)。

**需要采集**:

| 项 | 命令 | 为啥要 |
|---|---|---|
| 所有 conda env 名 | `conda env list` | 对账 SKILL.md 的 `env:` |
| 每个 env 的包列表 | `for e in $(conda env list \| awk 'NR>2 {print $1}' \| grep -v '^$'); do echo "=== $e ==="; conda list -n "$e" --no-pip 2>/dev/null; done` | 验 deps |
| 每个 env 的 pip 包 | 同上加 `pip list` | conda 缺的可能在 pip |
| 系统二进制 | `which alphafold cellpose vina foldx rosetta gromacs namd relion ...`(批量) | CLI 工具 |
| GPU | `nvidia-smi -L` + `nvidia-smi --query-gpu=name,memory.total --format=csv` | 验重算力 skill 能否跑 |
| HPC 模块系统(若有) | `module avail 2>&1` | LMOD 工具 |
| 数据集入口 | `ls -la /data /opt /home/zkyd/data1/mzy/ ~/datasets 2>/dev/null` | hg38 / Brunello / AFDB 等 |
| FoldX / Schrödinger / Rosetta license | `ls -la ~/.foldx ~/.schrodinger ~/.rosetta 2>/dev/null` | license-gated |
| 本机磁盘可用 | `df -h \| head -20` | 大模型 weights 落地预算 |

**两条采集路径,需用户二选一**:

| 路径 | 我做什么 | 用户做什么 |
|---|---|---|
| **A. ssh 我自跑** | `Bash: ssh zkyd@10.102.106.53 'bash -s' < scripts/collect_host_inventory.sh > _audit/host_inventory_raw.txt`,然后 python 解析 → host_inventory.json | 给我 ssh 通过(privkey 或临时密码) |
| **B. 用户代跑** | 我写 `scripts/collect_host_inventory.sh` 给用户 | scp/复制到 .53 跑完,把 stdout 贴回会话或 `_audit/raw.txt` |

**风险**:
- `conda list -n <env>` 在嵌套环境激活下可能拒绝执行 → 退化为 `ls ~/software/miniconda3/envs/<env>/lib/python*/site-packages/`
- 时间预算:全 env 列出可能 1–3 分钟(看 env 数);GPU / disk 秒级

### 阶段 1:解析大脑 SKILL.md

**目标产物**:`_audit/brains_deps_inventory.tsv`,列结构:

```
brain | skill | requirement_type | name | source_hint | confidence
cell  | cellpose-segment | py_import | cellpose | body:python -c "import cellpose" | high
cell  | cellpose-segment | cli       | cellpose | body:"which cellpose" | high
cell  | cellpose-segment | data      | manual_iou_set | body:"100 manually-annotated cells" | low
enzyme | foldx-stability-scan | cli   | foldx    | body:"foldx --command=BuildModel" | high
enzyme | foldx-stability-scan | license | foldx-academic | inferred from cli=foldx | medium
```

**提取规则**(优先级从高到低):

| 规则 | 正则 / 启发式 | confidence |
|---|---|---|
| frontmatter `deps:` 字段 | YAML key=`deps` | high |
| frontmatter `env:` 字段 | YAML key=`env` | high |
| python `import` / `from ... import` | `(?:^\|\\s)(?:import\|from)\\s+([a-zA-Z_][a-zA-Z0-9_]*)` | high |
| shell `which xxx` | `which\\s+([a-zA-Z0-9_\\-]+)` | high |
| shell `conda install -n <env> <pkgs>` | `conda\\s+install\\s+(?:-y\\s+)?-n\\s+(\\S+)\\s+(.+)` | high |
| shell `pip install xxx` | `pip\\s+install\\s+(.+)` | high |
| 已知工具白名单匹配 | `cellpose\|alphafold\|foldx\|...` 严格词边界 + 排除注释行 | medium |
| 上下文短语 | "需要 GPU"、"AF3 weights"、"hg38" | low(用于人工 review) |

**关键防 false positive**:
- `STAR` / `DALI` 等普通英文词:必须满足「**上下文里同时出现**关键字(`rnaseq`/`aligner`/`structural alignment`/`PDB`)或紧邻 `--xxx` 参数」才计数
- 排除 markdown 标题行(以 `#`) 和单纯的英文段落
- 排除示例数据中 random 字符串

**实现路径**:写一个一次性脚本 `scripts/audit/extract_brain_deps.py`,输入 `brains/`,输出 TSV。脚本本身只读、纯 python 标准库,**不进 praxis2/ 主仓**(一次性审计工具,放 `scripts/audit/`)。

**风险**:
- 启发式必有 false negative / false positive;脚本 v1 不追求 100%,目标是「**让人能 review**」
- 大脑里有些 skill body 是「描述性」的而非可执行代码 → 提取出的包名可能是「该用什么」而非「真要 import」

### 阶段 2:对账

**目标产物**:`_audit/parity_matrix.tsv`,行 = (brain, skill, requirement),列 = `requested | host_has | gap_kind | suggested_fix`。

`gap_kind` 枚举:

| 值 | 含义 | 修复路径 |
|---|---|---|
| `green` | host 有 | — |
| `red:env_missing` | 大脑要 env=praxis-cryo-base,host 没这 env | 建 env + 装 deps |
| `red:pkg_missing` | env 在但缺 pkg | `conda install` / `pip install`(走 §7.3.10 permission 装包) |
| `red:cli_missing` | 缺二进制 | 视情况:apt / 源码编译 / 商业 license |
| `red:data_missing` | 缺数据集 | 拉数据 + 配路径 |
| `red:license_required` | 商业软件未授权 | 跟用户拉 license |
| `red:gpu_required` | 需 GPU 而 host 无 | 走 HPC bio000070 投递(§M7) |
| `gray` | host 装了大脑没用 | 资源闲置,可在新 skill 里复用 |

### 阶段 3:写 SOFTWARE-GAP-REPORT.md

**目标产物**:`SOFTWARE-GAP-REPORT.md`(放仓库根),给用户决策用。

**结构**:

```
1. 摘要表:每个 brain 的 「skill 数 / green / red」三栏
2. Top-N 红色集中清单:装一个能解锁最多 skill 的软件 Top 10
3. 按 brain 细分:
   - 每个 brain 一节
   - 表格:skill → 缺什么 → 怎么修
4. 商业 license / weights 单列:FoldX / Schrödinger / Rosetta / AF3 weights / RoseTTAFold weights / ...
5. HPC-only skill 单列:cryo-EM 重建、大规模 docking、长 MD
6. 修复路线图:P0 / P1 / P2 / P3 + 估算时间
```

`_audit/*` 全部链接进报告,不当作主产物保留。

### 阶段 4(可选):回写 SKILL.md frontmatter

**目标**:把阶段 1 提取出的高置信度 deps / env 写回 SKILL.md frontmatter,这样:

1. `praxis2/skills/deps.py:probe_dependencies()` 真能工作(目前因 SKILL.md 没填 `deps:` → 无可探测)
2. `praxis2/skills/executor.py:choose_env()` 不再 ambiguous

**两种做法,需用户决策**:

| 做法 | 优点 | 缺点 |
|---|---|---|
| **A. 直接 Edit 改本地 brains/** | 立即可用,Mac canonical 直接更新 | 需要 rsync 到 .53,且改了若干文件评审压力 |
| **B. 产 diff/patch 给用户审** | 用户掌握节奏 | 多一步 |

**风险**:启发式 v1 即使是「high confidence」也未必 100% 准,直接落盘可能引入错误 deps。建议 B(产 patch 先看)。

---

## 4. claudecode 工具调用速查(本任务专用)

| 步骤 | tool | 命令样例 |
|---|---|---|
| ssh 拿 .53 数据(若授权) | `Bash` | `ssh zkyd@10.102.106.53 'bash -s' < scripts/audit/collect_host.sh > _audit/host_raw.txt` |
| 写一次性脚本 | `Write` | `scripts/audit/collect_host.sh`、`scripts/audit/extract_brain_deps.py` |
| 解析大脑 | `Bash` + python | `python scripts/audit/extract_brain_deps.py > _audit/brains_deps.tsv` |
| 检查产出 | `Read` | `Read _audit/parity_matrix.tsv`(若大,limit 100 行) |
| 写报告 | `Write` | `SOFTWARE-GAP-REPORT.md` |
| 回写 frontmatter(可选) | `Edit` | 单文件改,replace_all=false |
| 跨步骤检索 | `Agent(Explore, quick)` | 仅当一次 grep 不够时 |

**铁律**:
- 阶段 0 涉及 ssh,需用户先授权
- 阶段 1 脚本只读 `brains/`,绝不 Write
- 阶段 4 改 SKILL.md 必须先 Read 文件 + 跑 diff 给用户看再批量

---

## 5. 给用户的决策点(执行前必答)

| # | 问题 | 默认建议 |
|---|---|---|
| 1 | **阶段 0 怎么拿 .53 数据?** A=授权 ssh / B=您代跑给我贴 | A(快;您给一个 read-only 的临时方式,我跑完就停) |
| 2 | **阶段 1 工具白名单要不要预审?** 我会给一份 ~60 个常见科研工具的白名单 | 先看默认表,不满意您再删/加 |
| 3 | **阶段 2 对账时,大脑里有些 SKILL 是「reviewer aspirational」(论文里有但本地没打算装),要不要包括?** | 全部计入,在报告里标 `aspirational`,不当缺口 |
| 4 | **阶段 4 回写 frontmatter 要不要做?** A=本次做 / B=只产 patch 不写 / C=不做 | B |
| 5 | **报告要不要双语?** 中英对照 vs 纯中文 | 纯中文(与 CLAUDE.md 一致) |

---

## 6. 估算时间 / 工作量

| 阶段 | 估时 | 阻塞依赖 |
|---|---|---|
| 0 | 15–30 min(看 env 数,见 §3.1 风险) | ssh / 用户代跑 |
| 1 | 30 min(写脚本 + 跑) | 无 |
| 2 | 20 min(join + 标 gap_kind) | 阶段 0 + 1 |
| 3 | 40 min(写报告) | 阶段 2 |
| 4 | 30–60 min(若做),取决于改多少 SKILL.md | 阶段 1 高置信度集合 |
| **合计** | 2–3 小时 |

可中断点:每阶段产出独立文件,下次继续直接读。

---

## 7. 已知风险与不确定性

1. **大脑 vs staging 的 env 命名严重不对齐**(staging 只有 `praxis2`,大脑预设 20+ 个 `praxis-*-*`)→ **几乎所有 skill 都会标红 `env_missing`**,这意味着报告会很难看。需要在阶段 3 明确分类「**真要建这么多 env** vs **大脑里命名只是占位,后续合并**」
2. **粗扫 false positive**:`STAR`/`DALI` 等普通词;阶段 1 必须用上下文过滤
3. **license-gated 软件**(FoldX/Schrödinger/Rosetta):本计划只标「需 license」,不替用户去申请
4. **HPC-only skill**:暂时不能在 staging 跑,留 §M7 carry,但报告里标出来
5. **数据集**:很多 skill 需要大数据集(hg38 ~ 3GB / AFDB ~TB 级 / Brunello 几百 MB),磁盘预算要在阶段 0 一并看
6. **大脑「应有但本地缺」的子目录**(上次盘点出的 dock/drug/microbiome/protein 缺 PROMPT.md):这次阶段 1 解析时**仍能解 SKILL.md**(它们各 brain 的 skills 目录都在),不被这缺口阻塞

---

## 8. 不在本计划范围

- 真正安装缺失的软件(那是 SOFTWARE-GAP-REPORT.md 之后的执行)
- 修 SKILL.md 内容本身(只可能改 frontmatter)
- 跑任何真实 skill(需要等环境补齐后才有意义)
- 改 `praxis2/` 主仓代码(`probe_dependencies` / `choose_env` 接口已就绪,不需要改)

---

## 9. 输出物清单

```
_audit/
├── host_inventory.json        ← 阶段 0
├── brains_deps_inventory.tsv  ← 阶段 1
├── parity_matrix.tsv          ← 阶段 2
└── host_raw.txt               ← 阶段 0 原始输出留底
scripts/audit/
├── collect_host.sh            ← 阶段 0 采集脚本
└── extract_brain_deps.py      ← 阶段 1 解析脚本
SOFTWARE-GAP-REPORT.md         ← 阶段 3
(可选)
patches/skill_md_frontmatter_*.patch  ← 阶段 4
```

---

## 10. 待用户确认

请回答 §5 的 5 个问题。**默认全选「推荐项」**就能开干。

如果用户答完确认开干,执行顺序固定:
0 → 1 → 2 → 3 → (4 if 选 A/B)。每阶段产出落盘 + TaskUpdate completed,出问题不会回退已完成阶段的产出。

---

## 11. 配套改动:把 system prompt 真正注入大脑(本计划的孪生 PR)

上一轮发现:当前 `praxis2/server/app.py:_chat_stream` 调 `query(...)` **没传 `system` 参数**(`query.py:55 system=None`),即使 `resolve_agent` 已经算出 `selection.brain_slugs=["_common","cell"]`,**大脑案例 / RMCP 规则 / 安全规则 / skill 摘要全没注入**。模型实际拿到的 system 就是 `None`,只有工具描述出现在 `tools` 字段 → 模型**看见 AgentTool 但完全不知道什么时候、为什么要调它**。

这是「智能体幻觉大、不调工具」的更根本原因。修这个需要 5 步,**作为本对账计划的孪生 PR(独立提交,不打包)**:

| 步 | 代码动作 | 现成可用 | 还要写什么 |
|---|---|---|---|
| 1 | 加载领域大脑 docs(从 `brains/<slug>/memory/cases/*.md` + `rules/*.md`)| 数据已在 `brains/` 本地 | 一个 `BrainStoreLoader.load_for_slugs(slugs)` 函数,产 `list[BrainDoc]`(`praxis2/brains/store.py` 已有 `BrainDoc` 类) |
| 2 | `retrieve_brain(docs, user_query, top_k=K)` | `praxis2/brains/retrieve.py:retrieve_brain` 已就绪 | 调用点 + top_k 取自 settings(默认 5) |
| 3 | `progressive_disclosure(manifests, max_chars, budget_chars)` 产 skill 摘要 | `praxis2/skills/loader.py:progressive_disclosure` 已就绪 | 先用 `parse_skill_md` 把 `brains/<slug>/skills/workflows/*/SKILL.md` 全部解析进 `manifests` |
| 4 | `assemble_agent_sections(selection, retrieval, common_docs, skill_summary, memory_text)` | `praxis2/brains/inject.py:assemble_agent_sections` 已就绪 | `common_docs` = `brains/_common/` 加载;`memory_text` 第一版传空串即可 |
| 5 | `build_effective_system_prompt(agent=sections)` 产最终 system | `praxis2/core/prompt.py` 已就绪 | 把结果传 `query(system=system, ...)` |

**为何 §11 与本对账强耦合**:
- 没有 host inventory(阶段 0)→ skill 摘要里可能列出 `.53` 装不了的方案 → 模型推荐用户跑不了的工具 → 仍然「幻觉」
- 没有 deps 回写(阶段 4)→ `probe_dependencies()` 永远空,执行报错时无法精确告诉模型「装哪个 env 哪个包」

**建议顺序**:本对账计划阶段 0–3 先跑完,产出 `host_inventory.json` → §11 的 step 3 用它过滤 skill 摘要(只把 `.53` 上**真能跑**的 skill 进入 system prompt)。这样智能体的「方案」一开始就是落地的、可执行的,大幅压缩幻觉空间。

---

## 12. 执行哲学:先零报错路径,报错后才查大脑解决

用户明确的设计原则,本计划全程遵循:

> **用户问 → 智能体出方案 → 必须真能跑分析。先在大脑里找不报错的运行方式;只有跑了真报错,才回大脑找解决方案。**

落到执行就是 **双层检索 / 双 prompt 策略**:

### 12.1 第一层(主路径):**正例 + host filter**

智能体在出方案前,system prompt 注入的应是:
- 当 slug 对应大脑的 `memory/cases/*.md` **正例**(去掉 `_neg/` 反例)
- `skills/workflows/*/SKILL.md` 中 **`.53` 上真能跑** 的 skill(通过阶段 0 的 host_inventory 过滤)
- `_common/` 安全规则 + RMCP

效果:智能体推荐的方案默认是「**当下、此地、零报错**」可跑的。

### 12.2 第二层(报错路径):**反例 + troubleshooting**

只有当工具真跑了、`tool_result.is_error=True` 出现时,触发**二次检索**:
- 命中同 skill / 同主题的 `memory/cases/_neg/NEG-*.md`(反例库)
- 命中 `memory/rules/06-anti-rules-from-NEG-cases.md`(12 条反规则禁忌)
- 这些作为 **新一轮的检索结果**,经 `query()` 内核接 `tool_result(is_error)` 后下一回合的 system prompt 增量(或 user message 旁注)

效果:报错 → 智能体看到「这个错前人怎么解的」→ 主动改 deps / 换参数 / 换 skill,而不是瞎猜。

### 12.3 落到本对账计划的具体影响

| 任务 | 怎么体现「先零报错」原则 |
|---|---|
| 阶段 0 host_inventory | 必须详(env / pkg / cli / data / gpu / license 全栈),否则无法判一个 skill 是否「零报错可跑」 |
| 阶段 1 brain deps 提取 | 必须区分 **正例的 SKILL.md**(主路径用)与 **反例 NEG-*.md**(报错路径用);两类各产一份 inventory |
| 阶段 2 对账 | green 集 = 主路径候选;red 集中,有 NEG case 覆盖的标记为「报错有救」(后期模型还能自救),纯 red 没 NEG 覆盖的标 「报错无救」(必须靠装软件) |
| 阶段 3 报告 | 单独一节「主路径 skill 候选集」 + 单独一节「报错路径 NEG 覆盖率」 |
| §11 step 3 skill 摘要 | 第一轮 prompt 只投正例 + 主路径 skill;反例摘要不在 turn-1 暴露(避免误导模型主动建议反规则做法) |
| §11 step 5 build_system_prompt | 加 hook:`on_tool_error` 触发时,把对应反例摘要塞进下一回合 system 的「错误修复指南」section |

### 12.4 与现有大脑设计的对齐

INDEX.md / `_common` / 各 brain 都已显式区分 positive cases vs `_neg/NEG-*.md` vs `rules/06-anti-rules-from-NEG-cases.md`,本哲学**只是把这个区分落到 prompt 注入逻辑**,不需要改大脑文件结构。RMCP 5-Phase 写回(Retrieval → Memory → Case → Promotion)本身也是「报错驱动学习」的体现,§12.2 第二层与 RMCP 的 Case 写回阶段天然衔接(报错 + 修复 → 新案例写回大脑)。

---

## 13. 总览(精简版,给后接手的智能体看)

```
用户提问
  │
  ▼
resolve_agent  ──→ AgentSelection(slug + mode + is_discipline)
  │
  ▼
build_chat_registry(selection)  ──→ tools=[…](已修,§本仓 v0.9.2)
  │
  ▼   ┌──────────── 待修(§11)─────────────────┐
  │   │ load brains[slugs]                    │
  │   │ + retrieve_brain(query, top_k)        │
  │   │ + progressive_disclosure(skills       │
  │   │     ∩ host_inventory「能跑」)         │← 本计划阶段 0 提供过滤
  │   │ + assemble_agent_sections(...)        │
  │   │ + build_effective_system_prompt(...)  │
  │   └────────┬─────────────────────────────┘
  │            ▼
  ▼   query(system=system, registry=reg, ...)
聊天 + tool_use
  │
  ├─ tool ok      ──→ 主路径:智能体出方案,用户拿去 .53 跑
  └─ tool error   ──→ 触发 NEG 检索 → system 加错误修复 section → 重试
```


