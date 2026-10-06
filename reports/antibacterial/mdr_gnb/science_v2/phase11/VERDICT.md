# Phase 11 科学验证战役 · 总裁决(VERDICT)

> 本文由 `praxis_virtualcell/mdr_gnb/workflows/science_v2/validation/run_campaign.py` 真串跑 T1–T7 七层评分函数后生成,所有数字均从实跑 payload 插值。
> 结构化同源产物:`reports/science_v2/phase11/campaign.json`。

## 〇、两条读数

- `campaign_pass` = **True**
- `all_gates_pass` = **False**

**为什么给两个读数?** 计划书正文说 `campaign_pass = all(层 pass)`,而「验收标准」一节又把 T1 列为软指标、把 T2/T3/T4/T6/T7 列为硬红线。二者有张力。与其由我们替读者挑一个好看的,不如**两个都摆出来**,并写明定义差异:

| 读数 | 定义 | 本次 |
|---|---|---|
| `campaign_pass` | 硬红线语义:HARD_RED_LINE_LAYERS(T2/T3/T4/T6/T7)全部 pass,且全战役无 severity=red_line 的 finding。回答的是「平台的安全与诚实边界守住了吗」。T1 的软门槛(准确率/VME/MIC 误差)**不**参与本读数。 | **True** |
| `all_gates_pass` | 含软门槛:九层(含 T1 三子层)的**每一个** gate 都为 True,且无 red_line finding。它比 campaign_pass 严格 —— T1 的软门槛或 T5 的 gates 任一未达即 False。**门槛来源**:九层中八层的 gates 直读自各层自己的预注册字段,唯 T5 的两条 gate 系推导(详见「九层一览」下方的门槛来源披露)。 | **False** |

**差异**:二者的差 = T1 软指标 **及 T5 的非硬红线 gates**。campaign_pass=True 而 all_gates_pass=False 意味着:硬红线守住了,但某条非硬红线门槛未达 —— 差异若来自 T1,那是**科学局限**(预测性能未达预注册门槛,不是红线事故);若来自 T5,那是**边界缺口**(对抗输入未 fail-closed),性质更重,只是依预注册规则不由本读数拉黑(它由 red_line finding 拉黑)。**读数差异的来源要看是哪一层,不可一律当作科学局限。**两个读数同时呈现,是为了让读者自己判断,而不是由我们替他挑一个好看的。

**注意**:本次两条读数**不一致**(`campaign_pass`=True、`all_gates_pass`=False),差异全部来自 T1 软门槛。两个都摆在这里,请读者自行判断 —— 我们不替你挑。

**红旗规则**:红旗 = ①任一硬红线层失败 或 ②任一 severity=red_line 的 finding。非空 ⇔ campaign_pass=False。软门槛失败**不**进红旗(它是科学发现,如实记录,不调阈值)。

### 红旗清单(0 条)

(无)

### 九层一览

| 层 | 性质 | 判定 | 门槛 |
|---|---|---|---|
| T1A SIR | 软指标 | **FAIL** | `face.anchors_all_R`=True, `face.coverage_ge_0.70`=True, `gen.auc_ge_0.85`=True, `gen.vme_le_0.10`=False |
| T1B 小分子 | 软指标 | PASS | `face.ciprofloxacin_anchor_low`=True, `face.coverage_ge_0.70`=True, `gen.mae_le_0.75`=True, `gen.r2_ge_0.40`=True |
| T1C 肽 | 软指标 | PASS | `face.coverage_ge_0.70`=True, `face.magainin2_anchor_in_range`=True, `gen.mae_le_0.90`=True, `gen.r2_ge_0.20`=True |
| T2 OOD | 硬红线 | PASS | `fail_closed_verified`=True |
| T3 诚实性 | 硬红线 | PASS | `honest`=True |
| T4 确定性 | 硬红线 | PASS | `all_stable`=True |
| T5 对抗 | 红线缺口源 | PASS | `no_crashed`=True, `no_leaked`=True |
| T6 证据 | 硬红线 | PASS | `evidence_systems_consistent`=True |
| T7 端到端 | 硬红线 | PASS | `all_cases_schema_fixed_point`=True, `e2e_science_consistent`=True |

