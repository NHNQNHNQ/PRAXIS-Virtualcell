"""化合物标识符 → canonical SMILES 解析(线B B2 输入层)。

支持输入:裸 SMILES(本地 RDKit canonical,**不联网**)/ PubChem CID / 化合物名 /
ChEMBL ID / DrugBank ID(后四者经 PubChem PUG-REST 公开 API,无需 key,取 SMILES 再 RDKit 规范化)。

诚实边界(红线:不伪造):无网/超时/查不到/RDKit 解析失败 → ok=False + reason,**绝不编造 SMILES**。
rdkit 与网络均惰性调用:import 本模块不联网、不 import rdkit(53 无 rdkit 也能 import,只在真解析时才需)。

resolve 结果:
  {"ok": True,  "smiles": <canonical>, "input_kind": <kind>, "source": "rdkit_local"|"pubchem"}
  {"ok": False, "reason": <code>, "input_kind": <kind>}   # code ∈ network_error/not_found/rdkit_parse_failed
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable
from urllib.parse import quote

_PUBCHEM = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound"
# PubChem 2025 起 SMILES 属性名为 SMILES(旧 CanonicalSMILES/IsomericSMILES 已弃用)
_SMILES_PROP = "SMILES"

_CHEMBL_RE = re.compile(r"^CHEMBL\d+$", re.IGNORECASE)
_DRUGBANK_RE = re.compile(r"^DB\d+$", re.IGNORECASE)
_CID_RE = re.compile(r"^\d+$")


def classify_identifier(identifier: str) -> str:
    """标识符归类:chembl_id / drugbank_id / pubchem_cid / smiles / name。

    先按 ID 正则(不需 rdkit),再试 RDKit SMILES 解析(合法→smiles),否则当 name。
    rdkit 缺失时无法判 smiles,回退 name(交 PubChem 解析)。
    """
    s = (identifier or "").strip()
    if _CHEMBL_RE.match(s):
        return "chembl_id"
    if _DRUGBANK_RE.match(s):
        return "drugbank_id"
    if _CID_RE.match(s):
        return "pubchem_cid"
    if _is_valid_smiles_quiet(s):     # 静默探测:名称探 SMILES 会失败,不刷 RDKit stderr
        return "smiles"
    return "name"


def _is_valid_smiles_quiet(smiles: str) -> bool:
    """探测是否合法**非空** SMILES,静默 RDKit 日志(classify 探名称必失败,不该刷屏)。

    空/空白串:MolFromSmiles("") 返合法空 mol,但空串不是化合物 → 判 False(不当 smiles)。
    """
    if not (smiles or "").strip():
        return False
    return _rdkit_canonical(smiles) is not None


def _rdkit_canonical(smiles: str):
    """RDKit 规范化 SMILES → canonical;非法/空/rdkit 缺失 → None(惰性 import,静默日志,不崩)。"""
    if not (smiles or "").strip():        # 空/空白/None:不是化合物,不伪造空 SMILES
        return None
    try:
        from rdkit import Chem, RDLogger
    except ImportError:
        return None
    RDLogger.DisableLog("rdApp.*")        # 非法 SMILES 的解析错误由返回值表达,不刷 stderr
    try:
        m = Chem.MolFromSmiles(smiles)
    finally:
        RDLogger.EnableLog("rdApp.*")
    if m is None:
        return None
    canon = Chem.MolToSmiles(m)
    return canon or None                  # 空 mol 规范化为空串 → 视作无效(不伪造)


def _default_http_get(url: str, timeout: float) -> tuple[int, str]:
    """默认 HTTP GET:返回 (status_code, body_text)。传输层异常 → 抛(由 resolve 兜成 network_error)。"""
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return (r.status, r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:      # 4xx/5xx:有状态码,非传输失败
        return (e.code, "")


def _extract_smiles(body: str) -> str | None:
    """从 PubChem property JSON 抽 SMILES;结构不符/无值 → None。"""
    try:
        d = json.loads(body)
        props = d["PropertyTable"]["Properties"]
        if not props:
            return None
        smi = props[0].get(_SMILES_PROP)
        return smi or None
    except (json.JSONDecodeError, KeyError, TypeError, IndexError):
        return None


def _pubchem_url(kind: str, identifier: str) -> str:
    """按 kind 拼 PubChem property URL。CID 走 /cid/;名称/ChEMBL/DrugBank 走 /name/(PubChem 索引其同义词)。"""
    ident = quote(identifier.strip(), safe="")
    domain = "cid" if kind == "pubchem_cid" else "name"
    return f"{_PUBCHEM}/{domain}/{ident}/property/{_SMILES_PROP}/JSON"


def resolve_compound(identifier: str,
                     *, http_get: Callable[[str, float], tuple[int, str]] | None = None,
                     timeout: float = 10.0) -> dict[str, Any]:
    """标识符 → canonical SMILES。裸 SMILES 本地规范化(不联网);其余经 PubChem。

    http_get 可注入(测试用假实现,不真联网);默认用 urllib。失败一律诚实报错不伪造。
    """
    if not identifier or not str(identifier).strip():     # 空/None/空白:不是标识符,诚实报错不伪造
        return {"ok": False, "reason": "empty_identifier", "input_kind": "empty"}
    kind = classify_identifier(identifier)

    if kind == "smiles":                     # 本地规范化,不联网
        canon = _rdkit_canonical(identifier)
        if canon is None:
            return {"ok": False, "reason": "rdkit_parse_failed", "input_kind": kind}
        return {"ok": True, "smiles": canon, "input_kind": kind, "source": "rdkit_local"}

    get = http_get or _default_http_get
    url = _pubchem_url(kind, identifier)
    try:
        status, body = get(url, timeout)
    except Exception:                        # 传输失败/超时 → 诚实报网络错,不伪造
        return {"ok": False, "reason": "network_error", "input_kind": kind}
    if status != 200:
        return {"ok": False, "reason": "not_found", "input_kind": kind}
    smi = _extract_smiles(body)
    if smi is None:
        return {"ok": False, "reason": "not_found", "input_kind": kind}
    canon = _rdkit_canonical(smi)            # PubChem SMILES 再经 RDKit 规范化(对齐模型 canonical 口径)
    if canon is None:
        return {"ok": False, "reason": "rdkit_parse_failed", "input_kind": kind}
    return {"ok": True, "smiles": canon, "input_kind": kind, "source": "pubchem"}
