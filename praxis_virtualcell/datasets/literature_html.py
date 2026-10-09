"""Native official PMC HTML passages when the article has no public JATS feed.

HTML remains the original source. No reconstructed XML is presented as JATS.
Abstracts, citations, references and supplementary prose are excluded.
"""
from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser
import re
from typing import Mapping
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

from .literature import _sha, _text

_VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
_EXCLUDE = {'abstract', 'ref-list', 'kwd-group', 'glossary', 'ack', 'sm', 'fn-group'}


class _Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = ET.Element('html-document')
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        element = ET.SubElement(self.stack[-1], tag, dict((k, v or '') for k, v in attrs))
        if tag not in _VOID:
            self.stack.append(element)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        parent = self.stack[-1]
        if len(parent):
            parent[-1].tail = (parent[-1].tail or '') + data
        else:
            parent.text = (parent.text or '') + data


def parse_pmc_html(data: bytes, *, paper_id: str, source: Mapping) -> dict:
    url = urlparse(source.get('url', ''))
    if url.scheme != 'https' or url.hostname != 'pmc.ncbi.nlm.nih.gov' or not re.fullmatch(r'/articles/PMC[0-9]+/', url.path):
        raise ValueError('native_HTML_requires_official_PMC_article_URL')
    parser = _Tree()
    parser.feed(data.decode('utf-8'))
    parser.close()
    root = parser.root
    metadata = {e.get('name'): e.get('content') for e in root.iter('meta')}
    doi = metadata.get('citation_doi')
    bodies = [e for e in root.iter() if 'main-article-body' in e.get('class', '').split()]
    if not doi or len(bodies) != 1:
        raise ValueError('native_PMC_HTML_requires_DOI_and_one_full_article_body')
    pmcid = url.path.split('/')[2]
    declared_ids = {e.get('data-article-id') for e in root.iter() if e.get('data-article-id')}
    if pmcid.removeprefix('PMC') not in declared_ids:
        raise ValueError('native_PMC_HTML_article_identity_mismatch')
    paths = {root: '/html-document'}
    for parent in root.iter():
        counts = Counter()
        for child in parent:
            counts[child.tag] += 1
            paths[child] = f'{paths[parent]}/{child.tag}[{counts[child.tag]}]'
    passages = []

    def emit(element, kind, section, context=None):
        text = _text(element)
        if text:
            locator = {'file': source['file'], 'sha256': source['sha256'], 'xpath': paths[element],
                       'xml_id': element.get('id'), 'text_sha256': _sha(text.encode()), 'source_format': 'native_PMC_HTML'}
            passages.append({'passage_id': f'{paper_id}:passage:{_sha(paths[element].encode())[:16]}',
                             'paper_id': paper_id, 'kind': kind, 'section': section, 'text': text,
                             'locator': locator, 'context': context or {}, 'inference_eligible': False})

    def walk(element, section):
        classes = set(element.get('class', '').split())
        heading = next((e for e in element if e.tag in {'h2', 'h3', 'h4'}), None)
        title = _text(heading)
        if (classes.intersection(_EXCLUDE) or element.tag in {'script', 'style', 'nav'}
                or title in {'References', 'Supplementary Material', 'Supporting Information Available', 'Author Contributions'}):
            return
        if element.tag == 'section' and title:
            section = [*section, title]
        if element.tag == 'section' and 'tw' in classes:
            if heading is not None:
                emit(heading, 'table_caption', section, {'table_id': element.get('id'), 'label': title})
            rows = list(element.iter('tr'))
            headers = [[_text(cell) for cell in row if cell.tag in {'th', 'td'}] for row in rows if any(cell.tag == 'th' for cell in row)]
            for row_number, row in enumerate(rows, 1):
                cells = [e for e in row if e.tag in {'th', 'td'}]
                for column_number, cell in enumerate(cells, 1):
                    emit(cell, 'table_cell', section, {'table_id': element.get('id'), 'label': title, 'caption': title,
                         'header_rows': headers, 'row_number': row_number, 'column_number': column_number,
                         'row_cells': [_text(e) for e in cells], 'colspan': cell.get('colspan'), 'rowspan': cell.get('rowspan')})
            return
        if element.tag == 'figure':
            caption = next(iter(element.iter('figcaption')), None)
            if caption is not None:
                emit(caption, 'figure_caption', section, {'figure_id': element.get('id')})
            return
        if element.tag == 'p':
            emit(element, 'paragraph', section)
            return
        for child in element:
            walk(child, section)

    walk(bodies[0], ['body'])
    if not any(p['kind'] == 'paragraph' for p in passages):
        raise ValueError('native_PMC_HTML_has_no_body_paragraphs')
    licenses = [{'text': _text(e), 'url': e.get('href'), 'license_type': 'link_in_native_HTML', 'xpath': paths[e]}
                for e in root.iter('a') if 'creativecommons.org/licenses/' in e.get('href', '')]
    return {'identifiers': {'doi': doi, 'pmcid': pmcid, 'pmid': metadata.get('citation_pmid')},
            'licenses': licenses, 'passages': passages, 'supplementary_refs': []}
