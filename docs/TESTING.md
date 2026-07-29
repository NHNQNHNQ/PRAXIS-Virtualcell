# PRAXIS-VirtualCell 测试指南

> 本地观测：2026-07-29，分支 `codex/p9-ood-validation`，唯一起始基线 `480706fbf58343565532debeca70c4de093b045f`
>
> 状态：`P9_OOD_VALIDATION_LOCAL_IMPLEMENTED — GITHUB_FIVE_JOB_CI_REQUIRES_SEPARATE_AUTHORIZATION`。固定 C5 实现证据、C4 发行证据和 D1a `4/5` CI 仍是历史冻结快照；本地 P9 结果不是新的 GitHub、`.53`、原生 Linux/x86_64 或发布证据。

## 当前质量口径

| 层 | 命令 | 本地结果 |
|---|---|---|
| 依赖 | Python 3.13 hash locks → editable `--no-build-isolation --no-deps` → `python -m pip check` | macOS/arm64 Python 3.13.12 与 Docker Linux/arm64 Python 3.13.14 fresh strict hash install 均 PASS |
| Python lint | Python 3.13 lock 环境内 `ruff check .` | macOS/arm64 与 Docker Linux/arm64 均 PASS，0 diagnostics |
| FBA + packaging 定向回归 | 两条真实 FBA 正例，加 dev extra/lock 与 CI lock 角色测试 | macOS/arm64 `13 passed / 0 failed`；其中 packaging 单模块 `11 passed`，Linux/amd64 QEMU 同一 packaging 单模块 `11 passed / 0 failed` |
| VirtualCell 核心 | `python -m pytest praxis_virtualcell/tests -m "not llm" -o addopts='' -q -ra` | P9 macOS/arm64 Python 3.13.12：`1270 passed / 35 skipped / 9 deselected / 0 failed`；此前 GitHub attempt 2 native Linux core PASS 是旧候选证据 |
| Legacy unit | `python -m pytest tests -m "not (integration or llm or remote)" -o addopts='' -q -ra` | P9 macOS/arm64 Python 3.13.12：`1146 passed / 59 skipped / 105 deselected / 0 failed`；Docker Linux 数字仍是旧候选冻结证据 |
| Legacy broad non-LLM（C5 冻结） | `python -m pytest tests -m "not llm" -o addopts='' -q -ra` | C5 历史证据为 `1136 passed / 158 skipped / 6 deselected / 0 failed`；本轮未将其冒充为新候选 CI isolation |
| C5 Gate A 本地 seam | provenance gate 定向测试 + W4B remote test module 在普通本地 marker gate 下被收集并跳过 | `38 passed / 2 remote skipped / 0 failed`；三 adapter success/no-gate 与缺版本 fail-closed 已证明，非真 donor 推理 |
| C5 W4B remote | `test_ml_workflow_e2e.py --run-remote -m remote` | 本机无 torch：`2 skipped / 0 failed`，明确为 `REMOTE_VALIDATION_PENDING`；只有批准候选 SHA、clean donor SHA/remote 和可信六文件 digest 集上 `2 passed / 0 skipped / 0 failed` 可关闭 |
| 前端 | typecheck → lint → build → 对显式启动的 fresh dev-lock API 执行 `npm run e2e` | P9 本地 PASS；14 specs / 60 collected = `59 passed / 1 skipped / 0 failed`；唯一 skip 是需明确授权的真实 LLM |
| C4 完整 wheel（冻结） | 固定 `8ce42fe` 的两个 clean archive 分别构建、`cmp`、Python 3.13 locked clean install、console entry、站外 verifier | 922,334 bytes；SHA-256 `78e5287a5dd61478b041fd1a28783732cb75a250de02eec306d3803b3128fd4f`；全部 PASS；仅是 C4 历史证据，不能继承为尚未形成的新候选 artifact |
| C4 Linux container | Docker Desktop Linux/arm64，显式 Docker 双门，容器 `--network none` | `5 passed / 0 failed`；结束后无本次资源残留 |
| C2 历史干净 wheel | 从提交 `73f3324` 的 `git archive` 构建；独立 Python 3.13 venv `--no-deps` 安装后验证 import、version、CLI | `praxis_virtualcell-1.5.1-py3-none-any.whl`，714,871 bytes，SHA-256 `b571ee71a42d028774221b068a5d0b5a613bcebb456ba655c1a3b4e1d1690580`；不是当前 `1.6.0` wheel 证据 |

