"""Render verified observations and clearly attributed LLM hypotheses."""
from __future__ import annotations

import re
from typing import Any


def _citations(refs: list[dict]) -> str:
    return "；".join(f"`{ref['source_id']}`（`{ref['tool_call_id']}{ref['pointer']}`）" for ref in refs)


def _source_citation(citation: str) -> str:
    return re.sub(r"https?://[^\s;,，；]+", lambda match: f"[作者来源](<{match[0]}>)", citation)


def _structure_report(analysis: dict | None) -> list[str]:
    lines = ["", "## 细胞结构与可达性假说", ""]
    if analysis is None:
        return lines + ["未知（本报告未提供经引用核验的结构分析）；蛋白定位与当前细胞结构状态未知。"]
    scopes = {"species_prior": "物种背景（species_prior）；当前菌株结构与状态未知",
              "strain_evidence": "菌株来源证据（strain_evidence）；当前细胞状态仍未验证"}
    types = {"reference_knowledge": "参考知识", "source_annotation": "来源注释", "measured": "来源测定"}
    access = {"unknown": "可达性未知", "potentially_accessible": "可能可达（假说）",
              "potential_barrier": "可能构成屏障（假说）"}
    for section in ("compartment_hypotheses", "accessibility_barriers"):
        for claim in analysis.get(section, []):
            lines.append(f"- 已知（来源记录）：{claim['structure_id']} / {claim['compartment']}；"
                         f"{scopes[claim['evidence_scope']]}；{types[claim['evidence_type']]}。")
            if claim.get("protein_id"):
                lines.append(f"  - 来源中的蛋白定位：{claim['protein_id']}（{claim['protein_namespace']}）/ "
                             f"{claim['compartment']}；不由基因存在推断。")
            else:
                lines.append("  - 蛋白定位：未知（未提供原始蛋白定位记录）。")
            label = access[claim["accessibility"]] if section == "accessibility_barriers" else "区室假说"
            lines.append(f"  - {label}：{claim['hypothesis']}；不表示已验证该候选分子的穿透或结合。")
            lines.append(f"  - 精确引用：{_citations(claim['evidence_refs'])}")
    if not analysis.get("compartment_hypotheses") and not analysis.get("accessibility_barriers"):
        lines.append("结构与可达性：未知（未提供可引用的结构条目）。")
    lines.append("结构分析限制：")
    lines.extend(f"- {limitation}" for limitation in analysis.get("limitations", []))
    if not analysis.get("limitations"):
        lines.append("- 未列出额外限制；候选可达性与当前细胞状态仍未验证。")
    return lines


