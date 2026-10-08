from copy import deepcopy
import json

import pytest

from praxis_virtualcell.datasets.assessment_supervision import (
    assessment_target, feature_terms, validate_candidate,
)
from praxis_virtualcell.llm_prediction.schemas import Assessment


def request(profile=True):
    return {'candidate': {'smiles': 'CCO'}, 'profile_id': 'native' if profile else None,
            'conditions': {key: None for key in ('medium', 'medium_supplements', 'temperature_c',
                                                 'exposure_hours', 'method', 'inoculum')},
            'available_modalities': ['genome'] if profile else []}


def observed(value=2):
    return {'relation': '=', 'value': value, 'lower': value, 'upper': value,
            'lower_closed': True, 'upper_closed': True}


def tools():
    return [{'role': 'tool', 'content': json.dumps({'tool_call_id': 'native_call', 'name': 'query_features',
             'ok': True, 'data': {'features': [{'feature_id': 'locus1', 'gene_id': 'locus1',
             'gene_symbol': 'acrB', 'product': 'efflux transporter', 'modality': 'genome',
             'presence': True, 'variant': None, 'source_id': 'omics:native'}]}})}]


@pytest.mark.parametrize('candidate', [{}, {'name': 'ethanol'}, {'smiles': 'CCO', 'id': 'CHEMBL1'},
                                       {'smiles': 'not a SMILES'}, {'smiles': ''}])
def test_candidate_requires_actual_structure_only(candidate):
    with pytest.raises(ValueError, match='SMILES'):
        validate_candidate(candidate)


def test_structure_and_mechanism_terms_change_queries_without_candidate_names():
    assert 'gyr' not in feature_terms('CCO')
    assert 'beta-lactamase' in feature_terms('O=C1CCN1')
    assert 'gyr' in feature_terms('CCO', [{'target_names': ['DNA gyrase'], 'statement': 'gyrase inhibition'}])
    assert not any('CHEMBL' in term for term in feature_terms('CCO'))


def test_complete_report_cites_exact_native_rows_but_does_not_assert_causality():
    target, issues = assessment_target(request(), [observed(), observed()], tools())
    assert issues == []
    assert target['mic_estimate']['value'] == 2
    assert target['mic_observations'] == [observed(), observed()]
    assert target['supporting_evidence'][0]['observations'][4]['evidence_ref']['pointer'] == '/features/0/modality'
    assert target['confidence'] == {'level': 'low', 'calibrated': False}
    assert target['activity'] == 'uncertain' and target['killing_effect'] == 'unknown'
    assert target['targets'] == []
    Assessment.model_validate(target)


@pytest.mark.parametrize('observations', [[observed(2), observed(64)], [
    {'relation': '>', 'value': 64, 'lower': 64, 'upper': None, 'lower_closed': False, 'upper_closed': True}]])
def test_heterogeneity_and_censoring_never_become_an_averaged_point(observations):
    target, _ = assessment_target(request(), observations, tools())
    assert target['mic_estimate']['value'] is None
    assert target['mic_observations'] == observations


def test_resistance_enzyme_stays_out_of_targets_and_preserves_grade_scope():
    claim = {'statement': 'Hydrolysis of drug by enzyme.', 'evidence_grade': 'experimental',
             'experiment_type': 'enzyme_hydrolysis', 'target_names': ['ADC-11 beta-lactamase'],
             'mechanism_role': 'resistance_mechanism', 'scope': 'exact_compound_general_mechanism',
             'sources': [{'doi': '10.1234/source', 'locator_id': 'native-passage'}], 'limitations': []}
    original = deepcopy(claim)
    target, _ = assessment_target(request(), [observed()], tools(), claims=[claim])
    assert target['mechanism_claims'] == [original] and claim == original
    assert target['targets'] == []
    assert target['mechanism_hypotheses'][0]['status'] == 'hypothesis'


def test_target_family_links_native_product_without_inventing_unique_identity():
    messages = tools()
    reply = json.loads(messages[0]['content'])
    reply['data']['features'][0].update(gene_symbol='gyrB', product='DNA gyrase subunit B')
    messages[0]['content'] = json.dumps(reply)
    claim = {'statement': 'Gyrase enzyme inhibition.', 'evidence_grade': 'experimental',
             'experiment_type': 'enzyme_inhibition', 'target_names': ['DNA gyrase'],
             'mechanism_role': 'drug_target', 'scope': 'exact_compound_general_mechanism',
             'sources': [{'doi': '10.1234/source', 'locator_id': 'native-passage'}], 'limitations': []}
    target, issues = assessment_target(request(), [observed()], messages, claims=[claim])
    assert issues == []
    assert target['targets'][0]['target_id'] is None
    assert target['targets'][0]['evidence_refs'][0]['pointer'] == '/features/0/product'
    assert 'DNA gyrase subunit B' in target['mechanism_hypotheses'][0]['hypothesis']
    assert 'grade: experimental' in target['mechanism_hypotheses'][0]['hypothesis']


def test_auxiliary_reports_explicitly_lack_omics_validation():
    target, issues = assessment_target(request(False), [observed()], [])
    assert issues == [] and target['supporting_evidence'] == []
    assert any('no omics evidence validation' in gap for gap in target['gaps'])