核心结果与根 `tests/` 不能相加成一个“总通过数”。前者是 VirtualCell 发布权威口径；后者是继承的 PRAXIS-2 unit 范围。Phase 10 的 `912/40/9` 是新增产品版本契约测试之前的冻结证据，不应在原报告中回写成新数字。

### P4.3 legacy/MCP 本地收口

P4.3 以 `eaa9a4067518ab80591ffec7f033b248b43ed951` 为唯一起始基线。旧
`test_pool_slow_server_startup_timeout_skipped` 把 1 秒 pool 预算同时施加给 slow
fixture 和正常 FastMCP 冷启动；当前本机正常启动实测约 `3.15–3.34s`，因此两者
都被误判超时。

修复后 `PRAXIS_MCP_SERVERS_JSON` 的每个条目可声明可选
`startup_timeout_s`。未声明时沿用 pool 默认 10 秒；声明值必须是有限正数，否则
启动配置 fail-fast。slow fixture 仍使用 1 秒，good fixture 使用 10 秒，没有
skip 或放宽 slow 断言。

当前实际结果：

```text
MCP 红灯：7 failed / 12 passed
超大整数异常边界红灯：1 failed / 18 passed
MCP 收口：20 passed / 0 failed
锁文件目标顶层版本 mcp 1.28.1 / anyio 4.14.2 定向：37 passed / 0 failed
VirtualCell core：1104 passed / 43 skipped / 9 deselected / 0 failed
legacy：1147 passed / 58 skipped / 105 deselected / 0 failed
ruff check . --no-cache：All checks passed
```

完整 core/legacy 使用当前 Python 3.13 环境；锁版本 MCP 定向使用临时
system-site venv 覆盖顶层 `mcp/anyio`，不冒充完整 fresh hash-lock 安装。

### P5 VirtualCellPack multiomics / feature-alignment 收口

P5 以 `a229699deac1e791252739df71f4e4202cc72bac` 为唯一起始基线，在
`/Volumes/T7/PRAXIS-virtualcell-p0` 的 `codex/p5` 分支实施。测试先行证据分为：

```text
初始缺少 P5 error/API：collection error
首轮完整 P5 红灯：20 failed / 5 passed
canonical ModelFeatureContract + UniProt 边界红灯：5 failed / 0 passed
超大 fill 整数异常边界红灯：1 failed / 0 passed
mapping 必须为 Pack asset 红灯：1 failed / 0 passed
base-only optional omics import 红灯：1 failed / 0 passed
```

最小实现后，在全新 `/private/tmp/praxis-p5-verify` Python 3.13.12 环境中严格
hash-install `build-py313.lock` 与重生成的 `dev-py313.lock`，再以
`--no-build-isolation --no-deps -e .` 安装候选，实际结果：

```text
python -m pip check：
No broken requirements found.

锁版本：
anndata 0.12.19
mudata 0.3.10
scverse-misc 0.1.1

P5 定向：
32 passed / 0 failed

P1–P5 Pack/request/baseline 定向：
187 passed / 0 failed

python -m ruff check . --no-cache：
All checks passed

VirtualCell core：
1144 passed / 35 skipped / 9 deselected / 0 failed

legacy：
1146 passed / 59 skipped / 105 deselected / 0 failed
```

core 相对 P4.3 的总收集量精确增加 32 个 P5 case。完整 dev lock 还使 8 个既有
environment-gated case 从 skip 转为 pass，故不能把 passed 数的全部变化归因于
P5。legacy 总收集量不变；fresh lock 未包含非锁定的 `aiosmtpd`，1 个既有 email
test 从 pass 变为明确 skip。MCP slow/good timeout 测试保持通过。

