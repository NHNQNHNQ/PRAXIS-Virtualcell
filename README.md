# PRAXIS-VirtualCell

可信虚拟细胞扰动预测的可靠性治理系统：离线优先、可审计、可弃权。它的重点不是笼统宣称“更准”，而是在适用范围不足时明确拒绝、降级或弃权，并为结果保留证据与溯源。

用户描述物种、细胞场景和扰动任务后，系统把请求路由到适用的预测器或规则模块，产出包含治理裁决、证据边界和复现信息的 Markdown 报告。默认 `offline`，不需要 API key。

当前阶段事实：Phase 11B Cell-first 产品入口和 DOCS-CLOSURE 已完成；Phase 12
Virtual Cell Model Zoo v2 工程于
`1a5464fb0d2d9e105058f6797d92efd69783e5b2` 完成。Phase 13 Model Adapter SDK
从 `f83c13db386cb552b3ce7a5643e5ffbead0ff573` 开始，在
`744d0a28d2cfc13d1b10e85b133b6c13b9426174`（tree
`198e623120688d3704b9312990ddaa93c9a7b0e6`）完成本地工程，状态为
`P13_ENGINEERING_COMPLETE_P14E_ELIGIBLE`，现作为历史工程证据保留。Phase 14E 从
`0b193310009d6e4d2ebc0fc8abf95da20a56acdb` 开始，在
`8778e93c31c2dfe1ef0f77f06e7a80a425633736`（tree
`fa85e049bb36f3fbd8e6d4a7503e4b5837ed7c78`）完成本地 E. coli K-12
knockout→growth 工程合同，收口状态为
`P14E_ENGINEERING_COMPLETE_P15E_ELIGIBLE`，现作为历史工程证据保留。Phase 15E 从
P14E docs-closure `0ff6870a70a04d71098a16875e633f909e31cc5a` 开始，在
`62480a3951173a2aa7b006403af9b169521db138`（tree
`64906691c4c989a843df4da97f0a93f32cd65ad2`）完成本地 S. cerevisiae S288C
gene-deletion→fitness 工程合同，收口状态为
`P15E_ENGINEERING_COMPLETE_P16E_ELIGIBLE`，现作为历史工程证据保留。Phase 16E 从
P15E docs-closure `d1e2e37b69784bd2f440cba34f51cfb56dcc00b2` 开始，在
`9f6b14ea84cb0884b2bde2ed4c67c73aeb5a37e2`（tree
`098cd563e3d865e080a0d121727b987e2d40ed18`）完成本地 Human/K562 Golden Norman
perturbation→delta-expression 工程合同，当前收口状态为
`P16E_ENGINEERING_COMPLETE`。Phase 17 从 P16E docs-closure
`ff525a0611901df422161a7143ebfe9d1e051008` 开始，在
`16636f1b2c36e0a0fabb782a662b5b3b934891e0`（tree
`321a59eed44c45bf2bb8798714352b3303b92e58`）完成 deterministic Virtual Cell Brain
合同，状态为 `P17_CONTRACT_COMPLETE_REAL_MULTI_MODEL_ACCEPTANCE_PENDING_P18_ELIGIBLE`。
Phase 18 从 P17 docs-closure `f253664239e4b1c9665301cf1bdf4e117a3e9c31`
开始，在 `626c71ffd1ce18a5adc200f6a6e376e57b269beb`（tree
`2b570398caff6cf955d789c3cb4a7a77dc13a082`）完成 strict joint multi-omics
model-input 合同，状态为 `P18_CONTRACT_COMPLETE_REAL_MULTIOMICS_MODEL_ACCEPTANCE_PENDING`。
Phase 19 从 P18 docs-closure
`871c5a8a4265f5b8fe5c2c6e35d418644bf1c4be` 开始，在
`42eabe63ea1a444d8b2ad14cecba6c9d6fa351d5`（tree
`b4bd63833adc89bd1e30e9595d2cb6b38a3e005f`）完成 Controlled Pack Factory 工程合同，
状态为 `P19_CONTRACT_COMPLETE_REAL_EXTERNAL_FIXTURE_OPERATOR_SCIENCE_POLICY_NOT_RUN`。
Phase 20 从 P19 docs-closure `f53e29e5722a8fe48aa2eb6fe63be01f61b5cc9a`
开始，在分支 `codex/p20-training-pipeline` 的
`a4003704b70f06eb65297ddd32e0695ae8ee146b`（tree
`d12d64a7c8d013d8d299272eea88a4ce0431ccab`，source date epoch `1786040663`）
完成 RegisteredPack-bound Virtual Cell Training Pipeline 工程合同，状态为
`COMPLETE — CONTRACT_ONLY`；science `NOT_RUN`，policy `NO_NEW_DECISION`。Phase 21A 从
P20 docs-closure `5f3fc2d88c20e8083fb66a4c3399c5fe148241be` 开始，在分支
`codex/p21-benchmark-system` 的 `20ecc12542e5df40c90d1fc367dbe86b563478b8`
（tree `ffcd261dd7d506d0ad852023afcba0f5c97a2d72`，source date epoch
`1786050825`）完成 Virtual Cell Benchmark System，状态为
`COMPLETE — SYSTEM_ONLY`；science `NOT_RUN`，policy `NO_NEW_DECISION`。Phase 22 从
P21A docs-closure `09792e13e29a76b5e4434507f3334eefb947789c` 开始，以 P21A code
`20ecc12542e5df40c90d1fc367dbe86b563478b8` 为 prerequisite，在分支
`codex/p22-virtual-cell-registry` 的 `bca5ad661856e8d9aa832c47f23c6ad7179ee0c9`
（tree `f78476ac1dbe2f865e3c1bcdc71ecc512dbad22a`，source date epoch
`1786056220`）完成 Curated Virtual Cell Registry 工程合同，状态为
`COMPLETE — CONTRACT_ONLY`；science `NOT_RUN`，policy `NO_NEW_DECISION`，真实
import/catalog/revoke/supersede lifecycle 为 `NOT_RUN`。Phase 23A 从 P22 docs-closure
`2b5c28ac152857dfa1109de41ed5d5ddc7ab06a4` 开始，在分支
`codex/p23-cell-interaction` 的 `2b894966cd00b2af2fafbf8f009566dd69f393a7`
（tree `00bd98b0fd14091f4528115dcc66730264d5803a`，source date epoch
`1786061504`）完成 sender→receiver Cell Interaction Evidence 本地工程合同，状态为
`COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE`；science `NOT_RUN`，policy
`NO_NEW_DECISION`。输出只允许 `interaction_evidence_score`，不得输出 receiver response、
effect size 或 causal claim。P21B/P21C 与可选 P23B 均为
`AUTHORIZATION_REQUIRED / NOT_RUN`；P24 是下一顺序阶段，但其 First Real Community
Adapter 必须有另行授权的 exact real assets、固定模型和 write-new execution window，当前为
`AUTHORIZATION_REQUIRED / NOT_RUN`，不存在可替代它的 fake contract-only scaffold。没有
改变该事实的前提下，持续本地授权将 P25 拆为 E/R/policy 窗口：P25E 从现场 active baseline
`ae5e93571783cb3cf49a6e0fab531a89e963f7ec` 开始，在分支
`codex/p25e-virtual-microbiome` 的 `039393e6be897b3014bb0b657d0a439d879578b6`
（tree `b53e542940bf39fd44965fe55416798211ab580b`，source date epoch
`1786171049`）完成 fixed 2–3-member Virtual Microbiome contract、唯一 primary endpoint 与
value-free abstention，状态为 `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`；fixture
evidence 仅为 `SYNTHETIC_CONFORMANCE_ONLY`，science `NOT_RUN`，policy `NO_NEW_DECISION`。
P24/P25R 均未运行，P25E 没有 adapter/model/mapping/
benchmark/evidence/prediction。没有 product/API/runtime version bump、release 或 push。
P26E 从现场 active baseline `6bd02231449b6969e22aeb5bea6798fd334daef6` 开始，在同一分支
`codex/p25e-virtual-microbiome` 的 `5bd3e502a7a1f1cb0fd1b79ecfd109eeeaf265c4`
（tree `b3d7303cafb5b874c8b5a441b53e32ff77ef2c54`，source date epoch
`1786176771`）完成 host–microbiome contract、typed missing interface、time-unrolled DAG、
P22 context-only host audit 与 value-free abstention。状态为
`COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`；fixture evidence 仅为
`SYNTHETIC_CONFORMANCE_ONLY`，science `NOT_RUN`，policy `NO_NEW_DECISION`。P26R 因 exact
validated+promoted host/community releases、完整 request binding、matching release 和跨域 mapping
均缺失而 `BLOCKED_EXTERNAL / NOT_RUN`；P22 context match、P25E contract 或 K562 都不能补足该门。
P27A-E 从 P26E docs-closure `a12cf4f4b71efb653f8128afcb1f468211fdb837` 开始，在同一分支的
`5875571bf9d8b518dc7a857feb935206f756de59`（tree
`a7c65e7b30f51832660e66323b5946acbddcbf18`，source date epoch `1786180822`）完成 strict
experiment-design contracts 与 synthetic rank-then-reveal harness。状态为
`COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE_ONLY`；product action space 为空并 value-free
abstain，P27A-R 为 `REPLAY_NOT_RUN / ASSET_PENDING`，science `NOT_RUN`，policy
`NO_NEW_DECISION`，P27B/P27C 分别为 `AUTHORIZATION_REQUIRED / SHADOW_NOT_RUN` 与
`AUTHORIZATION_REQUIRED / PILOT_NOT_RUN`。没有接入 legacy ActiveLearningAgent/runtime 或 LLM
candidate；question/hypothesis prose 不具有 numeric/action-space/verdict authority。
P28E 从 P27A-E docs-closure `971f812faae09fa833dc66741e86ec9ffe97947c` 开始，在同一分支的
`da4bfc042d96f830e2a7e8cdc62ba227c7ace949`（tree
`e6f18371f5061c810b2cb87d9a278cfa6d6ac46b`，source date epoch `1786184568`）完成 strict
advisory role policy、typed value-free handoff/DAG、hash-bound no-run trace 与 authoritative
0/3 abstention。状态为 `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`；fixture evidence
仅为 `SYNTHETIC_CONFORMANCE_ONLY`，science `NOT_RUN`，policy `NO_NEW_DECISION`。真实 P28
仍为 `BLOCKED / 0_OF_3_QUALIFYING_MODULES`，comparison/ablation `NOT_RUN`；legacy
MessageBus/AgentMessage、runtime/API/LLM/registry positive path 均未接线。
P29E 从 P28E docs-closure `90990c198c40d0e6655aedaad101a783cde003aa` 开始，在同一分支的
`471767e5f38f9866fbe396f39836369d943f6657`（tree
`d1dec19f06ec88f563406b45f2b544effabad915`，source date epoch `1786187523`）完成 strict
state/action/observation/time requirement、authoritative empty typed subgraph 与 value-free
compilation。状态为 `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`；fixture evidence
仅为 `SYNTHETIC_CONFORMANCE_ONLY`，science `NOT_RUN`，policy `NO_NEW_DECISION`。图状态精确为
`empty_not_connected`，biological nodes/edges 均为 `0`，所有 data/weight/model/environment/
adapter/compute/benchmark/evidence/policy/result/tool/prediction identities 均为 `null`。真实 P29
仍为 `BLOCKED / 0_QUALIFYING_BIOLOGICAL_NODES`；content hash 是 identity，不是 signer 或
attestation。P30A-E1 已完成本地 release-contract hardening 与 reproducibility probes；下一
eligible local work unit 是 P30A-E2 trusted finalizer/orchestrator。formal P30A 仍为
`LOCAL_RC_INCOMPLETE`，且不授权 push、tag、发布或部署。
exact 验证与克制的科学/policy 边界见
[P12 完成报告](reports/phase12/PHASE12_COMPLETION.md)、
[P13 完成报告](reports/phase13/PHASE13_COMPLETION.md)和
[P14E 完成报告](reports/phase14e/PHASE14E_COMPLETION.md)及
[P15E 完成报告](reports/phase15e/PHASE15E_COMPLETION.md)和
[P16E 完成报告](reports/phase16e/PHASE16E_COMPLETION.md)及
[P17 完成报告](reports/phase17/PHASE17_COMPLETION.md)和
[P18 完成报告](reports/phase18/PHASE18_COMPLETION.md)及
[P19 完成报告](reports/phase19/PHASE19_COMPLETION.md)和
[P20 完成报告](reports/phase20/PHASE20_COMPLETION.md)以及
[P21A 完成报告](reports/phase21a/PHASE21A_COMPLETION.md)与
[P22 完成报告](reports/phase22/PHASE22_COMPLETION.md)和
[P23A 完成报告](reports/phase23a/PHASE23A_COMPLETION.md)以及
[P25E 完成报告](reports/phase25e/PHASE25E_COMPLETION.md)与
[P26E 完成报告](reports/phase26e/PHASE26E_COMPLETION.md)以及
[P27A-E 完成报告](reports/phase27ae/PHASE27AE_COMPLETION.md)以及
[P28E 完成报告](reports/phase28e/PHASE28E_COMPLETION.md)以及
[P29E 完成报告](reports/phase29e/PHASE29E_COMPLETION.md)。P14R、P15R 与 P16R 的真实
asset/science run 均为 `AUTHORIZATION_REQUIRED / NOT_RUN`，P14B、P15B 与 P16B 均为
`NOT_RUN`。当前 P12 `ModelRegistryV2` 有 5 个 legacy release、0 个 native、0 个 production-promoted
capability；P18 没有真实 multi-omics model execution/acceptance，science 为 `NOT_RUN`，
policy 为 `NO_NEW_DECISION`。P19 的 Git 外 real fixture/output root、真实 operator、
science 与 policy 也未运行；factory registration 不等于模型兼容、执行或 promotion。
P20 的成功 literal 仅为 `candidate_cataloged_contract_only`：它不是真实 candidate
training、benchmark、evidence、registry 或 promotion。在 Pack-root asset-byte 边界内，current
manifest 与 split metadata 在 audit 前读取，train-consumed feature/label bytes 只在 audit
通过后打开；stored P19 tree 仅作历史 provenance，test/external、未消费或上传的 code-like
asset 从未打开。Exact P19 store-chain replay 与受信 repository source verification 仍独立执行。

