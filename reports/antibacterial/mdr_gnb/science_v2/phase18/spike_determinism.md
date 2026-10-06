# P18 spike:接活运行时证据层 + 主动学习的「确定性门」

> 2026-07-17 · /loop 第 1 轮 · 只读探针(未改生产代码)· 脚本 scratchpad/p18_spike.py(临时,未入库)

## 背景

P18 要把两个「装了没接线」的升级件接进生产三方向路径(`run_mdr_query`→`/predict`):
运行时 EvidenceLevel E0-E5(`coordinator/evidence_level.attach_evidence_level`)与主动学习
(`coordinator/active_learning.attach_active_learning`),组合入口 `io/six_outputs.enrich_report`。
路线图点名**头号风险 = 接线破坏确定性**(task_id 内容寻址、跨进程字节一致是硬红线)。本 spike
先探这个门,门过才谈 TDD 接线;不改任何生产代码。

## 预注册判据(跑前定)

- **A 确定性**:同 `result` 两次 `enrich_report` → 排序 JSON **逐字节相等**,且跨 `PYTHONHASHSEED` 稳定。
- **B advisory 红线**:enrich 后 report 的裁决字段(task_id/drug/sir/sir_prob/abstained/abstain_reasons/
  downgrade_reasons/activity/peptide_activity/mic_range/output_kind/mechanism)与 enrich 前**逐字节相等**——
  只能新增 `provenance.evidence_level` / `provenance.active_learning` 两键。
- **C task_id 不受影响**:task_id 由 request 内容寻址(`service.canonical_task_id(raw)`,不读 report),
  故挂 provenance 不改 task_id(代码层已定,附验 report.task_id 字段不变)。

## 结果:门**通过**(all_pass=True)

4 个代表性 case(SIR accept / 无模型物种 / 小分子活性 / OOD 弃权)全过:

| case | det(同进程) | 裁决字段不变 | 新增 provenance 键 | 运行时 ev_level |
|---|---|---|---|---|
| SIR EC×ceftriaxone(accept) | ✅ | ✅ | evidence_level, active_learning | E3 |
| SIR morganella×meropenem(无模型) | ✅ | ✅ | 同上 | E3 |
| 小分子 EC×ciprofloxacin(accept) | ✅ | ✅ | 同上 | E3 |
| OOD EC×甲烷(弃权) | ✅ | ✅ | 同上 | E1 |

- **跨进程**:`PYTHONHASHSEED=0` 与 `=1` 两次运行,4 个 case 的 enriched-report sha256 **逐字相同**
  (f69ccd9a… / b971e528… / 8a97b169… / b1bb0a14…)。
- **代码层确认**:`attach_evidence_level`、`attach_active_learning`、`information_gain` 均为纯函数
  (读 report/request → 确定性映射,**无 wall-clock / 随机 / 文件 IO**,返回新 dict 不 mutate);`enrich_report`
  只组合二者、不写盘(写盘在 `write_six_outputs` 的 6 文件,含 ledger.jsonl append——**接线时不用它**,
  只用 `enrich_report` 或直接两个 attach 函数)。

**结论:接线在确定性上安全,头号风险清除,P18 可进入 TDD。**

## 发现(供 P18 wiring TDD 落实,非本 spike 阻塞项)

1. **两套 E0-E5 同源风险已实证**:运行时 evidence_level 对 SIR EC×ceftriaxone 给 **E3**,而其**验证层**
   tier 是 **E4·strong**(见 E2E 实测)。二者定义不同(运行时读 abstain/OOD/分歧信号;验证层读模型爬到
   证据阶梯哪级)。**接线必须两栏分开标注**「运行时置信」vs「模型验证级」,不可让用户误当同一个 E 级。
2. **无模型/无预测 case 的运行时级偏高**:morganella(无模型、`prediction_available=False`、但 `abstained=False`)
   运行时 evidence_level = **E3**——与真 accept 同级。因为 `map_evidence_level` 读的是 `abstained`(False),
   不看 `prediction_available`。**若直接显示会误导**(E3 暗示有像样置信,实则零预测)。wiring TDD 须:
   要么运行时层纳入 `prediction_available`,要么前端对「无预测结果」分支**不显运行时置信级**。这是接线的
   诚实性红线,预注册进 P18 TDD 验收门。

## 下一步

P18 下一子步:用 writing-plans 写 P18 wiring TDD plan(把 `enrich_report` 接进 `run_mdr_query` 出口或
`api/service.py`,report 挂运行时 evidence_level + active_learning_queue;前端加「运行时置信」栏与
验证徽章分开;落实上面两条发现的守卫),再 TDD 执行 + 双审 + E2E 网页复核(复用维度 3/7)。