P5 定向产生 2 条 MuData namespace 注册 API 的上游 DeprecationWarning；没有
`pull_on_update` FutureWarning，生产 loader 与 fixture 均显式使用
`pull_on_update=False`。本阶段没有 opt-in LLM、remote、Docker、前端或 `.53`
执行，不能把普通 skip 写成这些能力通过。

### P6 capability-driven runtime

P6 以 `e97cfa153281fb6c9ad33e39c916e2fed1225df9` 为唯一起始基线，在独立
`/Volumes/T7/PRAXIS-virtualcell-p0` 的 `codex/p6` 分支实施。测试先行证据：

```text
初始缺 CapabilityRegistry API：collection error
首轮契约实现后主链接线：5 failed / 32 passed
request identity/严格类型/重复 output/nested dependency：5 failed
request modality/namespace 与 Pack 关系约束：2 failed
plugin 非 dict 输出：1 failed
runtime task/output adapter 与错误 output shape：2 failed
超大 predictor integer：1 failed
提交前 fail-closed 对抗复审（Windows 路径、probe 异常、资产重验、
嵌套非 JSON plugin 输出）：5 failed / 55 passed
```

当前 P6 定向：

```text
praxis_virtualcell/tests/test_capability_runtime.py：
60 passed / 0 failed

P0 offline baseline + runtime determinism 定向：
29 passed / 0 failed

Model Zoo/Broker/wrapper 兼容定向：
58 passed / 0 failed
```

定向测试证明 strict model card、四因子 fingerprint、三层状态、资产/依赖/
资源/scope/runtime adapter fail-closed、Broker 动态 dummy plugin、无 mock
fallback、显式 legacy adapter 和 P0 报告基线。阶段末使用同一 P5 strict-lock
环境实际结果：

```text
python -m pip check：
No broken requirements found.

ruff check . --no-cache：
All checks passed!

VirtualCell core：
1204 passed / 35 skipped / 9 deselected / 0 failed

legacy：
1146 passed / 59 skipped / 105 deselected / 0 failed
```

core 相对 P5 的 `1144 passed` 精确增加 60 个 P6 case；legacy 结果与 P5 完全
一致。core 仍有 MuData 上游 namespace 注册的 2 条 DeprecationWarning。没有
运行真实 LLM、remote/GPU、Docker、前端或 `.53`；普通 skip 不能冒充这些门通过。

### P7 species data portal / controlled exchange

P7 以 `bcc812eed8a9b1cd162361f8c12fb9e325cdb17c` 为唯一起始基线，在独立
`/Volumes/T7/PRAXIS-virtualcell-p0` 的 `codex/p7` 分支实施。测试先行证据：

```text
初始 backend catalog/download/upload 合同：16 failed
初始 frontend data-library E2E：2 failed
hash 不可读 + upload symlink 逃逸：2 failed
声明 body 预解析上限：1 failed
chunked body 预落盘上限：1 failed
最终 frontend dependency audit：1 high（transitive postcss 8.5.16）
```

最小实现与安全复核后：

```text
python -m pip check：
No broken requirements found.

P7 定向：
20 passed / 0 failed

ruff 定向：
All checks passed!

VirtualCell core：
1224 passed / 35 skipped / 9 deselected / 0 failed

legacy：
1146 passed / 59 skipped / 105 deselected / 0 failed

frontend：
npm audit 0 vulnerabilities
typecheck PASS
lint PASS
build + bundle budget PASS
Playwright 58 passed / 1 skipped / 0 failed（59 collected）
```

core 相对 P6 精确增加 20 个 P7 case；legacy 与 P6 完全一致。Playwright 新增
2 个 P7 case，唯一 skip 仍是需明确授权的真实 LLM 流程。完整 core 的 35 skip
仍是 remote/Docker 外部门；本轮没有运行真实 LLM、GPU、Docker 或远端科学模型。
MuData 的 2 条上游 DeprecationWarning 保持不变。