P21A 只实现严格的 benchmark protocol/run/result/evidence 合同、重算门和
content-addressed 负证据 ledger。未经独立信任边界提供的 P21B composite
execution fingerprint（exact authorization + run + result）时，bundle 默认导出负状态；
合同和 content hash 不认证签发者。Ledger 只允许负证据，durable head 能检出
tail truncation，但没有外部/签名 anchor 时不能检出连同 head 一起回滚或删除。
合成 positive gate 仅是临时 conformance 测试，不是真实 benchmark、science、policy、
promotion 或 release 证据。设计和运维边界见
[P21A ADR](docs/ADR-0018-virtual-cell-benchmark-system.md)与
[P21A runbook](docs/runbooks/VIRTUALCELL-BENCHMARK-SYSTEM.md)。

P22 v1 严格组合一个 `FactoryRegisteredPackV1`、一个 P12 release/evidence/policy
closure、一个 P21B evidence bundle 和所有被 exact wrapper approval 约束的 adapter；它
不会创建或提升 scientific evidence/operator policy。Multi-Pack 和 direct P14/P15/P16
或其他 non-P21B evidence route 必须使用未来新 schema，不能静默扩宽 v1。Curated
registry import 一律从 quarantined 开始，后续只能通过显式 approve/quarantine/revoke/
supersede decision 改变 catalog metadata；science/policy state、asset 安装和执行均不变。

外置 trust 默认为 deny-all，并按 exact import/decision fingerprint allowlist 授权；稳定
authorization reference 不把可变 trust 全量哈希进记录。外置 checkpoint 是精确
`entry_count + last_entry_fingerprint`，必须独立保存在 registry root 之外；打开时先锚定
prefix，再用当前 trust 重验全部 suffix。`checkpoint()` 只返回新锚点，不替 operator
持久化；revoke/supersede 后在新 checkpoint 外置推进前，回滚到旧 checkpoint 仍可能。
content hash 和 authorization reference 都不是签名或签发者认证。

