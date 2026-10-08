import hashlib

import pytest

from praxis_virtualcell.datasets.literature import parse_article_source
from praxis_virtualcell.datasets.joint_supervision import Claim


def html_source(tmp_path, *, body=True, article_id='123'):
    content = ('<!DOCTYPE html><html><head><meta name="citation_doi" content="10.123/test">'
               '<meta name="citation_pmid" content="42"></head><body><div data-article-id="' + article_id + '"></div>'
               '<section class="body main-article-body"><section class="abstract"><p>Abstract only.</p></section>'
               + ('<p id="p1">Drug <i>A</i> inhibits &amp; binds enzyme.</p>' if body else '') +
               '<section class="tw" id="tbl1"><h2>Table 1. MIC</h2><table><tr><th>compound</th><th>ATCC 19606</th></tr>'
               '<tr><td>A</td><td>&gt;64</td></tr></table></section>'
               '<section class="ref-list"><p>Reference co-occurrence.</p></section></section></body></html>').encode()
    path = tmp_path / 'paper.html'
    path.write_bytes(content)
    return content, {'file': str(path), 'sha256': hashlib.sha256(content).hexdigest(),
                     'url': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC123/'}


def test_native_pmc_html_preserves_body_table_context_and_source(tmp_path):
    data, source = html_source(tmp_path)
    parsed = parse_article_source(data, paper_id='paper:test', source=source)
    paragraphs = [p for p in parsed['passages'] if p['kind'] == 'paragraph']
    assert [p['text'] for p in paragraphs] == ['Drug A inhibits & binds enzyme.']
    assert paragraphs[0]['locator']['source_format'] == 'native_PMC_HTML'
    cells = [p for p in parsed['passages'] if p['kind'] == 'table_cell']
    last = cells[-1]
    assert last['text'] == '>64' and last['context']['row_cells'] == ['A', '>64']
    assert last['context']['header_rows'] == [['compound', 'ATCC 19606']]
    assert parsed['identifiers']['doi'] == '10.123/test'
    assert parse_article_source(data, paper_id='paper:test', source=source) == parsed


@pytest.mark.parametrize('mutation', ['url', 'article_id', 'abstract_only'])
def test_native_html_rejects_unverified_or_abstract_only_pages(tmp_path, mutation):
    data, source = html_source(tmp_path, body=mutation != 'abstract_only', article_id='456' if mutation == 'article_id' else '123')
    if mutation == 'url':
        source['url'] = 'https://example.com/articles/PMC123/'
    with pytest.raises(ValueError):
        parse_article_source(data, paper_id='paper:test', source=source)


def test_enzyme_inhibition_has_its_own_evidence_type():
    claim = Claim(statement='The enzyme activity is inhibited.', evidence_grade='experimental',
                  experiment_type='enzyme_inhibition', target_names=['DNA gyrase'],
                  quotes=[{'passage_id': 'p', 'start': 0, 'end': 3, 'text': 'DNA'}])
    assert claim.experiment_type != 'target_binding'
    with pytest.raises(ValueError):
        Claim(**{**claim.model_dump(), 'target_names': []})


def test_drug_hydrolysis_cannot_be_labeled_as_killing_target():
    fields = {'statement': 'ADC hydrolyzes this beta-lactam.', 'evidence_grade': 'experimental',
              'experiment_type': 'enzyme_hydrolysis', 'target_names': ['ADC-11'],
              'mechanism_role': 'resistance_mechanism',
              'quotes': [{'passage_id': 'p', 'start': 0, 'end': 3, 'text': 'ADC'}]}
    assert Claim(**fields).mechanism_role == 'resistance_mechanism'
    with pytest.raises(ValueError, match='resistance_enzyme_not_drug_target'):
        Claim(**{**fields, 'mechanism_role': 'drug_target'})
