# finding v0.5 R6 — Co-culture sender→receiver 两步链 case(真跑)

> 目标:补应用 5 例 5C(sender 扰动 → receiver 状态迁移,多步)。证据类型:`[Mac确定性]`。**自主完成**(复用 Kang 2018)。对应 `docs/PLAN-v0.5-complete-remaining.md` R6。

## 1. 分析(两步链)

复用 `lr_comm.LRCommDB`(通讯)+ `state.cell_state.CellStateDB`(receiver 状态),做 sender→receiver 两步链:
- **step1 通讯**:sender(单核)IFN 诱导 CXCL10 → receiver CXCR3(ctrl vs stim,通讯是否诱导)
- **step2 receiver 响应**:receiver 细胞的 ISG 激活状态(ctrl vs stim,receiver 是否被激活)

route:`(human, ligand, communication) → communication`。

## 2. 结果 + 治理(实跑)

| sender→receiver | 通讯诱导 | receiver ISG(d) | **链裁决** |
|---|---|---|---|
| CD14+ Mono → CD8 T | ✓ | 2.77(激活) | **accept** |
| CD14+ Mono → NK | ✓ | 2.76(激活) | **accept** |
| CD14+ Mono → Megakaryocytes | ✗ | 0.20(未激活) | **downgrade** |

- **多步治理(R6)**:**两步都成立**(通讯诱导 AND receiver 激活)→ accept 完整信号链;任一弱 → downgrade。巨核细胞既不接收强通讯也不激活 → 链不完整 → **不硬报 sender→receiver 信号**。ligand 不在库 → abstain。测试 `test_coculture_case.py`(3 passed)。

## 3. 意义 + 边界

- 证明 agent 能**组织多步生物分析**:sender / ligand / receptor / receiver-state,并在**每一步**受治理,只有链完整才 accept——正是应用 5(通讯/微环境)需要的多模型协作 + 防过度承诺。
- **诚实**:两步均为代理(通讯=共表达,receiver 响应=ISG 评分);Kang 2018 **非真 co-culture**(以 sender/receiver 细胞类型 + 刺激模拟 sender 扰动);downgrade 表"链证据不完整"。**不训练模型**。
