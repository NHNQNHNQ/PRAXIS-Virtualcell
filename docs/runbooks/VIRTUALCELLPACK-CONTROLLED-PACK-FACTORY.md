# Controlled Pack Factory 本地合同运行手册

本 runbook 只用于 P19 本地 contract-only Pack authoring/validation/registration 审计。它不
下载或读取外置真实数据，不转换矩阵，不训练模型，不创建 checkpoint/model card/evidence/
promotion，不启动公共写服务，也不执行 `.53`、push、release 或 deploy。

## 1. 固定身份与允许的状态解释

从仓库根只读检查：

~~~bash
git rev-parse --show-toplevel
git rev-parse --git-dir
git branch --show-current
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
git status --short
~~~

P19 identity：

~~~text
starting SHA          871c5a8a4265f5b8fe5c2c6e35d418644bf1c4be
completion code SHA   42eabe63ea1a444d8b2ad14cecba6c9d6fa351d5
completion tree       b4bd63833adc89bd1e30e9595d2cb6b38a3e005f
source date epoch     1786034362
branch                codex/p19-controlled-pack-factory
status                P19_CONTRACT_COMPLETE_REAL_EXTERNAL_FIXTURE_OPERATOR_SCIENCE_POLICY_NOT_RUN
~~~

允许的结论只有 controlled Pack Factory engineering contract complete。Git 外 real tiny
fixture、专用 write-new output root、真实 operator、science 与 product policy 均未运行。
不得写成新真实 dataset 已接入、模型兼容、可执行、scientifically validated 或 promoted。

## 2. 唯一受控链路

~~~text
P7 quarantine payload + receipt
  → exact candidate Pack/file/source/mapping/metadata identities
  → complete reviewer confirmations
  → full deterministic validation report
  → exact named registration-only decision
  → explicit store + explicit index commit
  → factory-registered, model_compatible=null, executable=false
~~~

`quarantined` 不是 Pack，candidate 不是 validated Pack，`pack_valid=true` 不是
factory registration，factory registration 也不是 model compatibility 或 execution。

## 3. Receipt、source payload 与 taxon 审计

调用 `load_quarantined_upload()` 前确认 upload directory 只有 `payload` 与 `receipt.json`，且
两者都是 regular、non-symlink files。Loader 会 duplicate-key-safe 地解析 strict receipt JSON，
并重新核对 receipt UUID、原始 receipt bytes SHA-256、payload size/hash 和 directory identity；
它不要求原始 receipt bytes 已被 canonical reserialize，不得修改或复制替换原始 bytes。

Candidate 的 `source_asset_id` 必须是 manifest 实际 matrix/multi-omics data asset，且该 asset
的 path/size/hash 和磁盘 bytes 必须等于 receipt payload。一个额外声明但未被 Pack 数据语义
消费的 asset 不能充当 upload binding。

P7 `species` 全部仅作 routing hint。Exact taxon 的唯一 proof 是 candidate manifest taxon 加
reviewer 对 exact taxon claim 的 confirmation。特别地，`species=bacteria` 不能自动转换为
*E. coli* 或任一 taxon；`taxon_review_binding` 通过也不改变该边界。

## 4. Candidate 与 review 构造

Library authoring 入口是：

~~~python
from pathlib import Path

from praxis_virtualcell.pack_factory import (
    PackFactoryStore,
    prepare_pack_candidate,
    load_quarantined_upload,
)

upload = load_quarantined_upload(Path("/absolute/quarantine/<upload-id>"))
prepared = prepare_pack_candidate(
    upload,
    Path("/absolute/operator-authored-pack"),
    source_asset_id="<actual-data-asset-id>",
    mapping_asset_ids={"<ordered-modality-key>": "<mapping-asset-id>"},
    value_semantics={"<ordered-modality-key>": "<declared-semantics>"},
    units={"dose_units": ["<unit>"], "time_units": ["<unit>"]},
    claim_origins={"<every-canonical-topic>": "operator_declared"},
)

store = PackFactoryStore.create(Path("/absolute/new-empty-factory-store"))
~~~