> `t5` 不在计划书的硬红线层清单里,但**若**它产出 `severity=red_line` finding,依规则2 同样会拉黑 `campaign_pass`。本次 `t5` 无 red_line finding(见第二栏)。
>
> **门槛来源披露(科学产物须交代门槛从哪来)**:上表九层中,**八层**的 gates 均**直读**自各层自己的预注册字段(T1 的 `gates`、T2/T3/T6/T7 的 `verdict`、T4 的 `all_stable`)。**唯 T5 例外** —— 该层无预注册 `verdict` 字段,其两条 gate(`no_leaked`/`no_crashed`)系按 T5 docstring 声明的红线语义(「crashed 和 leaked 都是红线」)**推导**而来,取 `==0` 的最严读法,是九层中**唯一非直读**的门槛。**本次 T5 两条推导 gate 均 True**(无泄漏、无崩溃),且无 red_line finding,故 T5 既未经推导 gate、也未经 finding 拉黑 `campaign_pass`。

---

## 一、科学性(T1)

**双轨设计**:轨A(面值)拿 curated 真实株/真实药跑**部署平台**,验证服务链通 + 输出合理;但部署 artifact 训过全量数据,所以轨A 是**训练集乐观估计**,一律标 `stratum=train_set_optimistic`,**不作泛化门槛**。轨B(泛化)用已有留出(SIR 走 G2R evidence_tiers 的 per-ST 留出;小分子走 scaffold-OOF;肽走序列相似度连通分量-OOF),**泛化门槛只下在轨B**。两轨都诚实标 stratum,互不冒充。

### T1A 基因型 → SIR

- **轨A(`train_set_optimistic`,不作泛化门槛)**:accuracy=0.9118、coverage=1、**VME=0(n_R=52)**、ME=0.18(n_S=50)、n=102;强机制锚点全出 R = True。
- **轨B(`held_out`,真泛化,门槛在此)**:中位 VME(fusion)=**0.1254**、中位 AUC_R=0.94;取自 `evidence_tiers.yaml` 的 26 个 strong combo(VME 中位数的分母 = 26 个 combo,每个 combo 的 per-ST VME 各自带 `n_R_ST` 分母)。**泛化门槛**:`gen.auc_ge_0.85`=True, `gen.vme_le_0.10`=False

#### 🔬 发现① SIR 留出泛化 VME 未达门槛(软指标 FAIL,**不调阈值**)

轨B 中位 VME = **0.1254** > 门槛 0.1 → `gen.vme_le_0.10` = False;而 AUC_R = 0.94 过 0.85 门槛。

**VME(very major error)= 把耐药误判为敏感**,是抗菌药敏最严重的错误类型(临床后果:给了无效药)。故此处分母必须透出:轨A 的 VME=0 是 **0/52** 而非「没有 R 样本所以算不出 0」。

**科学意义 —— 这是双轨设计的成功,不是失败**:同一套模型,轨A(训练集内)VME=0,轨B(真留出)VME=0.1254。这道**「训练集乐观 vs 真泛化」的裂口**,正是本战役设置双轨要暴露的东西。若只报轨A,我们会得到一个「VME=0」的漂亮结论,而它对新病人毫无意义。门槛未达 → **如实记为科学发现,不调阈值、不换语料、不改算法让它变绿**。

### T1B 小分子(SMILES)→ 活性

- **轨A(`train_set_optimistic`,不作泛化门槛)**:R²=0.864、MAE=0.2484(log10 尺度)、coverage=1、n_scored=17;锚点 `ciprofloxacin_log10_lt_0`=True。面值哨兵:`face.ciprofloxacin_anchor_low`=True, `face.coverage_ge_0.70`=True
- **轨B(`held_out`,真泛化,门槛在此)**:**R²=0.5654**、MAE=0.5132、n=27175;取自 `reports/science_v2/qsar_baseline/qsar_per_compound.parquet`。**泛化门槛**:`gen.mae_le_0.75`=True, `gen.r2_ge_0.40`=True → 本层整体 **PASS**

