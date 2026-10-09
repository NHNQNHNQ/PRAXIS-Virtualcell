"""Tests for species module guards."""
import pytest

from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.biological_modules.registry import ModuleRegistry

reg = ModuleRegistry()


_MISMATCH = [
    ("bacteria", "bacteria_autophagy", "caution"),
    ("bacteria", "mitochondria", "caution"),
    ("yeast", "tissue_spatial_niche", "reject"),
    ("yeast", "mammalian_cell_communication", "reject"),
]


@pytest.mark.parametrize("species,query,verdict", _MISMATCH,
                         ids=[f"{s}_{q}" for s, q, _ in _MISMATCH])
def test_biological_mismatch_verdict(species, query, verdict):
    assert reg.biological_mismatch(species, query) == verdict


def test_weak_modules_never_silently_accept():
    """Verify weak modules never silently accept."""
    offenders = []
    for sp in ("human", "mouse", "yeast", "bacteria"):
        for mid in M.MODULE_ORDER:
            rec = reg.support(sp, mid)
            if rec["support"] == "weak" and reg.default_verdict(sp, mid) == "accept":
                offenders.append(f"{sp}/{mid}")
    assert offenders == [], f"Weakly supported modules were silently accepted:  {offenders}"


def test_unsupported_modules_reject():
    """Verify unsupported modules reject."""
    for sp in ("human", "mouse", "yeast", "bacteria"):
        for mid in M.MODULE_ORDER:
            if reg.support(sp, mid)["support"] == "unsupported":
                assert reg.default_verdict(sp, mid) == "reject"


def test_bacteria_m3_not_called_mitochondria_in_display():
    """Verify bacteria m3 not called mitochondria in display."""
    name = reg.display_name("bacteria", "mitochondrial_energy_metabolism")
    assert "Mitochond" not in name
