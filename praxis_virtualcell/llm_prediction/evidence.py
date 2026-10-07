"""Check factual citations against the exact tool values seen by the model."""
from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from .diagnostics import _public_value
from .schemas import Assessment, EvidenceReference


def _pointer(data: Any, pointer: str) -> tuple[Any, list[Any]]:
    if not pointer.startswith("/"):
        raise ValueError("pointer must identify a field, not an entire result")
    current = data
    ancestors = [current]
    for part in pointer[1:].split("/"):
        if re.search(r"~(?![01])", part):
            raise ValueError("invalid JSON Pointer escape")
        token = part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            current = current[token]
        elif isinstance(current, list) and re.fullmatch(r"0|[1-9][0-9]*", token):
            current = current[int(token)]
        else:
            raise ValueError("pointer does not resolve")
        ancestors.append(current)
    return current, ancestors


def _equal(actual: Any, quoted: Any) -> bool:
    # Python considers True == 1; expression measurements must not inherit that.
    if isinstance(actual, bool) or isinstance(quoted, bool):
        return type(actual) is type(quoted) and actual == quoted
    if isinstance(actual, (int, float)) and isinstance(quoted, (int, float)):
        return math.isfinite(actual) and math.isfinite(quoted) and actual == quoted
    if type(actual) is not type(quoted):
        return False
    if isinstance(actual, list):
        return len(actual) == len(quoted) and all(_equal(a, b) for a, b in zip(actual, quoted))
    if isinstance(actual, dict):
        return actual.keys() == quoted.keys() and all(_equal(v, quoted[k]) for k, v in actual.items())
    return actual == quoted


def _reference(ref: EvidenceReference, calls: dict[str, dict]) -> tuple[Any, dict | None]:
    call = calls.get(ref.tool_call_id)
    if not call or not call.get("ok"):
        raise ValueError("unknown_or_failed_tool_call")
    actual, ancestors = _pointer(call["data"], ref.pointer)
    if not _equal(actual, ref.value):
        raise ValueError("quoted_value_does_not_match_tool")
    source = next((v.get("source_id") for v in reversed(ancestors)
                   if isinstance(v, dict) and v.get("source_id")), None)
    if source != ref.source_id:
        raise ValueError("source_id_does_not_match_tool")
    gene = next((v for v in reversed(ancestors)
                 if isinstance(v, dict) and (v.get("gene_id") or v.get("feature_id") or v.get("protein_id"))), None)
    return actual, gene


def matching_value_pointers(ref: EvidenceReference, calls: dict[str, dict]) -> list[str]:
    """Suggest at most five actual scalar locations in this same successful call.

    This is diagnostic information only. It never edits a reference or makes an
    invalid assessment admissible. Both value and closest source must match.
    """
    call = calls.get(ref.tool_call_id)
    if not call or not call.get("ok"):
        return []
    matches: list[str] = []

    def walk(value: Any, pointer: str, source_id: Any) -> None:
        if len(matches) >= 5:
            return
        if isinstance(value, dict):
            if value.get("source_id"):
                source_id = value["source_id"]
            for key, child in value.items():
                escaped = str(key).replace("~", "~0").replace("/", "~1")
                walk(child, f"{pointer}/{escaped}", source_id)
                if len(matches) >= 5:
                    break
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{pointer}/{index}", source_id)
                if len(matches) >= 5:
                    break
        elif pointer and source_id == ref.source_id and _equal(value, ref.value):
            matches.append(pointer)

    walk(call.get("data"), "", None)
    return matches


