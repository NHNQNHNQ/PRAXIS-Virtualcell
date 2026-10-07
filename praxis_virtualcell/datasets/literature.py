"""Source-linked, open-access literature for manual strain-training review.

This module never produces gold mechanisms or inference evidence. It caches
official responses once, preserves JATS anchors, and locates candidate passages.
Case-to-paper links do not establish case-to-claim or case-to-omics pairing.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import time
import zipfile
from collections import Counter
from datetime import datetime, timezone
from http.client import HTTPException
from pathlib import Path
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/"
PMC_IDS = "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"
PMC_OAI = "https://pmc.ncbi.nlm.nih.gov/api/oai/v1/mh/"
_OFFICIAL_HOSTS = {"www.ebi.ac.uk", "europepmc.org", "www.europepmc.org", "pmc.ncbi.nlm.nih.gov"}
_DOI = re.compile(r"^10\.[0-9]{4,9}/\S+$", re.IGNORECASE)
_PHENOTYPE = re.compile(r"\bMIC\b|\bMBC\b|minimum inhibitory|susceptib\w*|resistan\w*|growth inhibition|bactericidal", re.I)
_CONDITION = re.compile(r"\b(?:cultured|grown|incubat\w*|untreated|unexposed|no antibiotic|without antibiotics?|"
                        r"Mueller[ -]Hinton|LB broth|Luria[ -]Bertani|logarithmic phase|exponential phase|"
                        r"OD\s*600|optical density|broth microdilution|agar dilution|CLSI|CAMHB|MHB|"
                        r"medium|media|supplement\w*)\b|\b\d+(?:\.\d+)?\s*°\s*C\b", re.I)
_MECHANISM = re.compile(r"\b(?:bind\w*|target\w*|mechanism\w*|efflux|enzyme|protein|"
                        r"knockout|knock[ -]out|overexpress\w*|mutant|mutation|Kd|Ki|IC50|"
                        r"co[ -]?crystal\w*|isothermal titration|pathway|biosynthe\w*|fatty acid|rescu\w*|"
                        r"abrogat\w*|permeability)\b", re.I)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":"))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_doi(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/|^doi:\s*", "", value.strip(), flags=re.I)
    return value.lower() if _DOI.fullmatch(value) else None


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _text(element: ET.Element | None) -> str:
    return re.sub(r"\s+", " ", "".join(element.itertext())).strip() if element is not None else ""


def _child(element: ET.Element, name: str) -> ET.Element | None:
    return next((item for item in element if _tag(item) == name), None)


def _request_bytes(url: str, *, max_bytes: int) -> tuple[bytes, Mapping[str, str]]:
    """Bounded GET; no publisher scraping or arbitrary external URLs."""
    if urlparse(url).scheme != "https" or urlparse(url).hostname not in _OFFICIAL_HOSTS:
        raise ValueError("literature requests must use an approved official HTTPS host")
    attempts = 1 if url.startswith(PMC_OAI) else 3
    for attempt in range(attempts):
        try:
            started = time.monotonic()
            transfer_seconds = 30 if url.endswith("/supplementaryFiles") else 45
            request = Request(url, headers={"User-Agent": "PRAXIS-open-literature-pilot/1.0"})
            with urlopen(request, timeout=15 if transfer_seconds == 30 else 30) as response:
                if urlparse(response.geturl()).hostname not in _OFFICIAL_HOSTS:
                    raise ValueError("official API redirected outside the approved hosts")
                length = response.headers.get("Content-Length")
                if length and int(length) > max_bytes:
                    raise ValueError("official asset exceeds the bounded pilot download size")
                chunks, size = [], 0
                while chunk := response.read(65_536):
                    chunks.append(chunk)
                    size += len(chunk)
                    if size > max_bytes:
                        raise ValueError("official asset exceeds the bounded pilot download size")
                    if time.monotonic() - started > transfer_seconds:
                        raise ValueError("official asset exceeded the bounded pilot transfer time")
                body = b"".join(chunks)
                headers = {key.lower(): response.headers[key] for key in
                           ("Content-Type", "ETag", "Last-Modified") if key in response.headers}
                return body, headers
        except HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == attempts - 1:
                raise
        except (URLError, TimeoutError, ConnectionError, HTTPException):
            if attempt == attempts - 1:
                raise
        time.sleep(0.25 * (attempt + 1))
    raise RuntimeError("unreachable retry state")


class RecordedSourceError(OSError):
    """A failed official request retained in the immutable pilot snapshot."""

    def __init__(self, label: str):
        self.label = label
        super().__init__(label)


class LiteratureCache:
    """Immutable content-addressed files and URL receipts, resumable offline."""

    def __init__(self, output_dir: str | Path, *, offline: bool = False):
        self.root = Path(output_dir).resolve() / "nativecache"
        self.root.mkdir(parents=True, exist_ok=True)
        self.offline = offline

    def fetch(self, url: str, kind: str) -> tuple[bytes, dict[str, Any]]:
        receipt_path = self.root / (_sha(url.encode())[:24] + ".receipt.json")
        failure_path = self.root / (_sha(url.encode())[:24] + ".unavailable.json")
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text())
            if receipt.get("url") != url:
                raise ValueError("native receipt URL mismatch")
            path = Path(receipt["file"])
            data = path.read_bytes()
            if len(data) != receipt["size"] or _sha(data) != receipt["sha256"]:
                raise ValueError("cached literature asset failed source fingerprint verification")
            return data, receipt
        if failure_path.exists():
            failure = json.loads(failure_path.read_text())
            if failure.get("url") != url:
                raise ValueError("native unavailable receipt URL mismatch")
            if self.offline or failure.get("terminal", True):
                raise RecordedSourceError(failure.get("error", f"official_api_http_{failure.get('http_status')}"))
        if self.offline:
            raise FileNotFoundError(f"offline_cache_miss:{url}")
        limits = {"json": 8_000_000, "xml": 20_000_000, "zip": 25_000_000}
        try:
            data, headers = _request_bytes(url, max_bytes=limits[kind])
        except (OSError, HTTPException, ValueError) as exc:
            # Failed source requests have reproducible offline status too.
            # Transient failures can be retried online; successful receipts
            # supersede them without modifying the original failure record.
            if not failure_path.exists():
                with failure_path.open("x") as handle:
                    handle.write(_json({"url": url, "http_status": getattr(exc, "code", None), "error": _error(exc),
                        "terminal": isinstance(exc, ValueError) or isinstance(exc, HTTPError) and exc.code in {400, 403, 404, 410},
                        "retrieved_at": datetime.now(timezone.utc).isoformat(),
                        "status": "official_failed_request_no_verified_content"}) + "\n")
            raise RecordedSourceError(json.loads(failure_path.read_text())["error"]) from exc
        if kind == "json":
            json.loads(data)
        elif kind == "xml":
            ET.fromstring(data)
        elif not zipfile.is_zipfile(io.BytesIO(data)):
            raise ValueError("supplementaryFiles did not return a ZIP archive")
        digest = _sha(data)
        path = self.root / f"{digest}.{kind}"
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError("content-addressed literature file conflict")
        else:
            with path.open("xb") as handle:
                handle.write(data)
        receipt = {"url": url, "file": str(path), "sha256": digest, "size": len(data),
                   "retrieved_at": datetime.now(timezone.utc).isoformat(), "headers": dict(headers)}
        with receipt_path.open("x") as handle:
            handle.write(_json(receipt) + "\n")
        return data, receipt

    def remembered_failure(self, url: str) -> str | None:
        """Use a checked failed EPMC response before one bounded PMC fallback."""
        path = self.root / (_sha(url.encode())[:24] + ".unavailable.json")
        if not path.exists():
            return None
        failure = json.loads(path.read_text())
        if failure.get("url") != url:
            raise ValueError("native unavailable receipt URL mismatch")
        return failure.get("error") or f"official_api_http_{failure.get('http_status')}"


def parse_jats(data: bytes, *, paper_id: str, source: Mapping[str, Any]) -> dict[str, Any]:
    """Return body paragraphs, individual table cells and figure captions.

    Each locator refers to the one cached XML. Abstracts and reference-list
    co-occurrence are excluded. Native XML IDs and positional XPath coexist.
    """
    envelope = ET.fromstring(data)
    paths: dict[ET.Element, str] = {envelope: "/" + _tag(envelope)}
    for parent in envelope.iter():
        counts: Counter[str] = Counter()
        for item in parent:
            name = _tag(item)
            counts[name] += 1
            paths[item] = f"{paths[parent]}/{name}[{counts[name]}]"
    if _tag(envelope) == "article":
        root = envelope
    elif _tag(envelope) == "OAI-PMH":
        errors = [item for item in envelope.iter() if _tag(item) == "error"]
        if errors:
            raise ValueError("official_PMC_OAI_error:" + ";".join(f"{item.attrib.get('code')}:{_text(item)}" for item in errors))
        articles = [item for item in envelope.iter() if _tag(item) == "article"]
        if len(articles) != 1:
            raise ValueError("expected one JATS article in official OAI envelope")
        root = articles[0]
    else:
        raise ValueError("expected one JATS article or official PMC OAI envelope")
    ids: dict[str, str] = {}
    for element in root.iter():
        if _tag(element) == "article-id":
            kind = element.attrib.get("pub-id-type", "")
            if kind in {"doi", "pmid", "pmcid", "pmc"}:
                ids[kind] = _text(element)
    licenses = []
    for element in root.iter():
        if _tag(element) == "license":
            licenses.append({"text": _text(element), "url": element.attrib.get("{http://www.w3.org/1999/xlink}href"),
                             "license_type": element.attrib.get("license-type"), "xpath": paths[element]})
    passages: list[dict[str, Any]] = []

    def emit(element: ET.Element, kind: str, section: list[str], context: Mapping[str, Any] | None = None):
        text = _text(element)
        if not text:
            return
        locator = {"file": source["file"], "sha256": source["sha256"], "xpath": paths[element],
                   "xml_id": element.attrib.get("id"), "text_sha256": _sha(text.encode())}
        passage_id = f"{paper_id}:passage:{_sha(paths[element].encode())[:16]}"
        passages.append({"passage_id": passage_id, "paper_id": paper_id, "kind": kind,
                         "section": section, "text": text, "locator": locator,
                         "context": dict(context or {}), "inference_eligible": False})

    def walk(element: ET.Element, section: list[str]):
        name = _tag(element)
        if name == "sec":
            title = _text(_child(element, "title"))
            section = [*section, title or element.attrib.get("sec-type") or "untitled"]
        if name == "p":
            emit(element, "paragraph", section)
            return
        if name == "table-wrap":
            caption, label = _text(_child(element, "caption")), _text(_child(element, "label"))
            caption_element = _child(element, "caption")
            if caption_element is not None:
                emit(caption_element, "table_caption", section, {"table_id": element.attrib.get("id"), "label": label})
            rows = [item for item in element.iter() if _tag(item) == "tr"]
            header_rows = [[_text(cell) for cell in row if _tag(cell) in {"th", "td"}]
                           for row in rows if any(_tag(cell) == "th" for cell in row)]
            for row_number, row in enumerate(rows, 1):
                cells = [cell for cell in row if _tag(cell) in {"th", "td"}]
                for column_number, cell in enumerate(cells, 1):
                    emit(cell, "table_cell", section, {"table_id": element.attrib.get("id"), "label": label,
                         "caption": caption, "header_rows": header_rows, "row_number": row_number,
                         "column_number": column_number, "row_cells": [_text(item) for item in cells],
                         "colspan": cell.attrib.get("colspan"), "rowspan": cell.attrib.get("rowspan")})
            return
        if name == "fig":
            caption_element = _child(element, "caption")
            if caption_element is not None:
                graphics = [item.attrib.get("{http://www.w3.org/1999/xlink}href") for item in element.iter()
                            if _tag(item) == "graphic"]
                emit(caption_element, "figure_caption", section,
                     {"figure_id": element.attrib.get("id"), "label": _text(_child(element, "label")), "graphics": graphics})
            return
        if name in {"ref-list", "supplementary-material", "fn-group"}:
            return
        for item in element:
            walk(item, section)

    body = _child(root, "body")
    if body is None:
        raise ValueError("JATS article has no body; abstract-only records are not full text")
    walk(body, ["body"])
    supplementary = [{"xml_id": item.attrib.get("id"), "xpath": paths[item], "caption": _text(item),
                      "href": item.attrib.get("{http://www.w3.org/1999/xlink}href"),
                      "linked_assets": [{"tag": _tag(link), "xpath": paths[link],
                          "href": link.attrib["{http://www.w3.org/1999/xlink}href"], "text": _text(link)}
                          for link in item.iter() if "{http://www.w3.org/1999/xlink}href" in link.attrib]}
                     for item in root.iter() if _tag(item) == "supplementary-material"]
    return {"identifiers": ids, "licenses": licenses, "passages": passages, "supplementary_refs": supplementary}


def _classification(text: str) -> str:
    if re.search(r"\b(?:may|might|suggest\w*|propos\w*|hypothes\w*|supposed|putative|docking|predicted|in silico)\b", text, re.I):
        return "author_proposed"
    if re.search(r"\b(?:knockout|knock[ -]out|overexpress\w*|mutation|mutant|deletion|disrupt\w*)\b", text, re.I):
        return "genetic"
    if re.search(r"\b(?:Kd|Ki|IC50|co[ -]?crystal\w*|isothermal titration|purified|recombinant|observed|abrogat\w*)\b", text, re.I):
        return "experimental"
    return "class_background"


def locate_candidates(passages: list[dict[str, Any]], *, doi: str, record_ids: list[str],
                      strain_labels: list[str] = (), compound_ids: list[str] = ()) -> list[dict[str, Any]]:
    """Lexical candidate locations, never inferred mechanisms or automatic gold."""
    candidates = []
    for passage in passages:
        text = passage["text"]
        for match in re.finditer(r"[^.!?]+(?:[.!?](?=\s|$)|$)", text):
            start, end = match.span()
            while start < end and text[start].isspace():
                start += 1
            quote = text[start:end]
            kinds = [kind for kind, pattern in (("conditions", _CONDITION), ("mechanism", _MECHANISM)) if pattern.search(quote)]
            if not kinds:
                continue
            mentions = lambda values: [value for value in values if value and re.search(r"(?<!\w)" + re.escape(value) + r"(?!\w)", quote, re.I)]
            for kind in kinds:
                identity = f"{passage['passage_id']}:{start}:{end}:{kind}"
                candidates.append({"candidate_id": "literature-candidate:" + _sha(identity.encode())[:24],
                    "paper_id": passage["paper_id"], "doi": doi, "record_ids": sorted(record_ids),
                    "record_binding_status": "paper_only_needs_review", "kind": kind,
                    "claim_classification": _classification(quote) if kind == "mechanism" else None,
                    "classification_basis": "lexical_candidate_only_not_verified_experiment",
                    "passage_id": passage["passage_id"], "quoted_span": quote,
                    "span": {"start": start, "end": end, "coordinate_system": "unicode_codepoints_in_passage_text"},
                    "context": {"before": text[max(0, start - 300):start], "after": text[end:end + 300],
                                "section": passage["section"], "source_context": passage["context"]},
                    "locator": passage["locator"], "strain_mentions": mentions(strain_labels),
                    "compound_mentions": mentions(compound_ids), "review_status": "needs_review",
                    "scope_status": "compound_strain_target_and_condition_binding_unverified",
                    "contains_phenotype_labels": bool(_PHENOTYPE.search(quote)), "inference_eligible": False,
                    "gold_eligible": False})
    return candidates


def _select_papers(cases_path: Path, limit: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    grouped: dict[str, dict[str, Any]] = {}
    counts: Counter[str] = Counter()
    seen_cases: set[str] = set()
    with cases_path.open() as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            case = json.loads(line)
            if not isinstance(case, dict):
                raise ValueError(f"case line {line_number} is not an object")
            counts["case_count"] += 1
            if case.get("split") != "train":
                counts["excluded_not_train"] += 1
                continue
            literature = case.get("literature") or {}
            source = case.get("source") or {}
            doi = normalize_doi(literature.get("doi") or source.get("doi") or case.get("doi"))
            if doi is None:
                counts["excluded_no_valid_doi"] += 1
                continue
            case_id = case.get("case_id") or case.get("record_id")
            if not isinstance(case_id, str) or not case_id or case_id in seen_cases:
                raise ValueError("train cases require unique nonempty case_id/record_id")
            seen_cases.add(case_id)
            strain = case.get("strain") or case.get("organism") or {}
            strain_label = strain.get("label") or strain.get("strain") or strain.get("isolate_id")
            if not strain_label or not (strain.get("namespace") or strain.get("strain_namespace")):
                counts["excluded_unresolved_strain_namespace"] += 1
                continue
            private = case.get("private_answer") or {}
            record_id = private.get("record_id") or case.get("record_id")
            if not isinstance(record_id, str) or not record_id:
                counts["excluded_missing_record_id"] += 1
                continue
            item = grouped.setdefault(doi, {"doi": doi, "record_ids": [], "case_ids": [], "strain_labels": [],
                                          "compound_ids": [], "document_ids": [], "native_metadata_refs": [], "priority": 1})
            item["record_ids"].append(record_id)
            item["case_ids"].append(case_id)
            item["strain_labels"].append(str(strain_label))
            if re.search(r"\bAB5075(?:[ -]UW)?\b", str(strain_label), re.I):
                item["priority"] = 0
            candidate = case.get("candidate") or case.get("molecule") or {}
            compound_id = candidate.get("source_molecule_id") or candidate.get("id")
            if compound_id:
                item["compound_ids"].append(str(compound_id))
            if literature.get("document_id") or source.get("document_id"):
                item["document_ids"].append(literature.get("document_id") or source["document_id"])
            refs = literature.get("native_metadata_refs") or []
            if literature.get("native_metadata_ref"):
                refs = [*refs, literature["native_metadata_ref"]]
            item["native_metadata_refs"].extend(refs)
            counts["eligible_train_cases"] += 1
    # Venue order is a pilot selection heuristic, not proof of open access.
    # Availability and rights are checked separately against official metadata.
    def pilot_order(item):
        venue = 0 if item["doi"].startswith("10.1021/acsmedchemlett.") else 1 if item["doi"].startswith("10.1128/") else 2
        return item["priority"], venue, item["doi"]
    selected = sorted(grouped.values(), key=pilot_order)[:limit]
    for item in selected:
        for key in ("record_ids", "case_ids", "strain_labels", "compound_ids", "document_ids"):
            item[key] = sorted(set(item[key]))
    counts["eligible_unique_dois"] = len(grouped)
    counts["selected_unique_dois"] = len(selected)
    return selected, dict(counts)


def _native_metadata(refs: list[Mapping[str, Any]], doi: str, cases_path: Path) -> list[dict[str, Any]]:
    """Reuse supplied exact DOI source locators without duplicating old files."""
    verified = []
    for ref in refs:
        path = Path(ref["file"])
        if not path.is_absolute():
            path = path if path.exists() else cases_path.parent / path
        path = path.resolve()
        data = path.read_bytes()
        digest = _sha(data)
        if ref.get("sha256") and ref["sha256"] != digest:
            raise ValueError("existing document metadata source fingerprint mismatch")
        value = json.loads(data)
        pointer = ref.get("pointer", "")
        for key in pointer.strip("/").split("/") if pointer else []:
            key = key.replace("~1", "/").replace("~0", "~")
            value = value[int(key)] if isinstance(value, list) else value[key]
        if not isinstance(value, dict) or normalize_doi(value.get("doi")) != doi:
            raise ValueError("native document metadata does not identify the selected DOI")
        verified.append({"file": str(path), "pointer": pointer, "sha256": digest,
                         "document_id": value.get("document_chembl_id"), "pmid": value.get("pubmed_id"),
                         "doi": doi, "reuse_status": "original_source_referenced_not_copied"})
    return verified


def _supplement_manifest(data: bytes, source: Mapping[str, Any]) -> list[dict[str, Any]]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if sum(item.file_size for item in entries) > 100_000_000 or len(entries) > 1000:
            raise ValueError("supplement archive exceeds bounded pilot inspection size")
        names: set[str] = set()
        output = []
        for item in entries:
            if item.is_dir():
                continue
            if item.filename in names:
                raise ValueError("duplicate supplementary archive member name")
            names.add(item.filename)
            output.append({"archive_file": source["file"], "archive_sha256": source["sha256"],
                           "member": item.filename, "uncompressed_size": item.file_size,
                           "compressed_size": item.compress_size, "crc32": f"{item.CRC:08x}",
                           "storage": "archive_member_reference_not_extracted"})
        return output


def _write_jsonl(path: Path, rows: list[dict[str, Any]]):
    content = "".join(_json(row) + "\n" for row in rows).encode()
    if path.exists() and path.read_bytes() == content:
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def _error(exc: Exception) -> str:
    if isinstance(exc, RecordedSourceError):
        return exc.label
    if isinstance(exc, HTTPError):
        return f"official_api_http_{exc.code}"
    return f"{type(exc).__name__}:{exc}"


def acquire_literature(cases_path: str | Path, output_dir: str | Path, *, limit: int = 25,
                       offline: bool = False, skip_supplements: bool = False) -> dict[str, Any]:
    """Acquire a bounded train-only DOI pilot from official PMC/Europe PMC APIs.

    Cases use literature.doi, private_answer.record_id and namespaced strain.
    Optional literature.native_metadata_ref(s) accepts file/pointer/sha256.
    The output selection is immutable; same-input runs resume missing assets.
    Offline regeneration uses verified receipts and makes no network requests.
    """
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    cases_path, output = Path(cases_path).resolve(), Path(output_dir).resolve()
    selected, counts = _select_papers(cases_path, limit)
    if not selected:
        raise ValueError("no train cases with valid DOI and explicit namespaced strain")
    output.mkdir(parents=True, exist_ok=True)
    selection = {"schema_version": "praxis.literature-selection.v1", "cases_file": str(cases_path),
                 "cases_sha256": _sha(cases_path.read_bytes()), "limit": limit, "papers": selected}
    selection_path = output / "selection.json"
    selection_bytes = (_json(selection) + "\n").encode()
    if selection_path.exists():
        if selection_path.read_bytes() != selection_bytes:
            raise ValueError("literature snapshot selection cannot be overwritten with changed cases/limit")
    else:
        selection_path.write_bytes(selection_bytes)
    cache = LiteratureCache(output, offline=offline)
    id_ref, converted, converter_error = None, {}, None
    try:
        url = PMC_IDS + "?" + urlencode({"ids": ",".join(item["doi"] for item in selected), "idtype": "doi", "format": "json"})
        data, id_ref = cache.fetch(url, "json")
        for index, record in enumerate(json.loads(data).get("records", [])):
            doi = normalize_doi(record.get("doi") or record.get("requested-id"))
            if doi and not record.get("errmsg"):
                converted[doi] = (record, f"/records/{index}")
    except (OSError, HTTPException, ValueError, KeyError, ET.ParseError) as exc:
        converter_error = _error(exc)
    papers, passages, candidates = [], [], []
    for selected_paper in selected:
        doi = selected_paper["doi"]
        paper_id = "paper:" + _sha(doi.encode())[:24]
        paper = {"schema_version": "praxis.literature-paper.v1", "paper_id": paper_id, "doi": doi,
                 "record_ids": selected_paper["record_ids"], "case_ids": selected_paper["case_ids"],
                 "document_ids": selected_paper["document_ids"], "pmid": None, "pmcid": None,
                 "metadata_sources": [], "native_metadata_refs": [], "licenses": [], "article": None,
                 "supplementary_refs": [], "supplementary_assets": [], "supplementary_status": "not_checked",
                 "status": "metadata_unresolved", "errors": [], "inference_eligible": False,
                 "record_binding_status": "paper_only_needs_review"}
        try:
            paper["native_metadata_refs"] = _native_metadata(selected_paper["native_metadata_refs"], doi, cases_path)
            native_pmids = {str(ref["pmid"]) for ref in paper["native_metadata_refs"] if ref.get("pmid")}
            if len(native_pmids) > 1:
                raise ValueError("existing native DOI metadata PMID conflict")
            if native_pmids:
                paper["pmid"] = next(iter(native_pmids))
            if doi in converted:
                record, pointer = converted[doi]
                if paper["pmid"] and record.get("pmid") and str(paper["pmid"]) != str(record["pmid"]):
                    raise ValueError("native and official DOI metadata PMID conflict")
                paper["pmid"] = record.get("pmid") or paper["pmid"]
                paper["pmcid"] = record.get("pmcid")
                paper["metadata_sources"].append({**id_ref, "pointer": pointer})
                paper["metadata_status"] = "official_DOI_PMID_PMCID_mapping_verified"
                paper["source_version"] = {"pmc_versions": record.get("versions", []), "version_basis": "native_response_and_hash"}
            elif converter_error:
                paper["errors"].append({"stage": "id_conversion", "error": converter_error})
            url = EUROPE_PMC + "search?" + urlencode({"query": f'DOI:"{doi}"', "format": "json", "resultType": "core", "pageSize": 1000})
            metadata_error = None
            try:
                previous_failure = cache.remembered_failure(url) if doi in converted else None
                if previous_failure:
                    raise RecordedSourceError(previous_failure)
                data, ref = cache.fetch(url, "json")
                results = json.loads(data).get("resultList", {}).get("result", [])
            except (OSError, HTTPException, ValueError) as exc:
                metadata_error = _error(exc)
                results = []
                paper["errors"].append({"stage": "europepmc_metadata", "error": metadata_error, "url": url})
            exact = [(index, record) for index, record in enumerate(results) if normalize_doi(record.get("doi")) == doi]
            if exact:
                index, metadata = next((pair for pair in exact if pair[1].get("source") == "MED"), exact[0])
                if paper["pmid"] and metadata.get("pmid") and str(paper["pmid"]) != str(metadata["pmid"]):
                    raise ValueError("official DOI metadata PMID conflict")
                if paper["pmcid"] and metadata.get("pmcid") and paper["pmcid"] != metadata["pmcid"]:
                    raise ValueError("official DOI metadata PMCID conflict")
                paper["pmid"] = metadata.get("pmid") or paper["pmid"]
                paper["pmcid"] = metadata.get("pmcid") or paper["pmcid"]
                paper["metadata_sources"].append({**ref, "pointer": f"/resultList/result/{index}"})
                paper["title"] = metadata.get("title")
                paper["is_open_access"] = metadata.get("isOpenAccess")
                paper["metadata_license"] = metadata.get("license")
                paper["status"] = "metadata_only"
            elif not paper["pmcid"]:
                paper["errors"].append({"stage": "metadata", "error": "no_exact_DOI_record"})
            pmcid = paper["pmcid"]
            if not pmcid or not re.fullmatch(r"PMC[0-9]+", pmcid):
                paper["fulltext_status"] = "unavailable_no_pmcid"
                paper["supplementary_status"] = "unavailable_no_pmcid"
                papers.append(paper)
                continue
            if paper.get("is_open_access") == "N":
                paper["fulltext_status"] = "not_open_access_in_official_metadata"
                paper["supplementary_status"] = "not_requested_non_open_access"
                papers.append(paper)
                continue
            if metadata_error:
                # This single official GetRecord format returns reusable full
                # text or an explicit OAI error; it is not publisher scraping.
                oai_url = PMC_OAI + "?" + urlencode({"verb": "GetRecord", "identifier":
                    "oai:pubmedcentral.nih.gov:" + pmcid.removeprefix("PMC"), "metadataPrefix": "pmc"})
                paper["fulltext_attempt"] = {"url": oai_url, "strategy": "official_PMC_OAI_single_request"}
                xml, source = cache.fetch(oai_url, "xml")
            else:
                xml, source = cache.fetch(EUROPE_PMC + f"{pmcid}/fullTextXML", "xml")
            parsed = parse_jats(xml, paper_id=paper_id, source=source)
            article_doi = normalize_doi(parsed["identifiers"].get("doi"))
            if article_doi != doi:
                raise ValueError("JATS article DOI does not exactly match selected paper")
            paper["article"] = source
            paper["article_path"] = source["file"]
            paper["source_sha256"] = source["sha256"]
            paper["source_version"] = {**paper.get("source_version", {}),
                "article_sha256": source["sha256"], "last_modified": source["headers"].get("last-modified"),
                "etag": source["headers"].get("etag"), "retrieved_at": source["retrieved_at"],
                "version_basis": "native_response_identifiers_headers_and_hash"}
            paper["article_identifiers"] = parsed["identifiers"]
            paper["licenses"] = parsed["licenses"]
            paper["license_status"] = "source_license_present_requires_usage_review" if parsed["licenses"] else "unknown_requires_review"
            paper["status"] = "open_fulltext_parsed"
            paper["fulltext_status"] = "official_open_fulltext_cached_and_parsed"
            paper["passage_count"] = len(parsed["passages"])
            paper["supplementary_refs"] = parsed["supplementary_refs"]
            passages.extend(parsed["passages"])
            candidates.extend(locate_candidates(parsed["passages"], doi=doi, record_ids=selected_paper["record_ids"],
                                               strain_labels=selected_paper["strain_labels"], compound_ids=selected_paper["compound_ids"]))
            if parsed["supplementary_refs"] and skip_supplements:
                paper["supplementary_status"] = "skip_supplements_current_pilot"
            elif parsed["supplementary_refs"]:
                try:
                    data, supplementary_source = cache.fetch(EUROPE_PMC + f"{pmcid}/supplementaryFiles", "zip")
                    paper["supplementary_assets"] = _supplement_manifest(data, supplementary_source)
                    paper["supplementary_source"] = supplementary_source
                    paper["supplementary_status"] = "cached_archive_singlecopy_members_referenced"
                except (OSError, HTTPException, ValueError, zipfile.BadZipFile) as exc:
                    paper["supplementary_status"] = "unavailable_or_exceeds_pilot_bound"
                    paper["errors"].append({"stage": "supplementary", "error": _error(exc)})
            else:
                paper["supplementary_status"] = "no_JATS_supplementary_material_reference"
        except (OSError, HTTPException, ValueError, KeyError, ET.ParseError) as exc:
            paper["status"] = "source_error_or_fulltext_unavailable"
            paper["fulltext_status"] = "api_error_or_parse_unavailable"
            paper["errors"].append({"stage": "metadata_or_fulltext", "error": _error(exc)})
        papers.append(paper)
    _write_jsonl(output / "papers.jsonl", papers)
    _write_jsonl(output / "passages.jsonl", passages)
    _write_jsonl(output / "extraction_candidates.jsonl", candidates)
    summary = {"schema_version": "praxis.literature-summary.v1", "selection": str(selection_path),
               "acquisition_policy": {"skip_supplements_current_pilot": skip_supplements},
               "cases_sha256": selection["cases_sha256"], "selection_counts": counts, "paper_count": len(papers),
               "paper_status_counts": dict(Counter(paper["status"] for paper in papers)),
               "pmid_count": sum(bool(paper["pmid"]) for paper in papers),
               "pmcid_count": sum(bool(paper["pmcid"]) for paper in papers),
               "bibliographic_metadata_count": sum(any("/search?" in ref["url"] for ref in paper["metadata_sources"]) for paper in papers),
               "supplementary_status_counts": dict(Counter(paper["supplementary_status"] for paper in papers)),
               "passage_count": len(passages), "candidate_count": len(candidates), "gold_count": 0,
               "candidate_kind_counts": dict(Counter(candidate["kind"] for candidate in candidates)),
               "candidate_classification_counts": dict(Counter(candidate["claim_classification"] for candidate in candidates if candidate["kind"] == "mechanism")),
               "papers_path": str(output / "papers.jsonl"), "passages_path": str(output / "passages.jsonl"),
               "candidates_path": str(output / "extraction_candidates.jsonl"),
               "limitations": ["Train-only paper links do not establish compound/strain/target/condition claim binding.",
                               "All lexical candidates require human review; none are gold or inference evidence.",
                               "Original paper and supplementary rights require separate review from database licensing.",
                               "Bounded official APIs may lack full text/supplements; missing content is explicitly reported.",
                               "Supplementary members remain in one archive; binary tables are not automatically interpreted."]}
    summary_path = output / "summary.json"
    content = (_json(summary) + "\n").encode()
    if not summary_path.exists() or summary_path.read_bytes() != content:
        summary_path.write_bytes(content)
    return summary


def acquire_document_compound_bindings(document_id: str, doi: str, output_dir: str | Path, *,
                                       document_ref: Mapping[str, Any] | None = None,
                                       offline: bool = False) -> dict[str, Any]:
    """One bounded ChEMBL source-document chemical-number mapping.

    This is paper compound identity, not protein binding or automatic structure
    verification. A supplied original document metadata locator is reused.
    """
    normalized = normalize_doi(doi)
    if not re.fullmatch(r"CHEMBL[1-9][0-9]*", document_id) or normalized is None:
        raise ValueError("valid ChEMBL document ID and DOI are required")
    output = Path(output_dir).resolve()
    cache = LiteratureCache(output, offline=offline)
    if document_ref is not None:
        refs = _native_metadata([document_ref], normalized, output / "cases.jsonl")
        if refs[0]["document_id"] != document_id:
            raise ValueError("native source document ID mismatch")
        source_document = refs[0]
    else:
        data, source_document = cache.fetch(f"https://www.ebi.ac.uk/chembl/api/data/document/{document_id}.json", "json")
        document = json.loads(data)
        if document.get("document_chembl_id") != document_id or normalize_doi(document.get("doi")) != normalized:
            raise ValueError("official source document ID/DOI mismatch")
        source_document = {**source_document, "pointer": ""}
    data, source = cache.fetch("https://www.ebi.ac.uk/chembl/api/data/compound_record.json?" +
                              urlencode({"document_chembl_id": document_id, "limit": 1000}), "json")
    response = json.loads(data)
    records = response.get("compound_records")
    if not isinstance(records, list):
        raise ValueError("official response has no compound_records list")
    page = response.get("page_meta") or {}
    if page.get("offset", 0) != 0 or not isinstance(page.get("total_count"), int) or page["total_count"] < len(records):
        raise ValueError("compound record page identity/count mismatch")
    rows, seen = [], set()
    for index, record in enumerate(records):
        if record.get("document_chembl_id") != document_id:
            raise ValueError("compound record returned a different source document")
        record_id = record.get("record_id")
        if not record_id or record_id in seen:
            raise ValueError("missing or duplicate native compound record ID")
        seen.add(record_id)
        molecule_id = record.get("molecule_chembl_id")
        if not isinstance(molecule_id, str) or not re.fullmatch(r"CHEMBL[1-9][0-9]*", molecule_id):
            raise ValueError("compound record has no native molecule ID")
        rows.append({"schema_version": "praxis.paper-compound-map.v1", "mapping_id": f"chembl-compound-record:{record_id}",
                     "doi": normalized, "document_id": document_id, "native_record_id": record_id,
                     "compound_key": record.get("compound_key"), "compound_name": record.get("compound_name"),
                     "molecule_chembl_id": molecule_id, "src_id": record.get("src_id"),
                     "src_compound_id": record.get("src_compound_id"),
                     "source": {**source, "pointer": f"/compound_records/{index}"}, "document_source": source_document,
                     "mapping_scope": "source_paper_chemical_identifier_to_database_molecule",
                     "review_status": "needs_review", "structure_and_tested_form_confirmed": False,
                     "protein_binding_supported": False, "inference_eligible": False})
    path = output / "compound_bindings.jsonl"
    if path.exists() and path.read_bytes() != "".join(_json(row) + "\n" for row in rows).encode():
        raise ValueError("compound binding snapshot cannot overwrite existing different mappings")
    _write_jsonl(path, rows)
    summary = {"document_id": document_id, "doi": normalized, "mapping_path": str(path),
               "record_count": len(rows), "source_total_count": page["total_count"],
               "complete_for_document": not page.get("next") and len(rows) == page["total_count"],
               "next_page": page.get("next"), "source": source, "document_source": source_document,
               "gold_count": 0, "scope": "chemical-number mapping only; mechanism linkage requires source review"}
    summary_path = output / "compound_bindings.summary.json"
    content = (_json(summary) + "\n").encode()
    if not summary_path.exists() or summary_path.read_bytes() != content:
        summary_path.write_bytes(content)
    return summary
