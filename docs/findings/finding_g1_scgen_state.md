# finding G1 — scGen / STATE 同协议入表 A 尝试:诚实的阻塞报告

> 目标:把 scGen / STATE 放到 donor norman test split + per-cell ΔPearson 入表 A(GEARS 0.4877 旁)。**结论:两者都撞真实障碍,未强行产出可疑数字**。证据类型:`[远端实跑]`(远端实测阻塞)。runbook:`docs/G1-scgen-state-remote-runbook.md`。

## 1. 已验证(远端实测)
- **env 兼容**:`pip install scgen` 保持 torch 2.6.0(不降级),scvi-tools 1.4.2 装成 → **donor 模型仍可用**(`load_norman` n=18874),G2/L4 的 virtualcell env 未被破坏。
- eval 接口(`load_vcbench_split` + `EvalAgent`)确认可复用(同 L4/scGPT/G2)。

## 2. scGen — 两重真实障碍,不强跑

**(a) 依赖不兼容**:`scgen 2.1.0` import 失败 —— `ModuleNotFoundError: No module named 'scvi._compat'`。scgen 2.1.0 依赖旧 scvi API(`_compat`,约 scvi-tools <1.0 才有),与装上的 scvi-tools 1.4.2 不兼容。修需 pin `scvi-tools<1.0`(如 0.20.x)→ 但旧 scvi 需旧 torch/lightning → **会把 torch 2.6 降级 → 破坏 donor 模型**(G2/L4 依赖)。**不值得为一个 scGen 牺牲已用 env**。

**(b) 方法学不匹配**:scGen 是**条件迁移**模型(学 ctrl→**已知**扰动的 latent 位移,应用到新细胞类型),**不用 perturbation embedding 泛化**。Norman 表 A 的 test 是 **151 个未见扰动**(OOD);scGen 对训练中未见的扰动**无 latent delta 可用** → 要么训练时纳入 test 扰动(**泄漏,违铁律**),要么无法预测。→ scGen **不是 Norman 未见扰动任务的合适同协议对照**(不同于 GEARS 用 pert emb 泛化)。

## 3. STATE — 未深跑(重/新)
STATE(Arc Institute)设计上支持扰动泛化(比 scGen 更合适),但需 `arc-state`+`cell-load` 大安装 + 特定数据格式 + 多半需预训练 checkpoint。自主全跑(装→数据转换→训练/加载→适配 donor EvalAgent)高风险、长耗时,本 session 未启(runbook 保留可执行清单)。

## 4. 结论 + 建议
- **表 A 的"同协议外部 baseline"缺口已由 GEARS 0.4877(L4)填补** —— 这是关键 gap-filler,scGen/STATE 属加分项。
- scGen 因**依赖 + 方法学**双重障碍,**不是**该任务的干净对照;强跑只会得到泄漏或无意义数字,违背诚实铁律 → **不做**。
- STATE 是更合适但更重的候选;若要补,建议**独立 env + 交互式远端设置**(非一次性自主跑),按 runbook 推进。
- **诚实优先**:宁可如实报"scGen N/A(条件迁移不适用未见扰动)+ STATE 待重设置",不产出可疑数字。这本身呼应 PRAXIS 主题——**适用性判断 + 不过度承诺**。

## 5. 环境状态
- virtualcell env 现含 scvi-tools 1.4.2 + scgen 2.1.0(附加,未破坏 donor);torch 保持 2.6.0+cu124。scgen import 失败不影响其它代码。如需彻底干净可 `pip uninstall scgen`(非必须)。
