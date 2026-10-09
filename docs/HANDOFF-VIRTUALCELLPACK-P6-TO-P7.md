# VirtualCellPack Phase 6 → Phase 7 交接

- 收口日期：2026-07-27（Asia/Shanghai）
- P6 唯一起始基线：`e97cfa153281fb6c9ad33e39c916e2fed1225df9`
- 分支：`codex/p6`
- 状态：`P6_COMPLETE_LOCAL_CANDIDATE — PHASE7_AUTHORIZATION_PENDING`
- 完成提交：由提交后的阶段报告给出；Git commit 不能可靠地自嵌其 SHA。

## 1. 结论

P6 已把严格 Model Zoo、CapabilityRegistry 和 ModelBroker 接入 Pack-aware 主
runtime：

```text
Request × Registered Pack × Model Card × Environment
→ vc.compatibility-report.v1
→ vc.execution-plan.v1
→ prepared ModelWrapper steps
```

无 Pack 调用仍走显式 `LegacyModelApplicabilityAdapter`。P6 没有新增模型、模型
权重、数据集、UI 或 LLM 裁决，也没有提前实施 Phase 7。

## 2. 新合同

`vc.model-card.v1` 以 strict/frozen Pydantic 合同声明：

- taxon、modality、assay、cell/tissue domain；
- perturbation、task、output；
- feature namespace/version/ID format、representation；
- assets/path/SHA-256/media type；
- Python dependencies、resources、wrapper/model revision；
- uncertainty methods 和 canonical complete OOD dimensions；
- self-trained training card 与 provenance。

未知字段、重复数组、非 canonical lower-snake model name、路径逃逸、坏 hash/
CURIE、bool 类型强制转换和不完整 training card 都 fail-closed。严格 card 的
registry 导出返回副本，外部修改不能改变 registry truth。生产 registry 的五个
既有条目已升级为该合同；模型状态没有被提升，也没有增加第六个模型。

## 3. 四因子兼容与三层状态

每份 CompatibilityReport 绑定完整 request、Pack、model card 和 environment
fingerprint。相同 `request_id` 但 request 内容不同会得到不同 plan ID。

状态保持独立：

- `pack_valid` 只来自完整注册的 `RegisteredPack`；
- `model_compatible` 只来自 Request×Pack×Model 的精确 scope/关系检查；
- `scientifically_validated` 在 P6 固定为 `false`。

资产、依赖、资源、wrapper 和 runtime task/output adapter 属于 execution
readiness，不能提升上述科学状态。请求所指 modality/namespace 必须实际存在于
Pack，不能靠 Model 与 Pack 的其他维度交集误通过。重复 requested outputs 明确
拒绝，不静默去重。

## 4. Broker、plugin 与 legacy 分流

`build_runtime()` 只注册一个 `ModelBrokerAgent`。完整
`pack_id + pack_version` 走 Broker：

1. 生成所有严格 card 的稳定排序 compatibility reports；
2. 只把 `executable=true` 的 card 放入 plan；
3. hash-bound step 才可实例化 wrapper，且实例化前重验资产 hash；
4. import/constructor 失败会修订 report/plan 并删除 step；
5. runtime 只执行 Broker 返回的 prepared agents。

测试 dummy predictor 只新增临时 model card 和 wrapper；没有改
`build_runtime`、`route_table` 或 `case_dispatch` 的模型专用分支。缺资产、坏
hash、缺 dependency/resource、越 scope、Pack 未注册或坏 plugin 输出都会
abstain，且 Pack-aware 路径不 fallback 到 Mock。

无 Pack 时走 `LegacyModelApplicabilityAdapter`，其内部
`_LEGACY_CANDIDATES`、`REAL_ENGINES`、`case_dispatch` 仅是冻结兼容路径。只给
Pack ID/version 之一会在任何模型运行前拒绝。P0 structured report 和 9-section
Markdown hash 未变。

## 5. 当前 execution adapter

Environment 明示当前主 coordinator 只支持：

```text
task = predict_delta_expression
output = delta_expression
```

其他 model card 可被发现和审计，但会以
`environment.runtime_task:*`/`environment.runtime_output:*` 拒绝。动态 plugin
必须返回递归合法 JSON 和非空有限 `prediction.delta`；bool、NaN/Inf、超大
不可表示整数、错误 output shape、未知 uncertainty method 或 OOD detection
都不能进入 ensemble。

## 6. 测试证据

测试先行红阶段：

