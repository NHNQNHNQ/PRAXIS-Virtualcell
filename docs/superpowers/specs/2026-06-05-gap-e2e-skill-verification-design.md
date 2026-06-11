# GAP-E2E:skill 真执行验证 harness + docking 切片

**日期**: 2026-06-05 · **状态**: 设计待批 · **范围**: GAP-E2E-1 第一轮(harness + docking archetype)
**前置**: v0.18.0 GA;`TEST-AGENT-FRAMEWORK.md` GAP-E2E-1(159 workflow 仅 1 个 DONE_real,109 写了没验)

---

## 0. 目标与非目标

### 目标
建一个**可复用的 skill 真执行验证 harness**,经**真实输入**驱动 skill 经 SkillExec 真路径(SSH+conda+`python run.py`,`simulate=false`)在 staging 跑,**用证据**判定每个 skill 是 DONE_real / N-A / RED / ERROR,更新 `_audit/skill_real_impl_inventory.csv`。本轮先在 **docking archetype(9 skill)** 跑通,把 DONE_real 从 1 扩到 docking 真可跑集,其余如实标因由。

### 非目标(本轮不做)
- **不一次性验 52/159**:harness 建好后逐 archetype 迭代,本轮只 docking。
- **不补缺失软件/不自动安装**:env/软件缺 → 如实标 RED(走 ops backlog)。
- **不改 skill 的 run.py 实现**:只验证现状(发现 bug 另立修复项)。
- **不接入相位门/stop_hook**(那是 GAP-AH,独立子项目)。

---

## 1. 关键决策(brainstorm 结论)

| # | 决策 | 理由 |
|---|---|---|
| 1 | 输入来源 = **策展参考输入集** `_audit/e2e_inputs/`(真数据) | skill 不自带测试数据;输入 SHAPE 在各 SKILL.md 输入契约。忠于"真分析"、可复用、确定性。对比"公共 DB 现取"(网络脆弱)、"最小合成"(不真正压软件) |
| 2 | 首切片 = **docking(9 skill)** | env 已验(praxis-dock+gnina);输入 shape 共享(receptor+ligand);vina 是现成 DONE_real 模板;后续 archetype 只需补输入集 |
| 3 | 执行 = **走 SkillExec 真路径**(`SkillExecTool.run(simulate=false)`) | 验的是生产执行链(SSH+conda+run.py+stdin JSON+解析),不是绕过它直跑 run.py |
| 4 | 判定四分类 **DONE_real / N-A / RED / ERROR**(见 §3.2) | 用证据替代猜测;诚实暴露"商业软件/GPU 权重缺"等真因 |
| 5 | harness 在 staging 跑(经既有 e2e SOP) | env 与参考数据都在 .53;复用 rsync+ssh+PYTHONPATH SOP |

### 已核查事实(2026-06-05)
- 既有 `scripts/audit/`(refresh_all/parity)只做**依赖对账**(green_skills.json 52 个)+ `skill_outputs_parsed.json` 只**静态解析 SKILL.md 输出契约**;`scripts/uplift/` 只**生成 run.py**。**无真执行 runner** → 即 GAP-E2E 空缺。
- run.py 契约:stdin JSON → `real(payload)` 真跑 / `simulate(payload)` 合成;`{"simulate":false}` 缺真输入 → `real()` 返 ok=False("receptor_pdb 不存在")。
- docking 9 skill(green_skills.json):`vina_gnina_dock`(DONE_real)/`covalent_docking`/`flexpepdock_peptide`/`induced_fit_docking`(Schrödinger 商业)/`pose_buster_validate`/`protein_na_docking`/`redock_benchmark`/`snugdock_antibody`/`af3_complex_predict`(GPU 权重)。
- staging:`praxis-dock` env 在;`~/data1/mzy/DL-masif/1.pdb` 等参考 PDB 存在。

---

## 2. 架构

```
_audit/e2e_inputs/docking.json     # 策展输入:每 skill 一个真 payload(引用 staging 上真数据文件路径)
        │
scripts/e2e_skill_matrix.py         # harness(可单测的纯逻辑 + 一个 staging 执行入口)
        │  读 green_skills.json[archetype] + e2e_inputs[skill]
        │  逐 skill → SkillExecTool.run({name, inputs, simulate:false})
        │  分类 verdict(DONE_real/N-A/RED/ERROR)
        ▼
_audit/e2e_results_<archetype>.json # 报告(verdict + 证据摘要 + 真输出 key)
_audit/skill_real_impl_inventory.csv# 回写 status(DONE_real 扩面)
```

### 职责拆分(便于单测)
- **纯逻辑层**(可本地单测,不依赖 SSH):`classify_verdict(tool_result, contract_keys) -> verdict`、`load_inputs()`、`update_inventory_csv()`。
- **执行层**(staging 真跑):`run_skill(name, inputs)` 调 SkillExecTool;`main()` 遍历 + 写报告。

---

## 3. harness 设计

