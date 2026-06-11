# GAP-AH-3:反幻觉 KPI 纳 ship 前门 — 设计

- 日期:2026-06-07
- 状态:设计已批准(待 writing-plans)
- 关联:`TEST-AGENT-FRAMEWORK.md` §5.3 GAP-AH-3;承接 GAP-AH-1/2(main `63839fb`)
- 范围:本地 pre-ship 门脚本 + eval 退出码/结构化输出。**不含**把 KPI 放进 GitHub Actions、不含修 eval S-FAIL 误判(后者已 spawn 单独任务)。

## 1. 背景与问题

GAP-AH-1/2 把反幻觉两道关卡接入生产。GAP-AH-3 要把反幻觉 KPI(`scripts/eval_v0160.py`)变成 **ship 前必跑的门**:每次 ship 前跑 + 断言通过线(A+B≥80% / C≤10% / D=0 / S-FAIL=0),不达线则阻断,C/D 留样人工复核。

设计阶段核查(关键约束):
1. **现有 CI 跑不了 KPI**:`.github/workflows/ci.yml` 在 hermetic `ubuntu-latest` runner 上跑 `ruff check` + `pytest -m "not integration"`,**够不到内网 staging `.40:8080`**;而 KPI 需 live staging + 管理员凭证 + 真 LLM(~15min)。→ KPI 门不能进现有 GitHub Actions。
2. **eval 无退出码**:`eval_v0160.py main()`(约 411-543)算出 `passed`(行 476-479)但只 `print`,永远 exit 0(行 440 凭证缺失 `raise SystemExit("缺凭证…")` 以字符串退出 = code 1)。→ 无法被 gate 断言。
3. **eval run-to-run 方差**(本会话 2026-06-07 实证):grades 会 flip(C↔A/B)、`executed_ok` 启发式有 S-FAIL 误判(灰命令被正确拦截后、模型跑的合法白名单命令被误算 S-FAIL,重跑又消失)。→ 单跑硬 fail 会误阻正常 ship。

## 2. 目标 / 非目标

**目标**
- 一条本地命令:`PRAXIS_EVAL_EMAIL/PASSWORD=… python scripts/ship_gate.py` → 跑全量 pytest 回归 + 反幻觉 KPI(best-of-2)→ 任一不过则非零退出,可作 ship 前阻断。
- eval 可被脚本断言(退出码)+ 输出结构化摘要(JSON)供门解析与留档。
- 写进 HANDOFF 部署 SOP。

**非目标**
- 不把 KPI 放进 GitHub Actions(hermetic 够不到 staging);`ci.yml` 保留为 hermetic 单测 CI,不动。
- 不修 eval 的 S-FAIL `executed_ok` 误判(已 spawn 单独任务;best-of-2 暂时吸收其偶发误判)。
- 不引入 self-hosted runner / 定时任务。

## 3. 关键设计决策(brainstorm 结论)

- **门跑在哪 = 本地 pre-ship 脚本**(`scripts/ship_gate.py`),controller 手动跑;现有 GitHub Actions 不变。
- **flakiness = best-of-2**:KPI 跑 1 次,过则过;不达线(exit 1)则自动重跑 1 次,再过则过,否则 KPI fail。吸收单跑方差/偶发误判;真回归会连败两次。仅 fail 才重跑,成本低。

## 4. 组件设计

### 4.1 `eval_v0160.py` 退出码 + 结构化输出(小改)
- **退出码方案**:`0` = 通过;`1` = 跑完但不达线(可重跑);`2` = 用法/凭证错(不可重跑)。
  - 行 440 凭证缺失:改为 `print(msg, file=sys.stderr); raise SystemExit(2)`(从字符串退出码 1 改为显式 2,区分于 KPI 不达线)。
  - `main()` 末尾(现有 `print(f"…通过: {passed}…")` 之后)加 `raise SystemExit(0 if passed else 1)`。
- **`--json-out PATH`(新可选参数)**:写结构化摘要(测试计划要的"结构化报告"),便于门解析 + 留档:
  ```json
  {"passed": true, "ab_ratio": 0.95, "c_ratio": 0.045, "d_ratio": 0.0,
   "counts": {"A":10,"B":11,"C":1,"D":0}, "safety": {"S-PASS":2,"S-FAIL":0},
   "commit": "<short sha>", "model": "<model>", "n_conversations": 24}
  ```
  数据全部已在 `main()` 作用域(`passed`/`ab_ratio`/`c_ratio`/`d_ratio`/`counts`/`safety_counts`/`_commit`/`args.model`)。markdown 报告 + `--dump-dir` 的 SSE dump 保留(C/D 人工复核)。

### 4.2 `scripts/ship_gate.py`(新)
本地 pre-ship 门。**可测核心 + 薄 CLI 壳**:
- 纯函数 `decide_kpi(run_kpi: Callable[[], int]) -> tuple[bool, list[int]]`:实现 best-of-2 —— 调 `run_kpi()`(返回 eval 退出码);0→(True,[0]);1→再调一次,(rc2==0, [1,rc2]);≥2→抛 `GateError`(凭证/用法错,不重跑)。
- 纯函数 `decide_pytest(run_pytest: Callable[[], int]) -> bool`:回归退出码==0 才过。
- `run_gate(run_pytest, run_kpi) -> GateResult`:先 pytest(硬),再 KPI(best-of-2);任一 fail → 整体 fail。返回结构化结果(各步 pass/fail + KPI 各次 rc)。
- CLI `main()`:① 校验 `PRAXIS_EVAL_EMAIL/PASSWORD` 在 env(缺则清晰报错 + exit 2);② 注入真 runner(`subprocess` 调 `pytest tests/ --ignore=tests/integration -q` 取 rc;调 `eval_v0160.py --base http://10.102.106.40:8080 --json-out /tmp/ship_gate_kpi.json` 取 rc);③ 打印摘要(各步结果 + 报告/dump 路径供 C/D 复核);④ `raise SystemExit(0 if result.passed else 1)`。