`.53` 只执行了本阶段明确授权的数据操作：在
`/home/zkyd/data1/mzy/praxis-virtualcell-data/public` 下载并逐文件核验 5 个
清单资产，总计 `27,823,623` bytes。远端代码 HEAD/branch/status 和现有
PRAXIS-2 进程保持不变；这不是部署或远端 runtime 测试。

### P8 Golden Norman/K562 Pack 与简单 baseline

P8 以 `09fb1bb3d02adfceed504cbccd7cf36c54a61b69` 为唯一起始基线，在独立
`/Volumes/T7/PRAXIS-virtualcell-p0` 的 `codex/p8-golden-norman` 分支实施。
测试先行证据：

```text
初始 Golden Norman 模块缺失：collection error
正式 evaluation API 缺失：collection error
真实 source/derived hash mismatch 调试：fail-closed，未产出错误 Pack
篡改 Pack 在 baseline 拟合前未校验：1 failed
冻结 control-assignment hash 未执行：1 failed
metric/baseline 标签可与固定数学不一致：5 failed
```

最小实现后，在全新 `/private/tmp/praxis-p8-verify` Python 3.13 strict-lock
环境中 hash-install `build-py313.lock`、`dev-py313.lock`，再以
`--no-build-isolation --no-deps -e .` 安装候选：

```text
python -m pip check：
No broken requirements found.

锁版本：
anndata 0.12.19
numpy 2.5.1
scipy 1.18.0
mcp 1.28.1

P8 定向：
21 passed / 0 failed

P6 capability + Pack/adapter + P8 合并定向：
172 passed / 0 failed

python -m ruff check . --no-cache：
All checks passed!

VirtualCell core：
1245 passed / 35 skipped / 9 deselected / 0 failed

legacy：
1146 passed / 59 skipped / 105 deselected / 0 failed
```

core 相对 P7 的 `1224 passed` 精确增加 21 个 P8 case；legacy 与 P7 完全一致。
core 的 35 skip 仍是 remote/Docker 外部门，2 条 warning 仍来自 MuData 上游
namespace decorator deprecation。没有运行真实 LLM、GEARS、GPU/checkpoint、
Docker 或 UI/E2E，不能把普通 skip 写成这些能力通过。

真实数据操作另有独立证据：

- Dataverse ZIP 与 H5AD 的 size/hash 全部匹配 frozen contract；
- source 和 derived Pack 的 CSR X/counts dataset hash 精确一致；
- 30 validation + 116 test condition × 3 baseline，共 438 次预测逐个经过正式
  Pack-aware broker/governance/Report；
- `.53` Golden 根 15 个文件逐项重算 size/SHA-256，与 Git
  `artifact-manifest.json` 一致，总计 `4,693,649,813` bytes；
- GEARS `run=false`、`assets_accessed=false`。

这类外置数据/评估成功不等于代码已部署，也不提升
`scientifically_validated=false`。

### P8 产品化收口：三物种 Pack、CLI/API/UI 与历史身份

产品化收口以 Golden 完成提交
`b6cf226382cb841fb50e70875c82d1804ae5681e` 为唯一起始基线，在
`codex/p8-product-closure` 分支实施。测试先行证据：

```text
产品模块尚不存在：
collection error / ModuleNotFoundError

React 尚未展示 Pack capability：
1 failed（找不到 “VirtualCellPack 能力与验证” region）

产品编排误放入 data_packs 基础层：
1 failed / 189 passed
既有架构守卫确认 model-zoo/runtime 反向依赖，模块上移后恢复
```

最小实现后的本地证据：

```text
P8 product 定向：
13 passed / 0 failed

API + Pack manifest/adapter/semantics + P6 capability + P8 product：
191 passed / 0 failed

python -m pip check：
No broken requirements found.

python -m ruff check . --no-cache：
All checks passed!

VirtualCell core：
1258 passed / 35 skipped / 9 deselected / 0 failed

legacy：
1146 passed / 59 skipped / 105 deselected / 0 failed

frontend：
typecheck PASS
lint PASS
build + bundle budget PASS
Playwright 59 passed / 1 skipped / 0 failed（60 collected）
```