### 3.1 输入集 `_audit/e2e_inputs/docking.json`
```json
{
  "vina_gnina_dock": {"receptor_pdb": "<staging 真受体路径>", "ligand_smiles": "CC(C)Oc1cnc(NC2CCC(C(=O)NC3CC3)CC2)nc1", "num_modes": 9, "exhaustiveness": 8, "simulate": false},
  "redock_benchmark": {"...": "复用同受体+晶体配体"},
  "...": "每 skill 一个,按其 SKILL.md 输入契约;真数据文件 rsync 到 staging 固定目录 ~/data1/praxis2-e2e-inputs/"
}
```
- 受体 PDB:策展一个**带晶体配体的标准复合物**(vina autobox 需 HETATM 晶体配体作 box 参考)。优先复用 staging 现有;否则取一个标准小复合物(如激酶-抑制剂)固化到 `~/data1/praxis2-e2e-inputs/`(plan 阶段定具体 PDB)。
- 商业软件/GPU 类(induced_fit/af3)给输入但预期判 N-A/RED(不阻塞)。

### 3.2 判定四分类(`classify_verdict`)
| verdict | 条件 |
|---|---|
| **DONE_real** | tool_result ok=True **且** 输出 `diagnostics.simulated != True` **且** 含 SKILL.md 契约的核心 key(如 docking 的 poses/best_pose/affinity) |
| **N-A** | real() 显式返回"N/A / 未装 / composite / 需上层编排"(ok=False 且 error 含 N/A 标记)或 `simulate=true` 兜底 |
| **RED** | env/软件缺(error 含 "未在 PATH" / "conda activate 失败" / rc=1 env 不存在) |
| **ERROR** | 其它失败(超时 / run.py 内部异常 / SSH 失败) |

### 3.3 执行细节
- 调 `SkillExecTool.run(payload)`,env 用 staging `~/praxis2.env`(PRAXIS_SKILL_SSH_HOST 等已配)。
- 逐 skill 超时(默认 600s,af3 等重型可在输入集标 `"skip": true` 跳过并记 SKIPPED)。
- 幂等:每次重跑覆盖 `_audit/e2e_results_docking.json`;CSV 回写按 (brain,skill) 主键更新 status。
- 不删不改 skill 源码。

### 3.4 CSV 回写
`update_inventory_csv(results)`:把 verdict=DONE_real 的行 status 从 TODO → DONE_real;其余保留 TODO 但在报告里带 verdict+原因(CSV 只认 DONE_real/TODO,详细因由在 JSON 报告)。

---

## 4. 测试策略

### 单测(`tests/test_e2e_skill_matrix.py`,纯逻辑,不依赖 SSH)
- `classify_verdict`:喂构造的 tool_result → 验四分类(DONE_real 真输出 / N-A 标记 / RED env 缺 / ERROR 超时)。
- `load_inputs`:读 docking.json + 缺 skill 输入的处理。
- `update_inventory_csv`:回写 DONE_real,不动其它行,幂等。

### e2e(staging,controller 亲做)
- rsync harness + `e2e_inputs/docking.json` + 受体数据 → .53 → ssh `PYTHONPATH=$PWD python scripts/e2e_skill_matrix.py docking`。
- 验:vina_gnina_dock = DONE_real(真 poses + 真 affinity,非 simulated);其余 8 个得到诚实 verdict(真跑的升 DONE_real,商业/GPU 类标 N-A/RED 带因由)。
- 输出 `_audit/e2e_results_docking.json` + 更新后的 CSV 拷回。

---

## 5. DoD

- [ ] `_audit/e2e_inputs/docking.json` 策展(9 skill 输入,真受体数据定位/固化)
- [ ] `scripts/e2e_skill_matrix.py`:load_inputs / run_skill(SkillExec real) / classify_verdict / 报告 / CSV 回写
- [ ] `tests/test_e2e_skill_matrix.py` 纯逻辑单测(四分类 + CSV 回写 + 幂等)
- [ ] 全量回归零回归
- [ ] e2e staging:docking 9 skill 跑出诚实 verdict;vina DONE_real 复现(真 affinity)
- [ ] `_audit/skill_real_impl_inventory.csv` DONE_real 扩面(docking 真可跑集);`e2e_results_docking.json` 归档
- [ ] 文档:`TEST-AGENT-FRAMEWORK.md` GAP-E2E-1 回填本轮结果 + harness 用法
- [ ] commit(只 add 目标文件,不碰 microbiome)

---

## 6. 依赖 + 影响

- **无新 pip 依赖**(harness 用 stdlib + 复用 SkillExecTool)。docking 软件(gnina)staging 已装。
- **staging**:固化参考输入到 `~/data1/praxis2-e2e-inputs/`;`~/praxis2.env` 的 SKILL SSH 三件套已配。
- **不动**:主链 / 工具 run.py 源码 / brains 内容 / 前端。
- **回滚**:harness + 输入集 + CSV 均为新增/审计产物,无运行时影响。

---

## 7. 后续(GAP-E2E 迭代)

docking 跑通后逐 archetype 补输入集复用同 harness:structure_predict(序列输入)/ omics_scrna(小数据集)/ pharma / mhc_epitope / mutation_scan 等。16 个 "(map-needed)" archetype 先归类再补。最终目标:`skill_real_impl_inventory.csv` 高频集 DONE_real,红项进 ops backlog。
