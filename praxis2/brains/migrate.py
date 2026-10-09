"""Load brain document trees and bootstrap the VirtualCell brain."""

from pathlib import Path

from praxis2.brains.store import BrainDoc


DISCIPLINE_SLUGS: list[str] = [
    "virtualcell",
]


THREE_LAYER_DIRS = ("cases", "neg_cases", "rules", "skills")


_SLUG_CASE_HINTS: dict[str, str] = {
    "virtualcell": (
        'virtualcell perturbation knockout transcriptome '
        'growth essentiality cross-species abstain predic'
        'tion workflow'
    ),
}


def build_fixture_brain(slug: str) -> list[BrainDoc]:

    if slug == "_common":
        return [
            BrainDoc(slug, "rules", "rmcp",
                     (
                         'RMCP rule: retrieve evidence, reverse-filter, pl'
                         'an, then execute. List sources, require DOI cita'
                         'tions, and prefer database APIs.'
                     )),
            BrainDoc(slug, "rules", "safety",
                     "Safety rule: do not invent DOI citations; require agreement from two of three tools"),
        ]


    hint = _SLUG_CASE_HINTS.get(slug.lower(), "Standard workflow and evidence")
    return [
        BrainDoc(slug, "cases", "c1",
                 f"{slug}positive domain case:{hint}(doi:10.0/{slug})"),
        BrainDoc(slug, "neg_cases", "NEG-1",
                 f"{slug}negative case: common misuse and exclusion methods"),
        BrainDoc(slug, "rules", "r1",
                 f"{slug}domain rule: methodological constraints"),
        BrainDoc(slug, "skills", "wf1",
                 f"{slug}skill wf1: reusable workflow"),
    ]


def migrate_dir_tree(root: Path, slug: str) -> list[BrainDoc]:

    root = Path(root)
    out: list[BrainDoc] = []
    for kind in ("cases", "neg_cases", "rules"):
        if kind == "cases":
            base, pat = root / "memory" / "cases", "*.md"
        elif kind == "neg_cases":
            base, pat = root / "memory" / "cases" / "_neg", "NEG-*.md"
        else:
            base, pat = root / "memory" / "rules", "*.md"
        if not base.is_dir():
            continue
        for f in sorted(base.glob(pat)):
            if f.name.startswith("._"):
                continue
            if kind == "cases" and f.stem.startswith("_"):
                continue
            out.append(BrainDoc(slug, kind, f.stem, f.read_text()))
    wf = root / "skills" / "workflows"
    if wf.is_dir():
        for d in sorted(p for p in wf.iterdir() if p.is_dir()):
            if d.name.startswith("._"):
                continue
            sk = d / "SKILL.md"
            text = sk.read_text() if sk.is_file() else d.name
            out.append(BrainDoc(slug, "skills", d.name, text))
    return out