core 相对 Golden P8 的 `1245 passed` 精确增加 13 个产品契约 case；legacy
计数不变。唯一 Playwright skip 仍是真实 LLM 显式门。三个约 44 KB 的 H5AD
fixture 连续生成两次得到完全相同 SHA-256；测试用正向 model 是 pytest 内部 dummy，
没有加入生产 model zoo。

从当前源码复制到 `/private/tmp` 的无 AppleDouble 临时源后，wheel content smoke
PASS：三个 manifest/H5AD 全部存在，`praxis_virtualcell/tests` 不在 wheel 中。
该 wheel 来自未提交候选，只证明 package-data 内容，不是可发布或可复现 release
artifact。直接在外置盘构建会被文件系统自动生成的 `._*.dist-info` 污染并由 pip
拒绝；正式 release script 仍须在提交后从 `git archive` 的临时源构建。

普通验收没有访问 `.53`、P7 大数据或 Golden 外置资产，没有运行 GEARS、GPU、
真实 LLM、Docker 或远端服务。35 个 core skip 仍是 remote/Docker 外部门，不能
冒充这些能力通过。

### P9 多轴 OOD、弃权与无适配外部验证

P9 以 `480706fbf58343565532debeca70c4de093b045f` 为唯一起始基线，在
`codex/p9-ood-validation` 分支实施。测试先行证据：

```text
初始 P9 模块缺失：
collection error / ModuleNotFoundError

来源 hash 与 selective 防篡改补强：
2 failed / 10 passed

feature contract / external metadata 防篡改补强：
1 failed / 11 passed
```

最小实现后的本地证据：

```text
P9 定向：
12 passed / 0 failed

python -m pip check：
No broken requirements found.

ruff check . --no-cache：
All checks passed!

VirtualCell core：
1270 passed / 35 skipped / 9 deselected / 0 failed

legacy：
1146 passed / 59 skipped / 105 deselected / 0 failed

frontend：
npm audit 0 vulnerabilities
typecheck PASS
lint PASS
build + bundle budget PASS
Playwright 59 passed / 1 skipped / 0 failed（60 collected）
```

core 相对 P8 product 的 `1258 passed` 精确增加 12 个 P9 合同 case；legacy 与
前端计数不变。首次 Playwright 命令因本轮严格 Python 环境位于 `/private/tmp`
而未找到 checkout `.venv/bin/python`，在测试收集前退出；随后按本指南显式启动
同一 fresh API 环境并复用，60 个 case 得到上述正式结果，没有修改配置或断言。
本机 Node 是 `26.4.0`，不替代 CI 固定的 `24.18.0` 平台证据。

公开输入在 Git 外临时目录重放，生成的
`external-validation.json` 与 checked-in artifact 逐字节一致。主 MSE
candidate `1.0603835779`、no-change `1.0533347059`，paired difference 95% CI
`[-0.9076414928, 0.9749711895]`；因此 `available=false`、
`scientifically_validated=false`。没有运行 GEARS、GPU、真实 LLM、remote
service 或 `.53`。

P9 implementation anchor
`6de2ec1543aada7f4e7b265280a784ce0528c9dc` 的 post-commit 发行证据已完成：

```text
双 clean archive wheel 可复现
wheel SHA-256 97a71283005ec462cd3b91f60efe2bcd95a8d5b2f63b44bd7c7160b5d34149ad
clean-install verifier PASS
Docker exact-HEAD smoke 5 passed / 0 failed
```

P9 release-closure 只修测试入口、AppleDouble bundle 审计和治理文档，不改变
runtime、模型或科学 artifact；其最终 commit、wheel hash 和隔离预览证据仍由
阶段结束报告绑定，因为 Git commit 无法自嵌其最终 SHA。

### P10 CommunityPack 前置接口

P10 以 `b0064fab936f06d09a88eea5292e934410302145` 为唯一起始基线，在独立
APFS 分支 `codex/p10-community-readiness` 实施。测试先行证据：

```text
初始 CommunityPack 模块缺失：
collection error / ModuleNotFoundError

namespace/member-current-bytes/exchange-contract 对抗补测：
4 failed / 27 passed

no-model plan/result 可伪造 execution content 补测：
4 failed / 34 passed
```

