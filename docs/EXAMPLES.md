# PRAXIS-VirtualCell 示例

> 全部 `--mode offline`,**无需 API key**。展示治理裁决三档:accept / caution / abstain(verdict 均已实跑确认)。
> 数值口径:offline 用 mock/可用 predictor 走完整治理流;真 donor 数值在远端 A100。
> 说明:offline 的自然语言 `ask` 用确定性关键词解析(对全大写基因符号如 AHR 有效;对 Trp53/lacZ 这类混合大小写建议直接用结构化 `run --request`;llm_assisted 模式解析更强)。

## 例 1 — human 基因扰动 → accept

原生 scRNA predictor 适用,给预测。存 `ex1.json`:
```json
{"species": "human", "cell_type": "K562", "perturbation_type": "gene",
 "perturbation_targets": ["AHR"], "input_modality": "scRNA",
 "output_modality": "delta_expression", "task_type": "predict_delta_expression"}
```
```bash
praxis-vc run --request ex1.json --mode offline --out runs/ex1
```
**实测 verdict = accept**(reliability=high,3 predictor 参与);`runs/ex1/report.md` 9 段。
自然语言等价(全大写基因,offline 可解析):
```bash
praxis-vc ask --text "在 human K562 里敲掉 AHR 会怎么样" --mode offline --yes --out runs/ex1
```

## 例 2 — mouse 基因扰动 → caution(跨物种 ortholog)

human predictor 迁移到 mouse,适用但需 ortholog 投影,带告警。存 `ex2.json`:
```json
{"species": "mouse", "cell_type": "fibroblast", "perturbation_type": "gene",
 "perturbation_targets": ["Trp53"], "input_modality": "scRNA",
 "output_modality": "delta_expression", "task_type": "predict_delta_expression"}
```
```bash
praxis-vc run --request ex2.json --mode offline --out runs/ex2
```
**实测 verdict = caution**(caution_flags: ortholog_required + cross_species_uncertainty);报告 §8 Limitations 标注非 human 物种按降级解读。

## 例 3 — bacteria 基因 → 表达:abstain(治理正确弃权)

铁律:哺乳类 scRNA predictor **不适用**微生物表达 → 无适用引擎 → 系统弃权,不编造。存 `ex3.json`:
```json
{"species": "bacteria", "cell_type": "E. coli", "perturbation_type": "gene",
 "perturbation_targets": ["lacZ"], "input_modality": "scRNA",
 "output_modality": "delta_expression", "task_type": "predict_delta_expression"}
```
```bash
praxis-vc run --request ex3.json --mode offline --out runs/ex3
```
**实测 verdict = abstain**(reliability=low,0 predictor 参与);`report.md` §4 明确"已弃权,不产出预测数值",§8 列原因。**这正是卖点**——不适用就诚实拒绝,而非硬报假数值。

## 一键自检

```bash
bash deploy/vc/check_install.sh    # 跑 ahr_k562 offline demo,断言 report.md 生成
```

## 更多

- 更多物种×应用组合见 golden 用例:`praxis_virtualcell/tests/golden_cases/*.yaml`。
- 错输入/不适用的拒绝行为见:`praxis_virtualcell/tests/negative_cases/*.yaml`。
- 完整能力与输出说明见 [USER-GUIDE.md](USER-GUIDE.md)。
