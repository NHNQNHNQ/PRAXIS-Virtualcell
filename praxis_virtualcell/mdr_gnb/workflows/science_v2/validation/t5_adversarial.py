"""T5:对抗输入验证。非法/超长/乱码 SMILES 与序列、化合物名称变体必须 fail-closed 或
一致解析,绝不崩管线、绝不编 MIC。

平台核心卖点验证(与 T2 OOD 互补):T2 测"训练分布外但结构合法"的输入弃权;T5 测
"结构本身就非法/畸形/超长/乱码"的输入不能让管线崩溃、也不能蒙出一个 MIC。

--- 实跑探明(compound,BAD_SMILES)------------------------------------------------
逐条实测(见 test_t5_adversarial.py::test_bad_smiles_fail_closed):
  - "not_a_smiles" / "((((" / "☠️💊" / ""(空串):RDKit 解析失败或空输入 →
    abstain_reasons=compound_featurization_failed / compound_smiles_missing,
    fail-closed 正确,无崩溃。
  - "C" * 5000(超长纯碳链):历史缺口,**Phase 12 已修复**。曾是语法合法的 SMILES,
    sm_activity_model 的 OOD 判据只看 Morgan 指纹对训练集最大 Tanimoto(阈值 0.30);实测无论
    链长 50/500/1000/5000,Morgan(radius=2)指纹在长链中部趋同饱和,max_tanimoto 恒 0.6154
    (> 0.30 判非 OOD),平台对任意长度纯碳长链给同一个"自信"MIC(log10_mic=1.2693)——
    Tanimoto 集合相似度对"加原子"单调失明的真实红线。**Phase 12 加了加法方向结构 sanity gate**
    (sm_activity 重原子数上限 SM_HAC_MAX=516、组分数上限,独立于 Tanimoto):HAC=5000 远超阈,
    现 fail-closed 弃权(reason=compound_size_out_of_range),不再泄漏。
    故 leaked 判定/findings 生成逻辑仍在(防回归:若将来又泄漏会重新上浮),但当前 leaks/findings
    均为空;测试侧的 strict xfail 已随缺口一并收掉(见 test_known_ood_gap_long_homopolymer_
    fail_closed 现为正常回归用例)。无性能/DoS 问题(5000 字符 <150ms)。

--- 实跑探明(peptide,BAD_SEQUENCES)-----------------------------------------------
逐条实测(见 test_t5_adversarial.py::test_bad_sequence_fail_closed):
  "ACGT123"(核酸字符掺杂)/ "😀😀😀"(emoji)/ "BBB"(非标准氨基酸 B 三连)/
  "X" * 5000(超长未知残基)/ ""(空串)—— 全部 5 条均 fail-closed
  (peptide_featurization_failed / peptide_sequence_missing),无一崩溃、无一泄漏。
  肽侧特征化(20 组成 + 6 理化)对非法字符集直接拒绝,没有"长同聚物饱和"这类漏洞。

--- 名称一致性(name_consistency,需联网 PubChem)-----------------------------------
ciprofloxacin / Ciprofloxacin / cipro 三个变体经 compound_resolver 解析到同一
canonical SMILES → run_mdr_query 给出同一 MIC(实测 log10_mic=-0.7799,
max_tanimoto=1.0,因该药本就在 ChEMBL 训练集里)。中文名"环丙沙星"经 PubChem
PUG-REST 查询返回 404 PUGREST.NotFound(其名称索引未收录该中文名,非我方 bug)→
诚实 fail-closed(compound_resolution_failed),不猜不编。无网时整体 gracefully skip
(不假装跑过)。

本子项**内部**的 crash(逐变体 run_query 抛 / resolve_compound 探针自身抛)由
_name_consistency_crashes() 抽出并汇入顶层 findings(id=name_consistency_crash,
severity=red_line),与其它 crash 一致地被看见 —— 此前它们只躺在子项里,而 T8 战役裁决
只读 findings,「名称解析路径崩了」对裁决完全不可见。诚实的无网 skip 不是 crash,不汇入。
"""
from __future__ import annotations

from typing import Any