最小实现后，在 `/private/tmp/praxis-p10-verify-20260729` Python 3.13.12
严格环境中 hash-install `build-py313.lock` 与 `dev-py313.lock`，再以
`--no-build-isolation --no-deps -e .` 安装当前 checkout：

```text
python -m pip check：
No broken requirements found.

P10 定向：
38 passed / 0 failed

Pack/capability/packaging/P10 合并定向：
192 passed / 0 failed

python -m ruff check . --no-cache：
All checks passed!

VirtualCell core：
1310 passed / 35 skipped / 9 deselected / 0 failed

legacy：
1146 passed / 59 skipped / 105 deselected / 0 failed
```

第一次完整 core 诊断误用了旧 T7 venv；其 distribution metadata 是 `0.0.0`，
因此唯一失败是版本合同要求的 `1.6.0`，其余 `1305 passed`。该运行不作为候选
证据，也没有放宽断言；上面的正式结果来自重新安装当前 checkout 的严格环境。

E. coli 复用 P8 tiny Pack；新增 S. cerevisiae H5AD 为 43,848 bytes，两次生成的
SHA-256 均为
`c675ddee3d96aef9000e48ca7480cd0169eb10d3d4eced0fb08891178c7c46fc`。
P10 不增加真实 community model、权重、API、CLI 或 UI；未运行 frontend、真实
LLM、remote/GPU、Docker 或 `.53` 服务测试。toy exchange 通过只证明精确声明量
守恒，不是实验、通量、热力学或科学有效性证据。

## 本地复现

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: \
  --require-hashes -r requirements/build-py313.lock
.venv/bin/python -m pip install \
  --require-hashes -r requirements/dev-py313.lock
.venv/bin/python -m pip install \
  --no-build-isolation --no-deps -e .
.venv/bin/python -m pip check
.venv/bin/ruff check .

.venv/bin/pytest praxis_virtualcell/tests \
  -m "not llm" -o addopts='' -q -ra

.venv/bin/pytest tests \
  -m "not (integration or llm or remote)" \
  -o addopts='' -q -ra

# 可选的广义 legacy 本地盘点；与上面的 CI isolation 分开记数
.venv/bin/pytest tests \
  -m "not llm" -o addopts='' -q -ra

cd praxis_vc_react
npm ci
npm audit --audit-level=high
npm run typecheck
npm run lint
npm run build
CI=1 npm run e2e
```

CI 配置固定 Python `3.13.14` 和 Node `24.18.0`。完整本地/CI 测试环境使用 `requirements/dev-py313.lock`；frontend Playwright 的 API 也使用该 lock，确保真实 FBA 正例具备 mechanistic/Cobra。`requirements/runtime-py313.lock` 继续服务于精简发行安装和 clean-wheel verifier，不能替代完整测试环境。

依赖/frontend 修复提交 `d6011d8` 已由 GitHub attempt 2 的四个通过 job 验证。唯一 legacy 失败在 native Linux 证明为 BashTool 只 kill 直接 shell、后代继续持有 pipe；提交 `6a81987` 用独立 process group、统一 deadline 和取消清理修复，并在 fresh macOS/Linux 严格锁环境得到 legacy `1139/59/105/0`。没有降格、skip 或放宽原失败断言；最终平台发布结论仍必须由下一候选的 GitHub native x86_64 retry 给出。C4 wheel/clean install 和 Docker 证据仍按固定 commit 冻结；最终文档提交完成后还必须重新绑定 exact candidate 的 release artifact。

## C4 发布复现

完整 wheel 从 committed HEAD 的临时 archive 构建，不复用 checkout 的 `dist/` 或 Python build 目录：

```bash
PYTHON_BIN=python3.13 scripts/build_release_wheel.sh /tmp/release-one
PYTHON_BIN=python3.13 scripts/build_release_wheel.sh /tmp/release-two
cmp /tmp/release-one/praxis_virtualcell-*.whl \
    /tmp/release-two/praxis_virtualcell-*.whl