```text
初始缺 CapabilityRegistry API：collection error
首轮主链接线：5 failed / 32 passed
request identity/strict type/重复 output/nested dependency：5 failed
request modality/namespace 与 Pack 关系约束：2 failed
plugin 非 dict 输出：1 failed
runtime task/output adapter 与错误 output shape：2 failed
超大 predictor integer：1 failed
tampered execution-step asset path：1 failed
提交前 fail-closed 对抗复审（Windows 路径、probe 异常、资产重验、
嵌套非 JSON plugin 输出）：5 failed / 55 passed
```

阶段末同一 Python 3.13 strict-lock 环境：

```text
pip check：No broken requirements found.
P6 定向：60 passed / 0 failed
P0 baseline/runtime determinism 定向：29 passed / 0 failed
Model Zoo/Broker/wrapper 兼容定向：58 passed / 0 failed
ruff check . --no-cache：All checks passed!
VirtualCell core：1204 passed / 35 skipped / 9 deselected / 0 failed
legacy：1146 passed / 59 skipped / 105 deselected / 0 failed
```

core 相对 P5 精确增加 60 个 P6 case；legacy 不变。未运行真实 LLM、remote/
GPU、Docker、前端或 `.53`，不能把 skip 写成这些能力通过。

## 7. 文件范围

实现：

- `praxis_virtualcell/model_zoo/capability_registry.py`
- `praxis_virtualcell/model_zoo/registry.py`
- `praxis_virtualcell/model_zoo/registry.yaml`
- `praxis_virtualcell/model_zoo/wrappers/base.py`
- `praxis_virtualcell/model_zoo/__init__.py`
- `praxis_virtualcell/agents/model_broker_agent.py`
- `praxis_virtualcell/agents/model_applicability.py`
- `praxis_virtualcell/core/runtime.py`
- `praxis_virtualcell/workflows/predict_delta_expression.py`
- `praxis_virtualcell/predictors/base.py`
- `praxis_virtualcell/data_packs/registry.py`
- `praxis_virtualcell/data_packs/__init__.py`

测试：

- `praxis_virtualcell/tests/test_capability_runtime.py`

文档：

- `README.md`
- `docs/ADR-0004-virtualcellpack-p6-capability-runtime.md`
- `docs/VIRTUALCELLPACK-CAPABILITY-MATRIX.md`
- `docs/VERSIONING.md`
- `docs/TESTING.md`
- `docs/P0-BASELINE.md`
- `docs/INDEX.md`
- `docs/runbooks/VIRTUALCELLPACK-CAPABILITY-RUNTIME.md`
- 本交接文件

## 8. 已知限制

- Pack-aware 主 workflow 仍从 legacy `VirtualCellRequest` 显式投影到 v2；不能
  直接运行不可投影的任意 v2 taxon/domain。
- Pack schema 尚无独立 assay 字段；当前只做已有 ontology 声明的精确比较，
  不做 ontology 推理。
- 当前只有 delta-expression execution adapter；growth、absolute expression
  等 card 不会经 P6 coordinator 执行。
- base `from_capability` 面向零参数 plugin；需要特殊 constructor 的 wrapper
  必须自行覆写该 classmethod，并仍通过 Broker identity checks。
- PackRegistry 是进程内验证快照，不做签名、跨进程事务或持续文件监控。
- Environment 是本地依赖/资源/adapter 声明，不是远端硬件 attestation。
- 模型卡、plan、成功执行和历史 provenance 都不等于新 benchmark 或科学验证。
- MuData 0.3.10 仍产生 2 条上游 DeprecationWarning。
- 本地 Git 仍有既存 AppleDouble pack-index 警告；未授权修改 `.git`。

## 9. 三端边界

P6 开始时的只读核对：

- P6 本地基线：`e97cfa153281fb6c9ad33e39c916e2fed1225df9`；
- GitHub `HEAD/main`：`8e0d06348ebdf22e076037e6d661094ae877c5d1`；
- `.53` `codex/deploy-v1.6.0`：`8e0d063...`，既存 `?? vc_api.log`；
- 旧 dirty T7 工作树：`24475f2eb14c27c7cfbb82b016b881e88e98b17c`。

本阶段没有 push，没有修改 main/tag，没有同步或写入 `.53`，没有修改旧 dirty
T7 用户文件。

## 10. Phase 7 授权模板

提交后的阶段报告会把占位符替换为精确 SHA：

```text
授权以 <P6 完成 SHA> 作为 Phase 7 唯一起始基线，开始实施 Phase 7。
```

精确迁移关系：

```text
expected_old_sha=e97cfa153281fb6c9ad33e39c916e2fed1225df9
→ new_sha=<P6 完成提交 SHA>
```