def validate_evidence(
    assessment: Assessment, tool_calls: list[dict], *, diagnostics: list[dict] | None = None,
) -> list[str]:
    """Return issues; a citation verifies an observation, never target causality."""
    calls = {call["tool_call_id"]: call for call in tool_calls}
    issues: list[str] = []
    refs = [(ref, ["mic_estimate", "evidence_refs", i])
            for i, ref in enumerate(assessment.mic_estimate.evidence_refs)]
    available_genes: set[str] = set()
    available_features: set[str] = set()
    available_targets: set[str] = set()
    expression_values: set[float] = set()
    source_ids: set[str] = set()

    def flag(code: str, location: list[str | int], ref: EvidenceReference | None = None) -> None:
        issues.append(code)
        if diagnostics is not None:
            message = ("field must equal the decoded final JSON Pointer segment; "
                       "/condition/medium -> medium; /genes/0/expression_value -> expression_value"
                       if code == "observation_field_does_not_match_pointer" else code)
            entry = {"location": location, "code": code, "message": message}
            if ref is not None:
                entry["offending_reference"] = _public_value(ref.model_dump())
                entry["matching_value_pointers"] = matching_value_pointers(ref, calls)
            if entry not in diagnostics:
                diagnostics.append(entry)

    def collect_sources(value: Any) -> None:
        if isinstance(value, dict):
            if isinstance(value.get("source_id"), str):
                source_ids.add(value["source_id"])
            for child in value.values():
                collect_sources(child)
        elif isinstance(value, list):
            for child in value:
                collect_sources(child)

    for call in tool_calls:
        if call.get("ok"):
            collect_sources(call.get("data"))
        if call.get("ok") and call.get("name") in {"query_genes", "search_annotations", "query_features", "search_features"}:
            data = call.get("data", {})
            for gene in data.get("genes", data.get("features", [])):
                if gene.get("feature_id") or gene.get("gene_id") or gene.get("protein_id"):
                    available_features.add(gene.get("feature_id") or gene.get("gene_id") or gene["protein_id"])
                if gene.get("gene_id"):
                    available_genes.add(gene["gene_id"])
                    available_targets.add(gene["gene_id"])
                if gene.get("protein_id"):
                    available_targets.add(gene["protein_id"])
                measured = gene.get("expression_value")
                if isinstance(measured, (int, float)) and not isinstance(measured, bool) and math.isfinite(measured):
                    expression_values.add(float(measured))
    if not available_features:
        flag("no_gene_observations_loaded", [])

    for section_name in ("supporting_evidence", "counterevidence"):
        for item_index, item in enumerate(getattr(assessment, section_name)):
            item_location = [section_name, item_index]
            if not item.observations:
                flag("evidence_claim_requires_structured_observations", item_location + ["observations"])
            refs.extend((ref, item_location + ["evidence_refs", i]) for i, ref in enumerate(item.evidence_refs))
            for observation_index, observation in enumerate(item.observations):
                location = item_location + ["observations", observation_index]
                ref = observation.evidence_ref
                refs.append((ref, location + ["evidence_ref"]))
                try:
                    actual, gene = _reference(ref, calls)
                    if not _equal(actual, observation.value):
                        flag("observation_value_does_not_match_tool", location + ["value"], ref)
                    pointer_field = ref.pointer.rsplit("/", 1)[-1].replace("~1", "/").replace("~0", "~")
                    if pointer_field != observation.field:
                        flag("observation_field_does_not_match_pointer", location + ["field"], ref)
                    if gene and gene.get("gene_id") and observation.gene_id != gene["gene_id"]:
                        flag("observation_gene_does_not_match_tool", location + ["gene_id"], ref)
                    if observation.gene_id and (not gene or observation.gene_id != gene.get("gene_id")):
                        flag("observation_gene_not_loaded", location + ["gene_id"], ref)
                except (KeyError, IndexError, TypeError, ValueError):
                    # The reference-specific reason is collected below as well.
                    flag("invalid_observation_reference", location + ["evidence_ref"], ref)

    for target_index, target in enumerate(assessment.targets):
        location = ["targets", target_index]
        refs.extend((ref, location + ["evidence_refs", i]) for i, ref in enumerate(target.evidence_refs))
        refs.extend((ref, location + ["counterevidence_refs", i]) for i, ref in enumerate(target.counterevidence_refs))
        if target.target_id and target.target_id not in available_targets:
            flag("target_identity_not_observed", location + ["target_id"])
        if target.target_id:
            bound = False
            for ref in target.evidence_refs:
                try:
                    _, gene = _reference(ref, calls)
                    bound |= bool(gene and target.target_id in {gene.get("gene_id"), gene.get("protein_id")})
                except (KeyError, IndexError, TypeError, ValueError):
                    pass
            if not bound:
                if target.evidence_refs:
                    for ref_index, ref in enumerate(target.evidence_refs):
                        flag("target_identity_not_bound_to_evidence", location + ["evidence_refs", ref_index], ref)
                else:
                    flag("target_identity_not_bound_to_evidence", location + ["evidence_refs"])
    for mechanism_index, mechanism in enumerate(assessment.mechanism_hypotheses):
        location = ["mechanism_hypotheses", mechanism_index]
        refs.extend((ref, location + ["evidence_refs", i]) for i, ref in enumerate(mechanism.evidence_refs))
        refs.extend((ref, location + ["counterevidence_refs", i]) for i, ref in enumerate(mechanism.counterevidence_refs))

    mic_has_gene_evidence = False
    for ref, location in refs:
        try:
            _, gene = _reference(ref, calls)
            if (location[0] == "mic_estimate" and gene and calls[ref.tool_call_id].get("name")
                    in {"query_genes", "search_annotations", "query_features", "search_features"}):
                mic_has_gene_evidence = True
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            reason = str(exc) if isinstance(exc, ValueError) else "unresolved_evidence_pointer"
            flag(reason, location, ref)
    if assessment.mic_estimate.value is not None and not mic_has_gene_evidence:
        if assessment.mic_estimate.evidence_refs:
            for ref_index, ref in enumerate(assessment.mic_estimate.evidence_refs):
                flag("numeric_mic_requires_verified_gene_evidence", ["mic_estimate", "evidence_refs", ref_index], ref)
        else:
            flag("numeric_mic_requires_verified_gene_evidence", ["mic_estimate", "evidence_refs"])

    # Native gene IDs mentioned in free text must also have been returned by a
    # tool. This catches fabricated ABUW IDs outside the structured fields.
    texts = [assessment.rationale_summary, assessment.mic_estimate.reason, *assessment.gaps]
    texts.extend(item.claim for item in (*assessment.supporting_evidence, *assessment.counterevidence))
    texts.extend(target.hypothesis + " " + target.name for target in assessment.targets)
    texts.extend(item.hypothesis for item in assessment.mechanism_hypotheses)
    mentioned = set(re.findall(r"\bABUW_[A-Za-z0-9]+\b", " ".join(texts)))
    if mentioned - available_genes:
        flag("gene_in_text_not_observed", ["public_text"])
    cited_sources = {source.rstrip(".,;") for source in re.findall(r"\bomics:[A-Za-z0-9_.:-]+", " ".join(texts))}
    if cited_sources - source_ids:
        flag("source_in_text_not_observed", ["public_text"])
    # Machine references remain exact. Prose may round a decimal measurement to
    # its displayed precision, but integers do not gain a rounding tolerance.
    pattern = r"(?:expression(?:[_ ]value)?|表达(?:值|量)?)\s*(?:为|是|[:=]|is|of|at|equals)?\s*([-+]?(?:\d*\.\d+|\d+)(?:[eE][+-]?\d+)?)"
    quantities = re.findall(pattern, " ".join(texts), flags=re.IGNORECASE)
    observed_decimals = {Decimal(str(value)) for value in expression_values}

    def observed_display(quantity: str) -> bool:
        displayed = Decimal(quantity)
        if displayed in observed_decimals:
            return True
        if "." not in quantity:
            return False
        quantum = Decimal((0, (1,), displayed.as_tuple().exponent))
        for actual in observed_decimals:
            try:
                if actual.quantize(quantum, rounding=ROUND_HALF_UP) == displayed:
                    return True
            except InvalidOperation:
                continue
        return False

    if any(not observed_display(quantity) for quantity in quantities):
        flag("expression_quantity_in_text_not_observed", ["public_text"])
    return sorted(set(issues))