from praxis_virtualcell.mdr_gnb.workflows.science_v2.validation import harness

_COMPOUND_SPECIES = "escherichia_coli"
_PEPTIDE_SPECIES = "escherichia_coli"

# 固定对抗语料(与 test_t5_adversarial.py 保持同款取值,供 run_adversarial_suite 汇总统计)。
BAD_SMILES: list[str] = ["not_a_smiles", "C" * 5000, "((((", "☠️💊", ""]
BAD_SEQUENCES: list[str] = ["ACGT123", "😀😀😀", "B" * 3, "X" * 5000, ""]

# 名称一致性探针:同一药物的多种书写变体 + 一个 PubChem 索引不到的中文名(诚实 fail-closed 对照组)。
NAME_VARIANTS: tuple[str, ...] = ("ciprofloxacin", "Ciprofloxacin", "cipro", "环丙沙星")


def _compound_query(smiles: str) -> dict[str, Any]:
    return {
        "species": _COMPOUND_SPECIES,
        "smiles": smiles,
        "drug_panel": [{"drug": smiles, "drug_class": "novel_compound"}],
        "requested_outputs": ["activity"],
    }


def _peptide_query(sequence: str) -> dict[str, Any]:
    return {
        "species": _PEPTIDE_SPECIES,
        "sequence": sequence,
        "drug_panel": [{"drug": sequence, "drug_class": "antimicrobial_peptide"}],
        "requested_outputs": ["peptide_activity"],
    }


def _compound_name_query(name: str) -> dict[str, Any]:
    """走 compound 标识符解析路径(非 smiles),供 name_consistency 用(注意用 compound 字段)。"""
    return {
        "species": _COMPOUND_SPECIES,
        "compound": name,
        "drug_panel": [{"drug": name, "drug_class": "novel_compound"}],
        "requested_outputs": ["activity"],
    }


def compound(smiles: str) -> dict[str, Any]:
    """跑一条(可能非法/超长/乱码的)SMILES 活性查询,返回 harness.run_query 扁平 dict。

    刻意不在此处 try/except:run_mdr_query 内部对 predictor 调用已有
    `except Exception: pred = None` 兜底(见 workflows/run_mdr_query.py),让真崩溃
    (若有)原样冒出不静默吞掉——统计 crashed 是 run_adversarial_suite() 的职责。
    """
    return harness.run_query(_compound_query(smiles))


def peptide(sequence: str) -> dict[str, Any]:
    """跑一条(可能非法/超长/乱码的)序列肽活性查询,返回扁平 dict。同 compound() 不吞异常。"""
    return harness.run_query(_peptide_query(sequence))


def _kleene_and(*vals: bool | None) -> bool | None:
    """三值(Kleene)合取,给 consistent 汇总各子项用:False > None > True(优先级从高到低)。

      · 任一子项 False → **False**:已经**发现**了真不一致 —— 这是个挣来的正面发现,
        不该被另一个「无从判断」的子项冲淡成 None。
      · 否则任一子项 None → **None**:有一半属性压根没被检验 → 整体只能算「未被完整验证」。
      · 全 True → **True**。
    ⚠️ 不能用内建 `all()`:`all([True, None])` == False —— 会把「无从判断」误报成「不一致」,
    正是本模块反复设防的那类**反方向编造**(假警报)。
    """
    if any(v is False for v in vals):
        return False
    if any(v is None for v in vals):
        return None
    return True


def _same_activity(comparable: bool, activity_set: set[tuple[Any, ...] | None]) -> bool | None:
    """「≥2 个变体给出了**同一个 MIC**」的三态判读。四情形①②③④与完整理由见 name_consistency
    的 docstring(那里是面向报告读者的契约,此处只放分支)。

    要害:`activity_set` 里的 `None` 是**弃权**(压根没有 MIC),不是一个 MIC **值** —— 故
    **不能**拿它的基数直接下结论:全弃权时 `{None}` 的基数也是 1,会把「都没给答案」算成
    「给了同一个答案」。`comparable`(解析半场的分母守卫)在此**拦不住** —— ④ 下
    n_resolved≥2 故 comparable=True,域非空,哨兵 None 就落在值域**内部**。唯一出路是把
    None 抬出值比较、单独记账,即下面第三个分支。
    """
    if not comparable:
        return None                    # 无第二方可比(分母 n_resolved < 2)
    if len(activity_set) > 1:
        return False                   # ②③ 真不一致(含「有的给 MIC 有的弃权」)
    if activity_set == {None}:
        return None                    # ④ 全部弃权:零个 MIC,该半从未被检验
    return True                        # ① ≥2 个变体给出了同一个 MIC