默认仓库不创建 curated root，也没有真实 curated release。公开面仅是 Python
`public_catalog()`/query 的路径与敏感字段脱敏投影，`executable=false`，installed 和
compatibility 均为 unknown；没有 HTTP/API、UI、Data Center、chat、runtime planning、
asset installation 或 execution 接线。设计和运维边界见
[P22 ADR](docs/ADR-0019-curated-virtual-cell-registry.md)与
[P22 runbook](docs/runbooks/VIRTUALCELL-CURATED-REGISTRY.md)。

P23A 复用 P13 prepared-input/output/provenance 形状，并用独立 strict schema 绑定两个
P22 release/Pack/context、typed P18 endpoint identity、同实验 donor/sample/well/
condition/dose/time、ligand/receptor/evidence namespace 与 mapping，以及声明但未验证的
P20/P21 scorer identity。它没有资产 loader、生物 scoring formula、模型 runtime、registry
mutation、默认 adapter registration 或 legacy co-culture 接线。`synthetic_conformance` projection 只是把调用方
提供的 unit-interval contract fixture 规范化为唯一公开投影
`{"interaction_evidence_score": [x]}`；元数据明确记录 real data/model execution、paired
linkage、baseline comparison、paired CI 与 registry state 均未验证或未运行。缺失 paired
evidence、baseline gate 失败、unsupported/OOD、execution 未授权或 registry state 未验证时
只能 abstain，且不能投影。设计和运维边界见
[P23A ADR](docs/ADR-0020-cell-interaction-evidence-contract.md)与
[P23A runbook](docs/runbooks/CELL-INTERACTION-EVIDENCE.md)。真实 paired/co-culture/spatial
输入、真实 curated release state、固定模型执行、baseline/CI/OOD science gate 仍须另行 exact
授权；合成 conformance 不是 interaction evidence、scientific validation 或 promotion。

P25E 以独立 `vc.virtual-microbiome-*.v1` schemas 冻结 ordered member Pack/taxonomy/
assembly/strain identity、initial abundance、medium/compartment、time 和 well-mixed scope，唯一
primary output 是 exact end time 的 ordered strain abundance fraction vector。Adapter requirement
明确把 P24 adapter、model、environment、metabolite mapping、P21 benchmark protocol、evidence
和 policy identities 固定为 missing；因此 exact request 仍是 empty plan、`prediction=null`。
P10 `vc.community-*.v1` source bytes 与 canonical no-model fingerprints 由 golden regression
保护，toy exchange balance 不能成为 P25 science。设计和操作边界见
[P25E ADR](docs/ADR-0021-virtual-microbiome-contract.md)与
[P25E runbook](docs/runbooks/VIRTUAL-MICROBIOME-CONTRACT.md)。

P26E 新增五个 strict public record schemas 和一个 canonical joint-scope fingerprint payload，
把 exact host request、P25E community contract、typed missing interface 与固定
`community_state_t0→mediator_state_t1→host_state_t2→community_state_t3` 拓扑绑定起来。
P22 v1 只能审计较粗的 host context，不能验证完整 P26 request；community/matching release、
mapping 和 output/input contracts 全部保持 `null`。因此 compilation 固定 empty steps、
`prediction=null`、无 host/community/mediator result，并按序记录缺少 host release、community
release、matching release、interface 与 P26R authorization。设计和操作边界见
[P26E ADR](docs/ADR-0022-host-microbiome-contract.md)与
[P26E runbook](docs/runbooks/HOST-MICROBIOME-CONTRACT.md)。

P27A-E 新增 strict `vc.virtual-experiment.v1` 与 synthetic action/replay contracts。Product design 只从
exact `VirtualCellRequestV2` 派生 public identities，不回显 raw metadata/constraint bytes；由于没有
exact-request executable + scientifically validated + production-promoted action domain，
model/Pack/evidence/policy/action catalog 仍为 `null`，control/replicate/
cost 不可用，selected actions 为空并要求人工批准。Synthetic harness 把 selection view 与 outcome ledger
结构分离，固定五个 deterministic strategies（一个 primary + 四个 baselines），先冻结全部 receipts 后
reveal；重签 selection、wrong group、
scope/unit drift 和 missing outcomes 均 fail closed。设计和操作边界见
[P27A-E ADR](docs/ADR-0023-agentic-experiment-design-contract.md)与
[P27A-E runbook](docs/runbooks/AGENTIC-EXPERIMENT-DESIGN.md)。当前没有 canonical local historical replay
pool，因此 P27A-R 保持 `REPLAY_NOT_RUN / ASSET_PENDING`；P27B 为
`AUTHORIZATION_REQUIRED / SHADOW_NOT_RUN`，P27C 为
`AUTHORIZATION_REQUIRED / PILOT_NOT_RUN`。

P28E 新增六个 strict public records：role policy、typed handoff、deterministic advisory DAG、trace event、
trace 与 authoritative compilation。Role permissions/budget/timeout/retry/cancellation/resource limits 固定；
external schema 必须绑定 exact P17/P27/replay fingerprint，internal handoff 必须绑定 declared predecessor，
trace 必须覆盖 exact DAG handoff set。Authoritative roles/handoffs/events/steps 为空，prediction/result/tool
output 为 `null`，0/3 并 abstain；synthetic advisory records 永不计为真实模型。P17 compilation 与
P27 experiment 同 request；P27 replay-result 只绑定 standalone exact fingerprint，
因 `ReplayResultV1` 没有 request/experiment link，不称 request-matched replay。设计和操作边界见
[P28E ADR](docs/ADR-0024-multi-agent-biology-contract.md)与
[P28E runbook](docs/runbooks/MULTI-AGENT-BIOLOGY-CONTRACT.md)。P29E 随后只消费 exact P28
compilation identity，新增三个 strict records，并固定 requirement identities 为 null、graph 为
`empty_not_connected`、nodes/edges 为 `0`、prediction/result/tool output 为 `null`。它没有定义
node/edge 占位类，没有接入 runtime/API/LLM/registry，也不把 standalone replay 称为
request-bound。设计和操作边界见
[P29E ADR](docs/ADR-0025-limited-biological-world-model-contract.md)与
[P29E runbook](docs/runbooks/LIMITED-BIOLOGICAL-WORLD-MODEL-CONTRACT.md)。真实 P29 仍 blocked，
不得补造 molecule→organism placeholder chain；P30A-E1 已完成，下一 eligible local work unit
是 P30A-E2 trusted finalizer/orchestrator；formal P30A 仍 `LOCAL_RC_INCOMPLETE`。

准确产品承诺是：任意符合显式合同的数据可以制作成 VirtualCellPack 接入；只有
存在匹配、可执行且经过验证并获 product policy 批准的模型时才产生预测，否则明确
abstain。

当前安装包版本来自 `pyproject.toml`，可用 `praxis-vc --version` 查询。GitHub、当前本地候选和 `.53` 的发布状态并不由版本字符串推断，请以 [三端同步台账](docs/status/SYNC-STATE.md) 为准。

## 安装与本地页面

源码开发的最低元数据要求是 Python 3.11；P30A 的离线 artifact path 则严格要求
CPython 3.13。两者都不等于当前候选已经完成发布验收。以下命令在源码仓库根目录执行：

```bash
git clone https://github.com/NHNQNHNQ/PRAXIS-Virtualcell.git
cd PRAXIS-Virtualcell
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[api]"
praxis-vc --version
```

源码可编辑安装的 `praxis-vc serve` 可以启动 API；若要让源码 checkout 在 `/` 同源托管 React 页面，先构建前端：

```bash
cd praxis_vc_react
npm ci
npm run build
cd ..
praxis-vc serve
```

浏览器打开 `http://127.0.0.1:8000`。安装自检脚本 `bash deploy/vc/check_install.sh` 仍是源码 checkout 专用；独立 wheel 与容器路径见 [安装指南](docs/INSTALL.md)。

