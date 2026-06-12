# PRAXIS-virtualcell Baseline

## 基线 1 — 复制后(原 PRAXIS-2 代码)

- 日期:2026-06-11
- 源:`/Volumes/T7/clade-learn/PRAXIS-2` @ commit `b124d66`
- Python:3.13.12(机器无 python3.11,`requires-python >=3.11` 满足)
- 安装:`python3 -m venv .venv && pip install -e ".[dev]"`;另 `brew install libmagic`
- 命令:`pytest tests -q`
- 结果:**2051 passed, 24 failed, 129 skipped, 26 xfail(共 2230)**

### 24 个失败 — 全部证明为 PRAXIS-2 自带 pre-existing(非复制引入)

**验证方法**:在**原仓自带 venv** `/Volumes/T7/clade-learn/PRAXIS-2/.venv` 跑 `test_md_ssh_unit::test_ssh_run_returns_stdout` + `test_files_mime::test_detect_png_magic` → **同样红、同样报错**(原仓也是 python 3.13)。证明我们的复制忠实、未损坏代码。

| 类别 | 数量 | 失败用例 | 根因 | 处置 |
|---|---|---|---|---|
| md 远程执行 infra | 13 | test_md_local_runner(6)、test_md_ssh_unit(4)、test_md_gpu_pool_unit(3) | `praxis2/md/ssh.py` 在函数内 lazy `import asyncssh`,测试 `@patch("praxis2.md.ssh.asyncssh")` 桩错对象 → AttributeError。PRAXIS-2 自带 test bug。 | 与虚拟细胞无关;Phase 3 后视情 skip/记录 |
| 可选工具链 `_real` | 10 | test_dock(3)、test_protein(3)、test_run_py_smoke(4) 的 `[*_real]` | 需 RDKit/BioPython(可选,未装)。dock/protein 正是 Phase 3 要删的学科 | Phase 3 删 dock/protein 后随测试一并移除 |
| libmagic MIME | 1 | test_files_mime::test_detect_png_magic | libmagic 5.48 对该 PNG fixture 返回 `text/plain`(版本差异)。原仓同样红 | 环境差异;Phase 3 后视情 skip/记录 |

- 结论:**复制忠实,代码可跑,0 个复制引入失败。** Gate PASS(失败已逐条解释并证明 pre-existing)。

## 基线 2 — 去学科脑 + 补 virtualcell 脑后

- 日期:2026-06-12
- 命令:`pytest tests -q -m "not integration"`
- 结果:**1099 passed, 14 failed, 39 skipped**

### 去脑变更
- `DISCIPLINE_SLUGS = ["virtualcell"]`,4 源对齐(`migrate.DISCIPLINE_SLUGS` / `migrate._SLUG_CASE_HINTS` / `loader._SLUG_KEYWORDS` / `server.app._AGENT_META`;`scripts.migrate_brains._LEGACY_SLUGS` 是 `DISCIPLINE_SLUGS` 的 alias)。
- 删 13 学科脑;新增 `brains/virtualcell`(metadata + AGENT-PROMPT + 1 case + 1 rule + 1 skill workflow `perturbation_predict`)。

### 用例总数 2230 → 1152 属预期
baseline-1 含 13 学科的逐学科 skill 测试(`tests/skills/test_{cell,crispr,...}.py` 大量 parametrized 用例)。删学科脑后被测对象已移除 → 这些用例不再 collect,**非回归**。

### 去脑引入失败:0(~48 个全部「靠重写」修复,覆盖 21 个测试文件)
- slug 计数不变式(==13→==1):test_correctness_slug_canonical / test_brains_profile / test_brains_store_migrate / test_migrate_brains / test_m5_invariants / test_m8_invariants / test_files_routes
- 路由(resolve_agent / OAA / yourself):学科 slug → virtualcell;OAA 关键词查询 → `norman perturbation`
- fixture 检索命中:test_brains_retrieve_first / test_brains_inject / test_brains_query_integration / test_m5(查询 → `Virtualcell 领域`)
- 工具注册 + brain_query + rmcp_write:enzyme/cell/dock → virtualcell;stiffler case → vcell-001 种子
- skill_exec(8):新增 virtualcell skill `perturbation_predict`(host_env=praxis-virtualcell + run.py),8 测试改用它

### 剩余 14 失败 — 全部 PRAXIS-2 自带 pre-existing(非去脑、非复制引入)
**已在原 PRAXIS-2 仓自带 venv 复跑确认同样红**(md_ssh / md_local_runner / md_gpu_pool / files_mime 均验证):

| 失败 | 数量 | 根因 |
|---|---|---|
| test_md_local_runner(6)、test_md_ssh_unit(4)、test_md_gpu_pool_unit(3) | 13 | `praxis2/md`(分子动力学 SSH 远程执行)lazy import asyncssh,测试 `@patch("praxis2.md.ssh.asyncssh.connect")` 桩错对象。与虚拟细胞无关。 |
| test_files_mime::test_detect_png_magic | 1 | libmagic 5.48 对 PNG fixture 返 `text/plain`(版本差异) |

- 处置:**不修、不 xfail** —— 属 PRAXIS-2 无关模块(MD 远程执行 / libmagic),修它们是 bootstrap 范围外 scope creep;如实记录为携带项,留待后续按需处理。
- 结论:**去脑+补脑后 0 净新增失败;14 失败全部 pre-existing 且证明非本项目引入。** Gate PASS。