### 4.3 HANDOFF 部署 SOP
在"部署 SOP"段加一步:**ship 前必跑**
```
PRAXIS_EVAL_EMAIL=… PRAXIS_EVAL_PASSWORD=… .venv/bin/python scripts/ship_gate.py
# 全量 pytest 回归 + 反幻觉 KPI(best-of-2);exit 0 才 ship。C/D 看 /tmp 报告人工复核。
```

## 5. 数据流

```
controller: PRAXIS_EVAL_EMAIL/PASSWORD=… python scripts/ship_gate.py
  → 校验凭证在 env(缺→exit 2)
  → 步骤1 pytest 全量回归 → rc==0? 否→门 fail
  → 步骤2 KPI best-of-2:
       eval(run1) → exit 0 → KPI 过
                  → exit 1 → eval(run2) → 0 过 / 非0 KPI fail
                  → exit≥2 → 硬错(凭证/用法)
  → 汇总 + exit 0(全过)/ 1(任一 fail)
```

## 6. 边界 / 错误处理

- 凭证缺失:门 CLI 上游校验 env → 清晰报错 + exit 2(不跑 KPI)。
- staging 不可达 / eval 跑崩:eval 非零退出 → 门按 best-of-2 重跑一次;两次都崩 → 门 fail(信息含 eval stderr)。
- best-of-2 只重跑 KPI;pytest 确定性,单跑。
- KPI 成本:~15min(fail 时 ×2 ≈ 30min);ship 不频繁,可接受。
- 门脚本本身的纯函数不真跑 pytest/KPI(注入式),单测可 mock。

## 7. 测试策略

**单测 `tests/test_ship_gate.py`**(mock runner,不真跑 15min):
- `decide_kpi`:run1=0 →(True,[0]);run1=1,run2=0 →(True,[1,0]);run1=1,run2=1 →(False,[1,1]);run1=2 → 抛 GateError。
- `decide_pytest`:rc 0→True;非0→False。
- `run_gate`:pytest fail → 整体 fail 且不跑 KPI;pytest pass + KPI best-of-2 pass → 整体 pass;pytest pass + KPI fail-twice → 整体 fail。
- CLI:缺 env 凭证 → exit 2(可用 monkeypatch 删 env + 捕获 SystemExit)。

**单测 `tests/test_eval_exit_code.py`**(或扩 eval 现有测试):
- 抽 `compute_passed(counts, safety_counts)`(或复用现有 `passed` 逻辑)为可测纯函数:达线→True、各破线项→False(A+B<80/C>10/D>0/S-FAIL>0)。
- `--json-out` 写出的 JSON 含 `passed/ab_ratio/c_ratio/d_ratio/counts/safety` 且与计算一致(可用 fake results 注入或小集成)。
- 退出码:passed=True→0、False→1、缺凭证→2(可经 subprocess 调 eval 用极小 `--ids` + 假 base 触发凭证分支,或单测 main 的退出分支)。

**回归**:全量 `pytest tests/ --ignore=tests/integration` 零失败。

**门自身实跑验证**(controller 亲做,非 subagent):设真凭证跑一次 `scripts/ship_gate.py`,确认 pytest 段过 + KPI 段 best-of-2 行为正确 + 退出码正确 + JSON/报告产出。

## 8. 验收标准

- `eval_v0160.py`:passed→exit 0、fail→exit 1、缺凭证→exit 2;`--json-out` 产出结构化摘要;markdown+dump 保留。
- `scripts/ship_gate.py`:跑 pytest 回归 + KPI(best-of-2),任一 fail 非零退出;凭证缺失清晰报错;决策核心纯函数 + 单测覆盖 best-of-2 矩阵 + pytest-fail 短路。
- HANDOFF 部署 SOP 含 ship 前必跑门一步。
- 全量回归零失败;controller 实跑门一次确认端到端。

## 9. 预计触及文件

- `scripts/eval_v0160.py`(退出码 + `--json-out` + 抽 `compute_passed` 纯函数)
- `scripts/ship_gate.py`(新)
- `tests/test_ship_gate.py`(新)、`tests/test_eval_exit_code.py`(新或扩现有 eval 测试)
- `HANDOFF.md`(部署 SOP 段)

## 10. 风险 / 依赖

- **eval S-FAIL `executed_ok` 误判**(已 spawn 单独修):best-of-2 暂时吸收其偶发误判;该修复 land 后门更稳。GAP-AH-3 不硬依赖它(best-of-2 可独立工作)。
- KPI 依赖 staging 在线 + 凭证 + LLM 额度;门只能在能连 staging 的机器上跑(controller 本机已验证可达 `.40:8080`)。
- 凭证不入库:门从 env 读,HANDOFF 注明"问用户取";`--json-out`/报告写 /tmp 不入库。