当且仅当 `scripts/build_release_wheel.sh` 从 clean exact HEAD 成功生成候选时，该完整
wheel 才内含 React 静态资源、CLI/API 代码、`praxis_vc_web/app.py` 和经过许可审查的默认
gene-set 数据；从该 wheel 启动 `praxis-vc serve` 不依赖源码 checkout 或外置 `dist/`。
P30A-E1 已从 exact commit `0a4d72b...` 两次生成 byte-identical wheel probe（`1,264,708`
bytes / `44e5e905…2303`），但它不是 retained clean-install-qualified RC artifact，也没有
accepted release manifest。P30A-E2 必须以 trusted finalizer 重新冻结完整证据 bundle。`praxis-vc
web` 的入口文件会被打包，但运行 Streamlit 仍需安装 `web` extra；当前发行门只验证其打包和
绝对路径接线，不声称完整 Streamlit server smoke。

P30 OCI 候选（尚未形成）只能由 `scripts/build_release_oci.sh` 从同一 exact wheel、
out-of-tree Linux/arm64 wheelhouse 和 pinned local base image 以 `--network none` 构建；
它必须注入候选 commit 和 epoch。历史 `scripts/build_release_container.sh` / `deploy/vc/Dockerfile`
不是 P30 artifact 证据，不能替代这个合同。若未来 P30 OCI 构建成功，最终镜像才会以
UID/GID 10001 非 root 运行、在 `/api/health` 暴露产品版本和注入的 Git SHA，并同源提供
打包后的 React 页面。

## 快速开始

```bash
# 结构化请求：离线确定性执行
praxis-vc run \
  --request examples/ahr_k562.json \
  --mode offline \
  --out runs/ahr

# 自然语言解析后确认执行
praxis-vc ask \
  --text "在 human K562 里敲掉 AHR 会怎么样" \
  --mode offline \
  --yes \
  --out runs/ahr
```

每次运行会生成 `runs/<job>/report.md`，包含 Question、Cell Context、Routing、Result、Governance Verdict、Evidence & Provenance、Biological Interpretation、Limitations 和 Reproducibility 九个确定性章节。

## 治理裁决

| verdict | 含义 |
|---|---|
| `accept` | 请求适用且证据足够，可以给出预测 |
| `caution` | 可以使用，但必须携带明确告警 |
| `downgrade` | 引擎存在，但数据或证据不足，只能降级解读 |
| `abstain` | 没有适用引擎，系统拒绝伪造预测 |

所有预测和治理终决由后端确定性 runtime 完成。LLM 只可参与自然语言解析、路由建议、critic 复核和报告润色，不能修改 prediction、hard rule、learned reliability、provenance 或最终 verdict。`llm_assisted` 需要 `DEEPSEEK_API_KEY`；缺少凭证或调用失败时回退到离线路径。

上述 `accept/caution/downgrade/abstain` 是现有 runtime verdict，不等于
`production_promoted`。P12 已把 artifact、environment、adapter、validation evidence
和 operator-policy 拆成独立 identity；工程完成不表示存在真实 evidence、具名
operator 决定或 production promotion。

## VirtualCellPack 与模型输入

可选 `omics` extra 提供严格、只读的数据合同：`vc.pack.v0.1/v0.2` 使用 H5AD，
`vc.pack.v0.3` 使用 H5MU，并显式区分完全配对和部分配对 observation。部分配对
不会为缺失 modality 造行或补零。

`vc.model-feature-contract.v1` 把模型要求的物种、assembly、modality、feature
namespace/version 和有序 feature ID 固定下来。默认必须逐字匹配；alias、
aggregate、drop、fill、reorder 只有被合同或 hash/version 绑定的 mapping asset
明确授权时才能执行，并写入 `vc.alignment-report.v1`。不存在自动 symbol
替换、Ensembl version 剥离、ortholog/同源转换或 mock fallback。

以下五层不能混用，也不是自动递进状态链：

- Pack：`pack_valid`；
- Registry：`cataloged / artifact_ready / revoked / superseded`；
- 每次请求计算：`model_compatible / environment_compatible / executable`；
- Scientific evidence：`benchmark_passed / scientifically_validated /
  promotion_eligible`；
- Product policy：`production_promoted`。

P12 以 `vc.model-registry.v2` 分层保存 `vc.model-artifact.v1`、
`vc.model-environment.v1`、`vc.model-adapter.v1`、
`vc.model-validation-evidence.v1`、`vc.model-operator-policy.v1` 和
`vc.model-release.v1`，并从 append-only lifecycle event 归约
`cataloged / artifact_ready / revoked / superseded`。旧 `vc.model-card.v1` 字节和
fingerprint 保持兼容；迁移只生成 `legacy_incomplete` release 和结构化
`legacy_status`，不生成 evidence/policy，不把 `planned/available/missing` 升级为
可执行、科学有效或 production promoted。Native `model_version` 必须是 path-safe
identifier；legacy raw 值只保留在内部 identity/fingerprint，若不安全，公开 catalog
中的 `model_version` 为 `null`，不会重写原值。

Pack-aware 产品路径生成 `vc.environment.v2`、`vc.compatibility-report.v2` 和
`vc.execution-plan.v2`，逐次核对 exact
request×Pack×release×artifact×environment×adapter×evidence×policy 及 lifecycle。
`model_compatible` 只表示 request×Pack×model；`adapter_compatible`、
`environment_compatible` 和 `executable` 分开计算。任一引用、hash、scope、环境、
adapter、evidence、policy 或 lifecycle 门缺失即产生空计划并弃权，不会 fallback 到
mock。正式 UI/API/CLI/Streamlit 在没有精确 Pack identity 时同样生成零步骤 V2 计划，
显式 `pack_unregistered` 并弃权；不会按物种或 cell preset 自动绑定 Pack。历史
`run_query`、`run_request`、`build_runtime()`、`vc.compatibility-report.v1` 与
`vc.execution-plan.v1` 仍可用于兼容/回归，但不是 P12 产品执行授权。

v2 compatibility/step 的 canonical identity 排除 runtime path 和公开 display-only
`model_version`；raw version 仍由 `model_fingerprint` 与 release fingerprint 约束，
因此 unsafe legacy version 脱敏为 `null` 不会改变 `plan_id`。`ExecutionPlanV2`
反序列化时重算 canonical `plan_id`，并核对 report、wrapper 和 agent 的 step binding。

当前 in-process 实例化只接受声明为 `safe_load_policy=data_only` 的 artifact，并在
计划和实例化时重复检查；`restricted_deserializer`、`isolated_runtime` 和
`unavailable` 均弃权。`data_only` 目前仍是 registry 声明，尚无类型级 wrapper loader
证明，因此不能把该字段当成任意权重安全加载证明。P12 没有下载或运行真实权重，也
没有新增任何真实 promoted release。

`EnvironmentIdentity.packages` 使用 PEP 503 distribution name+version；当次
`EnvironmentSnapshot.python_dependencies` 记录 import-module availability。两组名称
不是同一 namespace，不按字符串强行等同；exact environment 由 environment
fingerprint 及 lockfile/image digest 绑定。

P13 在 P12 `vc.model-adapter.v1` identity 上实现严格的本地 Adapter SDK：
`vc.adapter-input-contract.v1`、`vc.adapter-output-contract.v1`、
`vc.prepared-adapter-input.v1`、`vc.adapter-execution-provenance.v1`、
`vc.adapter-output-envelope.v1` 和 `vc.adapter-conformance-report.v1`。Broker/
CapabilityRegistry 准备 exact input，wrapper/ensemble 核验 output envelope，
reliability/critic 消费已验证状态，provenance/report 条件携带 envelope，governance
abstain 清除公开 output 并保留审计 provenance。其 provenance 绑定 exact request、
Pack、compatibility 和 adapter/input/output contract fingerprint。非法 shape/unit/type、
非有限值、漂移的 feature
alignment/provenance、未注册或混合 adapter 输出均 fail-closed。默认 registry 只注册
delta-expression reference adapter；P13 的 growth/fitness dummy 仅存在于通用 SDK
合同测试，不是生产 registry、真实模型或科学 evidence。P13 没有运行科学评估
（`Science: NOT_RUN`），没有
新增 operator policy（`Policy: NO_NEW_DECISION`），也没有 release、版本 bump、真实权重、
训练、下载或 production promotion。设计与操作边界见
[P13 ADR](docs/ADR-0010-virtualcell-model-adapter-sdk.md)和
[P13 runbook](docs/runbooks/VIRTUALCELL-MODEL-ADAPTER-SDK.md)。

