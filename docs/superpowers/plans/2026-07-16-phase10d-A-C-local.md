# P10.D-A/D-C 本地部分 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 建 T10.3 后端端到端 16 case(全本地,实测真值断言)+ reports/phase10 三脚本与可本地生成的交付物,把 Phase 10 A-C4 已建成的能力封装成可复现证据。

**Architecture:** D-A 用 `run_query(request_dict, config=OFFLINE)` 驱动 16 个 e2e case(8 单模块 + 8 跨模块),断言全部来自**控制器实测的真实输出**(非 grounding agent 声称);诚实钉住三条 paper 级事实(advisory entry ≠ 预测、路由声明与引擎背离 X8、C1 gate NO-OP X6)。D-C 三脚本用 pytest 核心自带 `--junitxml` 实跑取数(禁誊抄台账),生成本地可出的五交付物。

**Tech Stack:** pytest(现有栈)、pytest `--junitxml`(核心自带,无新插件)。**不引入新依赖。**

**Spec:** `docs/superpowers/specs/2026-07-16-phase10d-delivery-completion-gate-design.md`(commit `9a2c6c6`,用户已批)

**基线:** main = HEAD = `9a2c6c6`,分支 `feat/v0.9-phase0-module-core`。稳定基线 `-m "not llm"` = **896 / 40 / 9 deselected / 0**;phase10 单跑 = **247**。

**本计划范围(用户 2026-07-16 收窄)**:只 D-A + D-C **本地部分**。**延后**:D-B 前端 playwright、S2b(M2 真实 GEARS `@remote`)、D-D 的 .53 远端亲验 + 独立 GATE.md sign-off、交付物 ⑥UI 截图。

---

## 全局约束(每 task 适用,不可破)

1. **测试口径显式**:`PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider`,**绝不裸跑 pytest**。稳定基线 `-m "not llm"`。**报数必标口径**(896 not-llm / 905 裸 / 247 phase10)。9 条 `@pytest.mark.llm` 网络挂时 FAIL 不 skip → 看退出码给假红。
2. **红线零触碰**:核心内核(`core/message.py`/`bus.py`/`agent.py`)+ 根 `tests/`;`agents/reliability.py`/`critic.py` 裁决逻辑与数值零改。
3. **前端 WIP 全程隔离**:`praxis_vc_react/src/styles/{base,fonts,themes,tokens}.css`(M)+ `.claude/`、`.playwright-mcp/`、`string.jpeg`(??)**绝不 stage/touch/revert**。每次 `git add` 只显式列本 task 文件,**禁 `git add -A`/`git add .`**。
4. **诚实不伪造**:断言用**实测真值**(本计划已内嵌);advisory entry 断路由标注非预测;X8 断背离、X6 断 NO-OP;summarize 实跑取数禁誊抄台账。实际与预期不符 → 先报告,不弱化断言凑绿。
5. **开工先 `git log --oneline -3` 确认 HEAD**;**绝不 `--amend`** 不属于本 task 的 commit。不 push。trailer 恒 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。
6. **核实每条声称含自己产出**(本 Phase 血泪 11 次+spec 阶段又证伪 grounding agent 假 bug):写测试前若某断言与实测不符,先报告。

---

## File Structure

| 文件 | 责任 | 动作 | Task |
|---|---|---|---|
| `praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py` | T10.3 16 case e2e + 共享 harness helper | Create | 1-4 |
| `scripts/phase10/run_phase10_all.py` | 全 phase10 编排 + `--junitxml` 两口径 | Modify(填骨架) | 5 |
| `scripts/phase10/summarize_phase10.py` | 读 junitxml → ①SUMMARY 主体 + ②8 模块表 + ④负例表 | Modify(填骨架) | 6 |
| `scripts/phase10/export_trace_bundle.py` | 对 16 case 请求集调 run_query → ⑤trace bundle | Modify(填骨架) | 7 |
| `reports/phase10/*.md` | 五交付物(②③④⑤ + ①主体) | 由脚本生成 + 提交 | 6-8 |

