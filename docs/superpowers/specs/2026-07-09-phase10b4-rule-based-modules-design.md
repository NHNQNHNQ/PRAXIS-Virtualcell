# P10.B4 M1/M5/M8 rule-based advisory(膜系统/生物合成/降解 gene-set 激活)设计 spec

> P10.B 第四个"逐模块"单元。上游:roadmap `docs/superpowers/plans/2026-07-08-phase10-deep-validation-roadmap.md` §六.1(模型缺失→deterministic fallback,标 rule_based/evidence_limited,不伪装 full model)。与 B1/B2/B3 的引擎层 adapter 不同,本单元在**模块层**(module_plan)。

## 一、目标与诚实边界

M1(膜系统)/M5(生物合成)/M8(降解)是三个**零预测器模块**:`modules.py` 里 `engines:[]`,module_support.yaml 只有 tool 标签名,**无 gene-set 数据**;且 `module_rules.pick_primary` 纯按 (perturbation_object, target_output) 选模块,**从不选中 M1/M5/M8**——它们是"休眠的模块定义"。

本单元诚实做法(§六.1):建**公开策展 gene-set 数据** + 让模块层**按 gene-set 成员激活** M1/M5/M8 + 挂 **rule-based/evidence_limited advisory**。**不伪造数值 delta**(gene-set 成员只能给定性 advisory,数值预测=过度声称);预测仍归请求级引擎(如 gene→expression 的 donor_predictor)。做完后 M1/M5/M8 从"从不激活"→"相关基因时进 module_plan 并产结构化 advisory",达 G2"8/8 至少可运行 case"。

**架构定位**:module_plan 是 **advisory 产物**(经 provenance 透出),**非权威 abstain 裁决**(reliability 独立算 used predictors)。故本单元**不碰 reliability/critic/引擎/case_dispatch**,只扩 `module_rules`(激活)+ `module_router_agent`(entry advisory)+ 新增 gene-set 数据。

## 二、gene-set 数据(公开策展,真实基因符号)

新建 `praxis_virtualcell/data/module_gene_sets/{membrane_system,biosynthetic_network,degradation_machinery}.json`,每个含 `{"module": <code>, "source": "curated public (GO/Reactome-style)", "gene_set": [...symbols...]}`。策展代表性真实基因(小而真,非穷尽,大写符号):

- **M1 membrane_system**(脂质合成 + 转运体 + 膜结构):`FASN, SCD, SREBF1, SREBF2, HMGCR, ACACA, ELOVL6, DGAT1, SLC2A1, SLC7A5, SLC1A5, SLC3A2, SLC16A1, ATP1A1, ATP2A2, CAV1, FLOT1, ABCA1, ABCB1`
- **M5 biosynthetic_network**(核糖体 + UPR/折叠 + 翻译):`RPL5, RPL11, RPL23, RPS3, RPS6, RPS19, XBP1, ATF6, ERN1, HSPA5, EIF2AK3, DDIT3, HSP90AA1, CALR, EIF4E, EIF2S1, MTOR, PDIA3`
- **M8 degradation_machinery**(蛋白酶体 + 泛素 + 自噬 + 溶酶体):`PSMA1, PSMA5, PSMB5, PSMB6, PSMC1, PSMD1, UBB, UBC, UBA1, UBE2D1, ATG5, ATG7, ATG12, MAP1LC3B, SQSTM1, BECN1, ULK1, LAMP1, CTSB, CTSD`

匹配用 `str(target).strip().upper()` 归一后精确 `in` gene_set(与 B3 IFN-β 白名单同款精确匹配,防子串误命中)。基因可同时属多模块(激活多个)。

## 三、模块层组件

### 3.1 gene-set 加载(`praxis_virtualcell/biological_modules/module_gene_sets.py`,新建)
```python
def gene_set_of(module_code: str) -> frozenset[str]:  # 大写符号集,lazy 读 JSON 缓存
def modules_hit_by(targets: list[str]) -> list[str]:   # 返回 targets 命中的 module id(M1/M5/M8 子集)
```
确定性、零 LLM、缓存。

### 3.2 module_rules 激活(`agents/module_rules.py`)
`pick_secondary(req, primary)` 末尾并入 gene-set 激活(去重、排除 primary):
```python
    sec += module_gene_sets.modules_hit_by(req.get("perturbation_targets", []))
```
(即 gene-set 命中的 M1/M5/M8 作 secondary 加入;现有 M3 metabolic 逻辑不变。)