### T1C 抗菌肽(序列)→ 活性

- **轨A(`train_set_optimistic`,不作泛化门槛)**:R²=0.9245、MAE=0.2011(log10 尺度)、coverage=1、n_scored=18;锚点 `magainin2_log10_in_1_2`=True。面值哨兵:`face.coverage_ge_0.70`=True, `face.magainin2_anchor_in_range`=True
- **轨B(`held_out`,真泛化,门槛在此)**:**R²=0.2938**、MAE=0.4572、n=774;取自 `reports/science_v2/peptide_baseline/peptide_per_seq.parquet`。**泛化门槛**:`gen.mae_le_0.90`=True, `gen.r2_ge_0.20`=True → 本层整体 **PASS**

> **肽方向偏弱,如实说**:轨B R²=0.2938,门槛 `r2_ge_0.20` 是**诚实放宽**以对齐现状 —— 不是假装它强。它过了门槛,但 R²≈0.3 意味着序列→MIC 的可解释方差仍然有限,该方向**不足以支撑强科学声称**。提升路线见 Phase 13。

---

## 二、诚实性与边界(T2 / T3 / T5 / T6)

这一栏回答的不是「模型准不准」,而是**「模型知不知道自己不知道」**、**「不知道的时候会不会编」**。对一个要给临床用药提示的平台,这比准确率更要命。

- **T2 OOD 全弃权** — PASS(硬红线)。分布外化合物 3/3 弃权、肽 3/3 弃权;SIR 乱格式输入 3 例、泄漏 0 例。**总泄漏 = 0**。
- **T3 不伪造** — PASS(硬红线)。违规 0 例。①无模型物种(`enterobacter_cloacae`, `morganella_morganii`, `proteus_mirabilis`)必 `sir=None`/`prediction_available=False`,**不编 R/S**;②非代谢靶药(`colistin`, `meropenem`)`mechanism.available=False`,**不编机制**;③代谢靶候选药(`trimethoprim`)即便 FBA 真阻断了靶点,只要 G3 门未评估该药,`mechanism_claim` **恒 None** —— 有机制信号 ≠ 可以声称已证实。
- **T6 证据零串用** — PASS(硬红线)。112 个 case,mismatch=0。两套证据系统(per-prediction SIR evidence_tiers vs 模型级 QSAR 验证层)不得互相冒充 —— 陷阱:EC×trimethoprim 在 SIR 侧有 E3 证据,活性卡若取用它即误导(应取 QSAR 侧 E4)。
- **T5 对抗输入 fail-closed** — PASS。10 条恶意/畸形输入:fail-closed **10**、崩溃 0、**泄漏 0**。

本栏无 red_line finding。

---

## 三、治理有效性(T4 / T7)

这一栏回答:**我们建的这套治理机制,自己有效吗?** 确定性红线与端到端一致性红线,是装饰,还是真能抓到东西?

- **T4 trace 确定性** — PASS(硬红线)。语料 35 条 × 重复 **100** 次 = 3500 次预测,trace_hash 不稳定 0 条。语料构成:compound_activity×9, fail_closed×6, peptide_activity×8, sir×12。FBA 真进 trace(cobra LP 实跑 iML1515):`mechanism_available=True`、`growth_inhibition=1` —— 故「FBA 确定性已验证」是真覆盖,不是假声称。
- **T7 HTTP = 直调逐字一致** — PASS(硬红线)。7 个 case,科学字段不一致 0、内容寻址 task_id 不一致 0。比对字段:`abstained`, `output_kind`, `sir`, `activity`, `peptide_activity`, `mechanism`。

#### ✅ 发现③ SIR 路径间歇性非确定性 —— **战役中定位并已修复**

**这是治理机制真的抓到产品 bug 的实例。**

