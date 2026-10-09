# PRAXIS-VirtualCell v0.8 架构基线(冻结点)

> 冻结日期 2026-07-04 · tag `v0.8.0`(commit 7fc4aa5)· 升级起点。
> 详细复用映射见 `docs/superpowers/plans/2026-07-04-v0.9-v1.3-upgrade-roadmap.md`。

## 运行管线(core/runtime.py:46 run_workflow)

client → InputInterpreter → BioObjectNormalizer → SpeciesBrain → ModelApplicability
→ [LLMRouter 建议] → predictor fan-out → EnsembleCoordinator → Reliability → Critic
→ ProvenanceAgent → Report → [LLMCritic / LLMReport]

- 全程走 `MessageBus`(core/bus.py),记全量 trace 可 replay。
- 默认 mode=OFFLINE,llm_enabled=False,零 LLM token 可跑核心 case。

## 关键不变量(升级不得破坏)

1. 测试基线:`pytest praxis_virtualcell/tests` = 277 passed / 25 skipped / 0 failed。
2. LLM 边界:`assert_llm_boundaries` 三 flag(allow_llm_to_modify_core_decision /
   allow_llm_to_modify_prediction / allow_llm_to_override_hard_rules)恒 False。
3. 治理裁决:accept / caution / downgrade / abstain 四态(route_table.RouteDecision)。
4. KPI:golden unsafe-accept = 0;negative 无静默 accept。
5. offline 产 9 段 report.md(io/report_markdown.py),可复现。

## 4 物种 × 8 engine 现状

- 物种:human(原生)/ mouse(ortholog caution)/ yeast、bacteria(GEM 机制,scRNA abstain)。
- engine:donor_predictor / gem_fba / embedding / state_scoring / pathway_scoring /
  communication / spatial_niche / reject。
- 真实模型:E.coli iML1515、yeast iMM904(cobra-gated,真跑);LINCS 药物签名。
- mock / 远端:MockGEARS/MockCPA/MockLinear 本地 mock;GEARS/scGPT/Coordinator 远端 eval
  (@pytest.mark.remote,需 torch+GPU,本地 skip)。

## 继承包裹项(与虚拟细胞无关,永不维护)

- 整仓 `pytest` 会 collect ~1602(含根 tests/ 里 ~1398 个继承自 PRAXIS-2 的 Web/Auth/Admin
  框架测试,BASELINE.md 记录 14 个 pre-existing 失败)。这些是 bootstrap 时随 PRAXIS-2
  代码一起复制进来的历史包裹,与虚拟细胞科学核心无关。
- **决策(用户拍板 2026-07-04):这 ~1398 个继承测试永不纳入维护——不修、不迁移、不计入 CI
  绿勾口径、不计入 450+ 目标。升级全程只在 `praxis_virtualcell/tests` 内工作。**
