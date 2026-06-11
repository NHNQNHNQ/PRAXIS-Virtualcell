---
name: pdb-literature-report
description: 固化任务开始时的 PDB 候选检索、文献调研和报告写法。覆盖结构选择、候选解释、文献搜索和结果表达。
---

# PDB Literature And Report Skill

## 目的

收到任务后，先帮用户选对结构，再帮用户找对文献，最后把结果写成可读报告。背景和学习过程放进记忆；这里专门保留以后重复任务还能直接调用的方法。

## PDB 选择

### 默认动作

1. 抽取蛋白名、物种、配体、复合伙伴、构象状态。
2. 搜索相关 `PDB` 候选。
3. 逐个解释每个 `PDB` 的内容。
4. 让用户明确选择。

### 强制要求

- 开始体系构建前，必须先向用户确认要使用的 `PDB` 或起始结构来源。
- 如果用户打算用 `AlphaFold/AFDB` 结构，也不能跳过这一步。
- `AlphaFold/AFDB` 蛋白进入膜体系前，必须先确认膜方向和整体取向，不能把未定向结构直接交给后续构建。

### 每个候选必须说明

- `PDB ID`
- 蛋白名称与物种
- apo、holo、复合物还是突变体
- 链、配体、辅因子、抗体、G 蛋白或融合蛋白
- 实验方法与分辨率
- 缺失残基、缺失环、工程化片段与风险

### 用户确认前不要做的事

- 不要默认替用户锁定结构
- 不要只按分辨率选
- 不要忽略膜蛋白的方向和信号状态
- 不要把 `AlphaFold/AFDB` 结构当作“天然可直接构建”的输入

## 文献检索

### 目标

围绕结构来源、体系设计、模拟方法和结果解释找文献，而不是只找蛋白综述。

### 关键词模板

- `protein name + pdb id + structure`
- `protein name + molecular dynamics`
- `protein name + membrane + simulation`
- `ligand name + permeability + membrane`
- `protein name + umbrella sampling`
- `protein name + metadynamics`

### 优先级

- 结构原始论文
- 同体系或同家族的 MD 论文
- 方法论文和软件文档
- 与结果解释直接相关的机制论文

## 报告写法

### 基本结构

1. 任务目标
2. 起始结构与为什么选它
3. 体系构建方法
4. 模拟方法与关键参数
5. 结果
6. 生物学解释
7. 局限性与下一步

### 写法原则

- 不只罗列命令和数值
- 把 `RMSD`、`RMSF`、距离、氢键、PMF 翻译成生物学语言
- 先解释结构和机制，再给数字支持
- 说清不确定性，不夸大结论

### 典型问题类型

- 蛋白-配体体系：讲结合稳定性、关键接触和活性位点几何
- 膜蛋白体系：讲构象状态、门控、脂质环境和膜方向
- 跨膜小分子体系：讲能垒、PMF 形状、电荷和亲脂性

## 和其他技能的关系

- 选好结构和文献后，体系构建交给 `skills/workflows/md-build-run/SKILL.md`
- 命令和报错处理交给 `skills/workflows/md-gromacs/SKILL.md`

## 输出契约

```json
{
  "ok": true,
  "skill_id": "pdb-literature-report",
  "result": {},
  "diagnostics": {
    "brain": "Naruto-main",
    "archetype": "generic"
  }
}
```