P14E 只冻结 E. coli K-12 MG1655 单基因 knockout→`growth_ratio` 的严格工程
合同与合成 conformance。`EcoliK12KnockoutGrowthAdapter` 是 local contract-only
adapter，必须由测试或未来获授权的集成代码显式放入本地 `AdapterRegistry`；
它不在 `DEFAULT_ADAPTER_REGISTRY` 中，也没有修改 runtime route、wrapper 或 product
surface。P14E 没有读取或运行真实 GEM/SBML/data，没有 Cobra/solver 科学运行、
benchmark/evidence、operator promotion 或 release/deploy。设计、操作和完成边界见
[P14E ADR](docs/ADR-0011-virtualcell-ecoli-k12-growth-contract.md)、
[P14E runbook](docs/runbooks/VIRTUALCELL-ECOLI-K12-GROWTH-CONTRACT.md)和
[P14E 完成报告](reports/phase14e/PHASE14E_COMPLETION.md)。

P15E 只冻结 S. cerevisiae S288C（`NCBITaxon:559292`、R64、
`GCF_000146045.2`）单基因 deletion→`fitness` 的 strict、prepared-bound 工程合同。
`YeastDeletionFitnessAdapter` 只允许显式本地注册，negative compatibility 固定为
`assets_verified=false`、`executable=false`、`reason=p15r_not_authorized`；它不在
默认 registry、runtime route 或产品 surface 中。实现与测试分别位于
`praxis_virtualcell/model_zoo/yeast_deletion_fitness_contract.py` 和
`praxis_virtualcell/tests/test_yeast_deletion_fitness_contract.py`。P15E 只使用合成
identity/contract fixtures，没有读取或运行真实 deletion screen、model、GEM 或科学
benchmark，没有生成 evidence/policy、release、版本 bump、push 或 deploy。设计、操作
和完成边界见 [P15E ADR](docs/ADR-0012-virtualcell-yeast-deletion-fitness-contract.md)、
[P15E runbook](docs/runbooks/VIRTUALCELL-YEAST-DELETION-FITNESS-CONTRACT.md)和
[P15E 完成报告](reports/phase15e/PHASE15E_COMPLETION.md)。

P16E 只冻结 Human/K562（`NCBITaxon:9606`、`CVCL_0004`、GRCh38、Ensembl 84）
Golden Norman perturbation→`delta_expression` 的 strict、prepared-bound 工程合同。
`K562GoldenPerturbationAdapter` 分开绑定 single-gene 与 ordered combination scope，
只允许显式本地注册；negative compatibility 固定为 `assets_verified=false`、
`executable=false`、`reason=p16r_not_authorized`。A549 只作为 upstream metadata error
原样保留，不是请求 cell identity。实现与测试分别位于
`praxis_virtualcell/model_zoo/k562_golden_delta_contract.py` 和
`praxis_virtualcell/tests/test_k562_golden_delta_contract.py`。P16E 只读取 checked-in
小型 YAML/JSON identity manifests 并使用合成 5,045 维向量，没有读取 H5AD、运行
candidate/additive ridge、生成 MSE/CI/external evidence、修改 policy、release、版本、
push 或 deploy。设计、操作和完成边界见
[P16E ADR](docs/ADR-0013-virtualcell-k562-golden-delta-contract.md)、
[P16E runbook](docs/runbooks/VIRTUALCELL-K562-GOLDEN-DELTA-CONTRACT.md)和
[P16E 完成报告](reports/phase16e/PHASE16E_COMPLETION.md)。

P17 在不实例化 wrapper、不运行模型、不调用 LLM 的 direct exact `vc.request.v2` + exact
Pack 路径上编译 deterministic `vc.virtual-experiment-dag.v1`、immutable
`vc.virtual-cell-brain-context.v1` 与 contract-only abstain decision。Broker 的公开
plan-only 入口只生成既有 `ExecutionPlanV2`；LLM 只能提供严格候选 DAG，候选审计及其
独立 checksum 不进入 authoritative DAG/Brain/decision fingerprint。
`vc.job-execution-identity.v3` 绑定 Brain/DAG，并在有 companion 文件时拒绝降级、分裂
provenance、报告语义、trace/narrative 或重签篡改。测试内第五 taxon
`Danio rerio / NCBITaxon:7955` 只存在于临时 tiny fixture，未写入生产 registry 或
species route。当前 0 promoted capabilities，所以真实请求仍是空 DAG/abstain；该工程
完成不构成真实 multi-model acceptance、scientific evidence、policy、release 或 deploy。
设计、操作和完成边界见 [P17 ADR](docs/ADR-0014-virtual-cell-brain.md)、
[P17 runbook](docs/runbooks/VIRTUALCELL-VIRTUAL-EXPERIMENT-DAG.md)和
[P17 完成报告](reports/phase17/PHASE17_COMPLETION.md)。

P18 新增 strict、content-addressed joint multi-omics model-input compiler：ordered required/
optional slots、exact feature alignment、真实 observation join 或 explicit mask、Pack/view/
adapter/matrix identity 均 fail closed。它不补零、不插补、不静默归一化，不复用 single-tensor
adapter contract 授权联合输入，也不创建 Broker execution step；输出固定为 contract-only
abstain。当前 registry 仍为 5 releases / 0 native / 0 promoted，且环境缺可选 `mudata`，所以
真实 multi-omics model acceptance 仍 pending。设计、操作和完成边界见
[P18 ADR](docs/ADR-0015-multiomics-model-input.md)、
[P18 runbook](docs/runbooks/VIRTUALCELL-MULTIOMICS-MODEL-INPUT.md)和
[P18 完成报告](reports/phase18/PHASE18_COMPLETION.md)。

P19 把 P7 quarantine receipt/payload、operator-authored candidate、完整 metadata/mapping
review、strict validation report 和 registration-only decision 绑定到 append-only factory
store 与 `vc.pack-index.v2`。P7 species 全部只作 routing hint；exact taxon 只来自 manifest
与 reviewer confirmation，coarse bacteria 不推断 *E. coli*。Index v2 兼容读 v1；旧
path-only register 已退役。Store 必须由 `PackFactoryStore.create()` 在 write-new directory
创建，并带 exact `.factory-store.json` marker
`{"schema_version":"vc.pack-factory-store.v1"}\n`；普通既存目录拒绝。

公共 `GET /api/pack-factory` 只返回 root-free、reviewer/operator raw ID 与 rationale/reason
redacted 的 lifecycle catalog，无 HTTP 写 route；Quarantine、Candidate、Factory-registered、
Model-compatible 和 Executable 分层。
P19 没有训练/checkpoint/evidence/promotion，real external fixture/output root/operator/science/
policy 未运行。设计、操作和完成边界见
[P19 ADR](docs/ADR-0016-controlled-pack-factory.md)、
[P19 runbook](docs/runbooks/VIRTUALCELLPACK-CONTROLLED-PACK-FACTORY.md)和
[P19 完成报告](reports/phase19/PHASE19_COMPLETION.md)。

P8 产品化收口随发行物提供三个合成、微型、可审计 Pack：
`p8-human-tiny`、`p8-mouse-tiny`、`p8-bacteria-tiny`。它们覆盖
`EnsemblGene` 与 `NCBIGene` 两种 feature namespace，均通过同一个既有
`PackRegistry` 完整验证；没有复制或转换 P7 大数据，也没有新增生产模型。