上例只展示参数形状，不授权使用占位路径，也不替代具体 asset/output-root 授权。Store create
要求 absolute、canonical、write-new path；现有路径、symlink parent 或隐式 default 都拒绝。
它以 exclusive/non-following write 创建并 fsync exact `.factory-store.json` marker（bytes
`{"schema_version":"vc.pack-factory-store.v1"}\n`），再 fsync directory。
`PackFactoryStore.open()` 只接受该 marker 逐字节匹配的已初始化 store；普通既存目录即使为空
也拒绝。Supported initialization 只通过 `create()`；marker 是 exact capability marker，不是
防止具备 filesystem write 权限者仿造 bytes 的密码学真实性证明，因此不得手工创建 marker
或把普通用户目录直接传给 CLI。

Review 必须按 canonical order 确认全部 topic，并让每个 confirmation 绑定 candidate claim
fingerprint。即使 claim origin 是 `inferred_candidate`，也不能跳过人确认。Reject review 可以
保留，但不能产生 registration-allowed report。

## 5. Mapping 与 strict validation 审计

Mapping 必须是 Pack 声明的 `application/json` asset，并逐项核对：

- mapping ID/version 和 asset path/size/SHA-256；
- source/target namespace name/version；
- source/target feature IDs 与 ordered fingerprints；
- duplicate、unmapped、out-of-domain 和 order-preserved fields；
- 当前 view 的 exact feature order。

P19 registration 只接受 identity-only、无重复、无遗漏、无 out-of-domain、保持顺序且同
namespace 的 mapping。任何 alias/aggregate/fill/drop/reorder/implicit conversion 都不得通过
P19 factory gate。

使用 `validate_pack_candidate(prepared, review)` 生成 report；不要手工编辑 pass booleans。
完整 report 必须包含固定顺序 checks，尤其 `taxon_review_binding`、source bytes、完整
PackRegistry/canonical view、units、mapping、declared-files-only 和 no-transform checks。
Warnings 非空时不能 register。

## 6. CLI register 迁移

P19 前的 path-only 命令已退役：

~~~bash
# 已退役；现在 fail closed
praxis-vc pack register /absolute/path/to/pack
~~~

新命令只消费已由 library 生成并审阅的完整 artifact chain：

~~~bash
praxis-vc pack register \
  --upload-directory /absolute/quarantine/<upload-id> \
  --pack-root /absolute/operator-authored-pack \
  --candidate /absolute/contracts/candidate.json \
  --review /absolute/contracts/review.json \
  --validation /absolute/contracts/validation.json \
  --decision /absolute/contracts/decision.json \
  --index /absolute/existing-parent/pack-index.json \
  --store /absolute/initialized-factory-store
~~~

`--index` 和 `--store` 都是 required；`--store` 必须先由 `PackFactoryStore.create()` 初始化。
不得依赖 home default、普通既存目录或只设置环境变量完成管理写。
CLI 使用 strict、duplicate-key-safe JSON loader，重新绑定 upload/Pack root 并重算 validation
report。它不是 authoring wizard，也不会生成或批准 review/decision。

## 7. Index v1→v2 与 pending→committed

Reader 同时接受 `vc.pack-index.v1` 和 `vc.pack-index.v2`。Legacy v1 records 保持 readable，
但其 factory registration/store identities 为 `null`，不能声称 P19 approval。任何受控新写
输出 v2，并同时绑定 registration fingerprint 和 canonical absolute store root。

Commit 顺序是：先把预期 registration identity 写入 index，再把 verified registration
artifact append 到 store，最后通过 index consumer 重读。两次 durable write 之间是
`pending`：store registration 不存在或完整依赖链无法重验时，`get_record()`、`registry_for()`
及 Pack consumers 都必须返回 invalid/fail closed。只有 store commit 与 index exact match 后
才是 `committed`。崩溃后只可用同一 exact chain 重试，不能手工把 index 条目当成功或放宽
consumer validation。

## 8. Public projection 审计

配置只读 projection 时，`PRAXIS_VC_PACK_FACTORY_STORE` 必须指向已存在的 exact store；未
配置时返回 `configured=false` 空 catalog，不会自动创建目录。