def validate_modality_coverage(assessment: Assessment, tool_calls: list[dict], selected: list[str]) -> list[str]:
    """Every selected modality must actually be read and cited as an observation.

    Declaring a modality in an overview does not establish its use. Only exact
    references to successful feature/gene tool rows count, including zero values.
    """
    calls = {call["tool_call_id"]: call for call in tool_calls}
    observed: set[str] = set()
    cited: set[str] = set()
    names = {"query_genes", "search_annotations", "query_features", "search_features"}
    for call in tool_calls:
        if call.get("ok") and call.get("name") in names:
            data = call.get("data", {})
            for row in data.get("genes", data.get("features", [])):
                observed.add(row.get("modality") or data.get("modality") or "transcriptome")
    for item in (*assessment.supporting_evidence, *assessment.counterevidence):
        for observation in item.observations:
            ref = observation.evidence_ref
            call = calls.get(ref.tool_call_id, {})
            if call.get("name") not in names:
                continue
            try:
                _, row = _reference(ref, calls)
                if row and _equal(observation.value, ref.value):
                    cited.add(row.get("modality") or call.get("data", {}).get("modality") or "transcriptome")
            except (KeyError, IndexError, ValueError, TypeError):
                continue
    return [issue for modality in selected for issue in (
        *([f"selected_modality_not_observed:{modality}"] if modality not in observed else []),
        *([f"selected_modality_not_cited:{modality}"] if modality not in cited else []),
    )]
