---
name: consurf_conservation
description: ConSurf 蛋白残基进化保守度评分。输入 PDB + UniProt accession;输出每残基 1-9 保守度分数(9 = 最保守);PSSM/HMMER MSA 自动构建。
status: green
host_env: consurf
maturity: stub
note: 自动生成的占位 SKILL.md(SOFTWARE-GAP-REPORT v2 §7);该 env 在 .53 staging 已装,
  待人工补充 SOP / 输入输出契约 / SOP / 失败模式。
---

# consurf_conservation

ConSurf 蛋白残基进化保守度评分。输入 PDB + UniProt accession;输出每残基 1-9 保守度分数(9 = 最保守);PSSM/HMMER MSA 自动构建。

## 状态

**stub** — 仅声明该 staging env 的能力,让智能体能在 system prompt 中看到此 skill 候选。
具体 SOP / 输入输出契约 / run.py 实现待补。

## 建议下一步

1. 进 staging 该 env (`conda activate consurf`) 看 `pip list` / `which`,确定真有的入口工具。
2. 写一个跑得起来的最小 demo(可参考同 brain 内其他成熟 skill 的结构)。
3. 把 stub 标记从 `maturity: stub` 升到 `maturity: draft` → `maturity: production`。

## 输出契约

```json
{
  "skill_id": "consurf_conservation",
  "msa_path": "",
  "n_sequences": 0,
  "conservation_csv": "",
  "diagnostics": {
    "brain": "protein",
    "archetype": "msa_conservation"
  }
}
```