def render_report(result: dict[str, Any]) -> str:
    if "results" in result:
        return "\n\n---\n\n".join(render_report(item) for item in result["results"])
    candidate = result["candidate"]
    profile = result["profile"]
    species = profile.get("species", "未知物种")
    if isinstance(species, dict):
        species = species.get("scientific_name", "未知物种")
    assessment = result["assessment"]
    mic = assessment["mic_estimate"]
    estimate = "未知（未给出数值）" if mic["value"] is None else f"{mic['value']:g} µg/mL（LLM 估计）"
    species_reference = profile.get("input_role") == "species_reference"
    strain_reference = profile.get("input_role") == "strain_reference"
    identity = (f"- 物种参考档案：{profile.get('profile_id')}；{species}（物种参考背景）" if species_reference else
                f"- 菌株档案：{profile.get('profile_id')}；{species} / {profile.get('strain') or '未知菌株'}")
    lines = [
        f"# 候选 {candidate['id']}", "",
        f"- 状态：{result['status']}",
        identity,
        f"- 结构：`{candidate.get('canonical_smiles') or candidate.get('smiles')}`",
        f"- 活性判断：{assessment['activity']}",
        f"- MIC：{estimate}",
        f"- 信心：{assessment['confidence']['level']}（未经校准）",
        "- 杀伤率 / MBC / 时间杀菌曲线：未知；MIC 表示生长抑制。", "",
        assessment["rationale_summary"], "",
        f"MIC 依据：{mic['reason']}",
    ]
    selected = profile.get("selected_modalities") or result.get("analysis_plan", {}).get("selected_modalities")
    if selected:
        lines.insert(4, f"- 本次组学输入：{'、'.join(selected)}")
    if species_reference or strain_reference:
        source_lines = (["- 预测范围：物种参考背景；各模态来源不表示同一样本，也不代表所有菌株或当前细胞状态。"]
                        if species_reference else [
                            f"- 预测范围：具体菌株 {profile['strain']}；命名空间 {profile['strain_namespace']}；基因型 {profile.get('genotype') or '未知（未确认野生型）'}。",
                            f"- 菌株身份依据：{profile['identity_basis']}",
                            "- 同菌株参考可来自不同培养条件，不表示同一样本；缺失模态不借用其他菌株。",
                        ])
        names = {"genome": "基因组", "transcriptome": "转录组", "proteome": "蛋白组"}
        for name, source in profile.get("modalities", {}).items():
            condition = source.get("condition", {})
            # v2 stores native table semantics inside its selected modality;
            # historical v1 exposes the same fields at the source overview root.
            native = source.get("modalities", {}).get(name, source)
            source_lines.append(f"- {names.get(name, name)}参考来源：{source.get('profile_id')}；"
                                f"来源株 {source.get('strain') or '未知'}；条件 {condition.get('condition_id') or '未知'}；"
                                f"培养基 {condition.get('medium') or '未知'}；"
                                f"来源样本 {'、'.join(source.get('source_samples', [])) or '未知'}。")
            source_lines.extend([
                f"  - 数据解释与来源限制：{native.get('value_semantics') or '未知'}",
                f"  - 观察单位：{native.get('observation_unit') or '未知'}；"
                f"数值单位：{native.get('unit') or '未知'}；尺度：{native.get('scale') or '未知'}。",
                "  - 未知来源条件 / 字段：" + ("、".join(source.get("unknown_fields", [])) or "未列出"),
                "  - 作者引用：" + _source_citation(native.get("provenance", {}).get("citation") or "未知"),
            ])
        lines[5:5] = source_lines
    if mic["evidence_refs"]:
        lines.append(f"引用：{_citations(mic['evidence_refs'])}")
    stages = result.get("agent_trace", {}).get("stages", [])
    review = result.get("agent_review")
    if stages or review:
        lines.extend(["", "## 智能体阶段与审核", ""])
        names = {"planning": "规划", "analysis": "分析", "review": "审核", "revision": "修订"}
        for stage in stages:
            name = names.get(stage.get("stage"), stage.get("stage", "未知阶段"))
            lines.append(f"- {name}：{stage.get('status', '未知')}" +
                         (f"；模型 {stage['model']}" if stage.get("model") else ""))
        if review:
            lines.append(f"- 审核决定：{review.get('decision', '未知')}；处理结果：{result.get('review_resolution', '未记录')}")
            lines.extend(["", review.get("summary", "")])
            for issue in review.get("issues", []):
                lines.append(f"- [{issue.get('severity', 'warning')}] {issue.get('code', '')}：{issue.get('finding', '')}")
                if issue.get("evidence_refs"):
                    lines.append(f"  - 引用：{_citations(issue['evidence_refs'])}")
            changes = review.get("recommended_changes", [])
            if changes:
                lines.append("建议修改：" + "；".join(changes))
    for title, key in (("支持证据", "supporting_evidence"), ("反证", "counterevidence")):
        lines.extend(["", f"## {title}", ""])
        for item in assessment[key]:
            lines.append(f"- {item['claim']}")
            for observation in item["observations"]:
                ref = observation["evidence_ref"]
                lines.append(f"  - {observation.get('gene_id') or '来源字段'} / {observation['field']} = {observation['value']}；"
                             f"`{ref['source_id']}`，`{ref['tool_call_id']}{ref['pointer']}`")
        if not assessment[key]:
            lines.append("未提供可核验观察。")
    lines.extend(["", "## 靶点与机制假说", ""])
    for target in assessment["targets"]:
        lines.append(f"- {target['name']}（{target.get('target_id') or '身份未确认'}）：{target['hypothesis']}。"
                     "这是待验证假说，表达观察不能证明直接作用。")
        if target["evidence_refs"]:
            lines.append(f"  - 观察引用：{_citations(target['evidence_refs'])}")
        if target["counterevidence_refs"]:
            lines.append(f"  - 反证引用：{_citations(target['counterevidence_refs'])}")
    for mechanism in assessment["mechanism_hypotheses"]:
        lines.append(f"- {mechanism['hypothesis']}（待验证假说）")
        if mechanism["evidence_refs"]:
            lines.append(f"  - 观察引用：{_citations(mechanism['evidence_refs'])}")
        if mechanism["counterevidence_refs"]:
            lines.append(f"  - 反证引用：{_citations(mechanism['counterevidence_refs'])}")
    if not assessment["targets"] and not assessment["mechanism_hypotheses"]:
        lines.append("未知。")
    lines.extend(_structure_report(assessment.get("structure_analysis")))
    lines.extend(["", "## 缺口", ""])
    lines.extend(f"- {gap}" for gap in assessment["gaps"])
    if not assessment["gaps"]:
        lines.append("未列出额外缺口；信心仍未经校准。")
    lines.extend(["", f"证据校验：{result['evidence_validation']['status']}；模型：{result['execution_trace']['model']}。", ""])
    return "\n".join(lines)