### 3.3 ModuleRouter entry advisory(`agents/module_router_agent.py::_build_entry`)
对 gene-set 激活的 M1/M5/M8 entry(可判 `mid ∈ {M1,M5,M8} 且 mid ∈ modules_hit_by(targets)`),挂诚实 advisory:
- `caution_flags` 追加 `["rule_based:<module>_gene_set", "evidence_limited"]`;
- entry 的 `route_disposition` 降为 `"downgrade"`(**非 accept**——不伪装定量预测;**非 reject**——不把整请求拖成 abstain);
- `reason` 追加 `"rule_based_gene_set_advisory"`。
其余字段(engine 复用 route()、species_support 等)不变。**不改 M1/M5/M8 的 modules.py engines(仍 [])、不改 route()**——advisory 纯在 entry 层叠加。

## 四、数据流

gene 扰动请求 → ModuleRouter：pick_primary(现状,如 gene→expression 得 M2)+ pick_secondary(现状 M3 + **新增 gene-set 命中的 M1/M5/M8**)→ 每 module _build_entry(M1/M5/M8 挂 rule_based/evidence_limited advisory)→ ModulePlan → 经既有 provenance.module_plan 透出到 structured_report。预测仍由引擎(donor_predictor 等)产,M1/M5/M8 零 delta。

## 五、影响

- **膜/生物合成/降解基因 expression 请求**(如 SLC2A1/RPS6/PSMB5):接入前 module_plan 只有 M2(primary);现**额外含 M1/M5/M8 secondary + rule_based/evidence_limited advisory**。预测数值不变(仍 donor)。
- **非 M1/M5/M8 基因**(如 TP53):module_plan 不含 M1/M5/M8(gene-set 不命中),行为不变。
- reliability_decision.abstain **不受影响**(module_plan 是 advisory;abstain 由 used predictors 独立算)。受影响既有 module_plan/golden 测试执行时定位;确认变化确由"gene-set 激活"引起才更新。

## 六、测试(T10.2 扩充 + module_plan)

- **gene-set 单元**:`modules_hit_by(["SLC2A1"])==["membrane_system"]`、`modules_hit_by(["PSMB5","TP53"])==["degradation_machinery"]`(TP53 不命中)、精确匹配(大小写归一,子串不误命中)。
- **module_rules**:`pick_secondary` 对膜基因请求含 M1;非命中基因不含。
- **端到端**:SLC2A1 expression → module_plan 含 M1 entry、caution_flags 含 `rule_based:membrane_system_gene_set`+`evidence_limited`、route_disposition=downgrade;prediction 仍来自 donor(mock),reliability.abstain 不变。
- **诚实红线**:M1/M5/M8 entry 无数值 delta;advisory 明确 rule_based/evidence_limited；非命中基因不激活;确定性(重跑字节稳)。
- **8/8 可运行验证**:三模块各至少一个基因请求使其进 module_plan 并产 advisory。

## 七、红线

- 不碰 reliability/critic/引擎/case_dispatch/route() 裁决逻辑;module_plan 是 advisory 非权威 abstain。
- M1/M5/M8 **绝不伪造数值预测**(gene-set 成员→定性 evidence_limited advisory,标注 rule_based)。
- gene-set 精确匹配(防子串误命中,B3 IFNB2/IL-6 教训)。
- 核心+根 tests/ 零触碰;不 push;trailer 恒 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。

## 八、完成标准

1. 三模块 gene-set 数据(公开策展真实基因符号)+ 加载器(确定性缓存)。
2. gene-set 命中 → M1/M5/M8 进 module_plan secondary + rule_based/evidence_limited advisory(downgrade,无 delta)。
3. 非命中基因不激活;reliability.abstain 不受影响;mock/donor 预测数值不变。
4. 受影响既有测试(module_plan/golden)更新为语义提升;全量回归 0 failed。
5. 确定性字节稳;ruff 全绿;台账勾账(M1/M5/M8 从 limitation→rule-based advisory 可运行);记忆更新。

## 九、Self-review 覆盖

- gene-set 全真实基因符号(FASN/SLC/RPL/RPS/XBP1/PSMA/PSMB/ATG 等公认),精确匹配防误命中。
- 架构定位准:module_plan advisory 层,不碰引擎/裁决;M1/M5/M8 零 delta 不伪造。
- 激活经 pick_secondary(现有机制扩展),entry advisory 经 _build_entry(现有机制叠加),不改 modules.py engines/route()。
- 未越界:不接 M2 远端;不碰 reliability/critic/provenance 裁决逻辑(只经既有 provenance.module_plan 透出)。
