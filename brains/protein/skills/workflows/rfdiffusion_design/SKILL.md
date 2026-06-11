---
name: rfdiffusion_design
description: RFdiffusion 生成式蛋白骨架设计(scaffold/motif/binder/symmetric)。输入靶位点 + 长度;输出多个候选骨架 PDB;通常下游接 ProteinMPNN 反向序列设计。
status: green
host_env: rfdiffusion
maturity: stub
note: 自动生成的占位 SKILL.md(SOFTWARE-GAP-REPORT v2 §7);该 env 在 .53 staging 已装,
  待人工补充 SOP / 输入输出契约 / SOP / 失败模式。
---

# rfdiffusion_design

RFdiffusion 生成式蛋白骨架设计(scaffold/motif/binder/symmetric)。输入靶位点 + 长度;输出多个候选骨架 PDB;通常下游接 ProteinMPNN 反向序列设计。

## 状态

**stub** — 仅声明该 staging env 的能力,让智能体能在 system prompt 中看到此 skill 候选。
具体 SOP / 输入输出契约 / run.py 实现待补。

## 建议下一步

1. 进 staging 该 env (`conda activate rfdiffusion`) 看 `pip list` / `which`,确定真有的入口工具。
2. 写一个跑得起来的最小 demo(可参考同 brain 内其他成熟 skill 的结构)。
3. 把 stub 标记从 `maturity: stub` 升到 `maturity: draft` → `maturity: production`。

## 输出契约

```json
{
  "skill_id": "rfdiffusion_design",
  "sequence": "",
  "model_path": "",
  "plddt_mean": 0.0,
  "ptm": 0.0,
  "n_residues": 0,
  "runtime_sec": 0.0,
  "diagnostics": {
    "brain": "protein",
    "archetype": "structure_predict"
  }
}
```
