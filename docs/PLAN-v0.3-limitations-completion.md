# PLAN v0.3 — Limitations 补强执行计划(把缺陷转成补强路线)

> 目的:把 `docs/paper/v0.3/data-inventory.md` §9 缺口清单 + Limitations 转成**可执行、可自驱动**的补强步骤。
> **进度以本文件的勾选框为准**(loop 每次重读本文件找下一个 `- [ ]` 步骤);每步完成后把 `- [ ]` 改 `- [x]` 并回填 finding 路径。
> 当前测试基线:Mac **97 passed + 25 skipped**(L1 后);git HEAD 见 `git log -1`。

## 总原则(铁律,每步必守)

- 数字**实跑不臆造**;先远端见证再入表/论文;**无泄漏**(真 dp 只当 label,过 `governance/ledger_features`);**pert-level ≠ per-cell** 不混;OOF/泛化 与 in-sample 回放 分清;**硬规则不被 learned 覆盖**。
- 每步 **TDD**(先写失败测试)+ **本地单独 commit**(末尾 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`);commit 前 `find docs praxis_virtualcell -name '._*' -delete`。
- **不**重训 foundation model、**不**重写成熟工具、**不**做 Delta-Adapter、**不**把 E9 写进本论文。
- 自研模块/章节出可验证结果 → 在本文件勾选 + 简短汇报。

## 三类缺陷处理方针

| 类 | 定义 | 处理 |
|---|---|---|
| **A 类** | 小工作量、显著降审稿风险 | **现在补**(纯 Mac 自动) |
| **B 类** | 影响主刊竞争力、工作量大 | 投稿前第二阶段(多需远端,**停下等人**) |
| **C 类** | 真实边界 / future work | 论文诚实写,**不补** |

---

## 执行步骤(loop 按顺序找第一个未勾选项)

### - [x] L1 — perturbation-level bootstrap CI(A 类,纯 Mac)【已完成】
- 产出:`governance/bootstrap_ci.py` + `tests/test_bootstrap_ci.py`(4 passed)+ `docs/findings/finding_w9_m2_bootstrap_ci.md` + `docs/findings/m2_bootstrap_ci.json`。
- 结论:四个配对差值 CI 不跨 0(learned−disagreement AUROC +0.13 [0.056,0.191]、risk-cov AUC +0.026 [0.014,0.041];learned−rule wrong-accept 降 0.76 [0.59,0.92]、risk-cov 增 0.76 [0.59,0.92])。
- **注意**:此步已出 finding 但**可能尚未 commit** → loop 第一动作:若 `git status` 显示 L1 相关文件未提交,先单独 commit 它(message 例:`feat(w9/M2.1 L1): perturbation-level bootstrap CI — 配对差值 CI 不跨 0`)。

### - [x] A2 — 证据分层 + runtime-replay 限制句(A 类,无需新跑)【已完成】
- 已落在 `docs/paper/v0.3/learned-governance.md`(§A 证据分层表 + R7 限制句)、`-zh.md`、`data-inventory.md`(§0/§7)。loop 仅在 L3 整合时确认措辞,无需独立工作。

### - [x] L2 — OOD enrichment / OOD-only risk-coverage(A 类,纯 Mac)【已完成 → `docs/findings/finding_w9_m2_ood_enrichment.md`】
- 结果:learned-flagged 98% 是 OOD(odds ratio 74.7);但超越 OOD 标签 — OOD-only 子集 risk-cov AUC 0.577>0.5、learned AUROC 0.907>ood-only 0.788。`governance/ood_enrichment.py` + `tests/test_ood_enrichment.py`(4 passed)+ `m2_ood_enrichment.json`。
- **目标**:回答"learned abstain 是否偏好弃权 OOD(未见)扰动",并区分 learned 是否只是 OOD 标签的代理。
- **数据**:`docs/findings/m1_ledger_151.jsonl` 的 `seen_in_train` 字段(OOD flag,推理期可得 → 可分析,**非 label**);v0.2 记 82/151 未见。
- **复用**:`reliability_model.cv_reliability`(OOF)、`bootstrap_ci._prepare`(拿 learned/rule flag)、`abstain_head.risk_coverage/rc_auc`。
- **产出**:`governance/ood_enrichment.py`(纯 Python)+ `tests/test_ood_enrichment.py`(TDD)+ `docs/findings/finding_w9_m2_ood_enrichment.md` + `docs/findings/m2_ood_enrichment.json`。
- **验收(实跑数字)**:
  1. base rate:151 中 OOD(`seen_in_train` 为 0/False/None→未见)占比;
  2. learned flagged/abstained 中 OOD 占比 · rule_only flagged 中 OOD 占比 · random 中 OOD 占比;
  3. **OOD enrichment odds ratio** = (abstained 中 OOD 占比 / retained 中 OOD 占比);
  4. **OOD-only 子集 risk-coverage AUC** vs **seen-only 子集** risk-coverage AUC(learned 排序);
  5. 解读:learned bad-pert AUROC 0.907 > ood-only 0.788 ⇒ learned **不只是** OOD 标签;若 abstained 富集 OOD 则"learned 也抓 OOD regime",若不明显则诚实写"learned 抓低准度扰动**超越** OOD 本身"。
- **TDD**:合成小例验证 enrichment/odds-ratio 计算正确 + 151 实跑断言方向(odds_ratio 有定义、OOD-only 与 seen-only AUC 都返回)。
- **诚实边界**:`seen_in_train` 在 ledger 的覆盖率须如实报(若多 None,enrichment 仅在有 flag 的子集成立);pert-level;单 control(W4.5)。

### - [x] B3 — 多 seed 重复 5-fold CV(A 类补充,纯 Mac,轻)【已完成 → `finding_w9_m2_bootstrap_ci.md` 补充节 + `m2_repeated_cv.json`】
- 结果:5 seed learned AUROC 0.900±0.008、risk-cov AUC 0.744±0.001,每 seed 均 > disagreement(方向 100% 稳定)。`governance/repeated_cv.py` + `tests/test_repeated_cv.py`(4 passed)。
- **目标**:给 OOF 指标(AUROC 0.907 / risk-cov AUC 0.746)加跨 seed 稳健性,补 bootstrap CI(回应"单一确定性 5-fold")。
- **复用**:`reliability_model.cv_reliability` 现按固定 fold;加 `seed` 参数打乱 fold 分配(仍 leave-perturbation-out,无泄漏),跑 5 seeds × 5 folds。
- **产出**:在 `bootstrap_ci.py` 或新 `governance/repeated_cv.py` 加函数 + test + 在 `finding_w9_m2_bootstrap_ci.md` 追加"repeated CV"小节(或新 finding)。
- **验收**:报 5 seeds 的 learned AUROC / risk-cov AUC 的 mean ± sd(或 min–max);断言方向稳定(每个 seed learned > disagreement)。
- **诚实**:多 seed 只动 fold 划分,不动数据;仍 pert-level、151。

### - [ ] L3 — 把 CI + OOD + 多seed 整合进 v0.3 文档(A 类,纯 Mac,改 v0.3 文档)
- **改**(均为 v0.3 新文档,**不碰 v0.2 正文**):
  - `docs/paper/v0.3/learned-governance.md`:Limitations 的"无 CI"改成 finding_w9_m2_bootstrap_ci 里备好的英文句;R3/R2 加 CI 区间;新增 OOD-enrichment 一小段(R3 后或新 R)。
  - `docs/paper/v0.3/learned-governance-zh.md`:同步中文。
  - `docs/paper/v0.3/data-inventory.md`:§9 缺口表把"无 bootstrap CI"标【已补 → finding_w9_m2_bootstrap_ci】;§7A 加 CI;新增 OOD enrichment 行。
- **验收**:三文档数字与 finding 一致;无新引用需核验;`learned-governance.md` 与 `-zh.md` 逐节对应。
- **可选**:重生成中文 docx(pandoc),仅当用户要。

### - [ ] 🛑 L4 — GEARS same split / same metric 入表 A(B 类,**远端,必停**)
- **为何停**:需远端 `zkyd@10.102.106.53` 适配/(重)训 GEARS 到 donor norman split + per-cell ΔPearson(铁律:先远端见证再入表)。loop **不可**自动跑远端。
- **loop 动作**:把可跑配方/脚本准备好(检查 `benchmarks/gears_norman.py` 现状、写 donor-split 适配 TODO),写一份"远端执行清单",然后**停下汇报**,等用户在远端跑完贴回数字再入表 A + 解 R8。
- **诚实**:GEARS 原生 pearson_de 0.8392(off-axis)≠ ΔPearson;同 split 适配是关键。

### - [ ] 🛑 B2 — per-cell 解 W4.5 单 control(B 类,**远端+重,必停**)
- **为何停**:把 disagreement 从单 control 升级为 per-cell 全量,需远端重跑;影响面大。主刊增强项,优先级在 L4 之后。
- **loop 动作**:仅在 PLAN/文档登记为主刊增强,**不自动做**,等用户明确启动。

### C 类 — 不补,论文写 Future Work(loop 不执行)
- **Router**:固定 ensemble 0.693 近 oracle 0.7043,硬路由空间仅 +0.011 → deferred,接更异构 predictor 后再启。
- **Delta-Adapter**:易引入泄漏、把主线拉回性能 → 暂缓。
- **跨物种真 predictor**:mouse/bacteria/yeast 仅路由层原型 → future work。
- 论文 Discussion/Limitations 用 data-inventory §10 / learned-governance Discussion 的现成措辞。

---

## loop 执行协议(自动边界与停止条件)

**每次 loop fire**:读本文件 → 找**第一个未勾选 `- [ ]` 步骤** → 按其"产出/验收/铁律"完成 → 跑 `praxis_virtualcell/tests` 确认无回归 → 写/更新 finding → 本地单独 commit → 把该步骤勾上并回填 finding 路径 → 简短汇报 → 继续下一个未勾选步骤。

**遇到以下任一,立即停下汇报、不要继续**:
1. 步骤标 🛑(需远端 `zkyd@10.102.106.53`:L4 GEARS / B2 per-cell)——准备好脚本/配方后停;
2. 需要 `git push`(只本地 commit,push 留给用户);
3. 需要修改**已核验的 v0.2 正文**(`docs/paper/v0.2/`);
4. 测试失败、或 point estimate 与已落地 finding 数字对不上、且无法自行定位;
5. 需要新增**外部文献引用**(须先核验);
6. 所有非 🛑 步骤(L2/B3/L3)全部完成 → 停,交回用户决定是否启动远端 B 类。

**C 类一律不执行**,只在文档写 future work。

---

## /loop 提示词(直接粘贴到 Claude Code)

```
/loop 读 docs/PLAN-v0.3-limitations-completion.md，找到第一个未勾选(- [ ])的步骤，严格按它的"产出/验收/铁律"完成：TDD(先写失败测试)、数字实跑不臆造、无泄漏(真 dp 只当 label)、pert-level≠per-cell、OOF/泛化与 in-sample 回放分清、硬规则不被 learned 覆盖。完成后跑 .venv/bin/python -m pytest praxis_virtualcell/tests 确认无回归，写/更新对应 finding，commit 前先 find docs praxis_virtualcell -name '._*' -delete，再本地单独 commit(末尾 Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>)，并把 PLAN 里该步骤改成 [x] 回填 finding 路径。每完成一步简短汇报后继续下一个未勾选步骤。

遇到以下任一立即停下汇报、不要继续：①步骤标 🛑(需远端 zkyd@10.102.106.53：L4 GEARS / B2 per-cell)——把脚本/配方准备到可跑就停，等我远端跑完贴回数字；②需要 git push；③需要改已核验的 v0.2 正文(docs/paper/v0.2/)；④测试失败或数字与 finding 对不上且无法自解；⑤需新增外部文献引用；⑥所有非 🛑 步骤(L2/B3/L3)全部完成。C 类(Router/Delta-Adapter/跨物种 predictor)一律不做，只在文档写 future work。
```