**不新建其它文件**(不建 benchmarks/*.yaml,spec §3 明列)。

---

## Task 1:D-A harness + 8 单模块 case(前 4 个:S1/S2/S3/S4)

**Files:** Create `praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py`

- [ ] **Step 1: 确认 HEAD**
```bash
cd /Volumes/T7/PRAXIS-virtualcell && git log --oneline -3
```
Expected: HEAD = `9a2c6c6`(D spec commit)。

- [ ] **Step 2: 写文件头 + harness + S1-S4(TDD:先写,这些是新测试,直接对真实管线断言)**

创建 `praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py`:

```python
"""P10.D T10.3 端到端 16 case —— 8 单模块 + 8 跨模块,走完整管线 run_query。

**harness = run_query(request_dict)**(非 run_full_query(text)):spec §2.1 —— OFFLINE 确定性
解析无法设 output_modality,只能路由 gene→expression;故 16 case 用 request_dict 驱动。

**断言全部来自控制器实测的真实 run_query 输出**(非 grounding agent 声称;spec 阶段已证伪
agent 一条假 bug)。三条 paper 级诚实事实钉死:
1. M1/M5/M8 rule-based advisory:基因集成员 OOV → 请求自身 abstain,断言是 module_plan
   **secondary advisory entry**(caution_flags rule_based:*+evidence_limited, downgrade)
   **不是**非 abstain 预测(spec §2.2)。
2. module_plan.overall_verdict 是**路由级声明**,可与引擎实际执行**背离**——X8:overall=='accept'
   YET abstain==True。断言同时断两者,把背离文档化(spec §2.2)。
3. C1 跨模块一致性 gate 自然输入**从不触发**:cross_module_consistency 键在一致 plan 上缺席;
   gate 触发只能 monkeypatch(先例 test_t10_5)。X6 断 NO-OP,不声称自然触发(spec §2.2)。

**只有 S2b(M2 真实 GEARS)需 .53**,本计划延后;此文件的 16 core case 全本地。
"""
import json

import pytest

from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.workflows.run_virtualcell_query import run_query

_CFG = RuntimeConfig(mode=Mode.OFFLINE)
_BASE = {"input_modality": "scRNA", "task_type": "predict_delta_expression"}


def _req(species, ptype, targets, out="delta_expression"):
    return {**_BASE, "species": species, "perturbation_type": ptype,
            "perturbation_targets": targets, "output_modality": out}


def _run(req):
    """跑完整管线,返回 (structured_report, provenance, module_plan, out)。"""
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    mp = out["provenance"].get("module_plan")
    return sr, out["provenance"], mp, out


def _entry(mp, module):
    """取 module_plan 里某模块的 entry(找不到返 None)。"""
    for e in (mp or {}).get("entries", []):
        if e.get("module") == module:
            return e
    return None


# ============ 8 单模块 ============

def test_S1_M1_membrane_advisory():
    """M1 膜系统 rule-based advisory:human gene FASN(∈膜基因集,mock OOV)。
    实测:请求自身 abstain(learned_abstain),primary genetic_hub verdict=accept,
    membrane_system 作 secondary advisory downgrade,overall downgrade。
    **断言的是 advisory entry 不是预测**(FASN OOV → prediction None)。"""
    sr, prov, mp, out = _run(_req("human", "gene", ["FASN"]))
    assert sr["abstain"] is True
    assert "learned_abstain_low_reliability" in sr["abstain_reasons"]
    assert sr["prediction"] is None
    assert mp["primary"] == "genetic_hub"
    assert "membrane_system" in mp["secondary"]
    e = _entry(mp, "membrane_system")
    assert e["role"] == "secondary" and e["verdict"] == "downgrade"
    assert "rule_based:membrane_system_gene_set" in e["caution_flags"]
    assert "evidence_limited" in e["caution_flags"]
    assert mp["overall_verdict"] == "downgrade"
    assert out["llm_used_for_prediction"] is False


def test_S2_M2_genetic_hub_mock_accept():
    """M2 基因枢纽 mock donor accept:human gene AHR(in-vocab)。
    实测:abstain=False, reliability=high, models_used 三 Mock*, prediction {'delta':[0.3]},
    primary genetic_hub donor_predictor accept, secondary 空。(.53 真实 GEARS 变体 S2b 延后)"""
    sr, prov, mp, out = _run(_req("human", "gene", ["AHR"]))
    assert sr["abstain"] is False
    assert sr["reliability"] == "high"
    assert sr["models_used"] == ["MockLinear", "MockCPA", "MockGEARS"]
    assert sr["prediction"] == {"delta": [0.3]}
    assert mp["primary"] == "genetic_hub" and mp["secondary"] == []
    e = _entry(mp, "genetic_hub")
    assert e["engine"] == "donor_predictor" and e["verdict"] == "accept"
    assert mp["overall_verdict"] == "accept"
    assert out["llm_used_for_prediction"] is False


def test_S3_M3_mito_secondary_downgrade():
    """M3 线粒体能量:从不是 primary,只作 mammalian growth 的 secondary。
    human gene MYC growth。实测:primary cytoplasmic_metabolism verdict=downgrade
    (mammalian growth GEM 未 wire → CaseRunner rejected → abstain),M3 secondary downgrade。"""
    sr, prov, mp, out = _run(_req("human", "gene", ["MYC"], "growth"))
    assert sr["abstain"] is True
    assert "CaseRunner" in sr["models_rejected"]
    assert sr["prediction"] is None
    assert mp["primary"] == "cytoplasmic_metabolism"
    assert "mitochondrial_energy_metabolism" in mp["secondary"]
    e = _entry(mp, "mitochondrial_energy_metabolism")
    assert e["role"] == "secondary" and e["engine"] == "gem_fba" and e["verdict"] == "downgrade"
    assert mp["overall_verdict"] == "downgrade"


def test_S4_M4_cobra_fba_accept():
    """M4 胞质代谢真 cobra FBA:bacteria gene [b0720 gltA, b1136 icd] growth(双 essential)。
    实测:abstain=False, reliability=medium, models_used [CaseRunner], prediction {'delta':[-1.0,-1.0]}
    (双 essential → ratio 0 → delta -1.0), gem_fba accept。真实机制模型,非 mock。"""
    sr, prov, mp, out = _run(_req("bacteria", "gene", ["b0720", "b1136"], "growth"))
    assert sr["abstain"] is False
    assert sr["reliability"] == "medium"
    assert sr["models_used"] == ["CaseRunner"]
    assert sr["prediction"] == {"delta": [-1.0, -1.0]}
    assert mp["primary"] == "cytoplasmic_metabolism"
    e = _entry(mp, "cytoplasmic_metabolism")
    assert e["engine"] == "gem_fba" and e["verdict"] == "accept"
    assert mp["overall_verdict"] == "accept"
    assert out["llm_used_for_prediction"] is False
```

- [ ] **Step 3: 跑,确认全绿(这些断言即真实管线输出)**
```bash
PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py -p no:cacheprovider -v 2>&1 | tail -12
```
Expected: `test_S1..test_S4` **4 passed**。
**⚠️ 这些是"钉真实行为"的测试,不走 red-first(它们对既有管线断言,管线已存在)。** 若某条**红** → 说明实测真值与本计划内嵌值不符 → **停,报告实际输出**(不改断言凑绿,先查是不是管线被别的改动动过)。

- [ ] **Step 4: 变异证伪(证明断言有牙,非空壳)**

临时把 S4 的 `_req("bacteria",...)` 改成 `_req("human",...)`(human gene growth → 走 S3 的 abstain 路径),跑 `-k S4`:
```bash
PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py::test_S4_M4_cobra_fba_accept -p no:cacheprovider 2>&1 | tail -3
```
Expected: **FAIL**(human 走不到 cobra accept → abstain,`assert sr["abstain"] is False` 红)。**改回 bacteria**,重跑确认绿。

- [ ] **Step 5: Commit**
```bash
git add praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py
git commit -F - <<'EOF'
test(phase10d): Task 1 T10.3 harness + S1-S4 单模块 e2e —— 实测真值断言

run_query(request_dict) 驱动(spec §2.1:run_full_query 解析不出 output_modality)。
S1 M1 膜系统 rule-based advisory(FASN OOV→请求 abstain,断 secondary advisory entry 非预测);
S2 M2 genetic_hub mock accept(AHR in-vocab, prediction {'delta':[0.3]});
S3 M3 从不 primary 只作 growth secondary downgrade;
S4 M4 真 cobra FBA(b0720/b1136 双 essential, prediction {'delta':[-1.0,-1.0]})。
断言全部控制器实测真值,非 grounding agent 声称。变异证伪 S4(human→abstain)有牙。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
git show --stat HEAD
```
Expected: 只有 1 个测试文件。无前端 WIP。

---

## Task 2:8 单模块 case 后 4 个(S5/S6/S7/S8)

**Files:** Modify `praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py`

- [ ] **Step 1: 确认 HEAD** = Task 1 commit(`git log --oneline -3`)。

- [ ] **Step 2: 追加 S5-S8**

追加到测试文件末尾:

```python
def test_S5_M5_biosynthetic_advisory():
    """M5 生物合成 rule-based advisory:human gene RPL5(∈生物合成基因集,OOV)。
    实测同 S1 形状:请求 abstain,primary genetic_hub accept,biosynthetic_network secondary
    advisory downgrade,overall downgrade。断 advisory entry 非预测。"""
    sr, prov, mp, out = _run(_req("human", "gene", ["RPL5"]))
    assert sr["abstain"] is True
    assert sr["prediction"] is None
    assert mp["primary"] == "genetic_hub"
    assert "biosynthetic_network" in mp["secondary"]
    e = _entry(mp, "biosynthetic_network")
    assert e["verdict"] == "downgrade"
    assert "rule_based:biosynthetic_network_gene_set" in e["caution_flags"]
    assert "evidence_limited" in e["caution_flags"]
    assert mp["overall_verdict"] == "downgrade"


def test_S6_M6_spatial_niche_pipeline_limitation():
    """M6 细胞骨架/spatial_niche:管线**完全不可达**(∉ REAL_ENGINES ∉ dispatch_runner,
    _is_routable 门掉 medium 请求 → applicable 空)。诚实 limitation:
    human medium stromal_niche state → module_plan is None + abstain。
    (引擎级真值另在 tests/test_spatial_niche_case.py cohens_d~0.74,非本管线 case。)"""
    sr, prov, mp, out = _run(_req("human", "medium", ["stromal_niche"], "state"))
    assert sr["abstain"] is True
    assert mp is None                      # 管线不可达 = module_plan None
    assert sr["prediction"] is None
    assert sr["models_used"] == []


def test_S7_M7_state_scoring_accept():
    """M7 应激处理器真 state_scoring:human ligand IFNB1 state(Kang 2018 ISG)。
    实测:abstain=False, reliability=medium, models_used [CaseRunner], prediction {'delta':[2.485]}
    (ISG 强激活 cohens_d~2.5 映射), state_scoring accept。真实机制,非 mock。"""
    sr, prov, mp, out = _run(_req("human", "ligand", ["IFNB1"], "state"))
    assert sr["abstain"] is False
    assert sr["reliability"] == "medium"
    assert sr["models_used"] == ["CaseRunner"]
    assert sr["prediction"] == {"delta": [2.485]}
    assert mp["primary"] == "stress_processor"
    e = _entry(mp, "stress_processor")
    assert e["engine"] == "state_scoring" and e["verdict"] == "accept"
    assert mp["overall_verdict"] == "accept"


def test_S8_M8_degradation_advisory_mismatch():
    """M8 降解机器 rule-based advisory + 物种 mismatch:bacteria gene UBB growth。
    实测:primary cytoplasmic_metabolism(gem_fba)accept,degradation_machinery secondary
    verdict=downgrade **且 mismatch=='caution'**(bacteria_autophagy:原核无真核自噬),
    请求 abstain(UBB 非真实 E.coli 位点)。"""
    sr, prov, mp, out = _run(_req("bacteria", "gene", ["UBB"], "growth"))
    assert sr["abstain"] is True
    assert mp["primary"] == "cytoplasmic_metabolism"
    assert "degradation_machinery" in mp["secondary"]
    e = _entry(mp, "degradation_machinery")
    assert e["verdict"] == "downgrade"
    assert e["mismatch"] == "caution"
    assert "rule_based:degradation_machinery_gene_set" in e["caution_flags"]
    assert mp["overall_verdict"] == "downgrade"
```

- [ ] **Step 3: 跑 S5-S8 确认绿**
```bash
PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py -p no:cacheprovider -k "S5 or S6 or S7 or S8" -v 2>&1 | tail -8
```
Expected: **4 passed**。红 → 停报告实际输出。

- [ ] **Step 4: 变异证伪 S6(limitation 有牙)**

临时把 S6 的 `assert mp is None` 改成 `assert mp is not None`,跑 `-k S6` → 必须 **FAIL**(证明真断 module_plan None)。改回。

- [ ] **Step 5: Commit**
```bash
git add praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py
git commit -F - <<'EOF'
test(phase10d): Task 2 S5-S8 单模块 e2e —— advisory/limitation/mismatch 诚实断言

S5 M5 生物合成 advisory(RPL5 OOV);S6 M6 spatial_niche 管线 limitation(module_plan None,
诚实标不可达,引擎级真值另在 test_spatial_niche_case);S7 M7 state_scoring 真实 accept
(IFNB1 prediction {'delta':[2.485]});S8 M8 degradation advisory + 物种 mismatch=='caution'。
实测真值断言。变异证伪 S6(mp None)有牙。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
git show --stat HEAD
```

---

## Task 3:8 跨模块 case 前 4 个(X1/X2/X3/X4)

**Files:** Modify `praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py`

- [ ] **Step 1: 确认 HEAD** = Task 2 commit。

- [ ] **Step 2: 追加 X1-X4**

```python
# ============ 8 跨模块 ============

def test_X1_M4_M3_flux_positive():
    """跨模块正例:human ligand IFNB1 flux → primary cytoplasmic_metabolism + secondary
    mitochondrial_energy_metabolism,**均 pathway_scoring caution**,真实 prediction
    {'delta':[0.101,0.281]}(IFN 弱代谢信号 |d|<0.8), abstain=False。旗舰跨模块正例。"""
    sr, prov, mp, out = _run(_req("human", "ligand", ["IFNB1"], "flux"))
    assert sr["abstain"] is False
    assert sr["models_used"] == ["CaseRunner"]
    assert sr["prediction"] == {"delta": [0.101, 0.281]}
    assert mp["primary"] == "cytoplasmic_metabolism"
    assert mp["secondary"] == ["mitochondrial_energy_metabolism"]
    for m in ("cytoplasmic_metabolism", "mitochondrial_energy_metabolism"):
        e = _entry(mp, m)
        assert e["engine"] == "pathway_scoring" and e["verdict"] == "caution"
    assert mp["overall_verdict"] == "caution"


def test_X2_M4_M3_growth_negative_abstain():
    """跨模块应 abstain 负例:human gene_combination [MYC,KRAS] growth → 2-entry 均 downgrade,
    abstain(mammalian growth GEM 未 wire), prediction None。"""
    sr, prov, mp, out = _run(_req("human", "gene_combination", ["MYC", "KRAS"], "growth"))
    assert sr["abstain"] is True
    assert "CaseRunner" in sr["models_rejected"]
    assert sr["prediction"] is None
    assert mp["primary"] == "cytoplasmic_metabolism"
    assert mp["secondary"] == ["mitochondrial_energy_metabolism"]
    for m in ("cytoplasmic_metabolism", "mitochondrial_energy_metabolism"):
        assert _entry(mp, m)["verdict"] == "downgrade"
    assert mp["overall_verdict"] == "downgrade"


def test_X3_quad_four_module_advisory():
    """最富 module_plan(4 entry):human gene [SLC2A1,RPL5,PSMB5] 一次命中 3 个基因集 →
    primary genetic_hub + 3 advisory secondary(membrane/biosynthetic/degradation,MODULE_ORDER 序),
    全 downgrade,请求 abstain(全 OOV)。"""
    sr, prov, mp, out = _run(_req("human", "gene", ["SLC2A1", "RPL5", "PSMB5"]))
    assert sr["abstain"] is True
    assert sr["prediction"] is None
    assert mp["primary"] == "genetic_hub"
    assert mp["secondary"] == ["membrane_system", "biosynthetic_network", "degradation_machinery"]
    assert len(mp["entries"]) == 4
    for m in ("membrane_system", "biosynthetic_network", "degradation_machinery"):
        e = _entry(mp, m)
        assert e["verdict"] == "downgrade"
        assert f"rule_based:{m}_gene_set" in e["caution_flags"]
        assert "evidence_limited" in e["caution_flags"]
    assert mp["overall_verdict"] == "downgrade"


def test_X4_M4_M8_bacteria_mismatch():
    """跨模块 + 物种 mismatch:bacteria gene UBB growth → M4 primary(gem_fba)+ M8 secondary
    携 mismatch=='caution'(bacteria 无真核自噬),abstain。跨模块与 mismatch 治理同 plan。"""
    sr, prov, mp, out = _run(_req("bacteria", "gene", ["UBB"], "growth"))
    assert sr["abstain"] is True
    assert mp["primary"] == "cytoplasmic_metabolism"
    assert _entry(mp, "cytoplasmic_metabolism")["engine"] == "gem_fba"
    assert "degradation_machinery" in mp["secondary"]
    e = _entry(mp, "degradation_machinery")
    assert e["mismatch"] == "caution"
    assert "rule_based:degradation_machinery_gene_set" in e["caution_flags"]
    assert mp["overall_verdict"] == "downgrade"
```

- [ ] **Step 3: 跑 X1-X4 绿**
```bash
PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py -p no:cacheprovider -k "X1 or X2 or X3 or X4" -v 2>&1 | tail -8
```
Expected: **4 passed**。红 → 停报告。

- [ ] **Step 4: 变异证伪 X1(跨模块正例有牙)**

临时把 X1 的 `assert sr["prediction"] == {"delta": [0.101, 0.281]}` 改成 `== {"delta": [9.9, 9.9]}` → 必须 **FAIL**。改回。(证明断的是真实数值非任意。)

- [ ] **Step 5: Commit**
```bash
git add praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py
git commit -F - <<'EOF'
test(phase10d): Task 3 X1-X4 跨模块 e2e —— 正例/负例/四模块/物种mismatch

X1 M4+M3 flux 正例(真实 prediction {'delta':[0.101,0.281]});X2 M4+M3 growth 应 abstain 负例;
X3 四模块 advisory(3 基因集命中,MODULE_ORDER 序);X4 M4+M8 bacteria mismatch=='caution'。
实测真值。变异证伪 X1 数值有牙。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
git show --stat HEAD
```

---

## Task 4:8 跨模块 case 后 4 个(X5/X6/X7/X8)—— 含两条 paper 级诚实事实

**Files:** Modify `praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py`

- [ ] **Step 1: 确认 HEAD** = Task 3 commit。

- [ ] **Step 2: 追加 X5-X8(X6 断 C1 NO-OP + 确定性,X8 断路由/引擎背离)**

```python
def test_X5_negative_transfer_unroutable():
    """负迁移 unroutable:bacteria gene b0720 **expression**(哺乳 scRNA 预测器禁用于 bacteria)→
    abstain,all mock rejected,**module_plan is None**(不可路由,无 plan)。最干净的
    应 abstain 且不产 plan 的负例。"""
    sr, prov, mp, out = _run(_req("bacteria", "gene", ["b0720"]))
    assert sr["abstain"] is True
    assert "all_predictors_rejected" in sr["abstain_reasons"]
    assert sr["models_used"] == []
    assert set(sr["models_rejected"]) == {"MockLinear", "MockCPA", "MockGEARS"}
    assert mp is None
    assert sr["prediction"] is None


def test_X6_C1_gate_noop_and_deterministic():
    """**C1 跨模块一致性 gate 在自然输入上从不触发**(spec §2.2 paper 级事实):
    human gene MYC growth 是真 2-entry plan(gate 的检查对象),但 check_module_plan 返 []
    → provenance **无 cross_module_consistency 键**。且同请求 3 跑 structured_report 字节等价。
    **NOTE:gate 触发只能 monkeypatch runtime.check_module_plan(先例 test_t10_5),
    不可由任何自然请求达成 —— 不声称自然触发。**"""
    req = _req("human", "gene", ["MYC"], "growth")
    sr, prov, mp, out = _run(req)
    assert "cross_module_consistency" not in prov          # gate NO-OP:plan 内部一致
    assert mp["primary"] == "cytoplasmic_metabolism"       # 真 ≥2-entry plan(gate 的检查对象)
    assert mp["secondary"] == ["mitochondrial_energy_metabolism"]
    assert out["llm_used_for_prediction"] is False
    # 确定性:3 跑 structured_report canonical 一致
    hashes = {json.dumps(_run(req)[0], sort_keys=True, default=str) for _ in range(3)}
    assert len(hashes) == 1


def test_X7_M2_cross_species_ortholog_caution():
    """M2 跨物种:mouse gene GATA1 → genetic_hub primary caution(ortholog_required),
    仍产 mock prediction {'delta':[0.3]}, abstain=False。跨物种路由聚光。"""
    sr, prov, mp, out = _run(_req("mouse", "gene", ["GATA1"]))
    assert sr["abstain"] is False
    assert sr["reliability"] == "high"
    assert sr["prediction"] == {"delta": [0.3]}
    assert mp["primary"] == "genetic_hub"
    e = _entry(mp, "genetic_hub")
    assert e["verdict"] == "caution" and "ortholog_required" in e["caution_flags"]
    assert mp["overall_verdict"] == "caution"


def test_X8_route_declaration_diverges_from_engine():
    """**路由声明与引擎实际背离**(spec §2.2 paper 级事实,最重要的诚实 case):
    human gene SNAI1 state → module_plan overall_verdict=='accept'(路由层声明)
    **YET** structured_report.abstain==True(引擎层:state_scoring 只 wire IFN-β ligand,
    gene→state 走 UnsupportedEngine → CaseRunner rejected)。**同时断两者,把背离文档化**——
    module_plan.overall_verdict 是 ROUTE-level 声明,不等于引擎实际执行。"""
    sr, prov, mp, out = _run(_req("human", "gene", ["SNAI1"], "state"))
    # 路由层:声明 accept
    assert mp["primary"] == "stress_processor"
    e = _entry(mp, "stress_processor")
    assert e["engine"] == "state_scoring" and e["verdict"] == "accept"
    assert mp["overall_verdict"] == "accept"
    # 引擎层:实际 abstain(背离)
    assert sr["abstain"] is True
    assert "CaseRunner" in sr["models_rejected"]
    assert sr["models_used"] == []
    assert sr["prediction"] is None
```

- [ ] **Step 3: 跑 X5-X8 + 全文件绿**
```bash
PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py -p no:cacheprovider -v 2>&1 | tail -20
```
Expected: **16 passed**(S1-S8 + X1-X8)。红 → 停报告。

- [ ] **Step 4: 变异证伪 X8(背离断言有牙 —— 两侧各变异一次)**
- 变异 A:把 X8 的 `assert sr["abstain"] is True` 改成 `is False` → 必须 **FAIL**(证明真断引擎 abstain)。改回。
- 变异 B:把 `assert mp["overall_verdict"] == "accept"` 改成 `== "downgrade"` → 必须 **FAIL**(证明真断路由声明 accept)。改回。
**两侧都红 = 背离被真正钉住**(不是只断一边)。

- [ ] **Step 5: 全量回归**
```bash
PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider -m "not llm" 2>&1 | tail -3
```
Expected: `912 passed, 40 skipped, 9 deselected, 0 failed`(896 + 16 新 case)。**以实际为准**;既有测试变红 → 停报告(不改既有测试凑绿)。

- [ ] **Step 6: Commit**
```bash
git add praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py
git commit -F - <<'EOF'
test(phase10d): Task 4 X5-X8 跨模块 e2e —— 负迁移/C1 gate NO-OP/跨物种/路由引擎背离

X5 负迁移 unroutable(module_plan None);X6 **C1 gate 自然输入从不触发**(cross_module_consistency
键缺席 + 3 跑确定性,gate 触发只能 monkeypatch 不声称自然触发);X7 M2 跨物种 ortholog caution;
X8 **路由声明 accept 与引擎 abstain 背离**(paper 级诚实,两侧各变异证伪有牙)。
T10.3 16 case 全绿;全量 -m "not llm" 896→912。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
git show --stat HEAD
```

---

## Task 5:run_phase10_all.py —— 全 phase10 编排 + junitxml 两口径

**Files:** Modify `scripts/phase10/run_phase10_all.py`

- [ ] **Step 1: 确认 HEAD** = Task 4 commit。

- [ ] **Step 2: 实现编排(两口径 + junitxml,显式标口径)**

替换 `scripts/phase10/run_phase10_all.py` 全文:

```python
"""Phase 10 全量测试编排 —— 两口径 + junitxml(pytest 核心自带,无新插件)。

产出 reports/phase10/junit-not-llm.xml + junit-full.xml 供 summarize 消费。
**口径纪律(UPGRADE-PROGRESS 血泪)**:稳定基线 -m "not llm";裸口径含 9 条 @pytest.mark.llm
真实网络测试(网络挂时 FAIL 不 skip → 看退出码给假红)。两口径都跑、都存、都显式标注。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_OUT = _REPO / "reports" / "phase10"
_TESTS = "praxis_virtualcell/tests"


def _run(junit_name: str, extra_args: list[str]) -> int:
    _OUT.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "pytest", _TESTS, "-p", "no:cacheprovider",
           f"--junitxml={_OUT / junit_name}", *extra_args]
    print(f"[run_phase10_all] {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd, cwd=_REPO)


def main() -> int:
    # 口径 1:稳定基线(-m "not llm")—— 完成门槛的权威口径
    rc1 = _run("junit-not-llm.xml", ["-m", "not llm"])
    # 口径 2:裸口径(含 llm 真实网络测试)—— 如实标口径,网络挂时可能红
    rc2 = _run("junit-full.xml", [])
    print(f"[run_phase10_all] not-llm rc={rc1}  full(含llm网络) rc={rc2}", flush=True)
    # 稳定基线必须绿;裸口径红可能是网络(summarize 会按测试名区分)
    return rc1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: 跑脚本,确认产出 junitxml**
```bash
cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python scripts/phase10/run_phase10_all.py 2>&1 | tail -5
ls -la reports/phase10/junit-*.xml
```
Expected: 两个 junit xml 生成;not-llm 口径 `912 passed`。

- [ ] **Step 4: 核实 junitxml 可解析(summarize 前置)**
```bash
PYTHONPATH=$PWD .venv/bin/python -c "
import xml.etree.ElementTree as ET
for f in ['reports/phase10/junit-not-llm.xml']:
    ts = ET.parse(f).getroot()
    suite = ts if ts.tag=='testsuite' else ts.find('testsuite')
    print(f, 'tests=', suite.get('tests'), 'failures=', suite.get('failures'), 'skipped=', suite.get('skipped'))
"
```
Expected: tests/failures/skipped 数值出来,failures=0。

- [ ] **Step 5: Commit(junit xml 是否入库?—— 不入库,gitignore 或只提交脚本)**

先确认 junit xml 是否该忽略:
```bash
grep -n "junit\|reports/phase10" .gitignore 2>/dev/null || echo "(未忽略)"
```
若未忽略,在 `.gitignore` 加 `reports/phase10/junit-*.xml`(生成物不入库,同 dist)。然后:
```bash
git add scripts/phase10/run_phase10_all.py .gitignore
git commit -F - <<'EOF'
feat(phase10d): Task 5 run_phase10_all —— 全 phase10 编排 + junitxml 两口径

pytest 核心自带 --junitxml(无新插件)产 reports/phase10/junit-{not-llm,full}.xml 供
summarize 消费。两口径都跑都存(not-llm 稳定基线权威 + 裸口径含 llm 网络如实标)。
junit xml 生成物 gitignore 不入库(同 dist)。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
git show --stat HEAD
```

---

## Task 6:summarize_phase10.py —— ①SUMMARY 主体 + ②8 模块表 + ④负例表(实跑取数)

**Files:** Modify `scripts/phase10/summarize_phase10.py`;生成 `reports/phase10/{PHASE10_SUMMARY,PHASE10_FAILURES}.md`

- [ ] **Step 1: 确认 HEAD** = Task 5 commit。

- [ ] **Step 2: 实现 summarize(读 junitxml + MODULE_ORDER,禁誊抄台账)**

替换 `scripts/phase10/summarize_phase10.py` 全文:

```python
"""Phase 10 SUMMARY 生成 —— 实跑 junitxml 取数 + MODULE_ORDER,禁誊抄台账。

数据源:reports/phase10/junit-*.xml(Task 5 产)+ biological_modules/modules.py::MODULE_ORDER。
**口径纪律**:所有测试数须来自实跑 junitxml,显式标口径(not-llm 稳定基线 vs 裸口径);
禁止从 UPGRADE-PROGRESS 誊抄(858 是误记孤例)。
**诚实纪律(spec §8)**:8 模块状态须带 advisory(M1/M5/M8)/remote(M2)/limitation(M6/emt/fate)
限定词,不得写"8/8 真实模型"。
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from praxis_virtualcell.biological_modules.modules import MODULE_ORDER

_REPO = Path(__file__).resolve().parents[2]
_OUT = _REPO / "reports" / "phase10"

# 8 模块真实覆盖状态(源:UPGRADE-PROGRESS 定论 + spec §2.2 实测,非誊抄数字,是能力定性)
_MODULE_STATUS = {
    "membrane_system": "rule-based advisory(B4;基因集 OOV→请求 abstain,断 module_plan advisory entry)",
    "genetic_hub": "引擎级:mock donor(本地)/ 真实 GEARS(仅 .53,gears_available 门控)",
    "mitochondrial_energy_metabolism": "引擎级 gem_fba/pathway_scoring;**从不 primary**,只作 growth/flux secondary",
    "cytoplasmic_metabolism": "引擎级真实 cobra FBA(gem_fba)+ pathway_scoring",
    "biosynthetic_network": "rule-based advisory(B4)",
    "cytoskeletal_framework": "诚实 limitation:spatial_niche 管线不可达(引擎级另有真值)",
    "stress_processor": "引擎级真实 state_scoring(IFN-β)/ embedding(drug),窄门",
    "degradation_machinery": "rule-based advisory(B4)+ 物种 mismatch 治理",
}


def _parse_junit(path: Path) -> dict:
    if not path.exists():
        return {"tests": "N/A", "failures": "N/A", "skipped": "N/A", "errors": "N/A"}
    root = ET.parse(path).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    return {k: suite.get(k, "0") for k in ("tests", "failures", "skipped", "errors")}


def _summary_md() -> str:
    not_llm = _parse_junit(_OUT / "junit-not-llm.xml")
    full = _parse_junit(_OUT / "junit-full.xml")
    lines = [
        "# PHASE 10 SUMMARY",
        "",
        "> 本文件由 `scripts/phase10/summarize_phase10.py` 实跑 junitxml 生成,**禁誊抄台账数字**。",
        "> **完整能力边界、门槛对账、收窄项以 spec §0/§2.3/§8 为准**——本文件只做实测计数汇总。",
        "",
        "## 1. 测试计数(实跑 junitxml,显式标口径)",
        "",
        "| 口径 | tests | failures | skipped | 说明 |",
        "|---|---|---|---|---|",
        f"| `-m \"not llm\"` 稳定基线(**完成门槛权威口径**) | {not_llm['tests']} | {not_llm['failures']} | {not_llm['skipped']} | 9 条 llm deselect |",
        f"| 裸口径(含 9 条 `@pytest.mark.llm` 真实网络) | {full['tests']} | {full['failures']} | {full['skipped']} | 网络挂时 llm FAIL 不 skip→看退出码给假红 |",
        "",
        "## 2. 8 模块覆盖状态(诚实限定,**非 8/8 真实模型**)",
        "",
        "| 模块 | 覆盖状态 |",
        "|---|---|",
    ]
    for mid in MODULE_ORDER:
        code = mid if isinstance(mid, str) else mid.get("code", str(mid))
        lines.append(f"| `{code}` | {_MODULE_STATUS.get(code, '(未定义)')} |")
    lines += [
        "",
        "> **真实引擎级覆盖仅 4 族**:M2(.53)/M3/M4/M7。M1/M5/M8=rule-based advisory;",
        "> M6/emt/fate/spatial/communication=诚实 limitation。这不是 SOTA 预测模型,是**代码治理操作层**。",
        "",
        "## 3. 门槛对账 + 失败与修复叙事",
        "",
        "> **门槛 13 指标对账 + C1-C4 失败→修复叙事以 spec §2.3 + UPGRADE-PROGRESS 事件日志为准**",
        "> (含 C4 的 11 次过度声称、2 个新挖 500)。收窄项(conflict detection / LLM unsupported claim=0)",
        "> **绝不打绿**——见 spec §8。",
        "",
        "## 4. UI e2e / 16-case 明细",
        "",
        "> UI 段依赖 D-B(前端 playwright,延后);16-case 明细见 `PHASE10_TRACE_AUDIT.md` 与",
        "> `test_t10_3_end_to_end_cases.py`。",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    _OUT.mkdir(parents=True, exist_ok=True)
    (_OUT / "PHASE10_SUMMARY.md").write_text(_summary_md(), encoding="utf-8")
    print(f"[summarize] wrote {_OUT / 'PHASE10_SUMMARY.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: 跑 summarize(需先有 junitxml),核实产出**
```bash
cd /Volumes/T7/PRAXIS-virtualcell
PYTHONPATH=$PWD .venv/bin/python scripts/phase10/run_phase10_all.py >/dev/null 2>&1
PYTHONPATH=$PWD .venv/bin/python scripts/phase10/summarize_phase10.py
echo "--- SUMMARY 计数段 ---"
sed -n '/## 1. 测试计数/,/## 2./p' reports/phase10/PHASE10_SUMMARY.md
```
Expected: SUMMARY.md 生成;计数段 not-llm failures=**0**,tests/skipped **以 junitxml 实测为准**(**不预设硬编码总数** —— 本 Phase 教训:报数别猜,标口径)。**核实数字来自 junitxml 非编造**:SUMMARY 里的 tests 数须 == `grep -o 'tests="[0-9]*"' reports/phase10/junit-not-llm.xml | head -1` 的值。注:全量 `-m "not llm"` 加 16 case 后约为 912(896+16),但**以实跑 junitxml 为准,不硬编进 SUMMARY 或断言**。

- [ ] **Step 4: 诚实性自核(spec §8 收窄项未被打绿)**
```bash
grep -iE "8/8 真实|SOTA|根治|全覆盖|conflict detection.*(达标|通过|90)" reports/phase10/PHASE10_SUMMARY.md && echo "*** 有过度声称措辞!停" || echo "OK — 无过度声称"
```
Expected: OK。有命中 → 停,改措辞(SUMMARY 只做计数,收窄项指向 spec §8 不自己打绿)。

- [ ] **Step 5: Commit(SUMMARY.md 入库,是交付物)**
```bash
git add scripts/phase10/summarize_phase10.py reports/phase10/PHASE10_SUMMARY.md
git commit -F - <<'EOF'
feat(phase10d): Task 6 summarize —— ①SUMMARY 主体 + ②8模块表(实跑 junitxml,诚实限定)

读 Task 5 的 junitxml 取数(禁誊抄台账 858 教训),显式标两口径。8 模块状态带
advisory/remote/limitation 限定词,不写"8/8 真实模型"。门槛对账/失败修复叙事指向
spec §2.3+UPGRADE-PROGRESS,收窄项不自己打绿。诚实性 grep 自核无过度声称措辞。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
git show --stat HEAD
```

---

## Task 7:export_trace_bundle.py —— ⑤trace/provenance audit bundle(16 case 请求集)

**Files:** Modify `scripts/phase10/export_trace_bundle.py`;生成 `reports/phase10/PHASE10_TRACE_AUDIT.md`

- [ ] **Step 1: 确认 HEAD** = Task 6 commit。

- [ ] **Step 2: 实现 export(复用 D-A 的 16 case 请求集)**

替换 `scripts/phase10/export_trace_bundle.py` 全文:

```python
"""Phase 10 trace/provenance audit bundle 导出 —— 对 T10.3 的 16 case 请求集调 run_query。

权威请求集 = test_t10_3_end_to_end_cases 的 16 case（此处内嵌同一份,保持与 D-A 一致）。
导出每请求的 trace[](8 字段/条)+ provenance(rules_referenced/models_used/n_messages/per_call_hashes)
+ reliability_decision + 关键 structured_report 字段,落 PHASE10_TRACE_AUDIT.md。OFFLINE 确定性。
"""
from __future__ import annotations

import json
from pathlib import Path

from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.workflows.run_virtualcell_query import run_query

_REPO = Path(__file__).resolve().parents[2]
_OUT = _REPO / "reports" / "phase10"
_CFG = RuntimeConfig(mode=Mode.OFFLINE)
_BASE = {"input_modality": "scRNA", "task_type": "predict_delta_expression"}


def _req(name, species, ptype, targets, out="delta_expression"):
    return (name, {**_BASE, "species": species, "perturbation_type": ptype,
                   "perturbation_targets": targets, "output_modality": out})


# 与 test_t10_3_end_to_end_cases 的 16 core case 一致(S2b 远端变体不含,延后)
_CASES = [
    _req("S1_M1_membrane_FASN", "human", "gene", ["FASN"]),
    _req("S2_M2_genetic_AHR", "human", "gene", ["AHR"]),
    _req("S3_M3_mito_MYC_growth", "human", "gene", ["MYC"], "growth"),
    _req("S4_M4_cobra_b0720_b1136", "bacteria", "gene", ["b0720", "b1136"], "growth"),
    _req("S5_M5_biosynth_RPL5", "human", "gene", ["RPL5"]),
    _req("S6_M6_niche_state", "human", "medium", ["stromal_niche"], "state"),
    _req("S7_M7_state_IFNB1", "human", "ligand", ["IFNB1"], "state"),
    _req("S8_M8_degrad_UBB", "bacteria", "gene", ["UBB"], "growth"),
    _req("X1_M4M3_flux_IFNB1", "human", "ligand", ["IFNB1"], "flux"),
    _req("X2_M4M3_growth_MYC_KRAS", "human", "gene_combination", ["MYC", "KRAS"], "growth"),
    _req("X3_quad_SLC2A1_RPL5_PSMB5", "human", "gene", ["SLC2A1", "RPL5", "PSMB5"]),
    _req("X4_M4M8_bact_UBB", "bacteria", "gene", ["UBB"], "growth"),
    _req("X5_negtransfer_b0720_expr", "bacteria", "gene", ["b0720"]),
    _req("X6_C1gate_MYC_growth", "human", "gene", ["MYC"], "growth"),
    _req("X7_mouse_GATA1", "mouse", "gene", ["GATA1"]),
    _req("X8_diverge_SNAI1_state", "human", "gene", ["SNAI1"], "state"),
]


def _bundle_one(name: str, req: dict) -> dict:
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    prov = out["provenance"]
    return {
        "case": name,
        "request": req,
        "abstain": sr.get("abstain"),
        "models_used": sr.get("models_used"),
        "models_rejected": sr.get("models_rejected"),
        "prediction": sr.get("prediction"),
        "module_plan": prov.get("module_plan"),
        "provenance_keys": sorted(prov.keys()),
        "per_call_hashes": prov.get("per_call_hashes"),
        "rules_referenced": prov.get("rules_referenced"),
        "n_messages": prov.get("n_messages"),
        "reliability_decision": out.get("reliability_decision"),
        "trace_len": len(out.get("trace", [])),
        "llm_used_for_prediction": out.get("llm_used_for_prediction"),
    }


def main() -> int:
    _OUT.mkdir(parents=True, exist_ok=True)
    bundles = [_bundle_one(n, r) for n, r in _CASES]
    (_OUT / "trace_bundle.json").write_text(
        json.dumps(bundles, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    md = ["# PHASE 10 TRACE/PROVENANCE AUDIT BUNDLE", "",
          "> 对 T10.3 16 case 请求集调 `run_query`(OFFLINE 确定性)导出。原始 JSON 见 `trace_bundle.json`。",
          f"> `llm_used_for_prediction` 全部 = {all(b['llm_used_for_prediction'] is False for b in bundles)}(恒 False)。", "",
          "| case | abstain | models_used | prediction | module_plan.primary | trace_len |",
          "|---|---|---|---|---|---|"]
    for b in bundles:
        mp = b["module_plan"]
        prim = (mp or {}).get("primary") if mp else "None(unroutable)"
        md.append(f"| {b['case']} | {b['abstain']} | {b['models_used']} | {b['prediction']} | {prim} | {b['trace_len']} |")
    (_OUT / "PHASE10_TRACE_AUDIT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"[export_trace_bundle] wrote {_OUT / 'PHASE10_TRACE_AUDIT.md'} + trace_bundle.json ({len(bundles)} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: 跑 export,核实 16 case 全导出 + llm 恒 False**
```bash
cd /Volumes/T7/PRAXIS-virtualcell
PYTHONPATH=$PWD .venv/bin/python scripts/phase10/export_trace_bundle.py
sed -n '1,8p' reports/phase10/PHASE10_TRACE_AUDIT.md
PYTHONPATH=$PWD .venv/bin/python -c "import json; b=json.load(open('reports/phase10/trace_bundle.json')); print('cases=',len(b),'all_llm_false=',all(x['llm_used_for_prediction'] is False for x in b))"
```
Expected: 16 cases,all_llm_false=True。

- [ ] **Step 4: 交叉核实 bundle 与 D-A 测试一致(同请求同输出)**
```bash
PYTHONPATH=$PWD .venv/bin/python -c "
import json; b={x['case']:x for x in json.load(open('reports/phase10/trace_bundle.json'))}
assert b['S4_M4_cobra_b0720_b1136']['prediction']=={'delta':[-1.0,-1.0]}
assert b['X8_diverge_SNAI1_state']['abstain'] is True and b['X8_diverge_SNAI1_state']['module_plan']['overall_verdict']=='accept'
assert 'cross_module_consistency' not in b['X6_C1gate_MYC_growth']['provenance_keys']
print('bundle 与 D-A 断言一致 ✓')
"
```
Expected: ✓（bundle 与 Task 1-4 的实测断言同源）。

- [ ] **Step 5: Commit(trace bundle md 入库,json 是否入库—— md 入库,json gitignore)**
```bash
grep -q "trace_bundle.json" .gitignore || echo "reports/phase10/trace_bundle.json" >> .gitignore
git add scripts/phase10/export_trace_bundle.py reports/phase10/PHASE10_TRACE_AUDIT.md .gitignore
git commit -F - <<'EOF'
feat(phase10d): Task 7 export_trace_bundle —— ⑤trace/provenance audit(16 case)

对 T10.3 16 case 请求集调 run_query 导出 trace+provenance+reliability,落 PHASE10_TRACE_AUDIT.md
(原始 json gitignore)。llm_used_for_prediction 恒 False。交叉核实 bundle 与 D-A 测试同源
(S4 delta/X8 背离/X6 gate NO-OP 一致)。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
git show --stat HEAD
```

---

## Task 8:③16-case 表 + ④负例 abstain 表(交付物收尾)

**Files:** 生成 `reports/phase10/PHASE10_CASES.md`(③)+ `reports/phase10/PHASE10_FAILURES.md`(④负例);无新脚本(用已有数据 + D-A 测试清单)

- [ ] **Step 1: 确认 HEAD** = Task 7 commit。

- [ ] **Step 2: 从 D-A 测试 + trace bundle 生成 ③16-case 表**

新建一个小生成器 `scripts/phase10/gen_case_tables.py`:

```python
"""③16-case 表 + ④负例 abstain 表 —— 从 trace_bundle.json 派生(实测数据,非手写)。"""
from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_OUT = _REPO / "reports" / "phase10"


def main() -> int:
    bundles = json.load(open(_OUT / "trace_bundle.json", encoding="utf-8"))
    # ③ 16-case 表
    cases_md = ["# PHASE 10 — T10.3 端到端 16 CASE 表", "",
                "> 8 单模块(S)+ 8 跨模块(X),`run_query` 驱动,数据源 trace_bundle.json(实测)。",
                "> 断言明细见 `praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py`。",
                "> **诚实**:M1/M5/M8 是 advisory(断 module_plan entry 非预测);M6 管线 limitation;",
                "> X8 路由声明与引擎背离;X6 C1 gate NO-OP(自然输入不触发)。S2b 真实 GEARS 需 .53(延后)。", "",
                "| case | 类型 | abstain | prediction | primary | secondary |", "|---|---|---|---|---|---|"]
    for b in bundles:
        mp = b["module_plan"] or {}
        typ = "单模块" if b["case"].startswith("S") else "跨模块"
        cases_md.append(f"| {b['case']} | {typ} | {b['abstain']} | {b['prediction']} | "
                        f"{mp.get('primary','None')} | {mp.get('secondary',[])} |")
    (_OUT / "PHASE10_CASES.md").write_text("\n".join(cases_md) + "\n", encoding="utf-8")
    # ④ 负例与 abstain 表(从 bundle 抽 abstain==True 的)
    neg = [b for b in bundles if b["abstain"] is True]
    fail_md = ["# PHASE 10 — 负例与 ABSTAIN 表", "",
               f"> T10.3 16 case 中 {len(neg)} 个诚实 abstain(数据源 trace_bundle.json)。",
               "> 补充负例 corpus(schema/route/provenance gate/注入)见 tests/negative_cases、",
               "> test_t10_4/5/6、test_negative_cases.py —— 见 spec §2.5 数据源清单。", "",
               "| case | abstain_reason(推断) | models_rejected | module_plan |", "|---|---|---|---|"]
    for b in neg:
        mp = b["module_plan"]
        mps = "None(unroutable)" if mp is None else f"{mp.get('primary')} overall={mp.get('overall_verdict')}"
        fail_md.append(f"| {b['case']} | prediction None | {b['models_rejected']} | {mps} |")
    (_OUT / "PHASE10_FAILURES.md").write_text("\n".join(fail_md) + "\n", encoding="utf-8")
    print(f"[gen_case_tables] wrote PHASE10_CASES.md ({len(bundles)}) + PHASE10_FAILURES.md ({len(neg)} abstain)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: 跑生成器,核实表**
```bash
cd /Volumes/T7/PRAXIS-virtualcell
PYTHONPATH=$PWD .venv/bin/python scripts/phase10/gen_case_tables.py
echo "--- CASES 前几行 ---" && sed -n '1,12p' reports/phase10/PHASE10_CASES.md
echo "--- FAILURES 行数 ---" && grep -c "^|" reports/phase10/PHASE10_FAILURES.md
```
Expected: CASES.md 16 行 case;FAILURES.md 含 abstain 的 case(实测 S1/S3/S5/S6/S8/X2/X3/X4/X5/X6/X8 = 11 个 abstain）。

- [ ] **Step 4: 六交付物落位核实**
```bash
ls -1 reports/phase10/*.md
```
Expected(本计划本地部分产出):`PHASE10_SUMMARY.md`(①)、`PHASE10_TRACE_AUDIT.md`(⑤)、`PHASE10_CASES.md`(③)、`PHASE10_FAILURES.md`(②/④)。**延后**:⑥UI 截图(D-B)、独立 GATE.md sign-off + .53 段(D-D 远端)。

- [ ] **Step 5: Commit**
```bash
git add scripts/phase10/gen_case_tables.py reports/phase10/PHASE10_CASES.md reports/phase10/PHASE10_FAILURES.md
git commit -F - <<'EOF'
feat(phase10d): Task 8 ③16-case 表 + ④负例 abstain 表(从 trace_bundle 实测派生)

gen_case_tables.py 从 trace_bundle.json 派生 PHASE10_CASES.md(16 case)+ PHASE10_FAILURES.md
(实测 abstain case)。诚实标 advisory/limitation/背离/gate NO-OP。补充负例 corpus 指向
spec §2.5。本计划本地部分产出四交付物(①③④⑤);⑥UI+GATE.md+.53 延后。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
git show --stat HEAD
```

---

## 收官(控制器执行,不派 subagent)

- [ ] **opus final review**(fresh、只读):带本 Phase 血泪 —— **final review 也会漏**(#5、C4 的 app.py 第六次复发都是它漏的)。重点:①16 case 断言是否真钉住诚实事实(advisory≠预测、X8 背离两侧、X6 NO-OP);②summarize/export 是否真实跑取数无誊抄、无过度声称措辞;③是否有 case 断言写成"引擎内部"而非管线可观测;④红线(核心/根 tests/reliability/critic/前端 WIP 零触碰)。
- [ ] **控制器勾账**:台账 `UPGRADE-PROGRESS.md` + `memory/phase10-deep-validation.md` + `MEMORY.md`,标口径,记"D-A/D-C 本地部分收官,D-B/S2b/.53/GATE.md 延后"。
- [ ] **暂停 AskUserQuestion**:是否 FF 合并 main(合则 `git branch -f main HEAD`、不 push、保留分支);D-B/.53 是否本轮继续。

---

## Self-Review

**1. Spec 覆盖**(本计划范围 = D-A + D-C 本地):
- spec §4.A 16 case → Task 1-4(S1-S8 + X1-X8,断言全实测真值)。✅ S2b(remote)明确延后。
- spec §4.C 三脚本 → Task 5(run_phase10_all)/6(summarize)/7(export_trace_bundle)+ Task 8(gen_case_tables 派生表)。
- spec §4.C 六交付物 → ①SUMMARY(T6)②8模块表(T6 内)③16case表(T8)④负例表(T8)⑤trace bundle(T7);⑥UI + GATE.md sign-off **明确延后**(依赖 D-B/.53)。
- spec §2.2 三条诚实事实 → S1/S5(advisory≠预测)、X8(背离两侧变异)、X6(gate NO-OP)。
- spec §6 红线 → 全局约束 + 每 task commit 自核。
- **Gap**:GATE.md 13 指标对账表本计划不产(属 D-D,依赖全量+远端)→ SUMMARY 第3段指向 spec §2.3,不自己打绿。**已在 Task 6 处理,非遗漏。**

**2. 占位符扫描**:无 TBD/TODO;每步有完整可跑代码 + 命令 + 预期。测试断言全部内嵌实测真值(非"填入")。

**3. 类型一致性**:`_req`/`_run`/`_entry` helper 在 Task 1 定义,Task 2-4 复用同签名;16 case 请求集在 Task 1-4(测试)与 Task 7(export)两处内嵌,**已在 Task 7 Step 4 交叉核实同源**(防漂移);junitxml 路径 `reports/phase10/junit-{not-llm,full}.xml` 在 Task 5 产、Task 6 读,一致。

**4. 变异要求**:Task 1(S4 human→abstain)、Task 2(S6 mp None)、Task 3(X1 数值)、Task 4(X8 两侧)各含变异证伪 —— 防"路由声明 accept 就断言成功"的假绿(spec §7)。
