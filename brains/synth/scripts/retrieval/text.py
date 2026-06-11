"""BM25 over case markdown files.

Index: each case file is one document (frontmatter included).
Query: free-text string is tokenized and ranked against the BM25 index.
"""

from __future__ import annotations

import re
from pathlib import Path

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^\w\s\-/]", " ", text)
    return [t for t in text.split() if len(t) > 1]


class CaseTextIndex:
    """Tiny BM25 index over case markdown files.

    Built lazily on init by reading every *.md (excluding underscore-prefixed
    template files) under the cases directory.
    """

    def __init__(self, cases_dir: Path):
        if BM25Okapi is None:
            raise RuntimeError("rank_bm25 not installed; pip install rank-bm25")
        self.cases_dir = Path(cases_dir)
        self.case_ids: list[str] = []
        self.docs: list[list[str]] = []
        if not self.cases_dir.exists():
            self.bm25 = None
            return
        for path in sorted(self.cases_dir.glob("*.md")):
            if path.name.startswith("_") or path.name.startswith("."):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue   # skip macOS metadata files (._*) and other binaries
            self.case_ids.append(path.stem)
            self.docs.append(_tokenize(text))
        self.bm25 = BM25Okapi(self.docs) if self.docs else None

    def query(self, text: str, top_k: int = 10) -> list[tuple[str, float]]:
        if not self.bm25 or not text:
            return []
        scores = self.bm25.get_scores(_tokenize(text))
        ranked = sorted(zip(self.case_ids, scores), key=lambda x: -x[1])
        return [(cid, float(s)) for cid, s in ranked[:top_k] if s > 0]

    def __len__(self) -> int:
        return len(self.case_ids)


if __name__ == "__main__":
    import sys
    cases_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "memory/cases")
    idx = CaseTextIndex(cases_dir)
    print(f"Indexed {len(idx)} cases from {cases_dir}")
    if len(idx) == 0:
        sys.exit(0)
    for q in ["disulfide xylanase thermostability", "SCHEMA recombination cellulase", "LPMO copper"]:
        print(f"\nQuery: {q!r}")
        for cid, score in idx.query(q, top_k=3):
            print(f"  {cid:50}  {score:.3f}")
