---
name: esm-mutation-scan
description: 用 ESM-1v / ESM-2 / SaProt 等 PLM (protein language model) zero-shot 评估突变效应，输出每个候选突变的 log-likelihood ratio / 拟合度评分。Agent 在 Design 阶段必须先跑这个 skill 才能给出突变候选——禁止凭语言模型直觉构造突变位点。是 Hard Rule 9 强制分析门控的核心 skill 之一。
status: green
host_env: PRAXIS-Enzyme
deps: [fair-esm]
---

# ESM Mutation Scan Skill

## 一句话原则
**没有 ESM/PLM zero-shot 分数, 不允许 agent 给出突变候选**。这是 Hard Rule 9 强制分析门控的第一关——把"凭直觉给位点"的 LLM hallucination 从源头掐掉。

## 适用阶段
Design Agent 在生成候选突变集**之前**必须强制调用。所有进入 design_artifact 的候选 mutation 必须带 ESM 评分字段，否则 review agent 拒收。

## 先检查环境
```bash
python -c "import torch, esm; print('ESM:', esm.__version__, 'torch:', torch.__version__)" 2>&1
# 缺则: pip install fair-esm  (或 conda install -c bioconda fair-esm)
# GPU 可选, CPU 也能跑 (慢约 10×)
```

## 输入契约
```json
{
  "sequence": "MKVLLAPVA...",          // wild-type 蛋白序列
  "mutations": [                        // 候选突变列表 (X123Y 格式)
    "L23A", "F87V", "Y289L", "T149I", ...
  ],
  "model": "esm1v_t33_650M_UR90S_1",   // 默认 esm1v 集成 5 个 random seed; 也可用 esm2_t36_3B_UR50D
  "use_msa": false,                     // ESM-MSA 需 MSA 输入, 默认关
  "device": "auto"                      // "cuda" / "mps" / "cpu" / "auto"
}
```

## 输出契约
```json
{
  "skill_id": "esm-mutation-scan",
  "wt_score": 0.0,
  "scan_csv": "",
  "top_mutations": [
    {
      "position": 1,
      "from_aa": "A",
      "to_aa": "V",
      "ddg": 0.0
    }
  ],
  "diagnostics": {
    "brain": "enzyme",
    "archetype": "mutation_scan"
  }
}
```

## 评分阈值（与既有规则联动）
- ESM-1v score ≥ +1.0: 高度推荐, PLM 显示该突变在进化上 favored
- +0.5 ≤ score < +1.0: 推荐, PLM tolerated
- -0.5 < score < +0.5: 中性, 需要其他证据辅助决策
- -2.0 < score ≤ -0.5: 弱不推荐, PLM 略 disprefer
- score ≤ -2.0: **强不推荐**, PLM 显著 disprefer
- score ≤ -2.5: **入 anti-retrieval veto 池**, 触发 anti-rule 10 (top-1 计算预测不验)

## 输入约束 (★ 强制)
- mutation 列表必须**先经 catalytic-site-annotator skill 过滤**, 排除催化残基 / 辅因子配位 / 二硫键 / 金属位 / 寡聚界面
- mutation 列表来源必须是结构 / 序列分析的实际位点, 不允许是 LLM 自由构造的位点
  - 合法来源: family alignment 保守 / 非保守差异位 (consensus mutation), CASTp / CAVER 识别的 pocket 残基, DSSP 识别的 loop 区, 已知 case 转移的同源位
  - 非法来源: "agent 觉得有意思的位点", "active site 附近随机 5 Å"

## 与上下游的衔接
- **上游必跑 (顺序敏感)**:
  1. `catalytic-site-annotator` → 得 excluded_positions
  2. `structural-context-analyzer` → 得 RSA + DSSP + depth
  3. `conservation-msa-analyzer` → 得 ConSurf score 与 family conservation
  4. **本 skill** → 得 ESM zero-shot score
- **下游 (在 ESM scoring 之后)**:
  - `pyrosetta-stability-scan` → 得 simulated ΔΔG (PyRosetta 缺则 simulated, 见 anti-rule 检查)
  - 可选 `pocket-tunnel-analyzer` → 当 substrate engineering 时
  - 写入 design_artifact, 字段 `evidence_chain` 必须包含 ESM score

## 失败模式与排查
| 现象 | 根因 | 解法 |
|---|---|---|
| `ImportError: fair-esm` | 未装 ESM | `pip install fair-esm`; CPU 也能跑 |
| GPU OOM on ESM-2 3B | 显存 < 12 GB | 退到 esm1v (650M) 或 esm2_t12_35M |
| 评分全部接近 0 | 序列太短 (< 30 aa) | ESM 短序列质量差, 跳过 PLM 评估 |
| 评分波动大 (5 seed std > 0.5) | 突变在低保守区 | 报 std 给 reporting agent, 标 "uncertain" |
| 长序列 (> 1024 aa) 跑不下来 | ESM-1v 长度上限 | 切片或换 ESM-2 (8K context) |

## 失败兜底 (★ 重要)
若 ESM 因任何原因不可用, 不允许直接跳过 — 必须明示:
```json
{
  "esm_status": "unavailable",
  "fallback_strategy": "Tranception" | "EVE" | "evolutionary_velocity" | "skip_with_warning",
  "warning": "PLM-based mutation scoring not performed; recommendation downgraded to confidence: low until PLM fallback succeeds"
}
```
**禁止**在 ESM 不可用时给 medium/high confidence 推荐.

## 与 Anti-rule 的关联
- 触发 anti-rule 10 (top-1 计算预测无实验验证) 当: ESM top-1 直接 ship 无 PyRosetta / 无 wetlab plan
- 触发 anti-rule 4 (AF + PyRosetta ddG 单跑) 当: ESM + PyRosetta 是仅有信号且基于 AF model 输入
- 与 anti-rule 2 (multi-mutation 加性) 联动: ESM 单点分数不可线性叠加用于 multi-mutation 候选

## 引用与出处
- Meier J, Rao R, Verkuil R, Liu J, Sercu T, Rives A. "Language models enable zero-shot prediction of the effects of mutations on protein function." NeurIPS 2021. doi: 10.1101/2021.07.09.450648
- Lin Z et al. "Evolutionary-scale prediction of atomic-level protein structure." Science 2023;379:1123-1130. doi: 10.1126/science.ade2574
- Su J et al. "SaProt: Protein Language Modeling with Structure-aware Vocabulary." ICLR 2024.

## Skill 版本
v1.0, 2026-04-29; 需要时同步 ESM-2 / ESM-3 后续版本.