```bash
praxis-vc pack inspect /absolute/path/to/pack
praxis-vc pack validate /absolute/path/to/pack
praxis-vc pack list
praxis-vc pack compatibility \
  --request request.json --pack-id p8-human-tiny --pack-version 1.0.0
praxis-vc pack run \
  --request request.json --pack-id p8-human-tiny --pack-version 1.0.0 \
  --mode offline --out runs/p8-example
```

P19 受控 register 不再接受单一路径，必须先由 library 生成/复核 artifacts，并初始化
write-new store：

```bash
praxis-vc pack register \
  --upload-directory /absolute/quarantine/<upload-id> \
  --pack-root /absolute/operator-authored-pack \
  --candidate /absolute/contracts/candidate.json \
  --review /absolute/contracts/review.json \
  --validation /absolute/contracts/validation.json \
  --decision /absolute/contracts/decision.json \
  --index /absolute/existing-parent/pack-index.json \
  --store /absolute/initialized-factory-store
```

`inspect` 明确返回未校验状态；`validate/register/list/compatibility/run` 均按当前
bytes 重验。只读 API 位于 `/api/packs`、`/api/packs/{id}/{version}`、
`/api/packs/{id}/{version}/validate`、`/api/packs/compatibility` 和 `/api/pack-factory`；
服务器不提供 Pack register API。
`vc.pack-catalog.v1` 保持外层兼容，同时在 top-level `model_registry` 暴露路径脱敏的
`vc.model-registry-catalog.v2`，并在每个
`model_capabilities[*].registry_releases` 中只列该模型的 release 投影。React“数据
资源”页只显示后端验证/capability 字段，不复制科学路由。v2 Pack-aware job 使用
`vc.job-execution-identity.v2` 锁定 request、Pack、environment snapshot、release、
component、evidence、policy、structured report fingerprint 和 outcome；历史 v1 job
identity 仍可解析，`JobStore.load` 只做只读投影、不改旧 bytes，同名 job 仍不能覆盖。
P17 compilation-backed direct-v2 job 使用 `vc.job-execution-identity.v3`，在上述字段外绑定
Brain 与 DAG fingerprint；v1/v2/v3 只要存在 request/report/provenance/trace companions
就会重算并交叉核验，真正无 companions 的 historical identity-only 记录继续只读兼容。

P7 的“数据资源”页面提供独立的公开下载和隔离上传通道。公开目录使用 strict
`vc.data-catalog.v1`，只对外置数据根中 path、size、SHA-256 全部匹配的文件开放
下载；缺失或篡改文件保持不可用。上传需部署者配置至少 32 字符 bearer token，
成功后只生成 `vc.upload-receipt.v1` 并原样保存在 quarantine：

```bash
export PRAXIS_VC_DATA_ROOT=/absolute/path/praxis-virtualcell-data
export PRAXIS_VC_UPLOAD_TOKEN='<at-least-32-random-characters>'
praxis-vc serve
```

目录有效、文件可下载或上传成功都不等于 `pack_valid`、`model_compatible` 或
`scientifically_validated`。上传不会自动解包、归一化、补零、转换 feature、
注册 Pack 或参与预测；大数据仍不进入 Git。

P8 的 Norman/K562 Golden Pack 把一个公开真实数据集固定为可审计参考：source
H5AD、上游预处理 X/counts、有序 feature、三个 control guide、预定义
train/validation/test、condition-macro MSE、condition 级 bootstrap 和三个简单
baseline 全部 hash/版本绑定。每个 baseline 使用独立的一卡 registry 走正式
Pack→broker→governance→Report，不经 mock shortcut；未知/重复 canonical target
或篡改资产均 fail-closed。当前 test MSE 是 no-change `0.00620609`、global mean
`0.00458205`、additive ridge `0.00325706`，只适用于该冻结 benchmark。
`pack_valid=true` 与 `model_compatible=true` 仍保持
`scientifically_validated=false`；本阶段没有运行或访问 GEARS。

P9 进一步冻结 IID、perturbation、combination、cell type、donor、
dataset/platform、species、dose/time 八类 OOD 分组合同，并要求 biological unit
和 replicate 在评估前通过泄漏审计。随仓库提交的八轴 fixture 只证明合同，不是
八轴性能证据。真实的无适配外部验证固定为
`GSE67402 → GSE94117:glycerol_time_course`：4,484 个 feature 仅取原始 ID
精确交集，不补零、不做 symbol/ortholog 转换；阈值只在 source validation 选择。
候选主 MSE `1.06038358` 未胜 no-change `1.05333471`，paired 95% CI 跨 0，
因此 `available=false` 且 `scientifically_validated=false`。该失败结论是 P9
fail-closed 验收结果，不是待隐藏的异常。

P10 增加独立、无模型的 `vc.community-pack.v1` 前置接口：成员只按已经完整验证的
VirtualCellPack ID/version/fingerprint 引用，abundance、medium、compartment、
time、`well_mixed` space、共享代谢物 namespace 和 interaction evidence 全部显式
声明。E. coli 与合成 S. cerevisiae tiny Pack 只验证引用和合同可插拔性；toy
exchange 只做精确质量收支检查。当前没有真实 `CommunityModelAdapter`，因此
community plan 固定不可执行，run 只能 `prediction=null` 并诚实 abstain；不存在
单位/ID 转换、自动丰度归一或 mock fallback。完成项与尚缺实验验证见
[Community readiness checklist](docs/COMMUNITY-READINESS-CHECKLIST.md)。

架构和复现边界见 [ADR-0003](docs/ADR-0003-virtualcellpack-p5-multiomics-alignment.md)、
[ADR-0004](docs/ADR-0004-virtualcellpack-p6-capability-runtime.md)、
[ADR-0005](docs/ADR-0005-virtualcellpack-p7-data-portal.md)、
[ADR-0006](docs/ADR-0006-virtualcellpack-p8-golden-norman.md)、
[ADR-0007](docs/ADR-0007-virtualcellpack-p8-product-surfaces.md)、
[ADR-0008](docs/ADR-0008-virtualcellpack-p9-ood-validation.md)、
[ADR-0009](docs/ADR-0009-virtualcell-model-zoo-v2.md)、
[多组学 runbook](docs/runbooks/VIRTUALCELLPACK-MULTIOMICS.md) 与
[能力 runtime runbook](docs/runbooks/VIRTUALCELLPACK-CAPABILITY-RUNTIME.md)、
[数据资源库 runbook](docs/runbooks/VIRTUALCELLPACK-DATA-PORTAL.md) 和
[Golden Norman runbook](docs/runbooks/VIRTUALCELLPACK-GOLDEN-NORMAN.md)、
[Pack 产品面 runbook](docs/runbooks/VIRTUALCELLPACK-PRODUCT-SURFACES.md)、
[P9 OOD 验证 runbook](docs/runbooks/VIRTUALCELLPACK-P9-OOD-VALIDATION.md) 和
[Model Zoo v2 runbook](docs/runbooks/VIRTUALCELL-MODEL-ZOO-V2.md)、
[Community readiness checklist](docs/COMMUNITY-READINESS-CHECKLIST.md)。

## 能力边界

PRAXIS-VirtualCell 是带可靠性治理的操作层，不是通用或 SOTA 预测模型。历史
Phase 10 Gate 的可复现证据只支持以下克制表述；它不构成 P12
`ValidationEvidence`、operator policy 或 promotion：

- 当时记录的引擎级覆盖为四类：M2（真实 donor 证据来自 `.53` 历史亲验）、M3、M4
  和 M7。
- M1、M5、M8 属于 rule-based advisory；M6 以及 EMT、fate、spatial、communication 等路径存在明确 limitation。
- 历史本地 offline 流程中的 mock 只用于测试或演示 conformance，不构成生产预测、
  科学 evidence 或 product policy。
- 多模块结果表示路由计划中的多个 entry 与 advisory，不表示多个预测器已经完成证据融合。
- 更完整的 met / narrowed / unsupported / pending 边界以 [Phase 10 Gate](reports/phase10/PHASE10_GATE.md) 为准。

## 开发与测试

