"""Mechanistic sidecar interfaces with explicit, on-demand import boundaries.

Only the bounded GEM/FBA sidecar is reachable from the current MDR activity
path.  The remaining VirtualCell-inspired state, intervention, and
falsifiability helpers stay available for direct experiments, but importing this
package must not make them appear to be production-wired.
"""
from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .cell_state import BacterialCellState
    from .falsifiability import run_ablation, run_intervention_consistency
    from .gem_fba import GemFbaPredictor
    from .intervention import simulate_intervention
    from .mechanism_state_model import MechanismStateModel


_LAZY_EXPORTS = {
    "BacterialCellState": (".cell_state", "BacterialCellState"),
    "GemFbaPredictor": (".gem_fba", "GemFbaPredictor"),
    "MechanismStateModel": (".mechanism_state_model", "MechanismStateModel"),
    "simulate_intervention": (".intervention", "simulate_intervention"),
    "run_ablation": (".falsifiability", "run_ablation"),
    "run_intervention_consistency": (".falsifiability", "run_intervention_consistency"),
}

__all__ = list(_LAZY_EXPORTS)


def __getattr__(name: str) -> Any:
    """Resolve stable public helpers without package-level eager side effects."""
    try:
        module_name, attribute_name = _LAZY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        ) from exc
    value = getattr(import_module(module_name, __name__), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