- **症状**:T4 层建成后,`test_determinism_corpus_stable` 约 **1/3 概率**变红 —— 同一个查询、同一份 artifact,trace_hash 偶尔漂。
- **定位**:`predictors/genotype_to_sir.py` 的 `predict_proba_r` 直调 sklearn `RandomForestClassifier.predict_proba`;部署 artifact 是 `RandomForestClassifier(n_estimators=300, n_jobs=-1)`。sklearn 的 `_forest._accumulate_prediction` 在锁里按**线程完成顺序**累加各树结果 —— 浮点加法**不满足结合律**,线程调度一变,末位 ULP 就漂 → `sir_prob` 变 → trace_hash 不再恒定。
- **修复**(commit `19e24b9`):按 `estimators_` 的**固定顺序**逐树 `predict_proba` 再求均值。数学上恒等于 RF 的 `predict_proba` 定义(只固定了求和顺序),实测与 sklearn 差异 **5.55e-17**(阈值 1e-12)—— **科学结论未改**。性能反而 13.5ms → 8.2ms。
- **为什么早没发现**:线B 的 `small_molecule_model` / `peptide_activity_model` 当年已显式修过同一个坑;SIR 路径建于 v1、早于线B,故漏修。本次对齐。

**科学意义**:确定性红线**不是装饰**。它是本战役唯一一条「不看科学正确性、只看可复现性」的门槛,而恰恰是它抓到了一个**潜伏在生产路径上的真 bug** —— 一个会让「同样的病人、同样的基因型,两次查询给出不同 sir_prob」的 bug。战役不仅验证了平台,还修好了平台。本层现判定 **PASS**。

> **T7 负对照的判别力**:已获实证 `peptide_activity`, `sir`, `sm_activity`;未获实证 `no_model_species`, `ood` —— 二者本就恒 fail-closed,「剥字段」这族负对照对其无从发力。**措辞据实**:是「判别力未获实证」,**不等于**「无判别力」。

---

## 四、已知局限与遗留(不隐瞒)

1. **E5 外部 holdout 未做(论文最易被打的缺口)**。小分子的 `reports/science_v2/sm_activity_evidence/sm_activity_evidence.json` 载明 `not_e5_because="无外部数据集(换来源/换年份)holdout;当前仅 ChEMBL EC 内部 scaffold-split CV"`;SIR 同理。→ **已定为 Phase 12**。
2. **T1A 轨A 面值仅覆盖 2 物种**(以下为 T1A 层自报的 `limitations`,原样透出):
   - `face_validity_species_coverage`:轨A 面值仅覆盖 escherichia_coli / klebsiella_pneumoniae 两物种,因 pseudomonas_aeruginosa / acinetobacter_baumannii / salmonella_enterica 本地无 ncbi_amr_phenotypes.tsv;且轨A 为训练集乐观估计,不作泛化门槛。
   - `fidelity_reproducible`:轨A amr_profile(base 名)与训练特征化逐位一致,由 verify_amr_fidelity.py 一键复现(N/N 逐位相等),不写死具体数字。
   - `generalization_species_coverage`:轨B 泛化基于 evidence_tiers 全 26 strong combos,覆盖 5 物种(含 PA/AB/SE),为留出真泛化数字;泛化门槛下在此轨。