```bash
python -m pip install -e ".[dev,api,mechanistic,omics]"
python -m pip check
ruff check .

# VirtualCell 核心权威口径；真实 LLM 不在普通门中
pytest praxis_virtualcell/tests -m "not llm" -o addopts='' -q -ra

# 继承测试口径；排除容器、真实 LLM、GPU/checkpoint 和私网服务
pytest tests -m "not (integration or llm or remote)" -o addopts='' -q -ra

cd praxis_vc_react
npm ci
npm run typecheck
npm run lint
npm run build
CI=1 npm run e2e
```

当前 P29E 精确本地结果为 focused `51 passed`、P28+P29 adjacent `89 passed`、affected
`390 passed`、safe `1,934 passed / 49 skipped / 387 deselected`（`427.59s`）、legacy
`1,147 passed / 58 skipped / 105 deselected`（`58.07s`）、packaging/versioning `18 passed`，
静态门与前端 bundle budget 通过。
两次 completion-SHA archive wheel byte-identical：`1,263,199` bytes，SHA-256
`368a66a438c036a3b9c24f1093fc478886885fbefaecfea52bb50ad616206c01`，`378`
entries、React `14`、tests `0`、AppleDouble `0`；source/wheel
`praxis_virtualcell/limited_world_model.py` SHA-256 均为
`b730220099b36df99f7ba706be7dea6174b1c41329b62526dc45bda475c155ae`。工具链为
Python `3.13.12`、build `1.5.0`、setuptools `70.2.0`、packaging `26.0`、Node
`25.8.2`、npm `11.11.1`、Vite `8.1.2`。这是 exact local source/toolchain reproducibility，
不是 pinned dependency closure、clean-install 证明、historical/scientific evidence 或 release。
P30A-E1 另有 release-tool/source-archive/packaging `47 passed`、formal Pack-aware entrypoint
`148 passed` 和 React typecheck/lint/production build/bundle budget PASS；two source-archive
probes are `8,055,078` bytes / `ba5e5d0d…e642`. These probes do not complete P30A: P30A-E2 trusted
finalizer is next, while the offline runtime cache lacks `pyjwt==2.13.0` and `pyyaml==6.0.3`, and
the Linux/arm64 wheelhouse lacks `cffi`、`cryptography`、`pydantic-core`、`rpds-py` target inputs.
Science remains `NOT_RUN / SCIENCE_BADGE_INELIGIBLE`; policy remains `NO_NEW_DECISION`. 完整命令、用时、skip/deselect
含义、显式外部门和 GitHub CI 状态见 [测试指南](docs/TESTING.md)。普通测试默认不访问固定私网服务；`integration`、`llm`、`remote` 分别需要 `--run-integration`、`--run-llm`、`--run-remote`，一个测试拥有多个 marker 时必须同时满足对应门。

## 文档入口

