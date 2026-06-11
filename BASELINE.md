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

## 基线 2 — 去脑补脑后(Task 6 填)

(Phase 3 完成后填:命令 / 结果数字 / 因去脑而 skip 或删除的测试逐条 + 原因 / 结论)