```

随后在全新 Python 3.13 venv hash-install `requirements/runtime-py313.lock`，以 `--no-deps` 安装 wheel，运行 `pip check`，并从 checkout 外执行安装生成的 `praxis-vc --version` / `praxis-vc run` 与 `scripts/verify_release_install.py`。console entry 和 installed-package verifier 都覆盖 offline run 的四项产物；verifier 还覆盖 API health/job、同源 root/hashed asset、包内 web 入口和测试树排除。不包括完整 Streamlit server 或 `praxis-vc ask`。

Docker smoke 必须同时打开环境变量和 pytest integration 门；缺少任一项时只能得到 skip：

```bash
PRAXIS_RUN_DOCKER_SMOKE=1 .venv/bin/python -m pytest \
  praxis_virtualcell/tests/test_linux_docker_smoke.py \
  --run-integration -o addopts='' -q -ra
```

它从 committed HEAD 构建唯一标记镜像，以 `--network none` 启动，并在容器 loopback 验证 non-root、health/version/SHA、installed CLI、React assets 和 offline API report。本地结果只代表 Docker Desktop 的 Linux/arm64 container，不代表原生 Linux、amd64 或 `.53`。

## Marker 与外部门

pytest 启用 strict markers，并静态注册：

- `integration`：容器、数据库、Redis 或发行环境依赖；需 `--run-integration`。兼容旧流程的 `PRAXIS_INTEGRATION=1` 仍可开启该门。
- `llm`：真实外部 LLM 请求；需 `--run-llm`，测试还会单独检查凭证。
- `remote`：GPU、checkpoint、donor 或私网服务；需 `--run-remote`，测试还会单独检查本地依赖。
- `operational`：活部署健康探针，而非隔离测试依赖。

一个测试拥有多个 marker 时，必须满足全部相关 opt-in。只打开 integration 不会运行同时标记为 `integration + llm + remote` 的真实 LLM 模块。

固定 `.53:7788` 健康不变量标记为 `remote + operational`，普通 legacy 命令不会建立 socket 或 HTTP 连接。只有在授权网络与明确运维窗口中才运行：

```bash
.venv/bin/pytest \
  tests/test_m9_invariants.py::test_inv5_v1_backend_still_healthy \
  --run-remote -m "remote and operational" \
  -o addopts='' -q -ra
```

退出码 0 但全部为 skip 只表示前置条件缺失，不能写成 LLM、integration 或 remote 能力通过。

W4B/Gate A 真 ML 验证必须在用户批准的同一候选 SHA、独立批准的 clean donor Git SHA/remote 和可信六文件 digest 集上，按 [Remote Science Validation](runbooks/REMOTE-SCIENCE-VALIDATION.md) 执行：

```bash
# 非独立入口：必须先在 linked runbook 的同一会话通过 donor 与 digest 信任门。
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_ml_workflow_e2e.py \
  --run-remote -m remote -p no:cacheprovider -o addopts='' -q -ra