def name_consistency(variants: tuple[str, ...] = NAME_VARIANTS) -> dict[str, Any]:
    """名称变体一致性(需联网 PubChem)。无网/探测异常 → 诚实 {"skipped": True, ...},不假装跑过。

    能解析的变体必须给出同一 canonical SMILES → 同一 MIC(activity 相等);
    解析不了的(如未被 PubChem 名称索引收录)fail-closed,不猜不编。
    注意这条性质是个**合取**,两半各有各的分母,必须分别检验:
      ①「同一 canonical SMILES」—— 分母 n_resolved(几个变体解析成功);
      ②「→ 同一 MIC」        —— 分母 n_with_activity(几个变体真给出了 MIC)。

    --- 三个比较字段都是**三态**:True / False / None(JSON 里 null)------------------
    `comparable = n_resolved >= 2`:少于 2 个变体解析成功 → 无第二方可比 → 三个字段全 None。
    `mic_comparable = n_with_activity >= 2`:真正比对过 ≥2 个 MIC 才谈得上「同一 MIC」。

    ⚠️ **下游消费者注意**:拿它当门槛须显式 `is True` / `is None` 区分,**勿用真值判断**
    (`if not nc["consistent"]`)—— None 与 False 同为假值,真值判断会把「无从判断」误当成
    「不一致」,即把「一个都没解析出来 / 一个 MIC 都没产出」读成「平台有名称解析 bug」。
    __main__ 的印法即按此。

    --- same_canonical_smiles:为什么 n_resolved<2 时是 None(前一轮修复)---------------
    修复前写的是 `len(canon_set) <= 1`,而 `<=1` 对**空集**和**单元素集**都成立。于是
    「全部变体都没解析出来」(n_resolved=0)会报 consistent=True,报告读作「名称一致」——
    实则一个都没解析出来,**空集恒真**的假安慰。n_resolved=1 同理:单元素集里没有「互相」。
    也不能是 False:那是「名称不一致」这一**正面断言**,零样本下同属编造,且会造**假警报**
    (读者以为平台有解析 bug,真相只是 PubChem 没收录),还与「真不一致」不可区分。
    诚实的表达只能是「无从判断」。

    --- same_activity:为什么「全部弃权」是 None 而不是 True(本轮修复)-----------------
    弃权(activity=None)也会作为 None 落进 activity_set,故 `len(activity_set)==1`
    **不**等价于「都给出了同一个 MIC」—— 全部变体弃权时集合是 `{None}`,基数也是 1。
    这**不是**空集恒真(activity_set 非空),而是它的近亲:把 None(**没有答案**)当成一个
    **值**塞进值集合去数基数,于是「都没给答案」被算成了「给了同一个答案」。
    按分母看即知:n_with_activity=0 时,②「→ 同一 MIC」的分母是零,该半从未被检验过。
    分四种情形(与测试 test_name_consistency_all_abstained_* / *_mixed_activity_* 对应):
      ① 都给 MIC 且相同  activity_set={t}      → True (挣来的:n_with_activity=n_resolved≥2)
      ② 都给 MIC 但不同  activity_set={t1,t2}  → False(真不一致)
      ③ 有的给有的弃权   activity_set={t,None} → False(**真不一致**:同一 SMILES,一个给
                                                  MIC 一个不给,是平台行为不自洽)
      ④ 全部弃权         activity_set={None}   → None (无 MIC 可比 = 无从判断)
    ⚠️ `mic_comparable` **不是** ③ 判 False 的前提:③ 里只有 1 个 MIC(mic_comparable=False)
    时**仍然** False —— 不一致来自「结果形态不同」(一个给一个不给),不需要凑够两个 MIC 才能
    断定。mic_comparable 只是 True 分支的分母凭据(`same_activity is True` ⟹ 它必为 True)。

    为什么 ④ 必须改(而非「同样的非答案也是同样的答案」):后者是关于**行为一致性**的真陈述,
    但它与②「→ 同一 MIC」被焊在了同一个字段里,而字段名与 consistent 卖给读者的是后者。
    按读者动作分野:`consistent=True` → 「名称一致性已验证,放心」;真相(零个 MIC 产出)→
    「该追查为什么名称路径一个 MIC 都没出」。**导向相反动作 → 假安慰 → 必须改**。
    改后并未丢掉那个真陈述:④ 下 `same_canonical_smiles` 仍是 True(解析这半确实挣来了),
    读者看 `same_canonical_smiles=True, same_activity=None, n_with_activity=0` 得到的信息
    **严格多于**一个 `consistent=True`。

    --- 为什么改 consistent 却**不**改 unresolved_fail_closed(二者同为 all/len 恒真族)---
    `unresolved_fail_closed = all(...)` 在 unresolved==[] 时也是 `all([])` → True。二者在
    **形式逻辑上完全同族**(都是空集上的全称量化,空真性对两者都成立),**故意保留**的理由
    不是形式的而是**语用的** —— 看读者拿这个字段做什么决策:
      · `unresolved_fail_closed` 是**安全护栏**:空集与「真的没泄漏」导向**同一个**读者动作
        (不必担心),故空真**无害**;且分母 n_unresolved 就在旁边透出。
      · `consistent` 是**能力证据**:空集与「真的一致」导向**相反**动作(前者该追查为何一个都
        没解析出来,后者可以放心)。「零解析」其实比「不一致」更糟,却报出最好看的值 ——
        这才是假安慰。
    同仓 run_campaign.compute_verdict() 对 `all({})` 恒真(空 gates 假绿)也专门设防,同一族问题。
    """
    from praxis_virtualcell.mdr_gnb.drug_agent.compound_resolver import resolve_compound

    try:
        probes = {v: resolve_compound(v) for v in variants}
    except Exception as e:  # 防御性:resolve_compound 已自行兜底,这里再兜一层
        # 注意这个形状对顶层是**有歧义**的:它与真无网的诚实 skip 共用 skipped 字段,
        # 故 reason 前缀 network_probe_crashed 是 _name_consistency_crashes() 赖以把它
        # 认成 crash、汇进顶层 findings 的唯一凭据 —— 改前缀即等于把崩溃重新藏起来。
        # (由 test_name_consistency_probe_crash_surfaces_in_top_level_findings 钉住)
        return {"skipped": True, "reason": f"network_probe_crashed:{type(e).__name__}: {e}"}

    if all((not p.get("ok")) and p.get("reason") == "network_error" for p in probes.values()):
        return {"skipped": True, "reason": "network_unavailable(全部变体 resolve→network_error)"}

    results: list[dict[str, Any]] = []
    for v in variants:
        probe = probes[v]
        try:
            r = harness.run_query(_compound_name_query(v))
        except Exception as e:
            results.append({"variant": v, "crashed": True, "error": f"{type(e).__name__}: {e}"})
            continue
        results.append({
            "variant": v,
            "resolved": bool(probe.get("ok")),
            "canonical_smiles": probe.get("smiles"),
            "resolve_reason": probe.get("reason"),
            "abstained": r["abstained"],
            "activity": r["activity"],
        })

    resolved = [x for x in results if x.get("resolved")]
    canon_set = {x["canonical_smiles"] for x in resolved}
    # ⚠️ 弃权(activity=None)也会作为 None 落进这个集合 —— 故 `len(activity_set) == 1`
    # **不**等价于「都给出了同一个 MIC」(全弃权时集合是 {None},基数也是 1)。
    # 分情形的判读见 _same_activity() 与本函数 docstring;别在别处直接用它的基数下结论。
    activity_set = {
        tuple(sorted(x["activity"].items())) if x["activity"] is not None else None
        for x in resolved
    }
    with_activity = [x for x in resolved if x["activity"] is not None]
    unresolved = [x for x in results if not x.get("resolved") and not x.get("crashed")]
    unresolved_fail_closed = all(
        x["abstained"] is True and x["activity"] is None for x in unresolved
    )
    crashed = [x for x in results if x.get("crashed")]

    # 「互相一致」至少要有两方才谈得上。少于 2 个解析成功 → **无从比较**,三态里取 None
    # (JSON 里是 null),而不是 True/False —— 两者都是在编造一个从未被验证过的正面断言。
    # 分母 n_resolved 就在返回里,读者可自行核对 comparable 的由来。
    comparable = len(resolved) >= 2
    # 「→ 同一 MIC」这半的分母:真给出了 MIC 的变体数。两个分母**各管一半**,不可互相顶替 ——
    # comparable 只管「解析成功够不够 2 个」,挡不住「解析成功了但 MIC 一个都没产出」。
    mic_comparable = len(with_activity) >= 2

    same_activity = _same_activity(comparable, activity_set)

    # comparable 为真时 canon_set 至少有 1 个元素,故 `== 1` 与 `<= 1` 等价而意图更清楚。
    same_canonical_smiles = (len(canon_set) == 1) if comparable else None

    return {
        "skipped": False,
        "n_variants": len(variants),
        "n_resolved": len(resolved),
        "n_with_activity": len(with_activity),
        "n_unresolved": len(unresolved),
        "n_crashed": len(crashed),
        "comparable": comparable,
        "mic_comparable": mic_comparable,
        "same_canonical_smiles": same_canonical_smiles,
        "same_activity": same_activity,
        # 三值合取:任一半 False → False(发现了真不一致);否则任一半 None → None(未被完整
        # 验证);全 True 才 True。**不能**用 all():all([True, None]) 会假警报成 False。
        "consistent": _kleene_and(same_canonical_smiles, same_activity),
        "unresolved_fail_closed": unresolved_fail_closed,
        "results": results,
    }


