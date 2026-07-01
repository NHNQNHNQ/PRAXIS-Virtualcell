# PLAN v0.5 — 补齐所有剩余 case(strict 15/15 + roadmap extras + 远端硬门)

> 目的:v0.4 已让 **5 代表应用 × 4 物种全覆盖**(10 case + L4)。本计划把**剩余的"第 3 例"补到 strict 15/15**,并把需远端的准确性补强登记为硬门。loop 按顺序取第一个未勾选 `- [ ]` 完成。
> 现状:`docs/paper/v0.4/application-cases.md`。测试基线 Mac **179 passed + 25 skipped**。
> **自主授权**:标准 pip 工具自装;权威公开数据/模型自下载(scanpy/pertpy/squidpy 自带数据集、BiGG GEM、已下载的 LINCS 库)并记 provenance(URL+sha);科学默认(marker panel/阈值/培养基)自定并写明依据。

## 铁律(每步必守,自主 ≠ 降标准)

- **TDD** 先写失败测试;**真跑工具/公开数据不 mock**;每 case 强制 **7 部分**输出(structured input / object normalization / models selected / raw output / baseline / reliability decision / provenance+boundary)。
- **不过度承诺**:信号弱/证据不足 → **downgrade/abstain + boundary**,这算成功(治理有效),不算失败。
- **无泄漏**;**per-cell ≠ pert-level**;**不训练新模型**(不 new foundation model / Delta-Adapter / cross-species predictor / Router)。
- 复用现有基座(`GemModel`/`scoring.py`/`CaseReport`/route_table 引擎),**不复制**;新引擎才加 `ENGINES`。
- 完成后跑 `.venv/bin/python -m pytest praxis_virtualcell/tests` 无回归;commit 前 `find docs praxis_virtualcell data -name '._*' -delete`;**本地单独 commit**(末尾 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`);勾选 `- [x]` 回填 finding。
- 大数据 gitignore,只提交 curated 子集 + provenance。新 .py 过 ruff(E702/UP037/F401/E402/B/I;E501 中文长行可留)。

---

## A 类 — 自主可做(公开数据,纯 Mac,loop 主战场)

### - [x] R1 — Stem/progenitor 分化 fate(应用 3 例 3A)【已完成】
- **落地**:paul15(scanpy 自带)子集 750 cells;`predictors/state/fate.py`(复用 scoring.py)+ route state_scoring。
- **真跑**:fate 评分红系 +1.27 vs 髓系 −2.76,**Cohen's d 4.32 → accept**;两 panel 覆盖取 min,缺一→downgrade;原生小鼠 marker 分析(ortholog N/A)。`test_fate_case.py`(4 passed)。finding `finding_v0_5_fate_case.md`。

### - [x] R2 — Drug dose-response(应用 2 深化;dose)【已完成】
- **落地**:LINCS 剂量子集(3 药 × 各剂量 top-150,22.6KB committed);`predictors/embedding/drug_dose.py`;recall vs 最多信号剂量参考 的 dose-Spearman。
- **治理对照(实跑)**:geldanamycin Spearman 0.90→**accept**;sirolimus recall 近零→**downgrade**(幅度守卫);vorinostat→caution。`test_drug_dose_case.py`(4 passed)。finding `finding_v0_4_drug_case` §6。不训练模型。

### - [x] R3 — Bacteria antibiotic → growth(应用 2 例 2C)【已完成】
- **落地**:iML1515(BiGG,620KB committed);`predictors/mechanistic/antibiotic.py`(复用 GemModel);route 扩 `(microbe, drug, growth)→gem_fba`。
- **真跑**:trimethoprim(靶 DHFR)/ sulfamethoxazole(靶 DHPS2)→ growth 0(致死)→**accept**;ciprofloxacin(非代谢靶)/ 未知 →**abstain**(GEM 诚实弃权)。`test_antibiotic_case.py`(5 passed)。finding `finding_v0_4_metabolism_cases` §7。不训练模型。

### - [x] R4 — Cancer EMT/resistance state(应用 3 例 3C)【已完成】
- **落地**:pertpy `mcfarland_2020`(泛癌 MIX-seq)子集 900 cells;`predictors/state/emt.py`(复用 scoring.py)。
- **真跑**:EMT 评分肉瘤(间质)+0.03 vs 上皮癌 −1.16,**Cohen's d 1.72 → accept**;marker 覆盖取 min 缺一→downgrade。`test_emt_case.py`(4 passed)。finding `finding_v0_5_emt_case.md`。
- **诚实**:mcfarland 无 TGF-β 诱导扰动 → 本 case 是 EMT **状态刻画**(哪类癌偏间质),非扰动诱导 EMT 转变(已标注)。不训练模型。

### - [x] R5 — Spatial niche 响应(应用 5 例 5B)【已完成】
- **落地**:squidpy 装成;`imc`(乳腺癌 IMC)子集 3909 肿瘤细胞;空间 k-NN(k=15)预计算 niche;`predictors/spatial/niche.py`;route 加 `spatial_niche` 引擎(medium+state)。
- **真跑**:间质邻接肿瘤 EMT 评分 −1.90 vs 贫瘠 −4.70,**Cohen's d 0.74 → caution**(间质诱导部分 EMT:Vim↑ ECad↓);niche 细胞不足→abstain。`test_spatial_niche_case.py`(4 passed)。finding `finding_v0_5_spatial_case.md`。不训练模型。

### - [ ] R6 — Co-culture / two-cell receiver(应用 5 例 5C)
- **数据**:复用 Kang L-R 子集(`kang_lr_subset.json`)换 sender/receiver 组合(如 DC→NK 的不同 L-R 对),或自主找 co-culture 公开数据。
- **分析**:sender 扰动 → receiver state shift(L-R 通讯 + receiver marker 响应两步链)。复用 `lr_comm.py` + `cell_state` 评分。
- **验收**:通讯链 + receiver 响应一致→accept;任一环节弱→downgrade。7 部分。
- **产出**:扩 `lr_comm.py` 或 `predictors/communication/coculture.py` + test + finding。

### - [ ] R7 — 补矩阵到 15/15 + 更新 outline(纯 Mac)
- **产出**:`application-cases.md` 矩阵填满已完成格、R5/R6 表补 R1-R6 case、strict 15/15 计数;`RESULTS-CONSOLIDATED.md` 测试数 + 广度更新。
- **验收**:矩阵与 finding 一致;未做的(需注册/远端)如实标,不虚填。

---

## 🛑 B 类 — 远端硬门(需 zkyd@10.102.106.53,备 runbook 后停)

### - [ ] 🛑 G1 — scGen / STATE 同协议入表 A
- **为何停**:需远端适配/训练 scGen、STATE 到 donor norman split + per-cell ΔPearson(同 L4 口径)。
- **loop 动作**:仿 `docs/L4-gears-remote-runbook.md` 写 scGen/STATE 的 donor-eval runbook(接口 `load_norman`/`EvalAgent` 复用),**停下等远端跑**。

### - [ ] 🛑 G2 — B2 per-cell 解 W4.5 单 control
- **为何停**:把 disagreement 从单 control 升级 per-cell 全量,需远端重跑。备配方后停。

---

## loop 停止条件(其余一律继续,不问"下一步")

1. `git push`(只本地 commit);
2. 改**已核验的 v0.2/v0.3 正文**(只新增 v0.4/v0.5 文档);
3. 测试失败 / 真跑数字与 finding 对不上且诚实 debug 无法自解;
4. 数据需**凭证/许可/注册**或**无可定位公开源**(记清缺什么、试过哪些源);
5. 步骤标 🛑(需远端 zkyd)——备 runbook 后停;
6. 全部 A 类(R1-R7)完成、B 类停在远端门 → 停,简短汇报。

---

## /loop 提示词(直接粘贴)

```
/loop 自主推进 docs/PLAN-v0.5-complete-remaining.md：反复取第一个未勾选(- [ ])步骤，按其"数据/分析/验收/铁律"做到底，直到所有 A 类步骤完成或撞硬门，中途别打断我。自主授权(别问，直接做+finding 记 provenance)：标准 pip 工具自装(scanpy/pertpy/squidpy/cobra)；权威公开数据自下载(scanpy/pertpy/squidpy 自带数据集、BiGG iML1515、已下载 LINCS 库)记 URL+sha256；科学默认(marker panel/阈值/培养基/dose 解析)自定并写明依据。每步铁律：TDD 先写失败测试、真跑不 mock、每 case 强制 7 部分输出、信号弱则 downgrade/abstain 不过度承诺、无泄漏、不训练新模型、复用现有基座(GemModel/scoring.py/CaseReport/route 引擎)不复制。完成后跑 .venv/bin/python -m pytest praxis_virtualcell/tests 无回归、写/更新 finding、commit 前 find docs praxis_virtualcell data -name '._*' -delete、本地单独 commit(末尾 Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>)、把该步骤改 [x] 回填 finding、继续下一步。只在这些硬门停：①git push；②改已核验 v0.2/v0.3 正文；③测试失败或数字对不上且无法自解；④数据需凭证/许可/注册或无公开源(记清试过哪些源)；⑤步骤标 🛑 需远端 zkyd(备 runbook 后停)；⑥A 类 R1-R7 全完成。全部完成后简短汇报即可，别问我下一步。
```