```

该门要求先只读发现 donor/code 与 checkpoint 元数据，再由可信负责人批准 donor Git 身份和三组 `.json/.pt` digest；当前 `weights_only=False` PT 在批准前禁止反序列化。批准后仍须满足正确 sidecar class、manifest-matching Norman 数据和可用 torch/donor 环境，且结果为 `2 passed / 0 skipped / 0 failed`。CUDA 只作现场环境盘点；当前实现以 `map_location="cpu"` 加载且未迁移 tensor 到 GPU，所以该门不证明 GPU 推理。普通 `run_query()` 不装载 W4B runtime；测试覆盖的是 `build_runtime_ml(...).run_workflow(...)`。

## 前端覆盖边界

14 个 Playwright spec 共收集 57 个 case，覆盖本地 S1–S9 与 S11–S13：五阶段/返回/重置、abstain、敌对输入、扰动矩阵、高级字段、预设、六个结果 tab 与审计产物、主题/历史、离线重复性、响应式语义可达和稳定性，以及两个 Results lazy-loading 路径。S10 是真实 LLM 外部门的 1 条显式 skip；没有运行，不能写成通过。

视觉/几何边界：C3 已完成人工浅色/深色验收并自动验证实际 `data-theme`。Results 工具栏在 1280×720 使用 `.card-actions` 与 `getBoundingClientRect()` 做一条窄几何回归，因为它保护已复现的标题/按钮挤压 bug；mobile/tablet 只证明语义可达，不声称逐像素等价。

C4 的 build budget 实测 initial JavaScript aggregate 为 226,046 bytes（gzip 70,320），延迟加载的 Results chunk 为 410,889 bytes（gzip 114,914），八个本地 font assets 合计 214,292 bytes。旧 C3 单主包 `635.51 kB` 已由 lazy boundary 取代；预算脚本会在初始 aggregate、任一 JavaScript chunk 或 font 范围超标时使 build 失败。

## GitHub Actions

`.github/workflows/ci.yml` 配置五个 job：

1. Python lint + VirtualCell core
2. frontend build + Playwright
3. reproducible full release wheel
4. Linux release container smoke
5. legacy unit（外部套件 gated）

首次 D1a 已把 `codex/project-consolidation=6086e6995b1c3c01ec31075ce1164a0165cb8d43` 发布到 GitHub。对应 [run 29894971142](https://github.com/NHNQNHNQ/PRAXIS-Virtualcell/actions/runs/29894971142) 的实际结果为：

| GitHub job | 结果 | 失败边界 |
|---|---|---|
| Python lint and VirtualCell core | FAIL | dev lock 的严格 hash 安装阶段失败，未进入 Ruff/pytest |
| Frontend build and Playwright | FAIL | typecheck、lint、build 通过；Playwright `55 passed / 1 skipped / 1 failed` |
| Reproducible full release wheel | PASS | 只绑定旧 SHA `6086e6995b1c3c01ec31075ce1164a0165cb8d43`，不能继承给新候选 |
| Linux release container smoke | FAIL | hash 依赖安装阶段失败，未进入 smoke |
| Legacy unit tests (external suites gated) | FAIL | dev lock 的严格 hash 安装阶段失败，未进入 pytest |

三个 Python/Linux 失败首先暴露 macOS/arm64 编译的 dev lock 漏掉 Linux marker 依赖 `greenlet`，修复后 Linux 迭代又暴露 `watchdog`；hash mode 因此在环境创建阶段 fail-closed。frontend 使用 lean runtime lock 时没有 Cobra，真实 FBA 正例按设计返回 abstain，从而使旧断言失败。提交 `d6011d8` 通过显式 union `greenlet==3.5.3`、`watchdog==6.0.0`、重生成 dev lock、让 frontend CI 使用 dev lock 并增加 packaging 回归修复这两个环境问题，没有弱化科学断言。

首次修复后的 candidate `ee36d7948047f346f55a02d62ccaac84391e3c20` 经精确授权快进发布。对应 [run 29971566980](https://github.com/NHNQNHNQ/PRAXIS-Virtualcell/actions/runs/29971566980) 的实际结果为 Python core、frontend/Playwright、reproducible wheel、Linux release container **PASS**；legacy **FAIL**，汇总 `1 failed / 1135 passed / 59 skipped / 105 deselected`。唯一失败 `test_huge_output_capped_not_ooming` 是 Linux dash 派生的 `cat` 在直接 shell 被 kill 后仍持有 pipe；详见 [D1a retry report](status/PHASE-D1A-CI-RETRY-2026-07-23.md)。本地修复 `6a81987` 还关闭了 pipe 提前关闭绕过 timeout 与上层取消遗留进程组两个同源缺口。

“存在 run”不等于 CI 全绿，也不证明这些 job 是 branch-protection required checks。GitHub `main`/tag、本地 `main` 和 `.53` 未改变。最终文档提交和 post-commit artifact binding 完成后，必须以远端 candidate 的 expected old SHA `ee36d7948047f346f55a02d62ccaac84391e3c20` 申请新的 exact-SHA D1a retry 授权；在新 SHA 的五项 CI 全部完成前不得进入 D1b。