# 产品侧修复建议(顶层 findings 消费,供 T8 战役裁决读取)。Phase 12 已给 sm_activity/peptide
# 加了加法方向结构 sanity gate(重原子数/组分数/序列长度上限,独立于 Tanimoto),常见泄漏已堵。
# 本字段仅在**仍有新泄漏**时才会被 _build_findings 触发,届时说明现 gate 判据未覆盖该形态,须扩展。
_OOD_GAP_RECOMMENDATION = (
    "该输入仍绕过了现有加法方向 sanity gate(Phase 12:sm_activity 重原子数上限 SM_HAC_MAX、"
    "组分数上限)——说明其形态未被现判据覆盖(如另一类规模/计量维度)。请据其结构特征扩展 gate 判据,"
    "使之独立于 Tanimoto 集合相似度。"
)


def _name_consistency_crashes(nc: dict[str, Any]) -> list[dict[str, Any]]:
    """从 name_consistency 的产出里抽出**内部 crash**,供顶层 findings 汇入。

    为什么需要:name_consistency 自己把两类崩溃兜住了,但只记在子项里 —— 顶层 findings
    看不见,而 T8 战役裁决(run_campaign)**只读 findings**。名称解析路径崩了却不进裁决,
    等于没被看见。两种形状:
      ①探针崩溃 → {"skipped": True, "reason": "network_probe_crashed:..."}:最阴的一种,
        它与「真没网」的诚实 skip 挤在同一个字段里,顶层看上去只是「跳过了一项」。
      ②逐变体崩溃 → results 里的 {"crashed": True, "error": ...}。
    注意 reason=network_unavailable 的 skip **不是** crash(那是诚实降级),不得汇入 ——
    否则一台没网的机器会凭空造出红线。确定性:按 results 原序。
    """
    if nc.get("skipped"):
        reason = nc.get("reason") or ""
        if reason.startswith("network_probe_crashed"):
            return [{"variant": "<resolve_compound 探针>", "error": reason}]
        return []
    return [{"variant": r["variant"], "error": r["error"]}
            for r in nc.get("results", []) if r.get("crashed")]