| 文档 | 内容 |
|---|---|
| [当前项目与集成指南](docs/PRAXIS-VIRTUALCELL-CURRENT-PROJECT-AND-INTEGRATION-GUIDE.md) | 当前产品事实、P11–P30A-E2 边界和跨项目集成 |
| [P30A-E1 Engineering Completion Report](reports/phase30a/PHASE30A_ENGINEERING_COMPLETION.md) | release-contract hardening、probe identities、formal RC non-claim 与 P30A-E2 trusted-finalizer handoff |
| [P29E 完成报告](reports/phase29e/PHASE29E_COMPLETION.md) | exact empty-not-connected/value-free closure、package evidence 与真实 data/model/benchmark/science/policy non-runs |
| [P29E Limited World Model ADR](docs/ADR-0025-limited-biological-world-model-contract.md) | null requirement identities、empty typed graph、content-hash trust ceiling 与 0-node abstention 决策 |
| [P29E Limited World Model runbook](docs/runbooks/LIMITED-BIOLOGICAL-WORLD-MODEL-CONTRACT.md) | exact P28 input、empty graph、authority-null 与 artifact reproducibility 核验 |
| [P28E 完成报告](reports/phase28e/PHASE28E_COMPLETION.md) | exact 0/3 value-free closure、typed DAG/trace identities、package evidence 与真实 comparison/science/policy non-runs |
| [P28E Multi-Agent Biology ADR](docs/ADR-0024-multi-agent-biology-contract.md) | advisory authority ceiling、exact handoff/DAG/trace closure 与 authoritative empty graph 决策 |
| [P28E Multi-Agent Biology runbook](docs/runbooks/MULTI-AGENT-BIOLOGY-CONTRACT.md) | role/handoff/DAG/trace 核验、real 3-module gate 与 P29E empty-graph handoff |
| [P27A-E 完成报告](reports/phase27ae/PHASE27AE_COMPLETION.md) | exact design/replay closure、synthetic conformance、P27A-R/P27B/P27C non-runs、package evidence 与 P28E handoff |
| [P27A-E Agentic Experiment Design ADR](docs/ADR-0023-agentic-experiment-design-contract.md) | request/public identity、empty product action space、rank-then-reveal 与 maturity ceiling 决策 |
| [P27A-E Agentic Experiment Design runbook](docs/runbooks/AGENTIC-EXPERIMENT-DESIGN.md) | design/action/selector/reveal 核验、historical asset gate 与 P28E handoff |
| [P23A 完成报告](reports/phase23a/PHASE23A_COMPLETION.md) | exact evidence-only contract closure、synthetic conformance、reproducible local-toolchain wheel 与真实 data/model/science/policy 非运行边界 |
| [P23A Cell Interaction Evidence ADR](docs/ADR-0020-cell-interaction-evidence-contract.md) | directed endpoint/same-experiment/scorer identity、P13 envelope、唯一 score projection 与 non-claim 决策 |
| [P23A Cell Interaction Evidence runbook](docs/runbooks/CELL-INTERACTION-EVIDENCE.md) | local contract audit、negative/abstain 检查、真实输入/执行授权门与 P24 handoff |
| [P22 完成报告](reports/phase22/PHASE22_COMPLETION.md) | exact curated-registry closure、default-deny external trust/checkpoint、reproducible local-toolchain wheel 与真实 lifecycle/science/policy 非运行边界 |
| [P22 Curated Registry ADR](docs/ADR-0019-curated-virtual-cell-registry.md) | exact One-Pack/P21B release composition、append-only lifecycle、stable authorization reference 与外置 checkpoint 边界 |
| [P22 Curated Registry runbook](docs/runbooks/VIRTUALCELL-CURATED-REGISTRY.md) | local import/decision/query 审计、suffix reauthorization、checkpoint 推进与 rollback 限制 |
| [P21A 完成报告](reports/phase21a/PHASE21A_COMPLETION.md) | exact benchmark-system closure、reproducible local-toolchain wheel 与真实 benchmark/science/policy/promotion 非运行边界 |
| [P21A Benchmark System ADR](docs/ADR-0018-virtual-cell-benchmark-system.md) | frozen protocol/run/result/evidence、out-of-band P21B execution trust 与 negative-only ledger 边界 |
| [P21A Benchmark System runbook](docs/runbooks/VIRTUALCELL-BENCHMARK-SYSTEM.md) | local contract gates、bundle/ledger 核查、rollback 限制和 P22 contract-only handoff |
| [P20 完成报告](reports/phase20/PHASE20_COMPLETION.md) | exact training-contract closure、reproducible local-toolchain wheel 与真实 training/test/external/science 非运行、policy `NO_NEW_DECISION` |
| [P20 Training Pipeline ADR](docs/ADR-0017-virtual-cell-training-pipeline.md) | RegisteredPack binding、audit-before-label、fixed worker 与 candidate-only artifact 边界 |
| [P20 Training Pipeline runbook](docs/runbooks/VIRTUALCELL-TRAINING-PIPELINE.md) | local contract gates、read ordering、atomic artifact publish/cleanup 与 P21A handoff |
| [P19 完成报告](reports/phase19/PHASE19_COMPLETION.md) | controlled registration、v2 index/read-only catalog 与 real fixture/operator/science/policy 非运行边界 |
| [P19 Controlled Pack Factory ADR](docs/ADR-0016-controlled-pack-factory.md) | receipt→registration identities、explicit store/index 与 pending→committed fail-closed |
| [P19 Controlled Pack Factory runbook](docs/runbooks/VIRTUALCELLPACK-CONTROLLED-PACK-FACTORY.md) | local CLI migration、store marker、validation/public projection 审计 |
| [P18 完成报告](reports/phase18/PHASE18_COMPLETION.md) | exact code/tree、44 focused tests、reproducible wheel 与真实 multi-omics model acceptance 未完成边界 |
| [P18 Multi-omics Model Input ADR](docs/ADR-0015-multiomics-model-input.md) | ordered slots、join/missingness、Pack/view/adapter/matrix identity 与 contract-only abstain |
| [P18 Multi-omics Model Input runbook](docs/runbooks/VIRTUALCELL-MULTIOMICS-MODEL-INPUT.md) | strict contract 审计、tamper/replay 检查与 fail-closed 解读 |
| [P17 完成报告](reports/phase17/PHASE17_COMPLETION.md) | exact code/tree、deterministic contract 验证、reproducible wheel 与真实多模型验收未完成边界 |
| [P17 Virtual Cell Brain ADR](docs/ADR-0014-virtual-cell-brain.md) | authoritative DAG/Brain/decision、candidate isolation 与 JobStore v3 identity |
| [P17 Virtual Experiment DAG runbook](docs/runbooks/VIRTUALCELL-VIRTUAL-EXPERIMENT-DAG.md) | direct-v2 contract 审计、tamper/downgrade 检查与 fail-closed 解读 |
| [P16E 完成报告](reports/phase16e/PHASE16E_COMPLETION.md) | exact code/tree、本地 contract-only 验证、reproducible wheel 与 P16R/P16B 非运行边界 |
| [P16E K562 Golden delta ADR](docs/ADR-0013-virtualcell-k562-golden-delta-contract.md) | exact K562/P8 scope、ordered perturbation binding、prepared-bound 输出与 local-only adapter |
| [P16E K562 Golden delta runbook](docs/runbooks/VIRTUALCELL-K562-GOLDEN-DELTA-CONTRACT.md) | 本地 manifest/合同审计、定向验证、P16R 授权门和 fail-closed 解读 |
| [P15E 完成报告](reports/phase15e/PHASE15E_COMPLETION.md) | exact code/tree、本地 contract-only 验证、reproducible wheel 与 P15R/P15B 非运行边界 |
| [P15E S. cerevisiae deletion-fitness ADR](docs/ADR-0012-virtualcell-yeast-deletion-fitness-contract.md) | exact S288C scope、strict binding、prepared-bound 输出与 local-only adapter |
| [P15E S. cerevisiae deletion-fitness runbook](docs/runbooks/VIRTUALCELL-YEAST-DELETION-FITNESS-CONTRACT.md) | 本地合同审计、定向验证、P15R 授权门和 fail-closed 解读 |
| [P14E 完成报告](reports/phase14e/PHASE14E_COMPLETION.md) | exact start/code/tree、本地 contract-only 验证、P14R/P14B 非运行边界 |
| [P14E E. coli K-12 growth ADR](docs/ADR-0011-virtualcell-ecoli-k12-growth-contract.md) | exact scope、九个合同、prepared-bound 输出与 default-registry 隔离 |
| [P14E E. coli K-12 growth runbook](docs/runbooks/VIRTUALCELL-ECOLI-K12-GROWTH-CONTRACT.md) | 本地合同审计、定向验证、P14R 授权门和 fail-closed 解读 |
| [P13 完成报告](reports/phase13/PHASE13_COMPLETION.md) | 历史 exact code/tree、Adapter SDK 验证和 science/policy 非声明 |
| [P13 Model Adapter SDK ADR](docs/ADR-0010-virtualcell-model-adapter-sdk.md) | 六个严格 schema、identity binding、fail-closed 输出与兼容边界 |
| [P13 Model Adapter SDK runbook](docs/runbooks/VIRTUALCELL-MODEL-ADAPTER-SDK.md) | adapter 注册、conformance、运行时审计和定向验证 |
| [P12 Model Zoo v2 ADR](docs/ADR-0009-virtualcell-model-zoo-v2.md) | 当前分层 identity、迁移、fail-closed 和安全加载边界 |
| [P12 Model Zoo v2 runbook](docs/runbooks/VIRTUALCELL-MODEL-ZOO-V2.md) | 当前只读操作、验证命令和状态解释 |
| [P12–P30 顺序总提示词](docs/PHASE12-30-SEQUENTIAL-MASTER-PROMPT.md) | superseded 历史状态机/授权材料；不是当前 action authority |
| [P12–P30 执行路线](docs/PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md) | 详细 scope、硬门和条件式授权模板 |
| [P12–P30 完成清单](docs/PHASE12-30-DETAILED-COMPLETION-CHECKLIST.md) | 工程、科学和 policy 分离的验收台账 |
| [P12–P30 协调提示词](docs/PHASE12-30-MASTER-PROMPT.md) | 长期协调边界；不得替代现场 Git 证据 |
| [P11A 设计](docs/PHASE11A-DATA-CENTRIC-UI-DESIGN.md) | P11A 历史实现说明；现行产品以 P11B 为准 |
| [文档地图](docs/INDEX.md) | 当前权威入口与历史材料分层索引 |
| [2026-07-18 项目状态](docs/status/PROJECT-STATE-2026-07-18.md) | 历史快照，不是当前阶段台账 |
| [三端同步台账](docs/status/SYNC-STATE.md) | 历史远程观测；使用前必须在获准窗口现场刷新 |
| [安装指南](docs/INSTALL.md) | pip、前端、Docker 现状和可选依赖 |
| [用户指南](docs/USER-GUIDE.md) | 历史 CLI/五阶段界面说明；Cell-first 现状以上述集成指南为准 |
| [版本契约](docs/VERSIONING.md) | 产品、协议、schema、artifact 和模型版本边界 |
| [Phase 10 Gate](reports/phase10/PHASE10_GATE.md) | 科学能力与远端证据边界 |

## 版本与同步流程

唯一允许的流向是：本地 feature branch → GitHub branch/CI → 审批合入 GitHub `main` → 本地 `main` fast-forward → `.53` 从同一 GitHub SHA fast-forward → 三端 SHA 核对。不要在 `.53` 直接开发，也不要把本地 tag 当成已发布 tag。

本轮 P23A contract/docs closure 窗口未刷新 GitHub 或 `.53`。规范工作树是
`/Volumes/T7/PRAXIS-virtualcell`，Git metadata 是
`/Users/mzy/Projects/.PRAXIS-virtualcell-gitdir`；任何远程数字只有带日期和 exact
identity 的只读记录意义。

历史整理分支曾按两次精确 D1a 授权把 GitHub `codex/project-consolidation` 快进到 `ee36d7948047f346f55a02d62ccaac84391e3c20`。对应的 [GitHub Actions run 29971566980](https://github.com/NHNQNHNQ/PRAXIS-Virtualcell/actions/runs/29971566980) 为 `4/5`：Python core、frontend/Playwright、reproducible wheel 和 Linux release container 通过，legacy 唯一失败是 Linux shell 子进程未随直接 shell 终止。修复提交 `6a8198771581d0897a13457e93e50cfec172d59a` 已把输出截断、timeout、pipe 异常和上层取消统一为进程组清理，并在 macOS/Python 3.13.12 与 Linux/Python 3.13.14 严格锁环境得到 legacy `1139 passed / 0 failed`。这些都是绑定旧 SHA 的历史证据，不授权当前工作单元 push、CI、release 或 deploy；GitHub `main`/tag、本地 `main` 和 `.53` 当前状态必须在未来获准窗口重新只读核对。

## 派生关系

本项目由 PRAXIS-2 commit `b124d66` 复制改造，继承 agent runtime、长期大脑、规则系统与反幻觉基础，并扩展 VirtualCell 大脑、预测器注册表和生物 benchmark。兼容运行时代码位于 `praxis2/`，产品代码位于 `praxis_virtualcell/`，本地 API/React 界面位于 `praxis_vc_api/` 与 `praxis_vc_react/`。详见 [PROVENANCE.md](PROVENANCE.md)。
