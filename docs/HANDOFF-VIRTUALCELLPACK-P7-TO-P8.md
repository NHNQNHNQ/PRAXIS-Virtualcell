# VirtualCellPack Phase 7 → Phase 8 交接

- 收口日期：2026-07-28（Asia/Shanghai）
- P7 唯一起始基线：`bcc812eed8a9b1cd162361f8c12fb9e325cdb17c`
- 分支：`codex/p7`
- 状态：`P7_COMPLETE_LOCAL_CANDIDATE — PHASE8_AUTHORIZATION_PENDING`
- 完成提交：由提交后的阶段报告给出；Git commit 不能可靠地自嵌其 SHA。

## 1. 结论

P7 已实现独立于 Pack/model runtime 的物种数据交换层：

```text
vc.data-catalog.v1
→ allowlisted metadata
→ path + size + SHA-256 verified download

operator bearer + exact species/type/limits
→ byte-preserving quarantine
→ vc.upload-receipt.v1
```

React 页面可以筛选 human、mouse、yeast、bacteria，下载服务器已校验文件，并把
用户文件送入隔离区。P7 没有实现 Pack loader、增加模型、修改预测/裁决，也没有
让上传数据自动进入 runtime。

## 2. 严格公开目录

打包清单固定 dataset/species/modality/value semantics/source/terms 和每个文件的
path/size/hash。未知字段、重复 YAML key/ID/path、非 canonical 路径、坏 URL/
CURIE/hash/type 全部使目录 503；不回退到弱清单。

目录响应隐藏本地路径和 token。物种过滤逐字匹配，不做大小写归一或 fallback。
下载只接受清单 dataset/file ID，每次重新检查 containment、普通文件、size 和
SHA-256；缺失为 unavailable，篡改/符号链接逃逸/hash 不可读均 fail-closed。
Starlette Range 下载保持可用，但不跳过完整 hash 门。

## 3. 受控隔离上传

- 上传能力默认关闭；需绝对数据根、至少 32 字符 bearer token 和合法限额；
- 鉴权在读取 multipart body 前执行；
- `Content-Length` 与 chunked body 都在 multipart spool 前受限；
- 文件名、扩展名、物种、非空、单文件上限和总 quota 逐项精确检查；
- `flock` 保护并发 quota，上传/lock 符号链接逃逸被拒绝；
- payload 保持原字节，size/hash 流式计算，receipt 原子写入；
- 相同内容得到不同 upload ID，不静默去重；
- 任何失败不产生成功 receipt。

上传扩展名和 declared MIME 不是内容验证。当前 token 是部署级共享操作员凭证，
不是用户账户或 RBAC。

## 4. 科学状态边界

P7 的 catalog valid、file available、download success 和 upload receipt 均不授予：

- `pack_valid`；
- `model_compatible`；
- executable；
- `scientifically_validated`。

上传没有解包、schema/质量检查、归一化、补零、mapping、同源转换或自动注册。
LLM 没有参与清单、hash、上传批准、状态或裁决。

## 5. `.53` 首批数据

已在授权的新根
`/home/zkyd/data1/mzy/praxis-virtualcell-data/public` 下载：

- human 10x PBMC 1k：1 文件；
- mouse 10x E18 brain 1k：1 文件；
- yeast GEO GSE122392：2 文件；
- bacteria GEO GSE67402：1 文件。

5 个文件总计 `27,823,623` bytes，全部与 Git 清单的 size/SHA-256 精确一致。
Yeast 保留来源的 `submitter_normalized_expression` 语义，没有重新归一化。

没有修改或重启现有 PRAXIS-2 服务。远端
`/home/zkyd/data1/mzy/PRAXIS-virtualcell` 仍为：

```text
HEAD   8e0d06348ebdf22e076037e6d661094ae877c5d1
branch codex/deploy-v1.6.0
status ?? vc_api.log
```

数据落盘不表示 P7 代码已经部署。

## 6. 测试证据

测试先行红阶段：

```text
初始后端目录/下载/上传合同：16 failed
初始前端数据入口与 fail-closed UI：2 failed
hash 读取失败 + upload symlink 逃逸：2 failed
声明 body 预解析上限：1 failed
chunked body 预落盘上限：1 failed
最终 frontend dependency audit：1 high（transitive postcss 8.5.16）
```

