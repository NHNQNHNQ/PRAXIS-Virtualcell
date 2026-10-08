"""Conservative Assessment targets derived from experimental train supervision.

The reports are deterministic, weakly derived supervision, not expert reasoning
gold. Numeric labels and literature provenance never become inference tools.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from praxis_virtualcell.llm_prediction.evidence import _reference, validate_modality_coverage
from praxis_virtualcell.llm_prediction.schemas import Assessment, EvidenceReference
from praxis_virtualcell.llm_prediction.workflow import validate_assessment_evidence

CONTRACT = "praxis.assessment-supervision.v1"
SYSTEM = """根据候选分子的 SMILES 结构、明确菌株身份、已知 MIC 实验条件和可用参考组学给出完整 Assessment JSON。
candidate 只包含 smiles，不能用化合物名称或数据库编号替代结构。输入中的未知实验条件保持未知。
参考组学各自保留采样条件，不是当前 MIC 实验的配对样本。工具仅提供实际观察，不能查询实验 MIC 或论文答案。
输出 activity、mic_estimate、mic_observations、confidence、killing_effect、targets、mechanism_hypotheses、
mechanism_claims、mechanism_limitations、supporting_evidence、counterevidence、gaps 和 rationale_summary。
mic_estimate.basis 为 llm_estimate；重复或删失估计保留 relation/value/lower/upper/lower_closed/upper_closed。
存在删失或异质观测时 mic_estimate.value 为 null，不默默平均；只有相同精确观测支持一致点值。
confidence.calibrated 为 false；没有活动阈值时 activity 为 uncertain，killing_effect 为 unknown。
证据 observations 必须引用实际工具行的 tool_call_id/source_id/pointer/value；每个使用的模态分别保留精确观察。
参考注释、表达或蛋白丰度不能证明数值 MIC、候选结合、耐药功能或靶点因果性。缺失相关特征报告 gap。
机制只能是受范围限制的 hypothesis，原机制 evidence_grade/experiment_type/scope/mechanism_role 与来源必须保留。
降解药物的耐药酶不能列为杀伤靶点。未确认的靶点保持未知；没有原文输入不得编造逐字引文或人工金标。
只训练 assistant 输出和工具调用，输入和工具回复不计算生成损失。"""


def validate_candidate(candidate: dict) -> None:
    """Accept a structure-only molecule input, never a name/ID replacement."""
    from rdkit import Chem
    if not isinstance(candidate, dict) or set(candidate) != {"smiles"}:
        raise ValueError("candidate_requires_SMILES_only")
    smiles = candidate["smiles"]
    if not isinstance(smiles, str) or not smiles.strip():
        raise ValueError("candidate_requires_valid_SMILES")
    mol = Chem.MolFromSmiles(smiles)
    if mol is None or mol.GetNumAtoms() == 0:
        raise ValueError("candidate_requires_valid_SMILES")


def feature_terms(smiles: str, claims: list[dict] | None = None) -> tuple[str, ...]:
    """Coarse structural cues and reviewed mechanisms select search vocabulary.

    These cues select contextual genes; they do not establish a drug class,
    binding target or activity. Candidate names and chemical database IDs are
    deliberately absent. Heldout calls use structure cues only.
    """
    from rdkit import Chem
    validate_candidate({"smiles": smiles})
    mol = Chem.MolFromSmiles(smiles)
    terms = []
    text = " ".join(" ".join(c.get("target_names", [])) + " " + c.get("statement", "")
                    for c in claims or []).casefold()
    for words, queries in ((('gyrase', 'gyrb', 'gyra', 'topoisomerase'), ('gyr', 'par', 'topoisomerase')),
                           (('beta-lactamase', 'hydrolys', 'adc-11'), ('ADC', 'beta-lactamase', 'bla')),
                           (('fatty acid', 'fab'), ('fatty acid', 'fab')),
                           (('ribosom', 'translation'), ('ribosom', 'translation')),
                           (('efflux',), ('efflux', 'transport')),
                           (('membrane',), ('membrane', 'porin'))):
        if any(word in text for word in words):
            terms.extend(queries)
    beta_lactam = Chem.MolFromSmarts('[N;R]1[C;R](=O)[C;R][C;R]1')
    quinolone = Chem.MolFromSmarts('[n,N]1[c,C][c,C][c,C](=O)[c,C][c,C]1')
    if mol.HasSubstructMatch(beta_lactam):
        terms.extend(('penicillin', 'beta-lactamase', 'cell wall'))
    if mol.HasSubstructMatch(quinolone):
        terms.extend(('gyr', 'par', 'topoisomerase'))
    rings = mol.GetRingInfo().AtomRings()
    if sum(atom.GetAtomicNum() == 7 for atom in mol.GetAtoms()) >= 3 and sum(
            len(ring) in {5, 6} and any(mol.GetAtomWithIdx(i).GetAtomicNum() == 8 for i in ring)
            for ring in rings) >= 2:
        terms.extend(('ribosom', 'translation', 'aminoglycoside'))
    if any(len(ring) >= 12 for ring in rings):
        terms.extend(('ribosom', 'membrane', 'efflux'))
    return tuple(dict.fromkeys([*terms, 'efflux', 'porin', 'membrane', 'transport']))[:8]


def _tool_calls(messages: list[dict]) -> list[dict]:
    return [json.loads(message['content']) for message in messages if message['role'] == 'tool']


def _target_matches(name: str, row: dict) -> bool:
    product, symbol = str(row.get('product') or '').casefold(), str(row.get('gene_symbol') or '').casefold()
    name = name.casefold()
    if name in {product, symbol}:
        return True
    if 'gyrase' in name:
        return 'gyrase' in product or symbol in {'gyra', 'gyrb'}
    if 'topoisomerase iv' in name:
        return 'topoisomerase iv' in product or symbol in {'parc', 'pare'}
    if 'adc-' in name:
        return 'adc' in product or symbol.startswith(('adc', 'blaadc'))
    return False


def assessment_target(request: dict, observations: list[dict], messages: list[dict], *,
                      claims: list[dict] | None = None, limitations: list[str] | None = None) -> tuple[dict, list[str]]:
    """Preserve labels as supervised outputs, without pretending tools explain MIC."""
    validate_candidate(request['candidate'])
    calls = _tool_calls(messages)
    call_map = {call['tool_call_id']: call for call in calls}
    evidence, feature_refs, native_rows = [], [], []
    for call in calls:
        if call.get('name') != 'query_features' or not call.get('ok'):
            continue
        for index, row in enumerate(call['data'].get('features', [])):
            observed = []
            for key in ('feature_id', 'gene_id', 'gene_symbol', 'product', 'modality', 'presence',
                        'variant', 'copy_number', 'expression_value', 'abundance_value', 'unit', 'scale'):
                if key not in row:
                    continue
                ref = EvidenceReference(tool_call_id=call['tool_call_id'], pointer=f'/features/{index}/{key}',
                                        source_id=row['source_id'], value=deepcopy(row[key]))
                _reference(ref, call_map)
                observed.append({'gene_id': row.get('gene_id'), 'field': key, 'value': deepcopy(row[key]),
                                 'evidence_ref': ref.model_dump()})
            if observed:
                feature_refs.append(observed[0]['evidence_ref'])
                native_rows.append((row, observed))
                evidence.append({'claim': f"Observed {row.get('modality', 'reference')} feature context; "
                                          'this does not establish candidate binding or numerical MIC.',
                                 'observations': observed, 'evidence_refs': []})
    value = (observations[0]['value'] if observations and all(
        item['relation'] == '=' and item['value'] == observations[0]['value'] for item in observations) else None)
    gaps = ['Reference omics are not samples paired to the requested MIC culture.',
            'A candidate-specific activity threshold and calibrated probability are unavailable.',
            'Reference feature presence or abundance does not establish target causality or killing.']
    missing = [key for key, item in request['conditions'].items() if item in (None, [], '')]
    if missing:
        gaps.append('Unknown requested assay conditions: ' + ', '.join(missing) + '.')
    if not request.get('profile_id'):
        gaps.append('No verified same-strain omics are available; this auxiliary report has no omics evidence validation.')
    if value is None:
        gaps.append('A unique MIC point estimate is not justified; heterogeneous or censored observations remain explicit.')
    mechanism_claims = deepcopy(claims or [])
    if not mechanism_claims:
        gaps.append('No record-bound mechanism annotation is supplied; targets and mechanisms remain unresolved.')
    targets, hypotheses = [], []
    for claim in mechanism_claims:
        matching = [(row, observed) for row, observed in native_rows
                    if any(_target_matches(name, row) for name in claim['target_names'])]
        linked_refs = [next((item['evidence_ref'] for item in observed if item['field'] == 'product'),
                           observed[0]['evidence_ref']) for _, observed in matching]
        context = (' Queried native feature context: ' + '; '.join(
            str(row.get('gene_id') or row['feature_id']) + ' (' + str(row.get('product') or row.get('gene_symbol') or 'unknown annotation') + ')'
            for row, _ in matching[:3]) + '. This annotation association supports a hypothesis context only; '
            'it does not establish binding, functional resistance or causality in the requested culture.' if matching else
            ' No matching target feature identity was established by the available queries; mapping remains unknown.')
        hypotheses.append({'hypothesis': claim['statement'] + ' Evidence scope: ' + claim['scope']
                                          + '; grade: ' + claim['evidence_grade'] + '; role: ' + claim['mechanism_role'] + '.',
                           'status': 'hypothesis', 'evidence_refs': linked_refs, 'counterevidence_refs': []})
        hypotheses[-1]['hypothesis'] += context
        if claim['target_names'] and not matching:
            gaps.append('Literature target identity mapping remains unknown: ' + ', '.join(claim['target_names']) + '.')
        if claim['mechanism_role'] == 'drug_target':
            for name in claim['target_names']:
                if name not in {item['name'] for item in targets}:
                    bound = [(row, observed) for row, observed in matching if _target_matches(name, row)]
                    exact = [row for row, _ in bound if name.casefold() in {
                        str(row.get('product') or '').casefold(), str(row.get('gene_symbol') or '').casefold()}]
                    targets.append({'name': name, 'target_id': None, 'status': 'hypothesis',
                                    'hypothesis': 'Literature-associated target hypothesis; reference observations do not '
                                                  'demonstrate binding in this strain and culture.',
                                    'evidence_refs': [next((item['evidence_ref'] for item in observed if item['field'] == 'product'),
                                                          observed[0]['evidence_ref']) for _, observed in bound],
                                    'counterevidence_refs': []})
                    if len(exact) == 1:
                        targets[-1]['target_id'] = exact[0].get('gene_id') or exact[0].get('protein_id')
                    else:
                        gaps.append('Target family association does not determine a unique native target_id: ' + name + '.')
    target = Assessment.model_validate({
        'activity': 'uncertain', 'mic_estimate': {'value': value, 'unit': 'ug/mL', 'basis': 'llm_estimate',
            'reason': ('Conservative point estimate under the stated or unknown conditions; reference features '
                       'describe background and do not determine numerical potency.' if value is not None else
                       'No unique point estimate is justified; retain heterogeneous or censored conditional observations.'),
            'evidence_refs': feature_refs[:1]},
        'mic_observations': deepcopy(observations), 'mechanism_claims': mechanism_claims,
        'mechanism_limitations': deepcopy(limitations or []), 'confidence': {'level': 'low', 'calibrated': False},
        'killing_effect': 'unknown', 'targets': targets[:10], 'mechanism_hypotheses': hypotheses[:10],
        'supporting_evidence': evidence[:30], 'counterevidence': [], 'gaps': gaps,
        'rationale_summary': 'Conditional MIC estimation remains uncertain. Preserve assay uncertainty, censoring '
                             'and repeated observations; feature context and literature hypotheses do not establish '
                             'a paired cellular response, definitive target or killing mechanism.'})
    issues = (validate_assessment_evidence(target, calls) + validate_modality_coverage(
        target, calls, request['available_modalities'])) if request.get('profile_id') else []
    if issues:
        target.gaps.append('Relevant omics evidence is incomplete: ' + ', '.join(sorted(set(issues))) + '.')
    return target.model_dump(), sorted(set(issues))


def convert_assessment_row(row: dict, roots: dict[str, Path], cache: dict, *, training: bool) -> tuple[dict, dict]:
    """Rebuild candidate-specific actual tools and a common train/inference contract."""
    from .species_registry import _json
    from .strain_supervision import _view
    result = deepcopy(row)
    request = json.loads(result['messages'][1]['content'])
    validate_candidate(request['candidate'])
    original = json.loads(result['messages'][-1]['content']) if training else {}
    claims = original.get('mechanism_claims', [])
    terms = feature_terms(request['candidate']['smiles'], claims if training else None)
    profile_id = request.get('profile_id')
    tool_messages = []
    if profile_id:
        key = (profile_id, terms)
        if key not in cache:
            cache[key] = _view(profile_id, roots[profile_id], terms)
        tool_messages = deepcopy(cache[key]['messages'])
    result['messages'] = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': _json(request)}, *tool_messages]
    result['target_contract'] = CONTRACT
    metadata = {'feature_search_terms': list(terms)}
    if training:
        target, issues = assessment_target(request, original['observations'], tool_messages,
                                          claims=claims, limitations=original.get('mechanism_limitations'))
        result['messages'].append({'role': 'assistant', 'content': _json(target)})
        result['task_scope'] = ('strain_reference_Assessment_mechanism' if claims else 'strain_reference_Assessment'
                                if profile_id else 'strain_conditioned_Assessment_auxiliary')
        metadata.update(mic_supervision={'endpoint': original['endpoint'], 'unit': original['unit'],
                                        'observations': deepcopy(original['observations'])},
                        report_origin='deterministic_weakly_derived_supervision', human_gold=False,
                        omics_evidence_status='passed' if profile_id and not issues else
                                              'incomplete' if profile_id else 'not_applicable',
                        omics_evidence_issues=issues,
                        mic_point_rule='all_observations_exact_and_equal_else_null')
    return result, metadata


def omics_subset_indices(train: list[dict], private: list[dict]) -> tuple[list[dict], list[dict]]:
    """Reference the one canonical conversation file without copying long tools."""
    from .species_registry import _json
    passed, incomplete, offset = [], [], 0
    for line_number, (row, source) in enumerate(zip(train, private, strict=True), 1):
        if source.get('omics_evidence_status') in {'passed', 'incomplete'}:
            entry = {'record_id': row['record_id'], 'task_scope': row['task_scope'], 'file': 'train.jsonl',
                     'line_number': line_number, 'byte_offset': offset,
                     'omics_evidence_status': source['omics_evidence_status']}
            (passed if source['omics_evidence_status'] == 'passed' else incomplete).append(entry)
        offset += len((_json(row) + '\n').encode('utf-8'))
    return passed, incomplete


def prepare_assessment_review(dataset_dir: str | Path, output_dir: str | Path, *, per_species: int = 8) -> dict:
    """Inspect train reports and queue blank heldout mechanism annotations.

    Heldout label files are never opened. The annotator receives source locators
    separately from candidate-time inputs, and every gold field starts null.
    """
    from collections import Counter
    from .joint_qwen_sft import validate_joint_qwen_sft
    from .species_registry import _digest, _json
    from .strain_supervision import _rows
    dataset, output = Path(dataset_dir).resolve(), Path(output_dir).resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('assessment_review_output_nonempty')
    if not 1 <= per_species <= 100:
        raise ValueError('annotation_per_species_must_be_between_1_and_100')
    manifest = validate_joint_qwen_sft(dataset)
    if not manifest.get('assessment_supervision'):
        raise ValueError('assessment_dataset_required')
    train, provenance = _rows(dataset / 'train.jsonl'), _rows(dataset / 'source_refs.jsonl')
    by_id = {row['record_id']: row for row in provenance}
    selected, scopes = [], set()
    grades = set()
    for row in train:
        target = json.loads(row['messages'][-1]['content'])
        new_grades = {claim['evidence_grade'] for claim in target['mechanism_claims']} - grades
        if row['task_scope'] not in scopes or new_grades:
            selected.append({'record_id': row['record_id'], 'task_scope': row['task_scope'],
                             'request': json.loads(row['messages'][1]['content']), 'assessment': target,
                             'private_supervision': by_id[row['record_id']]})
            scopes.add(row['task_scope'])
            grades.update(new_grades)
    inputs = [row for row in _rows(dataset / 'validation.inputs.jsonl')
              if json.loads(row['messages'][1]['content']).get('profile_id')
              and 'compound_unseen' in row['cohorts']]
    inputs.sort(key=lambda row: ('source_unseen' not in row['cohorts'], row['record_id']))
    answers = {row['record_id']: row for row in _rows(dataset / 'validation.answers.index.jsonl')}
    counts, queue = Counter(), []
    for row in inputs:
        request = json.loads(row['messages'][1]['content'])
        species = request['organism']['species']
        if counts[species] >= per_species:
            continue
        counts[species] += 1
        queue.append({'record_id': row['record_id'], 'split': 'validation', 'cohorts': row['cohorts'], 'request': request,
                      'review_status': 'needs_human_annotation', 'human_gold': False, 'training_eligible': False,
                      'source_locators_private': answers[row['record_id']],
                      'gold_assessment': None, 'mechanism_claims': None, 'reviewer': None,
                      'annotation_instructions': [
                          'Verify structure and experimental strain/background against the original article before labeling.',
                          'Record grade, experiment type, biological scope, role, DOI and native passage locator separately.',
                          'Preserve unresolved targets and distinguish resistance enzymes from drug-killing targets.',
                          'Leave unavailable evidence unresolved; do not copy a train annotation or invent a gold answer.']})
    report = {'schema_version': 'praxis.assessment-review-package.v1', 'status': 'needs_human_annotation',
              'dataset_manifest': {'path': str(dataset / 'manifest.json'), 'sha256': _digest(dataset / 'manifest.json')},
              'inspection_samples': len(selected), 'heldout_mechanism_annotation_candidates': len(queue),
              'per_species': dict(counts), 'heldout_mechanism_gold_records': 0, 'human_gold': False,
              'source_unseen_omics_candidates_available': sum('source_unseen' in row['cohorts'] for row in inputs),
              'source_unseen_annotation_candidates': sum('source_unseen' in row['cohorts'] for row in queue),
              'scope': 'Frozen validation compound_unseen with same-strain omics; source_unseen preferred when available.',
              'heldout_MIC_answers_opened': 0, 'raw_assets_copied': False, 'training_runs': 0, 'LLM_calls': 0}
    output.mkdir(parents=True, exist_ok=True)
    (output / 'inspection_samples.json').write_text(json.dumps({'schema_version': report['schema_version'],
                                                               'samples': selected}, ensure_ascii=False, indent=2) + '\n')
    (output / 'human_mechanism_annotation.queue.jsonl').write_text(''.join(_json(row) + '\n' for row in queue))
    training_review = [{'record_id': row['record_id'], 'split': 'train', 'review_status': 'needs_human_review',
                        'human_gold': False, 'independent_evaluation': False,
                        'existing_agent_annotations': json.loads(row['messages'][-1]['content'])['mechanism_claims'],
                        'source_locators_private': by_id[row['record_id']], 'human_annotations': None, 'reviewer': None}
                       for row in train if by_id[row['record_id']].get('literature_review')]
    (output / 'training_mechanism_review.queue.jsonl').write_text(''.join(_json(row) + '\n' for row in training_review))
    report['training_mechanism_review_candidates'] = len(training_review)
    (output / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description='Prepare train inspection and blank heldout mechanism review package.')
    parser.add_argument('--dataset-dir', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--per-species', type=int, default=8)
    args = parser.parse_args()
    print(json.dumps(prepare_assessment_review(args.dataset_dir, args.output_dir, per_species=args.per_species),
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
