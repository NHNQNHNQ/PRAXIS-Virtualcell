# Finding W5 — cross-species brain + 路由(Workflow 对抗验证后实现)

> Week 5:4 species brain(human 充实 + mouse/bacteria/yeast 新建)+ ModelApplicabilityAgent 路由扩展(ortholog caution / negative-transfer 命中)。**经 Workflow 对抗验证(6 agent, 345k tokens)抓出设计缺陷后修正实现**,`test_cross_species_routing` 6/6 PASS,Mac 全套零回归(54 passed + 23 skipped)。

## GPT §7 验收(实测 6/6 PASS)
| § | 验收 | 实现 |
|---|---|---|
| 7.1 | 同 task 4 species 路由不同 | human=3 applicable 无 caution / mouse=3 applicable + caution / bacteria,yeast=全拒 → abstain |
| 7.2 | human predictor 不用于 bacteria | bacteria `model_applicability` supported_species=[human] → 全 reject |
| 7.3 | mouse ortholog caution(applicable 非 reject 且**可见**) | ModelApplicability 读 `caution.mouse`(LIST)→ `brain_context.routing.cautions` → `provenance.ortholog_cautions` → **`report.caution_flags` 非空** |
| 7.4 | bacteria 被理解但拒绝 → abstain | bacteria 有目录(=被理解)+ 全拒 → all_predictors_rejected → abstain |
| 7.5 | trace 引用具体规则 | `provenance.rules_hit` 含 `mammalian_scrna_predictor_not_applicable` / ortholog rule;`rules_referenced` 按 species_supported 条件(martian 不写指向不存在文件的假路径) |

## Workflow 对抗验证抓出并修复的缺陷(verdict consistent=false → 修正)
1. **§7.3 caution 不可见(最严重)**:原设计 caution 流到下游(base.py→provenance→report)**只是提案未实现**,实测 mouse/human report 字节级相同。→ 修:ModelApplicability **集中**算 caution → `brain_context.routing` → ProvenanceAgent(`ortholog_cautions`)+ ReportAgent(`caution_flags`)。不改 predictors/base.py(不影响真 predictor)。
2. **caution list/dict 类型自相矛盾**:落盘 yaml 是 LIST,提案代码当 dict(`.get('flag')` 会抛 AttributeError)。→ 统一按 LIST 处理。
3. **negative_transfer 死代码**:原设计依赖没人写的 `predictor_origin` 字段(全仓 0 命中)。→ 改:ModelApplicability 直接用 `generic.negative_transfer`(from=human 母种, to 含 species)命中 → `rejection_reasons` + `rules_hit`。
4. **martian 假证据**:不存在的 species 也写 `rules_referenced` 指向磁盘不存在的文件。→ SpeciesBrainAgent 按 `species_supported` 条件写 + 登记 generic negative_transfer 路径。
5. **仅断言 abstain 无法防 §7.3 退化**:→ test 断言 mouse `caution_flags` 非空 / bacteria `rejection_reasons` 含具体 rule / martian `rules_referenced` 无假路径(而非仅 abstain)。

## 字段语义(诚实标注:运行时 vs 声明式)
- **运行时**(ModelApplicabilityAgent/SpeciesBrainAgent 读取,影响路由/trace):`supported_species` / `supported_modalities` / `supported_tasks` / `reject_if` / `object_vocabulary.genes` / `caution.<species>`(LIST) / `cross_species.rule` / `generic.negative_transfer`。
- **声明式 brain 知识**(本期**不参与**运行时路由,人读/未来接入):`supported_perturbations` / `supported_cell_types` / `native_host` / `mouse/ortholog_rules.yaml` / `yeast/genetic_interaction_rules.yaml` / species 级 `negative_transfer.yaml` / `bacteria/abstain_rules.yaml` / `reject_reason_for_X`。诚实记:这些是 brain 知识库,SpeciesBrainAgent 暂不读取,不与运行时绑定(对抗验证特别指出不可 over-claim 它们参与判定)。

## 第二层对抗验证(实现级 review workflow,2 reviewer 实跑 dry-run + pytest)
overall_pass=true,但抓出 2 must-fix + nice/minor(reviewer **实跑确认**,非纸面),已全部修复 + 加回归测试(`test_cross_species_routing` 6→11 PASS):
1. **drug 拒因语义错误(must-fix)**:mouse drug[aspirin] 原把药名当基因做 vocab 比对(拒因误为 gene_not_in_graph_vocabulary)。→ `base.assess` + ModelApplicability + mock_gears 加 `supported_perturbations` 检查 + gene-vocab 守卫(仅 gene/gene_combination);drug 下 MockGEARS 以 `unsupported_perturbation` 拒。
2. **ortholog 投影零执行(must-fix,§7.3 言过其实)**:mouse OOV[ZZZZ9] 与可映射[TRP53] 原拿**相同** caution,`ortholog_rules.yaml` 是死文件。→ SpeciesBrainAgent 加载 ortholog_rules + ModelApplicability 用 `map_upper` **真投影**,未映射 target 加 `unmapped_ortholog` flag(OOV ≠ mappable);ortholog_rules.yaml 进 rules_referenced。
3. **per-species yaml 不进 trace(nice)**:→ SpeciesBrainAgent 加载 species 级 negative_transfer/abstain/ortholog/interaction → `species_rules` + rules_referenced(§7.5 审计链完整)。
4. **空 targets 静默出预测(nice)**:→ ReliabilityAgent 空 perturbation_targets → abstain(`no_perturbation_specified`)。
5. **martian abstain_reasons(minor)**:→ ReliabilityAgent species_supported=False 加 `species_not_supported`,区分"物种未知"vs"模型不适配"。
+ caution `isinstance list` 守卫、`native_host` per-predictor(取代全局硬编码 origin)。confirmed-ok:§7.1/7.2/7.4 真满足、向后兼容真不破、鲁棒性(畸形输入不抛异常)。

## 留 backlog
species 级 negative_transfer/abstain/genetic_interaction 接入**判定**(目前进 rules_referenced 可审,但路由真相源仍是 generic.negative_transfer);更多 species(rat/zebrafish);真 cross-species ML predictor(在 W4c GEARS/scGPT 之上做 ortholog 投影 + 真预测,取代 mock);cross-species 端到端 abstain 强化(W6)。