def _build_findings(compound_leaks: list[dict[str, Any]],
                    peptide_leaks: list[dict[str, Any]],
                    crashes: list[dict[str, Any]],
                    name_crashes: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """从实测 leaks/crashes 数据驱动生成顶层 findings(红线缺口),供 T8 战役裁决消费。

    确定性:严格按 compound_leaks → peptide_leaks → crashes → name_crashes 顺序;
    无 leak/crash → findings=[](产品修好该缺口后本字段自动清空,与 xfail 变 XPASS 双重提醒)。
    """
    findings: list[dict[str, Any]] = []
    for r in compound_leaks:
        findings.append({
            "id": "ood_gap_long_homopolymer",
            "severity": "red_line",
            "kind": "leak",
            "surface": "sm_activity",
            "summary": ("结构合法但化学荒谬的输入(超长同聚物 SMILES)绕过 Tanimoto-only "
                        "OOD 判据,平台未 fail-closed、给出了自信 MIC"),
            "example_input": r["input"],
            "leaked_activity": r["activity"],
            "recommendation": _OOD_GAP_RECOMMENDATION,
        })
    for r in peptide_leaks:
        findings.append({
            "id": "ood_gap_peptide_leak",
            "severity": "red_line",
            "kind": "leak",
            "surface": "peptide_activity",
            "summary": "非法/超长序列未 fail-closed、给出了自信 MIC",
            "example_input": r["input"],
            "leaked_activity": r["peptide_activity"],
            "recommendation": "肽侧特征化/OOD 判据需拦截该序列;修复不在本任务,另开独立任务。",
        })
    for r in crashes:
        findings.append({
            "id": "pipeline_crash",
            "severity": "red_line",
            "kind": "crash",
            "surface": "run_mdr_query",
            "summary": "对抗输入让管线抛异常未被兜住(fail-closed 兜底失效)",
            "example_input": r["input"],
            "error": r["error"],
            "recommendation": ("run_mdr_query 的 except 兜底需覆盖该异常路径;"
                               "修复不在本任务,另开独立任务。"),
        })
    for r in name_crashes or []:
        findings.append({
            "id": "name_consistency_crash",
            "severity": "red_line",
            "kind": "crash",
            "surface": "compound_resolver",
            "summary": "化合物名称解析路径抛异常未被兜住(fail-closed 兜底失效)",
            "example_input": r["variant"],
            "error": r["error"],
            "recommendation": ("compound_resolver / 名称查询路径的异常兜底需覆盖该路径;"
                               "修复不在本任务,另开独立任务。"),
        })
    return findings


def _summarize_input(raw: str) -> str:
    return raw if len(raw) < 60 else raw[:60] + f"...(len={len(raw)})"


def _run_one(fn, raw: str, activity_key: str) -> dict[str, Any]:
    """跑一条对抗输入,分类 fail_closed / leaked / crashed。真崩溃在此兜住计数,不让
    run_adversarial_suite() 因单条崩溃就中断全量统计——但仍如实记入 crashes,不吞异常信息。"""
    try:
        r = fn(raw)
    except Exception as e:
        return {"input": _summarize_input(raw), "outcome": "crashed",
                "error": f"{type(e).__name__}: {e}"}
    leaked = (not r["abstained"]) and r[activity_key] is not None
    return {
        "input": _summarize_input(raw),
        "outcome": "leaked" if leaked else "fail_closed",
        "abstained": r["abstained"],
        activity_key: r[activity_key],
        "abstain_reasons": r.get("abstain_reasons"),
    }


def run_adversarial_suite() -> dict[str, Any]:
    """跑全部 BAD_SMILES / BAD_SEQUENCES,统计 fail-closed / 崩溃 / 泄漏 + 名称一致性。

    crashed 和 leaked 都是红线:前者=兜底失效(管线崩了),后者=对非法/超长输入编出了
    具体 MIC(平台不该对"结构合法但化学上荒谬"的输入盲目自信,但实测发现"C"*5000 确实
    如此——如实记入 leaks,不通过改测试/改本函数掩盖,见模块 docstring)。

    计数口径:n_crashed / n_leaked / n_fail_closed 只统计 BAD_SMILES + BAD_SEQUENCES 两族
    对抗语料(=n_total)。name_consistency 的内部 crash **不**计入 n_crashed(不改既有红线
    语义/门槛口径),但会汇入顶层 findings —— 它带 severity=red_line,依 run_campaign 的
    预注册规则2 同样拉黑战役裁决,故「名称路径崩了」不会被裁决漏看。
    """
    smiles_results = [_run_one(compound, s, "activity") for s in BAD_SMILES]
    seq_results = [_run_one(peptide, s, "peptide_activity") for s in BAD_SEQUENCES]
    all_results = smiles_results + seq_results

    crashes = [r for r in all_results if r["outcome"] == "crashed"]
    leaks = [r for r in all_results if r["outcome"] == "leaked"]
    n_fail_closed = sum(1 for r in all_results if r["outcome"] == "fail_closed")

    compound_leaks = [r for r in smiles_results if r["outcome"] == "leaked"]
    peptide_leaks = [r for r in seq_results if r["outcome"] == "leaked"]
    nc = name_consistency()
    name_crashes = _name_consistency_crashes(nc)
    findings = _build_findings(compound_leaks, peptide_leaks, crashes, name_crashes)

    return {
        "n_bad_smiles": len(BAD_SMILES),
        "n_bad_sequences": len(BAD_SEQUENCES),
        "n_total": len(all_results),
        "n_fail_closed": n_fail_closed,
        "n_crashed": len(crashes),
        "n_leaked": len(leaks),
        # 顶层醒目缺口清单(数据驱动自 leaks/crashes),供 T8 战役裁决消费;无缺口→空列表。
        "findings": findings,
        "n_findings": len(findings),
        "crashes": crashes,
        "leaks": leaks,
        "smiles_results": smiles_results,
        "sequence_results": seq_results,
        "name_consistency": nc,
    }


if __name__ == "__main__":
    payload = run_adversarial_suite()
    p = harness.write_report("t5_adversarial", payload)
    print(f"t5_adversarial 报告写入 {p}")
    print(f"  坏 SMILES {payload['n_bad_smiles']} 条 + 坏序列 {payload['n_bad_sequences']} 条"
          f" = {payload['n_total']} 条")
    print(f"  fail-closed {payload['n_fail_closed']} / 崩溃 {payload['n_crashed']}"
          f" / 泄漏 {payload['n_leaked']}")
    if payload["n_crashed"]:
        print(f"  崩溃明细:{payload['crashes']}")
    if payload["n_leaked"]:
        print(f"  泄漏明细(红线):{payload['leaks']}")
    if payload["n_findings"]:
        print(f"  红线缺口 findings({payload['n_findings']} 条,供 T8 裁决):")
        for f in payload["findings"]:
            print(f"    - [{f['severity']}] {f['id']}: {f['summary']}")
    nc = payload["name_consistency"]
    if nc.get("skipped"):
        print(f"  name_consistency 跳过:{nc['reason']}")
    else:
        # consistent 是三态,None=无从判断,别印成看着像 True 的东西。None 有**两个**来源
        # (解析不足 2 个 / 解析一致但 MIC 一个都没产出),分别印明白 —— 二者要读者做的事不同。
        # 同时透出两个分母 n_resolved 与 n_with_activity ——「一致」是基于几个变体、几个 MIC
        # 得出的,读者有权自行核对。
        c = nc["consistent"]
        if c is None:
            why = ("解析成功不足 2 个,无可比对象" if not nc["comparable"]
                   else "解析一致,但变体全部弃权、零个 MIC 产出,「同一 MIC」未被检验")
            verdict = f"无从判断({why})"
        else:
            verdict = str(c)
        print(f"  name_consistency consistent={verdict}"
              f" [解析成功 {nc['n_resolved']}/{nc['n_variants']},其中给出 MIC "
              f"{nc['n_with_activity']} 个]"
              f" same_canonical_smiles={nc['same_canonical_smiles']}"
              f" same_activity={nc['same_activity']}"
              f" unresolved_fail_closed={nc['unresolved_fail_closed']}"
              f" [未解析 {nc['n_unresolved']} 条]")