`GET /api/pack-factory` 只返回 root-free lifecycle projection：不含 root/directory、原始
reviewer/operator ID、rationale 或 reason；operator identity 以 fingerprint 表达。Receipt
filename 等非目录 identity/display 字段仍可出现，因此 redaction claim 只覆盖前述敏感字段。确认
`write_api_enabled=false`，且不存在 `/api/pack-factory` POST/register write route。

UI/API 必须分别显示：

1. Quarantine；
2. Candidate；
3. Factory-registered；
4. Model-compatible（未按 exact request 评估）；
5. Executable（false）。

不得从前三层推导后两层，也不得把 factory operator decision 描述成 model policy promotion。

## 9. 安全与回归 gates

最终 code identity 冻结后运行并回填结果：

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_pack_factory.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  -ra \
  praxis_virtualcell/tests/test_pack_factory.py \
  praxis_virtualcell/tests/test_pack_product.py \
  praxis_virtualcell/tests/test_data_packs.py \
  praxis_virtualcell/tests/test_virtual_experiment.py

python -m ruff check \
  praxis_virtualcell/pack_factory.py \
  praxis_virtualcell/pack_product.py \
  praxis_virtualcell/cli.py \
  praxis_vc_api/main.py \
  praxis_vc_api/services/runtime_service.py \
  praxis_virtualcell/tests/test_pack_factory.py

python -m ruff format --check \
  praxis_virtualcell/pack_factory.py \
  praxis_virtualcell/tests/test_pack_factory.py

python -m py_compile \
  praxis_virtualcell/pack_factory.py \
  praxis_virtualcell/pack_product.py \
  praxis_virtualcell/cli.py

npm --prefix praxis_vc_react run typecheck
npm --prefix praxis_vc_react run lint
npm --prefix praxis_vc_react run build
git diff --check
~~~

结果：focused `23 passed / 1 skipped`；上述 combined focused+adjacent four-file gate
`108 passed / 1 skipped`；safe Python gate `1,554 passed / 49 skipped / 387 deselected`；legacy
gate `1,143 passed / 58 skipped / 105 deselected`。Frontend typecheck/lint/build、Ruff check、
P19 changed-file format、`py_compile` 与 diff check 均 passed。可选 MuData 正向路径因未安装
`mudata` 而 skip；没有联网补装，也不能解释为通过。

两个 exact-code offline clean-archive build byte-identical：wheel `1,154,421` bytes，SHA-256
`1231f948e6f519b9cea66e5ab0e7ccb41b3b7f5a7aa73efdd7dbaf885bfa969f`，`368` entries，React
`14`、tests `0`、AppleDouble `0`；source/wheel `pack_factory.py` SHA-256 均为
`06fb5267c47e8fcf8bcc596e18c9d12e3cb429b0670b662eb0b2ae448b560508`，ZIP integrity passed。
这不声称 dependency-closure/clean-install proof。

## 10. 失败语义与停止条件

下列任一情况必须停止且不得写成 committed registration：

- receipt/payload、candidate tree、manifest/source asset 或任一 fingerprint 漂移；
- review topic 缺失、顺序错误、claim mismatch 或未确认；
- P7 routing species 被当作 exact taxon，尤其把 bacteria 自动推为某一物种；
- mapping duplicate/unmapped/out-of-domain/order/namespace 不满足 identity-only gate；
- warning、failed validation check、invalid Pack 或 non-approved decision；
- relative/default/symlink index、缺失/篡改/symlink `.factory-store.json` marker、普通目录冒充
  initialized store、path traversal、duplicate JSON key 或 unknown field；
- index/store registration provenance 不一致或 pending commit 缺失；
- public projection 泄露 root、reviewer/operator rationale/reason 或原始 operator identity；
- 出现训练、checkpoint、model card、benchmark、evidence 或 promotion 标记。

以下外部门仍为明确 non-runs：

~~~text
real Git-external fixture              NOT_RUN
authorized new write-only output root  NOT_RUN
real operator action                   NOT_RUN
science                                NOT_RUN
product policy                         NO_NEW_DECISION
network / .53 / push / release/deploy  NOT_RUN
~~~

完整边界见 [ADR-0016](../ADR-0016-controlled-pack-factory.md) 和
[P19 completion report](../../reports/phase19/PHASE19_COMPLETION.md)。