3. **肽方向偏弱**:轨B R²=0.2938,门槛 `r2_ge_0.20` 系诚实放宽以对齐现状。→ **Phase 13**(全量 DBAASP + ESM)。
4. **T5 `name_consistency` 正例无离线测试**(原「T5 遗留」三条,两条早前已修,「`consistent` 恒真」一族的**两处**——解析半场的空集恒真、活性半场的全弃权——**均已修复**,余此一条):`run_adversarial_suite()` 已有直接测试(`test_run_adversarial_suite_known_state`:钉计数口径 + 缺口上浮 findings + 连跑逐字确定性);其 `name_consistency` 子项的内部 crash(逐变体崩 / `resolve_compound` 探针自身崩)已汇入顶层 findings(`id=name_consistency_crash`、`severity=red_line`),依规则2 同样拉黑裁决 —— 不再只躺在子项里对裁决不可见。**修复一(解析半场:空集恒真)**:`consistent` 原写作 `len(canon_set) <= 1`,对**空集**恒真 —— 全部变体都没解析出来(`n_resolved=0`)时反而报 `consistent=True`,报告读作「名称一致」,是空集恒真的假安慰。现改为**三态**:`comparable = n_resolved >= 2`,不足 2 个可比对象时 `consistent`/`same_canonical_smiles`/`same_activity` 全取 `null`(**无从判断**)而非 `true`/`false`(后者是反方向的编造);比较逻辑另加离线负对照(互异 SMILES → `consistent=false`)钉住。**修复二(活性半场:全弃权)**:`same_activity` 原写作 `len(activity_set) == 1`,而弃权(`activity=None`)也作为 `None` 落进该值集合 —— 变体**全部弃权**时集合是 `{None}`、基数也是 1 → 报 `same_activity=true` → `consistent=true`。这**不是**空集恒真(集合非空),而是它的近亲:把 `None`(**没有答案**)当成一个**值**去数基数,「都没给答案」被算成了「给了同一个答案」;此时平台**零个 MIC 产出**,而本项声称的性质「同一 canonical SMILES → **同一 MIC**」后半句从未被检验。现按同一把语用尺子改为三态:全弃权 → `same_activity=null`;`consistent` 改用**三值(Kleene)合取**汇总两半(任一半 `false` → `false`;否则任一半 `null` → `null`;全 `true` 才 `true` —— 不能用 `all()`,`all([True, None])==False` 会把「无从判断」误报成「不一致」的假警报)。并透出活性半场的**分母** `n_with_activity` / `mic_comparable`(`same_activity is true` ⟹ `mic_comparable` 必为 true),读者可自行核对「一致」是基于几个 MIC 得出的。⚠️「有的给 MIC 有的弃权」(`{tuple, None}`)**仍判 `false`** —— 同一 SMILES 一个给一个不给是平台行为不自洽,属**真发现**,不得在修全弃权时被顺手放成 `null`;该回归由 `test_name_consistency_mixed_activity_is_inconsistent` 参数化钉住(含仅 1 个 MIC、`mic_comparable=false` 的边界:不一致来自「结果形态不同」,不需要凑够两个 MIC 才能断定)。本存档 `name_consistency` 的 `consistent=true` 系**挣来的**(`n_resolved=3`、`n_with_activity=3` 均 ≥2,真联网所跑)。注:`unresolved_fail_closed` 的 `all([])` 恒真**有意保留** —— 它是**违规检查**,零样本→零违规→True 语义正确,且分母 `n_unresolved` 就在旁边透出;而 `consistent` 声称的是「正面属性被验证过」,零样本下报 True 即撒谎。**残留**:`name_consistency` 的**正例**(`ciprofloxacin`/`Ciprofloxacin`/`cipro` 三个书写变体经 PubChem 解析到同一 canonical SMILES → 同一 MIC)本质是**联网事实**,离线注入假解析器去测它只会得到同义反复(假解析器返回什么就「一致」什么),故**不予测试**,仅由存档 `reports/science_v2/phase11/t5_adversarial.json` 的真跑记录佐证(该存档系真联网所跑:`skipped=false`、`n_resolved=3/4`,中文名「环丙沙星」未被 PubChem 名称索引收录 → 诚实 fail-closed)。
5. **T6 遗留**:负对照覆盖面窄于实际能力(实测肽/弃权类均有判别力,但无测试钉住);`contract_selector` 是 `PredictionResult.tsx` 的**手写 Python 复刻件** —— TSX 若改用 `result.evidence` 喂活性卡,则 T6 恒绿(由 `PredictionResult.test.tsx` + T7 的 `phase11.e2e.test.tsx` 兜底)。
6. **T7 遗留**:`emit_frontend_fixtures` 用 `as unknown as`,故 `tsc` **不**校验 fixture 与前端类型的一致性(主因是 `Report.mic_range` 前端未声明);契约由运行时断言守。
7. **离线脚本 ULP 隐患**:`workflows/science_v2/qsar_baseline.py:142` 仍用 `rf.predict` + `n_jobs=-1`,与发现③同源。但它是**离线 baseline 脚本、不在 trace 路径**,不影响产品确定性;仅在「复现报告 R² 逐位相同」的严格意义上有影响。(`peptide_baseline.py` 早已用固定顺序逐树平均,**无**此问题。)
8. **前端 trimethoprim 示例输入不一致（本地已修复）**:旧 `genes.ts` 曾把示例写成 C14H18N4O 的 `Cc1cc(C)c(Cc2cnc(N)nc2N)cc1OC`,而 golden 正确三甲氧结构是 C14H18N4O3 的 `COc1cc(Cc2cnc(N)nc2N)cc(OC)c1OC`。该示例会让活性 QSAR 使用错误 SMILES,但 `drug_panel` 仍以 `trimethoprim` 标签触发 DHFR sidecar,因此不是可接受的 展示差异。现前端示例已改为 golden 结构，`QueryInput` 用户路径回归同时钉住示例和提交 payload；本地 React/API/浏览器均已复核。此为战役后的本地输入完整性修复，**不改变 Phase11 的模型、规则、阈值或证据**；GitHub/.53 静态资产仍未核验。