阶段末同一 Python 3.13 strict-lock 环境：

```text
pip check：No broken requirements found.
P7 定向：20 passed / 0 failed
ruff 定向：All checks passed!
VirtualCell core：1224 passed / 35 skipped / 9 deselected / 0 failed
legacy：1146 passed / 59 skipped / 105 deselected / 0 failed
frontend typecheck：PASS
frontend lint：PASS
frontend build + bundle budget：PASS
frontend npm audit：0 vulnerabilities
Playwright：58 passed / 1 skipped / 0 failed（59 collected）
```

core 相对 P6 的 `1204 passed` 精确增加 20 个 P7 case；legacy 与 P6 完全一致。
唯一 Playwright skip 仍是需显式授权的真实 LLM 路径。core 的 35 skip 仍是
remote/Docker 外部门，不能冒充通过。MuData 的 2 条上游 DeprecationWarning
保持不变。

## 7. 文件范围

实现/清单：

- `praxis_vc_api/main.py`
- `praxis_vc_api/services/data_portal_service.py`
- `praxis_virtualcell/catalogs/data_catalog.yaml`
- `praxis_vc_react/src/api.ts`
- `praxis_vc_react/src/components/data/DataLibrary.tsx`
- `praxis_vc_react/src/components/layout/AppShell.tsx`
- `praxis_vc_react/src/components/layout/JobSidebar.tsx`
- `praxis_vc_react/src/styles/components.css`
- `praxis_vc_react/playwright.config.ts`
- `praxis_vc_react/package-lock.json`

测试：

- `praxis_virtualcell/tests/test_data_portal.py`
- `praxis_vc_react/e2e/data-library.spec.ts`

文档：

- `README.md`
- `docs/ADR-0005-virtualcellpack-p7-data-portal.md`
- `docs/VIRTUALCELLPACK-CAPABILITY-MATRIX.md`
- `docs/VERSIONING.md`
- `docs/TESTING.md`
- `docs/INDEX.md`
- `docs/runbooks/VIRTUALCELLPACK-DATA-PORTAL.md`
- 本交接文件

Git 未包含任何下载数据、上传 payload、token 或模型权重。

## 8. 已知限制

- 共享 bearer token 无用户身份、撤销列表、租户隔离或细粒度权限。
- 只按安全文件名/扩展名接收；没有病毒扫描、压缩炸弹检测、内部 H5AD/H5MU/
  matrix schema 验证或隐私检查。
- quota 没有数据库、自动过期和管理员 UI；进程崩溃残留须人工审计。
- catalog 可用性检查每次重算完整 hash；当前小基线可接受，超大目录需另立缓存
  身份和失效合同。
- 浏览器页面没有上传进度/续传；应用不提供公开目录管理或删除 API。
- 来源许可、consent 和再分发仍由部署者复核；hash 不证明科学质量或许可。
- P7 没有在 `.53` 部署代码、修改 nginx/systemd、开放端口或启动 VirtualCell。
- 本地 Git 仍有既存 AppleDouble pack-index 警告；未授权修改 `.git`。

## 9. 三端与受保护工作树

P7 开始前只读核对：

- 本地唯一起始基线：`bcc812eed8a9b1cd162361f8c12fb9e325cdb17c`；
- GitHub `HEAD/main`：`8e0d06348ebdf22e076037e6d661094ae877c5d1`；
- `.53` 代码仓库：`8e0d063...`，既存 `?? vc_api.log`。

本阶段没有 push，没有修改 main/tag，没有同步 `.53` 代码，没有改变 PRAXIS-2，
也没有在旧 dirty `/Volumes/T7/PRAXIS-virtualcell` 开发或覆盖用户文件。唯一远端
写入是用户明确授权的新数据根及上述 5 个校验文件。

## 10. Phase 8 授权模板

提交后的阶段报告会把占位符替换为精确 SHA：

```text
授权以 <P7 完成 SHA> 作为 Phase 8 唯一起始基线，开始实施 Phase 8。
```

精确迁移关系：

```text
expected_old_sha=bcc812eed8a9b1cd162361f8c12fb9e325cdb17c
→ new_sha=<P7 完成提交 SHA>
```
