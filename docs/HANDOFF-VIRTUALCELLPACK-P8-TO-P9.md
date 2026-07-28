# VirtualCellPack Phase 8 → Phase 9 交接

- 收口日期：2026-07-28（Asia/Shanghai）
- Phase 8 唯一起始基线：`09fb1bb3d02adfceed504cbccd7cf36c54a61b69`
- 分支：`codex/p8-golden-norman`
- 状态：`P8_COMPLETE_LOCAL_CANDIDATE — PHASE9_AUTHORIZATION_PENDING`
- 完成提交：由提交后的阶段报告给出；Git commit 不能可靠地自嵌其 SHA。

## 1. 结论

Phase 8 已把公开 Norman/K562 数据做成首个 Golden VirtualCellPack，并冻结：

- source ZIP/H5AD、X/counts、observation/feature/condition/split/guide hash；
- K562 canonical identity 与保留的 source `cell_type=A549` 错误字段；
- 无随机性的 train/validation/test 和三个精确 control guide；
- condition-macro full-5045-feature delta MSE；
- condition 级 PCG64 seed 0、2,000 次 paired percentile bootstrap；
- no-change、condition-equal global mean、alpha=1 additive ridge；
- Pack→broker→predictor→governance→Report 正式路径。

没有 Pack loader 泛化扩展、UI 修改、新科学模型或 GEARS 执行。

## 2. 真实资产与状态

外置根：

```text
/home/zkyd/data1/mzy/praxis-virtualcell-data/golden/norman-2019
```

包含 source、派生 Pack、三种 baseline artifact/一卡 registry 和完整 evaluation。
15 个文件已在 `.53` 逐个重算 SHA-256，与
`data/golden/norman_2019/artifact-manifest.json` 一致；文件总计
`4,693,649,813` bytes。

状态严格保持：

```text
pack_valid=true
model_compatible=true
scientifically_validated=false
```

GEARS `run=false`、`assets_accessed=false`。大数据、`.npy` 和完整 evaluation 未进
Git。

## 3. 冻结结果

| Baseline | validation MSE | test MSE | test 95% condition interval |
|---|---:|---:|---:|
| no-change | 0.0046334813 | 0.0062060923 | [0.0052718065, 0.0071798953] |
| global mean | 0.0036030173 | 0.0045820474 | [0.0038500613, 0.0053562761] |
| additive ridge | 0.0023373717 | 0.0032570634 | [0.0027929521, 0.0037390137] |

test paired loss difference 的 95% interval 都大于零：

- no-change minus global mean：
  `[0.0013631044, 0.0018814661]`；
- no-change minus additive：
  `[0.0022916705, 0.0036761179]`；
- global mean minus additive：
  `[0.0008422753, 0.0018762176]`。

这些是冻结 benchmark 内的 baseline 结果，不是跨数据集外部验证、机制证明、
临床声明或 SOTA 结论。

## 4. 测试先行证据

```text
初始 Golden 模块缺失：collection error
新增正式 evaluation API 前：collection error
篡改 Pack 在 baseline 拟合前未校验：1 failed
冻结 control-assignment hash 未执行：1 failed
metric/baseline 标签可与固定数学不一致：5 failed
Phase 8 定向：21 passed / 0 failed
Phase 8 定向 ruff：All checks passed
P6 capability + Pack/adapter + P8：172 passed / 0 failed
strict-lock pip check：No broken requirements found
strict-lock 全库 ruff：All checks passed
VirtualCell core：1245 passed / 35 skipped / 9 deselected / 0 failed
legacy：1146 passed / 59 skipped / 105 deselected / 0 failed
```

core 相对 P7 精确增加 21 个 P8 case；legacy 与 P7 完全一致。35 个 core skip
仍是 remote/Docker 外部门，不能冒充 remote、LLM、Docker 或 GEARS 通过。

## 5. 文件范围

实现：

- `praxis_virtualcell/benchmarks/golden_norman.py`
- `praxis_virtualcell/model_zoo/wrappers/golden_baseline_wrapper.py`
- `praxis_virtualcell/agents/ensemble.py`

测试：

- `praxis_virtualcell/tests/test_golden_norman.py`

小型合同/manifest：

- `data/golden/norman_2019/contract.yaml`
- `data/golden/norman_2019/pack.manifest.yaml`
- `data/golden/norman_2019/model_cards/*.yaml`
- `data/golden/norman_2019/artifact-manifest.json`

文档：

- `README.md`
- `docs/ADR-0006-virtualcellpack-p8-golden-norman.md`
- `docs/runbooks/VIRTUALCELLPACK-GOLDEN-NORMAN.md`
- `docs/VIRTUALCELLPACK-CAPABILITY-MATRIX.md`
- `docs/VERSIONING.md`
- `docs/TESTING.md`
- `docs/INDEX.md`
- 本交接文件

## 6. 已知限制

- 只覆盖 Norman/K562 CRISPRa 和 source 已预处理 X。
- 不是 counts/raw metric，也不能与其他 feature/split 指标直接比较。
- baseline 是 point estimate，没有 calibrated uncertainty。
- additive ridge 只表达 target 可加效应；35 个 train 未见 target 被显式标记。
- source A549 字段保留为来源事实，K562 canonical identity 另列。
- control 分配是固定审计规则，不是随机代表性估计。
- 没有 GEARS、checkpoint、GPU 或远端科学模型结果。
- 没有修改 UI、默认 model zoo、`.53` 代码仓库或 PRAXIS-2。
- 本地 Git 仍有既存 AppleDouble pack-index 警告；未修改 `.git`。

## 7. 三端与受保护工作树

Phase 8 开始前只读核对：

- 本地：`codex/p7`，HEAD
  `09fb1bb3d02adfceed504cbccd7cf36c54a61b69`，clean；
- GitHub `main`：
  `8e0d06348ebdf22e076037e6d661094ae877c5d1`；
- `.53` 代码仓库：`codex/deploy-v1.6.0`，
  `8e0d06348ebdf22e076037e6d661094ae877c5d1`，既存 `?? vc_api.log`。

本阶段没有 push、main/tag 修改、`.53` 代码同步、PRAXIS-2 修改或服务重启。
旧 dirty `/Volumes/T7/PRAXIS-virtualcell` 未用于开发；一次工具相对路径误建的
全新未跟踪 manifest 副本在发现后立即按精确文件列表删除，未覆盖用户文件，旧
工作树该路径恢复原状态。

## 8. Phase 9 授权模板

提交后的阶段报告会把占位符替换为精确 SHA：

```text
授权以 <P8 完成 SHA> 作为 Phase 9 唯一起始基线，开始实施 Phase 9。
```

精确迁移关系：

```text
expected_old_sha=09fb1bb3d02adfceed504cbccd7cf36c54a61b69
→ new_sha=<P8 完成提交 SHA>
```