---

## 五、后续路线

| 阶段 | 内容 | 触发本裁决的哪一项 |
|---|---|---|
| **Phase 12** | E5 外部 holdout(换来源/换年份的独立数据集) | 局限 1 —— 论文最易被打处 |
| **Phase 13** | 肽方向增强(全量 DBAASP + ESM 表征) | 发现①栏的肽 R²≈0.3 / 局限 3 |
| **Phase 14** | KP-QSAR:小分子从 EC only → EC + KP 双物种 | 局限 2(物种覆盖窄) |
| **Phase 15** | Synergy 原型:激活已预埋的 `output_kind=synergy` | 能力扩展(非本裁决缺陷) |
| **加法方向 sanity gate(已完成)** | sm_activity/peptide 结构规模/组分/长度上限(独立于 Tanimoto)fail-closed | 历史发现②——现已修复,第二栏无 red_line finding |

**Phase 14:KP-QSAR** —— 小分子从 EC only 扩到 EC + KP 双物种(KP 的 MIC 数据量第二大、临床价值最高)。交付:`chembl_pull.py` 拉 KP MIC + scaffold 防泄漏 baseline + KP `sm_activity` artifact(按物种分文件)+ 注册进 registry + 证据分层 + `golden_compounds` 加 KP 栏。验收门:KP scaffold-CV R² 达「有意义预测」阈且优于 baseline;多物种活性证据**按物种 gate**;确定性。依赖:ChEMBL KP MIC 数据量核对(探查)。

**Phase 15:Synergy 原型** —— 激活核心已预埋的 `output_kind=synergy`:输入 drugA + drugB + species → 输出 FICI / synergy 概率。交付:synergy 数据门探查 + baseline + `SynergyPredictor` 注册进核心 + 证据分层 + fail-closed。验收门:**须有真实组合数据支撑**(无则明确「数据门未过、不产 FICI 数字」)。**风险**:数据可能根本不够 —— 那就诚实给出结论「synergy 需先解决数据门」,**不硬做**。

**路线层总原则**:①每个 Phase **先探数据门/算力门 spike,再立详细 plan** —— 数据门未过就写 TDD 步骤,会编造;②**诚实优先于涨点**;③**复用不抛弃核心**;④顺序可调(Phase 12 数据门若难,可先做 Phase 13 顶上),但 **E5 缺口始终是论文最大风险**。

> **另记**:计划书显式记录了「方向5 虚拟细胞升级」(QSAR → 预测靶点 → FBA → growth 闭环)**不排进 Phase 12–15**,理由是它依赖 Phase 12 的外部验证与 Phase 14 的多物种能力。而本战役的 **T3(机制诚实性)恰好为这条线打了地基** —— 机制恒作候选、G3 门约束,使未来的闭环不会在证据不足时越权声称。

---

## 六、复现

```bash
.venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v2.validation.run_campaign
```

该入口同时重写 `reports/science_v2/phase11/campaign.json` 与本文件,用 `t4_repeats=100`(= 本次存档口径,与 `reports/science_v2/phase11/t4_determinism.json` 的 `n_repeats` 一致)。耗时约 5 分钟,其中绝大部分是 T4 的 35×100 次真实预测。

